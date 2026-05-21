from app import db, create_app
from app.models.restaurant import Subscription

app = create_app()
with app.app_context():
    subs = Subscription.query.all()
    print(f'Total subscriptions: {len(subs)}')
    for sub in subs:
        owner = sub.owner
        name = owner.email if owner else 'N/A'
        print(
            f'Owner: {name}, Plan: {sub.plan}, '
            f'Locations: {sub.max_locations}, Payment: {sub.payment_completed}'
        )
