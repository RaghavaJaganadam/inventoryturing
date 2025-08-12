from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from asset_config import config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from asset_app.routes import auth_bp, asset_bp, api_bp
    from asset_app.routes.bulk import bulk_bp
    from asset_app.routes.analytics import analytics_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(asset_bp, url_prefix='/')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(bulk_bp, url_prefix='/bulk')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        from asset_app.models import User
        admin_user = User.query.filter_by(email='admin@company.com').first()
        if not admin_user:
            admin_user = User(
                name='Asset Administrator',
                email='admin@company.com',
                role='Admin'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
    
    return app