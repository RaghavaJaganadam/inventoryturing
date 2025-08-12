from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, desc
from datetime import datetime, date
from asset_app import db
from asset_app.models import Asset, User, MovementLog, log_audit_event
import json
import pytz

def now_ist():
    return datetime.now(pytz.timezone('Asia/Kolkata'))

asset_bp = Blueprint('assets', __name__)

@asset_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    # Build query with filters
    query = Asset.query
    
    # Search functionality
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(or_(
            Asset.serial_number.contains(search),
            Asset.invoice_no.contains(search),
            Asset.description.contains(search),
            Asset.manufacturer.contains(search),
            Asset.model.contains(search),
            Asset.vendor.contains(search),
            Asset.owner_email.contains(search)
        ))
    
    # Filter by status
    status_filter = request.args.get('status')
    if status_filter and status_filter != 'all':
        query = query.filter(Asset.status == status_filter)
    
    # Filter by manufacturer
    manufacturer_filter = request.args.get('manufacturer')
    if manufacturer_filter and manufacturer_filter != 'all':
        query = query.filter(Asset.manufacturer == manufacturer_filter)
    
    # Filter by calibration status
    calibration_filter = request.args.get('calibration')
    if calibration_filter == 'due':
        query = query.filter(Asset.next_calibration <= date.today())
    elif calibration_filter == 'due_soon':
        from datetime import timedelta
        query = query.filter(and_(
            Asset.next_calibration > date.today(),
            Asset.next_calibration <= date.today() + timedelta(days=30)
        ))
    
    # Sort options
    sort_by = request.args.get('sort', 'serial_number')
    sort_order = request.args.get('order', 'asc')
    
    if hasattr(Asset, sort_by):
        column = getattr(Asset, sort_by)
        if sort_order == 'desc':
            query = query.order_by(desc(column))
        else:
            query = query.order_by(column)
    
    asset_list = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get filter options for dropdowns
    manufacturers = db.session.query(Asset.manufacturer.distinct()).all()
    manufacturers = [mfg[0] for mfg in manufacturers if mfg[0]]
    
    statuses = ['Active', 'Inactive', 'Disposed']
    
    if request.headers.get('HX-Request'):
        return render_template('assets/asset_table.html',
                             asset_list=asset_list,
                             current_user=current_user)
    
    return render_template('assets/index.html', 
                         asset_list=asset_list,
                         manufacturers=manufacturers,
                         statuses=statuses,
                         current_user=current_user)

@asset_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    if not current_user.has_permission('create'):
        flash('You do not have permission to add assets', 'error')
        return redirect(url_for('assets.index'))
    
    if request.method == 'POST':
        try:
            # Create new asset from form data
            asset = Asset()
            
            # Basic information
            asset.invoice_no = request.form.get('invoice_no').strip()
            asset.serial_number = request.form.get('serial_number').strip()
            asset.description = request.form.get('description').strip()
            asset.owner_email = request.form.get('owner_email').strip()
            
            # Dates
            invoice_date = request.form.get('invoice_date')
            if invoice_date:
                asset.invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d').date()
            
            received_date = request.form.get('received_date')
            if received_date:
                asset.received_date = datetime.strptime(received_date, '%Y-%m-%d').date()
            
            last_calibrated = request.form.get('last_calibrated')
            if last_calibrated:
                asset.last_calibrated = datetime.strptime(last_calibrated, '%Y-%m-%d').date()
            
            next_calibration = request.form.get('next_calibration')
            if next_calibration:
                asset.next_calibration = datetime.strptime(next_calibration, '%Y-%m-%d').date()
            
            # Product details
            asset.purchase_order_no = request.form.get('purchase_order_no', '').strip() or None
            asset.manufacturer = request.form.get('manufacturer', '').strip() or None
            asset.model = request.form.get('model', '').strip() or None
            asset.vendor = request.form.get('vendor', '').strip() or None
            asset.mfg_country = request.form.get('mfg_country', '').strip() or None
            asset.hsn_code = request.form.get('hsn_code', '').strip() or None
            
            # Dropdowns
            asset.is_bonded = request.form.get('is_bonded', 'na')
            asset.returnable = request.form.get('returnable', 'na')
            asset.cap_x = request.form.get('cap_x', 'na')
            
            # Conditional field
            if asset.cap_x == 'yes':
                asset.amortization_period = request.form.get('amortization_period', '').strip() or None
            
            # Additional info
            asset.notes = request.form.get('notes', '').strip() or None
            asset.entry_no = request.form.get('entry_no', '').strip() or None
            
            # Future dynamic fields
            asset.team = request.form.get('team', '').strip() or None
            asset.recipient_name = request.form.get('recipient_name', '').strip() or None
            asset.recipient_email = request.form.get('recipient_email', '').strip() or None
            asset.category = request.form.get('category', '').strip() or None
            asset.sub_category = request.form.get('sub_category', '').strip() or None
            asset.location = request.form.get('location', '').strip() or None
            
            # Validate required fields
            if not asset.invoice_no:
                flash('Invoice number is required', 'error')
                return render_template('assets/add.html')
            
            if not asset.serial_number:
                flash('Serial number is required', 'error')
                return render_template('assets/add.html')
            
            if not asset.description:
                flash('Description is required', 'error')
                return render_template('assets/add.html')
            
            if not asset.owner_email:
                flash('Owner email is required', 'error')
                return render_template('assets/add.html')
            
            # Check for duplicate serial number
            existing = Asset.query.filter_by(serial_number=asset.serial_number).first()
            if existing:
                flash(f'Serial number {asset.serial_number} already exists', 'error')
                return render_template('assets/add.html')
            
            db.session.add(asset)
            db.session.commit()
            
            # Log the creation
            log_audit_event(
                current_user.id, 
                'create_asset', 
                'assets', 
                asset.id,
                None,
                {
                    'serial_number': asset.serial_number,
                    'invoice_no': asset.invoice_no,
                    'description': asset.description
                },
                asset.id
            )
            
            # Create movement log
            movement = MovementLog(
                asset_id=asset.id,
                user_id=current_user.id,
                action='create',
                to_location=asset.location,
                notes=f'Asset created'
            )
            db.session.add(movement)
            db.session.commit()
            
            flash(f'Asset {asset.serial_number} added successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return '', 200, {'HX-Redirect': url_for('assets.view', id=asset.id)}
            return redirect(url_for('assets.view', id=asset.id))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding asset: {str(e)}', 'error')
    
    return render_template('assets/add.html')

@asset_bp.route('/view/<int:id>')
@login_required
def view(id):
    asset = Asset.query.get_or_404(id)
    
    # Get recent movement logs
    movements = MovementLog.query.filter_by(asset_id=id).order_by(desc(MovementLog.timestamp)).limit(10).all()
    
    return render_template('assets/view.html', asset=asset, movements=movements)

@asset_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    asset = Asset.query.get_or_404(id)
    
    if not current_user.has_permission('update'):
        flash('You do not have permission to edit assets', 'error')
        return redirect(url_for('assets.view', id=id))
    
    if request.method == 'POST':
        try:
            # Store old values for audit log
            old_values = {
                'serial_number': asset.serial_number,
                'invoice_no': asset.invoice_no,
                'description': asset.description,
                'owner_email': asset.owner_email,
                'status': asset.status
            }
            
            # Update asset from form data
            asset.invoice_no = request.form.get('invoice_no').strip()
            asset.serial_number = request.form.get('serial_number').strip()
            asset.description = request.form.get('description').strip()
            asset.owner_email = request.form.get('owner_email').strip()
            
            # Dates
            invoice_date = request.form.get('invoice_date')
            if invoice_date:
                asset.invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d').date()
            else:
                asset.invoice_date = None
            
            received_date = request.form.get('received_date')
            if received_date:
                asset.received_date = datetime.strptime(received_date, '%Y-%m-%d').date()
            else:
                asset.received_date = None
            
            last_calibrated = request.form.get('last_calibrated')
            if last_calibrated:
                asset.last_calibrated = datetime.strptime(last_calibrated, '%Y-%m-%d').date()
            else:
                asset.last_calibrated = None
            
            next_calibration = request.form.get('next_calibration')
            if next_calibration:
                asset.next_calibration = datetime.strptime(next_calibration, '%Y-%m-%d').date()
            else:
                asset.next_calibration = None
            
            # Product details
            asset.purchase_order_no = request.form.get('purchase_order_no', '').strip() or None
            asset.manufacturer = request.form.get('manufacturer', '').strip() or None
            asset.model = request.form.get('model', '').strip() or None
            asset.vendor = request.form.get('vendor', '').strip() or None
            asset.mfg_country = request.form.get('mfg_country', '').strip() or None
            asset.hsn_code = request.form.get('hsn_code', '').strip() or None
            
            # Dropdowns
            asset.is_bonded = request.form.get('is_bonded', 'na')
            asset.returnable = request.form.get('returnable', 'na')
            asset.cap_x = request.form.get('cap_x', 'na')
            asset.status = request.form.get('status', 'Active')
            
            # Conditional field
            if asset.cap_x == 'yes':
                asset.amortization_period = request.form.get('amortization_period', '').strip() or None
            else:
                asset.amortization_period = None
            
            # Additional info
            asset.notes = request.form.get('notes', '').strip() or None
            asset.entry_no = request.form.get('entry_no', '').strip() or None
            
            # Future dynamic fields
            asset.team = request.form.get('team', '').strip() or None
            asset.recipient_name = request.form.get('recipient_name', '').strip() or None
            asset.recipient_email = request.form.get('recipient_email', '').strip() or None
            asset.category = request.form.get('category', '').strip() or None
            asset.sub_category = request.form.get('sub_category', '').strip() or None
            asset.location = request.form.get('location', '').strip() or None
            
            asset.updated_at = now_ist()
            
            db.session.commit()
            
            # Log the update
            new_values = {
                'serial_number': asset.serial_number,
                'invoice_no': asset.invoice_no,
                'description': asset.description,
                'owner_email': asset.owner_email,
                'status': asset.status
            }
            
            log_audit_event(
                current_user.id, 
                'update_asset', 
                'assets', 
                asset.id,
                old_values,
                new_values,
                asset.id
            )
            
            # Create movement log for significant changes
            movement = MovementLog(
                asset_id=asset.id,
                user_id=current_user.id,
                action='update',
                to_location=asset.location,
                notes='Asset updated'
            )
            db.session.add(movement)
            db.session.commit()
            
            flash(f'Asset {asset.serial_number} updated successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return '', 200, {'HX-Redirect': url_for('assets.view', id=asset.id)}
            return redirect(url_for('assets.view', id=asset.id))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating asset: {str(e)}', 'error')
    
    return render_template('assets/edit.html', asset=asset)

@asset_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    if not current_user.has_permission('delete'):
        flash('You do not have permission to delete assets', 'error')
        return redirect(url_for('assets.view', id=id))
    
    asset = Asset.query.get_or_404(id)
    
    try:
        # Store values for audit log
        old_values = {
            'serial_number': asset.serial_number,
            'invoice_no': asset.invoice_no,
            'description': asset.description
        }
        
        # Delete the asset (cascade will handle related records)
        db.session.delete(asset)
        db.session.commit()
        
        # Log the deletion
        log_audit_event(
            current_user.id, 
            'delete_asset', 
            'assets', 
            id,
            old_values,
            None,
            id
        )
        
        flash(f'Asset {old_values["serial_number"]} deleted successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return '', 200, {'HX-Redirect': url_for('assets.index')}
        return redirect(url_for('assets.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting asset: {str(e)}', 'error')
        return redirect(url_for('assets.view', id=id))