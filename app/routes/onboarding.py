"""Onboarding blueprint — plan selection and initial payment."""
from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.services.subscription_service import (
    PLAN_LIMITS,
    PLAN_ORDER,
    apply_plan_limits,
    ensure_owner_subscription,
    get_owner_subscription,
)
from app.utils.decorators import restaurant_required, role_required

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/onboarding')


# ──────────────────────────────────────────────
# Plan Selection
# ──────────────────────────────────────────────

@onboarding_bp.route('/plans', methods=['GET'])
@login_required
@role_required('owner')
@restaurant_required
def plans():
    """Display plan selection page."""
    restaurant = g.restaurant
    sub = get_owner_subscription(current_user)
    
    # Prevent accessing plan selection if payment is already completed
    if sub and sub.payment_completed:
        return redirect(url_for('dashboard.overview'))
    
    current_plan = sub.plan if sub and sub.plan in PLAN_ORDER else 'free'
    
    return render_template(
        'onboarding/plans.html',
        restaurant=restaurant,
        subscription=sub,
        current_plan=current_plan,
        plan_limits=PLAN_LIMITS,
        plan_order=PLAN_ORDER,
    )


@onboarding_bp.route('/plans/select', methods=['POST'])
@login_required
@role_required('owner')
@restaurant_required
def select_plan():
    """Handle plan selection."""
    restaurant = g.restaurant
    plan = request.form.get('plan', '').strip()
    
    if plan not in PLAN_LIMITS:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('onboarding.plans'))
    
    sub = get_owner_subscription(current_user)
    
    # Prevent changing plan after payment is completed
    if sub and sub.payment_completed:
        flash('Your plan is already active. Cannot change plan now.', 'error')
        return redirect(url_for('dashboard.overview'))
    
    if not sub:
        sub = ensure_owner_subscription(current_user, restaurant=restaurant)
    
    now = datetime.now(timezone.utc)
    apply_plan_limits(sub, plan)
    sub.is_active = True
    sub.started_at = now
    
    if plan == 'free':
        sub.expires_at = None
        # Free plan doesn't need payment
        sub.payment_completed = True
        db.session.commit()
        flash('Welcome! You\'re all set with the free plan.', 'success')
        return redirect(url_for('dashboard.overview'))
    else:
        # Paid plans require payment
        # Ensure expires_at is timezone-aware for comparison
        current_expires = sub.expires_at
        if current_expires and current_expires.tzinfo is None:
            current_expires = current_expires.replace(tzinfo=timezone.utc)
        
        if not current_expires or current_expires <= now:
            sub.expires_at = now + timedelta(days=30)
        db.session.commit()
        flash(f'Great choice! Now let\'s complete your {plan.title()} plan payment.', 'info')
        return redirect(url_for('onboarding.payment'))


# ──────────────────────────────────────────────
# Payment Processing
# ──────────────────────────────────────────────

@onboarding_bp.route('/payment', methods=['GET'])
@login_required
@role_required('owner')
@restaurant_required
def payment():
    """Display payment page."""
    restaurant = g.restaurant
    sub = get_owner_subscription(current_user)
    
    if not sub or sub.payment_completed:
        return redirect(url_for('dashboard.overview'))
    
    if sub.plan == 'free':
        return redirect(url_for('dashboard.overview'))
    
    plan_price = PLAN_LIMITS.get(sub.plan, {}).get('price', 0)
    
    return render_template(
        'onboarding/payment.html',
        restaurant=restaurant,
        subscription=sub,
        plan_price=plan_price,
    )


@onboarding_bp.route('/payment/process', methods=['POST'])
@login_required
@role_required('owner')
@restaurant_required
def process_payment():
    """Process payment (mock or real payment integration)."""
    restaurant = g.restaurant
    sub = get_owner_subscription(current_user)
    
    if not sub or sub.payment_completed or sub.plan == 'free':
        flash('Invalid payment request.', 'error')
        return redirect(url_for('dashboard.overview'))
    
    # For now, simulate payment processing
    # In production, integrate with Flouci or another payment gateway
    payment_method = request.form.get('payment_method', 'card')
    
    # Mock payment validation
    if payment_method not in ('card', 'bank_transfer', 'cash'):
        flash('Invalid payment method.', 'error')
        return redirect(url_for('onboarding.payment'))
    
    # Mark payment as completed
    sub.payment_completed = True
    db.session.commit()
    
    flash(f'Payment successful! Your {sub.plan.title()} plan is now active.', 'success')
    return redirect(url_for('onboarding.confirmation'))


@onboarding_bp.route('/confirmation', methods=['GET'])
@login_required
@role_required('owner')
@restaurant_required
def confirmation():
    """Display payment confirmation."""
    restaurant = g.restaurant
    sub = get_owner_subscription(current_user)
    
    if not sub or not sub.payment_completed:
        return redirect(url_for('onboarding.plans'))
    
    return render_template(
        'onboarding/confirmation.html',
        restaurant=restaurant,
        subscription=sub,
    )


@onboarding_bp.route('/skip', methods=['POST'])
@login_required
@role_required('owner')
@restaurant_required
def skip_upgrade():
    """Skip to free plan and proceed to dashboard."""
    restaurant = g.restaurant
    sub = get_owner_subscription(current_user)
    
    if not sub:
        sub = ensure_owner_subscription(current_user, restaurant=restaurant)
    
    if sub.plan != 'free':
        apply_plan_limits(sub, 'free')
        sub.expires_at = None
    
    sub.payment_completed = True
    db.session.commit()
    
    flash('You\'re all set! Starting with the free plan.', 'info')
    return redirect(url_for('dashboard.overview'))
