"""Blueprint registration utility."""


def register_blueprints(app):
    """Register all application blueprints."""
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.customer import customer_bp
    app.register_blueprint(customer_bp)

    # Future blueprints will be registered here in later phases
