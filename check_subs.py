from app import db, create_app
from app.models.restaurant import Subscription, Restaurant

app = create_app()
with app.app_context():
    subs = Subscription.query.all()
    print(f'Total subscriptions: {len(subs)}')
    for sub in subs:
        rest = Restaurant.query.get(sub.restaurant_id)
        name = rest.name if rest else 'N/A'
        print(f'Restaurant: {name}, Plan: {sub.plan}, Payment: {sub.payment_completed}')
