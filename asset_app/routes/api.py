from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from asset_app import db
from asset_app.models import Asset, User, MovementLog, AuditLog
from sqlalchemy import or_, desc
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/assets', methods=['GET'])
@login_required
def get_assets():
    """Get asset list with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    query = Asset.query
    
    # Search
    search = request.args.get('search', '').strip()
    if search:
        query = query.filter(or_(
            Asset.serial_number.contains(search),
            Asset.invoice_no.contains(search),
            Asset.description.contains(search),
            Asset.manufacturer.contains(search),
            Asset.model.contains(search),
            Asset.vendor.contains(search)
        ))
    
    # Filters
    status = request.args.get('status')
    if status:
        query = query.filter(Asset.status == status)
    
    manufacturer = request.args.get('manufacturer')
    if manufacturer:
        query = query.filter(Asset.manufacturer == manufacturer)
    
    # Pagination
    asset_list = query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'assets': [{
            'id': asset.id,
            'serial_number': asset.serial_number,
            'invoice_no': asset.invoice_no,
            'description': asset.description,
            'manufacturer': asset.manufacturer,
            'model': asset.model,
            'vendor': asset.vendor,
            'status': asset.status,
            'owner_email': asset.owner_email,
            'created_at': asset.created_at.isoformat() if asset.created_at else None,
            'updated_at': asset.updated_at.isoformat() if asset.updated_at else None
        } for asset in asset_list.items],
        'pagination': {
            'page': asset_list.page,
            'pages': asset_list.pages,
            'per_page': asset_list.per_page,
            'total': asset_list.total,
            'has_next': asset_list.has_next,
            'has_prev': asset_list.has_prev
        }
    })

@api_bp.route('/assets/<int:id>', methods=['GET'])
@login_required
def get_asset_detail(id):
    """Get detailed asset information"""
    asset = Asset.query.get_or_404(id)
    
    return jsonify({
        'id': asset.id,
        'invoice_no': asset.invoice_no,
        'invoice_date': asset.invoice_date.isoformat() if asset.invoice_date else None,
        'serial_number': asset.serial_number,
        'purchase_order_no': asset.purchase_order_no,
        'received_date': asset.received_date.isoformat() if asset.received_date else None,
        'owner_email': asset.owner_email,
        'description': asset.description,
        'manufacturer': asset.manufacturer,
        'model': asset.model,
        'vendor': asset.vendor,
        'mfg_country': asset.mfg_country,
        'hsn_code': asset.hsn_code,
        'is_bonded': asset.is_bonded,
        'last_calibrated': asset.last_calibrated.isoformat() if asset.last_calibrated else None,
        'next_calibration': asset.next_calibration.isoformat() if asset.next_calibration else None,
        'notes': asset.notes,
        'entry_no': asset.entry_no,
        'returnable': asset.returnable,
        'cap_x': asset.cap_x,
        'amortization_period': asset.amortization_period,
        'status': asset.status,
        'team': asset.team,
        'recipient_name': asset.recipient_name,
        'recipient_email': asset.recipient_email,
        'category': asset.category,
        'sub_category': asset.sub_category,
        'location': asset.location,
        'created_at': asset.created_at.isoformat() if asset.created_at else None,
        'updated_at': asset.updated_at.isoformat() if asset.updated_at else None
    })

@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get asset statistics"""
    total_assets = Asset.query.count()
    active = Asset.query.filter_by(status='Active').count()
    inactive = Asset.query.filter_by(status='Inactive').count()
    disposed = Asset.query.filter_by(status='Disposed').count()
    
    # Calibration due
    from datetime import date, timedelta
    calibration_due = Asset.query.filter(
        Asset.next_calibration <= date.today()
    ).count()
    
    calibration_due_soon = Asset.query.filter(
        Asset.next_calibration > date.today(),
        Asset.next_calibration <= date.today() + timedelta(days=30)
    ).count()
    
    # Manufacturer breakdown
    manufacturers = db.session.query(
        Asset.manufacturer, 
        db.func.count(Asset.id)
    ).group_by(Asset.manufacturer).all()
    
    return jsonify({
        'total_assets': total_assets,
        'active': active,
        'inactive': inactive,
        'disposed': disposed,
        'calibration_due': calibration_due,
        'calibration_due_soon': calibration_due_soon,
        'manufacturers': dict(manufacturers)
    })

@api_bp.route('/search', methods=['GET'])
@login_required
def search():
    """Global search across assets"""
    query_term = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)

    if not query_term:
        if request.headers.get('HX-Request') == 'true':
            return render_template('assets/search_results.html', results=[])
        return jsonify({'results': []})

    results = Asset.query.filter(or_(
        Asset.serial_number.contains(query_term),
        Asset.invoice_no.contains(query_term),
        Asset.description.contains(query_term),
        Asset.manufacturer.contains(query_term),
        Asset.model.contains(query_term),
        Asset.vendor.contains(query_term)
    )).limit(limit).all()

    if request.headers.get('HX-Request') == 'true':
        return render_template('assets/search_results.html', results=results)

    return jsonify({
        'results': [{
            'id': asset.id,
            'serial_number': asset.serial_number,
            'invoice_no': asset.invoice_no,
            'description': asset.description,
            'manufacturer': asset.manufacturer,
            'status': asset.status,
            'location': asset.location
        } for asset in results]
    })