from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from asset_app import db
import pytz

def now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='User')  # Admin, Manager, User, Read-only
    created_at = db.Column(db.DateTime, default=now_ist)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    assigned_assets = db.relationship('Asset', backref='owner_user', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    movement_logs = db.relationship(
        'MovementLog',
        foreign_keys='MovementLog.user_id',
        backref='user', lazy='dynamic'
    )
    outgoing_movements = db.relationship(
        'MovementLog',
        foreign_keys='MovementLog.from_user_id',
        backref='from_user_obj', lazy='dynamic'
    )
    incoming_movements = db.relationship(
        'MovementLog',
        foreign_keys='MovementLog.to_user_id',
        backref='to_user_obj', lazy='dynamic'
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, action):
        permissions = {
            'Admin': ['create', 'read', 'update', 'delete', 'bulk_import', 'user_management'],
            'Manager': ['create', 'read', 'update', 'delete', 'bulk_import'],
            'User': ['read', 'update', 'checkout', 'checkin'],
            'Read-only': ['read']
        }
        return action in permissions.get(self.role, [])
    
    def __repr__(self):
        return f'<User {self.email}>'

class Asset(db.Model):
    __tablename__ = 'assets'
    
    # Primary identifiers
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(100), nullable=False, index=True)
    invoice_date = db.Column(db.Date)
    serial_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    purchase_order_no = db.Column(db.String(100))
    received_date = db.Column(db.Date)
    
    # Owner and description
    owner_email = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    
    # Product details
    manufacturer = db.Column(db.String(100), index=True)
    model = db.Column(db.String(100))
    vendor = db.Column(db.String(100), index=True)
    mfg_country = db.Column(db.String(50))
    hsn_code = db.Column(db.String(20))
    
    # Bonding and compliance
    is_bonded = db.Column(db.String(10))  # 'yes', 'no', 'na'
    
    # Calibration
    last_calibrated = db.Column(db.Date)
    next_calibration = db.Column(db.Date)
    
    # Additional info
    notes = db.Column(db.Text)
    entry_no = db.Column(db.String(100))
    returnable = db.Column(db.String(10))  # 'yes', 'no', 'na'
    
    # Capital expenditure
    cap_x = db.Column(db.String(10))  # 'yes', 'no', 'na'
    amortization_period = db.Column(db.String(100))  # Only if cap_x is 'yes'
    
    # System fields
    created_at = db.Column(db.DateTime, default=now_ist)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)
    status = db.Column(db.String(50), nullable=False, default='Active', index=True)  # Active, Inactive, Disposed
    
    # Future dynamic fields (will be implemented later)
    team = db.Column(db.String(100))
    recipient_name = db.Column(db.String(100))
    recipient_email = db.Column(db.String(120))
    category = db.Column(db.String(100))
    sub_category = db.Column(db.String(100))
    location = db.Column(db.String(200))
    
    # Relationships
    movement_logs = db.relationship('MovementLog', backref='asset', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='asset', lazy='dynamic', cascade='all, delete-orphan')
    
    def is_calibration_due(self, days_ahead=30):
        """Check if calibration is due within specified days"""
        if not self.next_calibration:
            return False
        from datetime import date, timedelta
        return self.next_calibration <= date.today() + timedelta(days=days_ahead)
    
    def calibration_status(self):
        """Get calibration status"""
        if not self.next_calibration:
            return 'Not Scheduled'
        from datetime import date
        if self.next_calibration < date.today():
            return 'Overdue'
        elif self.is_calibration_due(30):
            return 'Due Soon'
        else:
            return 'Current'
    
    def __repr__(self):
        return f'<Asset {self.serial_number}: {self.description[:50]}>'

class MovementLog(db.Model):
    __tablename__ = 'movement_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    action = db.Column(db.String(50), nullable=False)  # create, update, transfer, dispose, calibrate
    from_location = db.Column(db.String(200))
    to_location = db.Column(db.String(200))
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    timestamp = db.Column(db.DateTime, default=now_ist, index=True)
    notes = db.Column(db.Text)
    
    # Relationships for from/to users
    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])
    
    def __repr__(self):
        return f'<MovementLog {self.action} for Asset {self.asset_id}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, login, logout, etc.
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    
    old_values = db.Column(db.Text)  # JSON string of old values
    new_values = db.Column(db.Text)  # JSON string of new values
    
    timestamp = db.Column(db.DateTime, default=now_ist, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id}>'

# Utility function to log audit events
def log_audit_event(user_id, action, table_name=None, record_id=None, old_values=None, new_values=None, asset_id=None):
    import json
    from flask import request
    
    audit_log = AuditLog(
        user_id=user_id,
        asset_id=asset_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        ip_address=request.remote_addr if request else None,
        user_agent=request.headers.get('User-Agent') if request else None
    )
    
    db.session.add(audit_log)
    db.session.commit()