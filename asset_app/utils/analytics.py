from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from asset_app import db
from asset_app.models import Asset, MovementLog, AuditLog, User

class AnalyticsEngine:
    """Advanced analytics and reporting for asset management"""
    
    @staticmethod
    def get_utilization_report(days=30):
        """Generate asset utilization report"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all assets
        total_assets = Asset.query.count()
        
        # Assets by status
        active = Asset.query.filter_by(status='Active').count()
        inactive = Asset.query.filter_by(status='Inactive').count()
        disposed = Asset.query.filter_by(status='Disposed').count()
        
        # Activity in the period
        activities = MovementLog.query.filter(
            MovementLog.timestamp >= start_date
        ).count()
        
        # Most active assets
        most_active = db.session.query(
            Asset.serial_number,
            Asset.description,
            func.count(MovementLog.id).label('activity_count')
        ).join(MovementLog).filter(
            MovementLog.timestamp >= start_date
        ).group_by(Asset.id).order_by(
            func.count(MovementLog.id).desc()
        ).limit(10).all()
        
        # Activity by manufacturer
        manufacturer_activity = db.session.query(
            Asset.manufacturer,
            func.count(MovementLog.id).label('activity_count')
        ).join(MovementLog).filter(
            MovementLog.timestamp >= start_date
        ).group_by(Asset.manufacturer).order_by(
            func.count(MovementLog.id).desc()
        ).all()
        
        return {
            'period_days': days,
            'total_assets': total_assets,
            'active': active,
            'inactive': inactive,
            'disposed': disposed,
            'utilization_rate': (active / total_assets * 100) if total_assets > 0 else 0,
            'activities_in_period': activities,
            'most_active_assets': [
                {
                    'serial_number': item.serial_number,
                    'description': item.description,
                    'activity_count': item.activity_count
                } for item in most_active
            ],
            'manufacturer_activity': [
                {
                    'manufacturer': item.manufacturer or 'Unknown',
                    'activity_count': item.activity_count
                } for item in manufacturer_activity
            ]
        }
    
    @staticmethod
    def get_calibration_report():
        """Generate calibration report"""
        from datetime import date
        
        # Assets with calibration due
        calibration_due = Asset.query.filter(
            and_(
                Asset.next_calibration.isnot(None),
                Asset.next_calibration < date.today()
            )
        ).all()
        
        # Assets with calibration due soon (next 30 days)
        calibration_due_soon = Asset.query.filter(
            and_(
                Asset.next_calibration.isnot(None),
                Asset.next_calibration >= date.today(),
                Asset.next_calibration <= date.today() + timedelta(days=30)
            )
        ).all()
        
        # Assets never calibrated
        never_calibrated = Asset.query.filter(
            Asset.last_calibrated.is_(None)
        ).count()
        
        # Calibration by manufacturer
        calibration_by_mfg = db.session.query(
            Asset.manufacturer,
            func.count(Asset.id).label('total'),
            func.sum(func.case([(Asset.next_calibration < date.today(), 1)], else_=0)).label('overdue')
        ).filter(
            Asset.next_calibration.isnot(None)
        ).group_by(Asset.manufacturer).all()
        
        return {
            'calibration_due': [
                {
                    'serial_number': asset.serial_number,
                    'description': asset.description,
                    'next_calibration': asset.next_calibration.isoformat(),
                    'days_overdue': (date.today() - asset.next_calibration).days,
                    'manufacturer': asset.manufacturer
                } for asset in calibration_due
            ],
            'calibration_due_soon': [
                {
                    'serial_number': asset.serial_number,
                    'description': asset.description,
                    'next_calibration': asset.next_calibration.isoformat(),
                    'days_remaining': (asset.next_calibration - date.today()).days,
                    'manufacturer': asset.manufacturer
                } for asset in calibration_due_soon
            ],
            'never_calibrated': never_calibrated,
            'calibration_by_manufacturer': [
                {
                    'manufacturer': item.manufacturer or 'Unknown',
                    'total_assets': item.total,
                    'overdue': item.overdue or 0
                } for item in calibration_by_mfg
            ]
        }
    
    @staticmethod
    def get_activity_trends(days=30):
        """Analyze activity trends over time"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Daily activity counts
        daily_activity = db.session.query(
            func.date(MovementLog.timestamp).label('date'),
            func.count(MovementLog.id).label('activity_count')
        ).filter(
            MovementLog.timestamp >= start_date
        ).group_by(func.date(MovementLog.timestamp)).all()
        
        # Activity by action type
        action_counts = db.session.query(
            MovementLog.action,
            func.count(MovementLog.id).label('count')
        ).filter(
            MovementLog.timestamp >= start_date
        ).group_by(MovementLog.action).all()
        
        # Most active users
        active_users = db.session.query(
            User.name,
            User.email,
            func.count(MovementLog.id).label('activity_count')
        ).join(MovementLog, MovementLog.user_id == User.id).filter(
            MovementLog.timestamp >= start_date
        ).group_by(User.id).order_by(
            func.count(MovementLog.id).desc()
        ).limit(10).all()
        
        return {
            'period_days': days,
            'daily_activity': [
                {
                    'date': item.date.isoformat(),
                    'activity_count': item.activity_count
                } for item in daily_activity
            ],
            'action_breakdown': [
                {
                    'action': item.action,
                    'count': item.count
                } for item in action_counts
            ],
            'most_active_users': [
                {
                    'name': item.name,
                    'email': item.email,
                    'activity_count': item.activity_count
                } for item in active_users
            ]
        }
    
    @staticmethod
    def get_manufacturer_analysis():
        """Analyze assets by manufacturer"""
        # Asset count by manufacturer
        manufacturer_counts = db.session.query(
            Asset.manufacturer,
            func.count(Asset.id).label('count')
        ).filter(
            Asset.manufacturer.isnot(None)
        ).group_by(Asset.manufacturer).order_by(
            func.count(Asset.id).desc()
        ).all()
        
        # Status distribution by manufacturer
        status_by_mfg = db.session.query(
            Asset.manufacturer,
            Asset.status,
            func.count(Asset.id).label('count')
        ).filter(
            Asset.manufacturer.isnot(None)
        ).group_by(Asset.manufacturer, Asset.status).all()
        
        # Country distribution
        country_counts = db.session.query(
            Asset.mfg_country,
            func.count(Asset.id).label('count')
        ).filter(
            Asset.mfg_country.isnot(None)
        ).group_by(Asset.mfg_country).order_by(
            func.count(Asset.id).desc()
        ).all()
        
        return {
            'manufacturer_distribution': [
                {
                    'manufacturer': item.manufacturer,
                    'count': item.count
                } for item in manufacturer_counts
            ],
            'status_by_manufacturer': [
                {
                    'manufacturer': item.manufacturer,
                    'status': item.status,
                    'count': item.count
                } for item in status_by_mfg
            ],
            'country_distribution': [
                {
                    'country': item.mfg_country,
                    'count': item.count
                } for item in country_counts
            ]
        }