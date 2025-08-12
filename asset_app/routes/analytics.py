from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from asset_app.utils.analytics import AnalyticsEngine

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

@analytics_bp.route('/api/calibration')
@login_required
def calibration_data():
    """API endpoint for calibration report data"""
    data = AnalyticsEngine.get_calibration_report()
    return jsonify(data)

@analytics_bp.route('/api/trends')
@login_required
def trends_data():
    """API endpoint for activity trends data"""
    days = request.args.get('days', 30, type=int)
    data = AnalyticsEngine.get_activity_trends(days)
    return jsonify(data)

@analytics_bp.route('/api/manufacturer-analysis')
@login_required
def manufacturer_analysis_data():
    """API endpoint for manufacturer analysis"""
    data = AnalyticsEngine.get_manufacturer_analysis()
    return jsonify(data)

@analytics_bp.route('/reports/utilization')
@login_required
def utilization_report():
    """Detailed utilization report page"""
    return render_template('analytics/utilization.html')

@analytics_bp.route('/reports/calibration')
@login_required
def calibration_report():
    """Detailed calibration report page"""
    return render_template('analytics/calibration.html')