"""Blueprint registration utility."""


def register_blueprints(app):
    """Register all application blueprints."""
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.customer import customer_bp
    app.register_blueprint(customer_bp)

    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    # Future blueprints will be registered here in later phases
