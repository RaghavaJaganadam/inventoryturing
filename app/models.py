from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# class User(UserMixin, db.Model):
#     __tablename__ = 'users'
    
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     email = db.Column(db.String(120), unique=True, nullable=False, index=True)
#     password_hash = db.Column(db.String(128), nullable=False)
#     role = db.Column(db.String(20), nullable=False, default='Researcher')  # Admin, Lab Staff, Researcher, Read-only
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     is_active = db.Column(db.Boolean, default=True)
    
#     # Relationships
#     assigned_equipment = db.relationship('Equipment', backref='assignee', lazy='dynamic')
#     audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
#     movement_logs = db.relationship('MovementLog', backref='user', lazy='dynamic')
    
#     def set_password(self, password):
#         self.password_hash = generate_password_hash(password)
    
#     def check_password(self, password):
#         return check_password_hash(self.password_hash, password)
    
#     def has_permission(self, action):
#         permissions = {
#             'Admin': ['create', 'read', 'update', 'delete', 'bulk_import', 'user_management'],
#             'Lab Staff': ['create', 'read', 'update', 'delete', 'bulk_import'],
#             'Researcher': ['read', 'update', 'checkout', 'checkin'],
#             'Read-only': ['read']
#         }
#         return action in permissions.get(self.role, [])
    
#     def __repr__(self):
#         return f'<User {self.email}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Researcher')  # Admin, Lab Staff, Researcher, Read-only
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    assigned_equipment = db.relationship('Equipment', backref='assignee', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    # Distinct movement logs
    # All logs where this user performed the action
    movement_logs = db.relationship(
        'MovementLog',
        foreign_keys='MovementLog.user_id',
        backref='user', lazy='dynamic'
    )
    # All logs where this user is the "from_user" (e.g., transferred FROM)
    outgoing_movements = db.relationship(
        'MovementLog',
        foreign_keys='MovementLog.from_user_id',
        backref='from_user_obj', lazy='dynamic'
    )
    # All logs where this user is the "to_user" (e.g., transferred TO)
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
            'Lab Staff': ['create', 'read', 'update', 'delete', 'bulk_import'],
            'Researcher': ['read', 'update', 'checkout', 'checkin'],
            'Read-only': ['read']
        }
        return action in permissions.get(self.role, [])
    
    def __repr__(self):
        return f'<User {self.email}>'


class Equipment(db.Model):
    __tablename__ = 'equipment'
    
    # Primary identifiers
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Categorization
    category = db.Column(db.String(100), nullable=False, index=True)
    model_number = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100), index=True)
    serial_number = db.Column(db.String(100))
    
    # Dates
    procurement_date = db.Column(db.Date)
    warranty_expiry = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status and condition
    status = db.Column(db.String(50), nullable=False, default='Available', index=True)  # Available, In Use, Under Maintenance, Retired, Missing
    condition = db.Column(db.String(50), nullable=False, default='Good')  # New, Good, Needs Repair, Obsolete
    
    # Chip-specific fields (nullable for non-chip equipment)
    chip_type = db.Column(db.String(50))  # FPGA, ASIC, ARM, etc.
    package_type = db.Column(db.String(50))  # BGA, QFN, DIP, etc.
    pin_count = db.Column(db.Integer)
    temperature_grade = db.Column(db.String(50))  # Commercial, Industrial, Military
    testing_status = db.Column(db.String(50))  # Untested, Passed, Failed, Rework
    revision_info = db.Column(db.String(100))
    
    # Files and documentation
    design_files = db.Column(db.Text)  # URL or file path
    
    # Location and assignment
    location = db.Column(db.String(200))  # Building / Lab Room / Cabinet / Shelf
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Additional metadata
    tags = db.Column(db.String(500))  # Comma-separated tags
    notes = db.Column(db.Text)
    
    # Cost and value (for future reporting)
    purchase_cost = db.Column(db.Numeric(10, 2))
    current_value = db.Column(db.Numeric(10, 2))
    
    # Relationships
    movement_logs = db.relationship('MovementLog', backref='equipment', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='equipment', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_tags_list(self):
        return [tag.strip() for tag in (self.tags or '').split(',') if tag.strip()]
    
    def set_tags_list(self, tags_list):
        self.tags = ', '.join(tags_list) if tags_list else ''
    
    def is_available(self):
        return self.status == 'Available'
    
    def can_be_assigned(self):
        return self.status in ['Available', 'In Use']
    
    def __repr__(self):
        return f'<Equipment {self.asset_tag}: {self.name}>'

class MovementLog(db.Model):
    __tablename__ = 'movement_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    action = db.Column(db.String(50), nullable=False)  # checkout, checkin, move, assign, unassign
    from_location = db.Column(db.String(200))
    to_location = db.Column(db.String(200))
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    notes = db.Column(db.Text)
    
    # Relationships for from/to users
    from_user = db.relationship('User', foreign_keys=[from_user_id])
    to_user = db.relationship('User', foreign_keys=[to_user_id])
    
    def __repr__(self):
        return f'<MovementLog {self.action} for Equipment {self.equipment_id}>'




class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=True)
    
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, login, logout, etc.
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    
    old_values = db.Column(db.Text)  # JSON string of old values
    new_values = db.Column(db.Text)  # JSON string of new values
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id}>'

# Utility function to log audit events
def log_audit_event(user_id, action, table_name=None, record_id=None, old_values=None, new_values=None, equipment_id=None):
    import json
    from flask import request
    
    audit_log = AuditLog(
        user_id=user_id,
        equipment_id=equipment_id,
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