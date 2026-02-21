"""Waiter blueprint — table overview, waiter calls, serve orders."""
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, render_template
from flask_login import current_user, login_required

from app import db
from app.models.order import WaiterCall
from app.models.table import Table
from app.services.order_service import update_order_status
from app.utils.decorators import restaurant_required, role_required

waiter_bp = Blueprint('waiter', __name__, url_prefix='/waiter')


@waiter_bp.route('/tables')
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def tables():
    """Show tables assigned to the current waiter."""
    restaurant = g.restaurant

    # Owners see all tables; waiters see only their assigned tables
    if current_user.role == 'owner':
        assigned = Table.query.filter_by(
            restaurant_id=restaurant.id
        ).order_by(Table.table_number).all()
    else:
        assigned = Table.query.filter_by(
            restaurant_id=restaurant.id,
            assigned_waiter_id=current_user.id,
        ).order_by(Table.table_number).all()

    # Pending call count per table
    call_counts: dict[int, int] = {}
    if assigned:
        table_ids = [t.id for t in assigned]
        calls = WaiterCall.query.filter(
            WaiterCall.table_id.in_(table_ids),
            WaiterCall.status == 'pending',
        ).all()
        for c in calls:
            call_counts[c.table_id] = call_counts.get(c.table_id, 0) + 1

    return render_template(
        'waiter/tables.html',
        restaurant=restaurant,
        tables=assigned,
        call_counts=call_counts,
    )


@waiter_bp.route('/calls')
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def calls():
    """Return pending WaiterCall records as JSON."""
    restaurant = g.restaurant
    pending = WaiterCall.query.filter_by(
        restaurant_id=restaurant.id, status='pending'
    ).order_by(WaiterCall.created_at.asc()).all()

    return jsonify(calls=[
        {
            'id': c.id,
            'table_id': c.table_id,
            'call_type': c.call_type,
            'message': c.message,
            'created_at': c.created_at.isoformat(),
        }
        for c in pending
    ])


@waiter_bp.route('/calls/<int:id>/resolve', methods=['POST'])
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def resolve_call(id):
    """Mark a waiter call as resolved. Returns JSON."""
    restaurant = g.restaurant
    call = WaiterCall.query.filter_by(
        id=id, restaurant_id=restaurant.id
    ).first_or_404()

    call.status = 'resolved'
    call.resolved_at = datetime.now(timezone.utc)
    call.resolved_by = current_user.id
    db.session.commit()

    return jsonify(success=True, call_id=id)


@waiter_bp.route('/orders/<int:id>/served', methods=['POST'])
@login_required
@restaurant_required
@role_required('waiter', 'owner')
def mark_served(id):
    """Advance order to 'served'. Returns JSON."""
    ok, msg = update_order_status(id, 'served', g.restaurant.id)
    if not ok:
        return jsonify(success=False, error=msg), 400
    return jsonify(success=True, order_id=id, new_status='served')
