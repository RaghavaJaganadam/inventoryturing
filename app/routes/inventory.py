from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, desc
from datetime import datetime, date
from app import db
from app.models import Equipment, User, MovementLog, log_audit_event
import json

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    # Build query with filters
    query = Equipment.query
    
    # Search functionality
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(or_(
            Equipment.asset_tag.contains(search),
            Equipment.name.contains(search),
            Equipment.model_number.contains(search),
            Equipment.manufacturer.contains(search),
            Equipment.serial_number.contains(search),
            Equipment.location.contains(search)
        ))
    
    # Filter by status
    status_filter = request.args.get('status')
    if status_filter and status_filter != 'all':
        query = query.filter(Equipment.status == status_filter)
    
    # Filter by category
    category_filter = request.args.get('category')
    if category_filter and category_filter != 'all':
        query = query.filter(Equipment.category == category_filter)
    
    # Filter by assigned user
    assigned_filter = request.args.get('assigned')
    if assigned_filter == 'assigned':
        query = query.filter(Equipment.assigned_to_id.isnot(None))
    elif assigned_filter == 'unassigned':
        query = query.filter(Equipment.assigned_to_id.is_(None))
    
    # Sort options
    sort_by = request.args.get('sort', 'asset_tag')
    sort_order = request.args.get('order', 'asc')
    
    if hasattr(Equipment, sort_by):
        column = getattr(Equipment, sort_by)
        if sort_order == 'desc':
            query = query.order_by(desc(column))
        else:
            query = query.order_by(column)
    
    equipment_list = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get filter options for dropdowns
    categories = db.session.query(Equipment.category.distinct()).all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    statuses = ['Available', 'In Use', 'Under Maintenance', 'Retired', 'Missing']
    
    if request.headers.get('HX-Request'):
        return render_template('inventory/equipment_table.html', 
                             equipment_list=equipment_list,
                             current_user=current_user)
    
    return render_template('inventory/index.html', 
                         equipment_list=equipment_list,
                         categories=categories,
                         statuses=statuses,
                         current_user=current_user)

@inventory_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_equipment():
    if not current_user.has_permission('create'):
        flash('You do not have permission to add equipment', 'error')
        return redirect(url_for('inventory.index'))
    
    if request.method == 'POST':
        try:
            # Create new equipment from form data
            equipment = Equipment()
            
            # Basic information
            equipment.asset_tag = request.form.get('asset_tag').strip()
            equipment.name = request.form.get('name').strip()
            equipment.description = request.form.get('description', '').strip()
            equipment.category = request.form.get('category').strip()
            equipment.model_number = request.form.get('model_number', '').strip()
            equipment.manufacturer = request.form.get('manufacturer', '').strip()
            equipment.serial_number = request.form.get('serial_number', '').strip()
            
            # Dates
            procurement_date = request.form.get('procurement_date')
            if procurement_date:
                equipment.procurement_date = datetime.strptime(procurement_date, '%Y-%m-%d').date()
            
            warranty_expiry = request.form.get('warranty_expiry')
            if warranty_expiry:
                equipment.warranty_expiry = datetime.strptime(warranty_expiry, '%Y-%m-%d').date()
            
            # Status and condition
            equipment.status = request.form.get('status', 'Available')
            equipment.condition = request.form.get('condition', 'Good')
            
            # Chip-specific fields
            equipment.chip_type = request.form.get('chip_type', '').strip() or None
            equipment.package_type = request.form.get('package_type', '').strip() or None
            
            pin_count = request.form.get('pin_count', '').strip()
            if pin_count:
                equipment.pin_count = int(pin_count)
            
            equipment.temperature_grade = request.form.get('temperature_grade', '').strip() or None
            equipment.testing_status = request.form.get('testing_status', '').strip() or None
            equipment.revision_info = request.form.get('revision_info', '').strip() or None
            
            # Files and location
            equipment.design_files = request.form.get('design_files', '').strip() or None
            equipment.location = request.form.get('location', '').strip()
            
            # Assignment
            assigned_to = request.form.get('assigned_to')
            if assigned_to and assigned_to != '':
                equipment.assigned_to_id = int(assigned_to)
                equipment.status = 'In Use'  # Auto-set status when assigning
            
            # Cost information
            purchase_cost = request.form.get('purchase_cost', '').strip()
            if purchase_cost:
                equipment.purchase_cost = float(purchase_cost)
                equipment.current_value = equipment.purchase_cost  # Default current value to purchase cost
            
            # Tags and notes
            tags_input = request.form.get('tags', '').strip()
            if tags_input:
                tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                equipment.set_tags_list(tags_list)
            
            equipment.notes = request.form.get('notes', '').strip() or None
            
            # Validate required fields
            if not equipment.asset_tag:
                flash('Asset tag is required', 'error')
                return render_template('inventory/add.html', users=User.query.filter_by(is_active=True).all())
            
            if not equipment.name:
                flash('Name is required', 'error')
                return render_template('inventory/add.html', users=User.query.filter_by(is_active=True).all())
            
            # Check for duplicate asset tag
            existing = Equipment.query.filter_by(asset_tag=equipment.asset_tag).first()
            if existing:
                flash(f'Asset tag {equipment.asset_tag} already exists', 'error')
                return render_template('inventory/add.html', users=User.query.filter_by(is_active=True).all())
            
            db.session.add(equipment)
            db.session.commit()
            
            # Log the creation
            log_audit_event(
                current_user.id, 
                'create_equipment', 
                'equipment', 
                equipment.id,
                None,
                {
                    'asset_tag': equipment.asset_tag,
                    'name': equipment.name,
                    'category': equipment.category
                },
                equipment.id
            )
            
            # If assigned, create movement log
            if equipment.assigned_to_id:
                movement = MovementLog(
                    equipment_id=equipment.id,
                    user_id=current_user.id,
                    action='assign',
                    to_user_id=equipment.assigned_to_id,
                    to_location=equipment.location,
                    notes=f'Initial assignment during creation'
                )
                db.session.add(movement)
                db.session.commit()
            
            flash(f'Equipment {equipment.asset_tag} added successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return '', 200, {'HX-Redirect': url_for('inventory.view', id=equipment.id)}
            return redirect(url_for('inventory.view', id=equipment.id))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding equipment: {str(e)}', 'error')
    
    users = User.query.filter_by(is_active=True).all()
    return render_template('inventory/add.html', users=users)

@inventory_bp.route('/view/<int:id>')
@login_required
def view(id):
    equipment = Equipment.query.get_or_404(id)
    
    # Get recent movement logs
    movements = MovementLog.query.filter_by(equipment_id=id).order_by(desc(MovementLog.timestamp)).limit(10).all()
    
    return render_template('inventory/view.html', equipment=equipment, movements=movements)

@inventory_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    equipment = Equipment.query.get_or_404(id)
    
    if not current_user.has_permission('update'):
        flash('You do not have permission to edit equipment', 'error')
        return redirect(url_for('inventory.view', id=id))
    
    if request.method == 'POST':
        try:
            # Store old values for audit log
            old_values = {
                'asset_tag': equipment.asset_tag,
                'name': equipment.name,
                'status': equipment.status,
                'assigned_to_id': equipment.assigned_to_id,
                'location': equipment.location
            }
            
            # Track if assignment changed
            old_assigned_to = equipment.assigned_to_id
            
            # Update equipment from form data
            equipment.asset_tag = request.form.get('asset_tag').strip()
            equipment.name = request.form.get('name').strip()
            equipment.description = request.form.get('description', '').strip()
            equipment.category = request.form.get('category').strip()
            equipment.model_number = request.form.get('model_number', '').strip()
            equipment.manufacturer = request.form.get('manufacturer', '').strip()
            equipment.serial_number = request.form.get('serial_number', '').strip()
            
            # Dates
            procurement_date = request.form.get('procurement_date')
            if procurement_date:
                equipment.procurement_date = datetime.strptime(procurement_date, '%Y-%m-%d').date()
            else:
                equipment.procurement_date = None
            
            warranty_expiry = request.form.get('warranty_expiry')
            if warranty_expiry:
                equipment.warranty_expiry = datetime.strptime(warranty_expiry, '%Y-%m-%d').date()
            else:
                equipment.warranty_expiry = None
            
            # Status and condition
            equipment.status = request.form.get('status', 'Available')
            equipment.condition = request.form.get('condition', 'Good')
            
            # Chip-specific fields
            equipment.chip_type = request.form.get('chip_type', '').strip() or None
            equipment.package_type = request.form.get('package_type', '').strip() or None
            
            pin_count = request.form.get('pin_count', '').strip()
            equipment.pin_count = int(pin_count) if pin_count else None
            
            equipment.temperature_grade = request.form.get('temperature_grade', '').strip() or None
            equipment.testing_status = request.form.get('testing_status', '').strip() or None
            equipment.revision_info = request.form.get('revision_info', '').strip() or None
            
            # Files and location
            equipment.design_files = request.form.get('design_files', '').strip() or None
            equipment.location = request.form.get('location', '').strip()
            
            # Assignment
            assigned_to = request.form.get('assigned_to')
            new_assigned_to = int(assigned_to) if assigned_to and assigned_to != '' else None
            
            # Handle assignment changes
            if old_assigned_to != new_assigned_to:
                equipment.assigned_to_id = new_assigned_to
                
                # Create movement log for assignment change
                if new_assigned_to:
                    # Assigning to someone
                    equipment.status = 'In Use'
                    movement = MovementLog(
                        equipment_id=equipment.id,
                        user_id=current_user.id,
                        action='assign',
                        from_user_id=old_assigned_to,
                        to_user_id=new_assigned_to,
                        to_location=equipment.location,
                        notes='Assignment changed via edit'
                    )
                else:
                    # Unassigning
                    equipment.status = 'Available'
                    movement = MovementLog(
                        equipment_id=equipment.id,
                        user_id=current_user.id,
                        action='unassign',
                        from_user_id=old_assigned_to,
                        to_location=equipment.location,
                        notes='Unassigned via edit'
                    )
                
                db.session.add(movement)
            
            # Cost information
            purchase_cost = request.form.get('purchase_cost', '').strip()
            equipment.purchase_cost = float(purchase_cost) if purchase_cost else None
            
            current_value = request.form.get('current_value', '').strip()
            equipment.current_value = float(current_value) if current_value else equipment.purchase_cost
            
            # Tags and notes
            tags_input = request.form.get('tags', '').strip()
            if tags_input:
                tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
                equipment.set_tags_list(tags_list)
            else:
                equipment.tags = None
            
            equipment.notes = request.form.get('notes', '').strip() or None
            equipment.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log the update
            new_values = {
                'asset_tag': equipment.asset_tag,
                'name': equipment.name,
                'status': equipment.status,
                'assigned_to_id': equipment.assigned_to_id,
                'location': equipment.location
            }
            
            log_audit_event(
                current_user.id, 
                'update_equipment', 
                'equipment', 
                equipment.id,
                old_values,
                new_values,
                equipment.id
            )
            
            flash(f'Equipment {equipment.asset_tag} updated successfully', 'success')
            
            if request.headers.get('HX-Request'):
                return '', 200, {'HX-Redirect': url_for('inventory.view', id=equipment.id)}
            return redirect(url_for('inventory.view', id=equipment.id))
            
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating equipment: {str(e)}', 'error')
    
    users = User.query.filter_by(is_active=True).all()
    return render_template('inventory/edit.html', equipment=equipment, users=users)

@inventory_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    if not current_user.has_permission('delete'):
        flash('You do not have permission to delete equipment', 'error')
        return redirect(url_for('inventory.view', id=id))
    
    equipment = Equipment.query.get_or_404(id)
    
    try:
        # Store values for audit log
        old_values = {
            'asset_tag': equipment.asset_tag,
            'name': equipment.name,
            'category': equipment.category
        }
        
        # Delete the equipment (cascade will handle related records)
        db.session.delete(equipment)
        db.session.commit()
        
        # Log the deletion
        log_audit_event(
            current_user.id, 
            'delete_equipment', 
            'equipment', 
            id,
            old_values,
            None,
            id
        )
        
        flash(f'Equipment {old_values["asset_tag"]} deleted successfully', 'success')
        
        if request.headers.get('HX-Request'):
            return '', 200, {'HX-Redirect': url_for('inventory.index')}
        return redirect(url_for('inventory.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting equipment: {str(e)}', 'error')
        return redirect(url_for('inventory.view', id=id))

@inventory_bp.route('/checkout/<int:id>', methods=['POST'])
@login_required
def checkout(id):
    equipment = Equipment.query.get_or_404(id)
    
    if not equipment.is_available():
        flash('Equipment is not available for checkout', 'error')
        return redirect(url_for('inventory.view', id=id))
    
    if not current_user.has_permission('checkout'):
        flash('You do not have permission to checkout equipment', 'error')
        return redirect(url_for('inventory.view', id=id))
    
    try:
        # Update equipment status and assignment
        equipment.status = 'In Use'
        equipment.assigned_to_id = current_user.id
        
        # Create movement log
        movement = MovementLog(
            equipment_id=equipment.id,
            user_id=current_user.id,
            action='checkout',
            to_user_id=current_user.id,
            to_location=equipment.location,
            notes='Self-checkout'
        )
        
        db.session.add(movement)
        db.session.commit()
        
        log_audit_event(
            current_user.id, 
            'checkout_equipment', 
            'equipment', 
            equipment.id,
            {'status': 'Available', 'assigned_to_id': None},
            {'status': 'In Use', 'assigned_to_id': current_user.id},
            equipment.id
        )
        
        flash(f'Equipment {equipment.asset_tag} checked out successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error checking out equipment: {str(e)}', 'error')
    
    return redirect(url_for('inventory.view', id=id))

@inventory_bp.route('/checkin/<int:id>', methods=['POST'])
@login_required
def checkin(id):
    equipment = Equipment.query.get_or_404(id)
    
    if equipment.assigned_to_id != current_user.id and not current_user.has_permission('update'):
        flash('You can only check in equipment assigned to you', 'error')
        return redirect(url_for('inventory.view', id=id))
    
    try:
        old_assigned_to = equipment.assigned_to_id
        
        # Update equipment status and assignment
        equipment.status = 'Available'
        equipment.assigned_to_id = None
        
        # Create movement log
        movement = MovementLog(
            equipment_id=equipment.id,
            user_id=current_user.id,
            action='checkin',
            from_user_id=old_assigned_to,
            to_location=equipment.location,
            notes='Equipment returned'
        )
        
        db.session.add(movement)
        db.session.commit()
        
        log_audit_event(
            current_user.id, 
            'checkin_equipment', 
            'equipment', 
            equipment.id,
            {'status': 'In Use', 'assigned_to_id': old_assigned_to},
            {'status': 'Available', 'assigned_to_id': None},
            equipment.id
        )
        
        flash(f'Equipment {equipment.asset_tag} checked in successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error checking in equipment: {str(e)}', 'error')
    
    return redirect(url_for('inventory.view', id=id))