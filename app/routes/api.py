from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Equipment, User, MovementLog, AuditLog
from sqlalchemy import or_, desc
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/equipment', methods=['GET'])
@login_required
def get_equipment():
    """Get equipment list with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    query = Equipment.query
    
    # Search
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(or_(
            Equipment.asset_tag.contains(search),
            Equipment.name.contains(search),
            Equipment.model_number.contains(search),
            Equipment.manufacturer.contains(search)
        ))
    
    # Filters
    status = request.args.get('status')
    if status:
        query = query.filter(Equipment.status == status)
    
    category = request.args.get('category')
    if category:
        query = query.filter(Equipment.category == category)
    
    # Pagination
    equipment_list = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'equipment': [{
            'id': eq.id,
            'asset_tag': eq.asset_tag,
            'name': eq.name,
            'category': eq.category,
            'model_number': eq.model_number,
            'manufacturer': eq.manufacturer,
            'status': eq.status,
            'condition': eq.condition,
            'location': eq.location,
            'assigned_to': eq.assignee.name if eq.assignee else None,
            'created_at': eq.created_at.isoformat() if eq.created_at else None,
            'updated_at': eq.updated_at.isoformat() if eq.updated_at else None
        } for eq in equipment_list.items],
        'pagination': {
            'page': equipment_list.page,
            'pages': equipment_list.pages,
            'per_page': equipment_list.per_page,
            'total': equipment_list.total,
            'has_next': equipment_list.has_next,
            'has_prev': equipment_list.has_prev
        }
    })

@api_bp.route('/equipment/<int:id>', methods=['GET'])
@login_required
def get_equipment_detail(id):
    """Get detailed equipment information"""
    equipment = Equipment.query.get_or_404(id)
    
    return jsonify({
        'id': equipment.id,
        'asset_tag': equipment.asset_tag,
        'name': equipment.name,
        'description': equipment.description,
        'category': equipment.category,
        'model_number': equipment.model_number,
        'manufacturer': equipment.manufacturer,
        'serial_number': equipment.serial_number,
        'procurement_date': equipment.procurement_date.isoformat() if equipment.procurement_date else None,
        'warranty_expiry': equipment.warranty_expiry.isoformat() if equipment.warranty_expiry else None,
        'status': equipment.status,
        'condition': equipment.condition,
        'chip_type': equipment.chip_type,
        'package_type': equipment.package_type,
        'pin_count': equipment.pin_count,
        'temperature_grade': equipment.temperature_grade,
        'testing_status': equipment.testing_status,
        'revision_info': equipment.revision_info,
        'design_files': equipment.design_files,
        'location': equipment.location,
        'assigned_to': equipment.assignee.name if equipment.assignee else None,
        'assigned_to_id': equipment.assigned_to_id,
        'purchase_cost': float(equipment.purchase_cost) if equipment.purchase_cost else None,
        'current_value': float(equipment.current_value) if equipment.current_value else None,
        'tags': equipment.get_tags_list(),
        'notes': equipment.notes,
        'created_at': equipment.created_at.isoformat() if equipment.created_at else None,
        'updated_at': equipment.updated_at.isoformat() if equipment.updated_at else None
    })

@api_bp.route('/equipment/<int:id>/movements', methods=['GET'])
@login_required
def get_equipment_movements(id):
    """Get movement history for equipment"""
    equipment = Equipment.query.get_or_404(id)
    
    movements = MovementLog.query.filter_by(equipment_id=id)\
        .order_by(desc(MovementLog.timestamp))\
        .limit(50).all()
    
    return jsonify({
        'movements': [{
            'id': mov.id,
            'action': mov.action,
            'user': mov.user.name,
            'from_location': mov.from_location,
            'to_location': mov.to_location,
            'from_user': mov.from_user.name if mov.from_user else None,
            'to_user': mov.to_user.name if mov.to_user else None,
            'timestamp': mov.timestamp.isoformat(),
            'notes': mov.notes
        } for mov in movements]
    })

@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get inventory statistics"""
    total_equipment = Equipment.query.count()
    available = Equipment.query.filter_by(status='Available').count()
    in_use = Equipment.query.filter_by(status='In Use').count()
    maintenance = Equipment.query.filter_by(status='Under Maintenance').count()
    
    # Category breakdown
    categories = db.session.query(
        Equipment.category, 
        db.func.count(Equipment.id)
    ).group_by(Equipment.category).all()
    
    return jsonify({
        'total_equipment': total_equipment,
        'available': available,
        'in_use': in_use,
        'maintenance': maintenance,
        'categories': dict(categories)
    })

@api_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    """Get list of active users"""
    if not current_user.has_permission('user_management'):
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    users = User.query.filter_by(is_active=True).all()
    
    return jsonify({
        'users': [{
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat()
        } for user in users]
    })

# @api_bp.route('/search', methods=['GET'])
# @login_required
# def search():
#     """Global search across equipment"""
#     query_term = request.args.get('q', '').strip()
#     limit = request.args.get('limit', 10, type=int)
    
#     if not query_term:
#         return jsonify({'results': []})
    
#     results = Equipment.query.filter(or_(
#         Equipment.asset_tag.contains(query_term),
#         Equipment.name.contains(query_term),
#         Equipment.model_number.contains(query_term),
#         Equipment.manufacturer.contains(query_term),
#         Equipment.serial_number.contains(query_term)
#     )).limit(limit).all()
    
#     return jsonify({
#         'results': [{
#             'id': eq.id,
#             'asset_tag': eq.asset_tag,
#             'name': eq.name,
#             'category': eq.category,
#             'status': eq.status,
#             'location': eq.location
#         } for eq in results]
#     })



from flask import render_template, request, jsonify

@api_bp.route('/search', methods=['GET'])
@login_required
def search():
    """Global search across equipment"""
    query_term = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)

    if not query_term:
        # For HTMX, render empty result partial; for others, return empty JSON
        if request.headers.get('HX-Request') == 'true':
            return render_template('inventory/search_results.html', results=[])
        return jsonify({'results': []})

    results = Equipment.query.filter(or_(
        Equipment.asset_tag.contains(query_term),
        Equipment.name.contains(query_term),
        Equipment.model_number.contains(query_term),
        Equipment.manufacturer.contains(query_term),
        Equipment.serial_number.contains(query_term)
    )).limit(limit).all()

    # If HTMX, render the HTML partial
    if request.headers.get('HX-Request') == 'true':
        return render_template('inventory/search_results.html', results=results)

    # Otherwise, fallback to JSON (for API/AJAX/non-HTMX)
    return jsonify({
        'results': [{
            'id': eq.id,
            'asset_tag': eq.asset_tag,
            'name': eq.name,
            'category': eq.category,
            'status': eq.status,
            'location': eq.location
        } for eq in results]
    })
