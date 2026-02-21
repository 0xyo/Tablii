"""Blueprint registration utility."""


def register_blueprints(app):
    """Register all application blueprints."""
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.customer import customer_bp
    app.register_blueprint(customer_bp)

    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.routes.cashier import cashier_bp
    app.register_blueprint(cashier_bp)

    from app.routes.kitchen import kitchen_bp
    app.register_blueprint(kitchen_bp)

    from app.routes.waiter import waiter_bp
    app.register_blueprint(waiter_bp)
