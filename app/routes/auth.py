from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
# from werkzeug.urls import url_parse
from urllib.parse import urlparse as url_parse
from app import db, login_manager
from app.models import User, log_audit_event

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('inventory.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            log_audit_event(user.id, 'login')
            
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('inventory.index')
            
            if request.headers.get('HX-Request'):
                return '', 200, {'HX-Redirect': next_page}
            return redirect(next_page)
        else:
            flash('Invalid email or password', 'error')
            if request.headers.get('HX-Request'):
                return render_template('auth/login_form.html', error='Invalid email or password'), 400
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit_event(current_user.id, 'logout')
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.has_permission('user_management'):
        flash('You do not have permission to register new users', 'error')
        return redirect(url_for('inventory.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Researcher')
        
        # Validate input
        if not all([name, email, password]):
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        user = User(name=name, email=email, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        log_audit_event(current_user.id, 'create_user', 'users', user.id, None, {
            'name': name, 'email': email, 'role': role
        })
        
        flash(f'User {name} created successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return render_template('auth/register_success.html', user=user)
        return redirect(url_for('inventory.index'))
    
    return render_template('auth/register.html')