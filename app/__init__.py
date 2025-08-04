from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

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
    from app.routes import auth_bp, inventory_bp, api_bp
    from app.routes.bulk import bulk_bp
    from app.routes.analytics import analytics_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(bulk_bp, url_prefix='/bulk')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        from app.models import User
        admin_user = User.query.filter_by(email='admin@lab.com').first()
        if not admin_user:
            admin_user = User(
                name='Lab Administrator',
                email='admin@lab.com',
                role='Admin'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
    
    return app