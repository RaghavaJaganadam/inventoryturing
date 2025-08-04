from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.utils.analytics import AnalyticsEngine

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard')
@login_required
def analytics_dashboard():
    """Main analytics dashboard"""
    return render_template('analytics/dashboard.html')

@analytics_bp.route('/api/utilization')
@login_required
def utilization_data():
    """API endpoint for utilization report data"""
    days = request.args.get('days', 30, type=int)
    data = AnalyticsEngine.get_utilization_report(days)
    return jsonify(data)

@analytics_bp.route('/api/maintenance')
@login_required
def maintenance_data():
    """API endpoint for maintenance report data"""
    data = AnalyticsEngine.get_maintenance_report()
    return jsonify(data)

@analytics_bp.route('/api/valuation')
@login_required
def valuation_data():
    """API endpoint for inventory valuation data"""
    data = AnalyticsEngine.get_inventory_valuation()
    return jsonify(data)

@analytics_bp.route('/api/trends')
@login_required
def trends_data():
    """API endpoint for activity trends data"""
    days = request.args.get('days', 30, type=int)
    data = AnalyticsEngine.get_activity_trends(days)
    return jsonify(data)

@analytics_bp.route('/api/heatmap')
@login_required
def heatmap_data():
    """API endpoint for location heatmap data"""
    data = AnalyticsEngine.get_location_heatmap()
    return jsonify(data)

@analytics_bp.route('/api/chip-analysis')
@login_required
def chip_analysis_data():
    """API endpoint for chip-specific analysis"""
    data = AnalyticsEngine.get_chip_analysis()
    return jsonify(data)

@analytics_bp.route('/reports/utilization')
@login_required
def utilization_report():
    """Detailed utilization report page"""
    return render_template('analytics/utilization.html')

@analytics_bp.route('/reports/maintenance')
@login_required
def maintenance_report():
    """Detailed maintenance report page"""
    return render_template('analytics/maintenance.html')

@analytics_bp.route('/reports/valuation')
@login_required
def valuation_report():
    """Detailed valuation report page"""
    return render_template('analytics/valuation.html')