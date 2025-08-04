from .auth import auth_bp
from .inventory import inventory_bp
from .api import api_bp

__all__ = ['auth_bp', 'inventory_bp', 'api_bp']