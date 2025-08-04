from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from app import db
from app.models import Equipment, MovementLog, AuditLog, User

class AnalyticsEngine:
    """Advanced analytics and reporting for lab inventory"""
    
    @staticmethod
    def get_utilization_report(days=30):
        """Generate equipment utilization report"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all equipment
        total_equipment = Equipment.query.count()
        
        # Equipment currently in use
        in_use = Equipment.query.filter_by(status='In Use').count()
        
        # Equipment checked out in the period
        checkouts = MovementLog.query.filter(
            and_(
                MovementLog.action == 'checkout',
                MovementLog.timestamp >= start_date
            )
        ).count()
        
        # Most used equipment
        most_used = db.session.query(
            Equipment.asset_tag,
            Equipment.name,
            func.count(MovementLog.id).label('usage_count')
        ).join(MovementLog).filter(
            MovementLog.timestamp >= start_date
        ).group_by(Equipment.id).order_by(
            func.count(MovementLog.id).desc()
        ).limit(10).all()
        
        # Utilization by category
        category_usage = db.session.query(
            Equipment.category,
            func.count(MovementLog.id).label('usage_count')
        ).join(MovementLog).filter(
            MovementLog.timestamp >= start_date
        ).group_by(Equipment.category).order_by(
            func.count(MovementLog.id).desc()
        ).all()
        
        return {
            'period_days': days,
            'total_equipment': total_equipment,
            'currently_in_use': in_use,
            'utilization_rate': (in_use / total_equipment * 100) if total_equipment > 0 else 0,
            'checkouts_in_period': checkouts,
            'most_used_equipment': [
                {
                    'asset_tag': item.asset_tag,
                    'name': item.name,
                    'usage_count': item.usage_count
                } for item in most_used
            ],
            'category_usage': [
                {
                    'category': item.category,
                    'usage_count': item.usage_count
                } for item in category_usage
            ]
        }
    
    @staticmethod
    def get_maintenance_report():
        """Generate maintenance and downtime report"""
        # Equipment under maintenance
        under_maintenance = Equipment.query.filter_by(status='Under Maintenance').all()
        
        # Equipment needing repair
        needs_repair = Equipment.query.filter_by(condition='Needs Repair').all()
        
        # Warranty expiring soon (next 90 days)
        warranty_expiring = Equipment.query.filter(
            and_(
                Equipment.warranty_expiry.isnot(None),
                Equipment.warranty_expiry <= datetime.now().date() + timedelta(days=90),
                Equipment.warranty_expiry >= datetime.now().date()
            )
        ).all()
        
        # Expired warranties
        warranty_expired = Equipment.query.filter(
            and_(
                Equipment.warranty_expiry.isnot(None),
                Equipment.warranty_expiry < datetime.now().date()
            )
        ).all()
        
        return {
            'under_maintenance': [
                {
                    'asset_tag': eq.asset_tag,
                    'name': eq.name,
                    'location': eq.location,
                    'notes': eq.notes
                } for eq in under_maintenance
            ],
            'needs_repair': [
                {
                    'asset_tag': eq.asset_tag,
                    'name': eq.name,
                    'condition': eq.condition,
                    'location': eq.location
                } for eq in needs_repair
            ],
            'warranty_expiring': [
                {
                    'asset_tag': eq.asset_tag,
                    'name': eq.name,
                    'warranty_expiry': eq.warranty_expiry.isoformat(),
                    'days_remaining': (eq.warranty_expiry - datetime.now().date()).days
                } for eq in warranty_expiring
            ],
            'warranty_expired': [
                {
                    'asset_tag': eq.asset_tag,
                    'name': eq.name,
                    'warranty_expiry': eq.warranty_expiry.isoformat(),
                    'days_expired': (datetime.now().date() - eq.warranty_expiry).days
                } for eq in warranty_expired
            ]
        }
    
    @staticmethod
    def get_inventory_valuation():
        """Calculate inventory valuation and financial metrics"""
        # Total purchase cost
        total_purchase = db.session.query(
            func.sum(Equipment.purchase_cost)
        ).filter(Equipment.purchase_cost.isnot(None)).scalar() or 0
        
        # Current total value
        total_current = db.session.query(
            func.sum(Equipment.current_value)
        ).filter(Equipment.current_value.isnot(None)).scalar() or 0
        
        # Value by category
        category_values = db.session.query(
            Equipment.category,
            func.sum(Equipment.current_value).label('total_value'),
            func.count(Equipment.id).label('count')
        ).filter(
            Equipment.current_value.isnot(None)
        ).group_by(Equipment.category).all()
        
        # Value by status
        status_values = db.session.query(
            Equipment.status,
            func.sum(Equipment.current_value).label('total_value'),
            func.count(Equipment.id).label('count')
        ).filter(
            Equipment.current_value.isnot(None)
        ).group_by(Equipment.status).all()
        
        # Most valuable equipment
        most_valuable = Equipment.query.filter(
            Equipment.current_value.isnot(None)
        ).order_by(Equipment.current_value.desc()).limit(10).all()
        
        return {
            'total_purchase_cost': float(total_purchase),
            'total_current_value': float(total_current),
            'depreciation': float(total_purchase - total_current),
            'depreciation_rate': ((total_purchase - total_current) / total_purchase * 100) if total_purchase > 0 else 0,
            'category_breakdown': [
                {
                    'category': item.category,
                    'total_value': float(item.total_value),
                    'count': item.count,
                    'average_value': float(item.total_value / item.count)
                } for item in category_values
            ],
            'status_breakdown': [
                {
                    'status': item.status,
                    'total_value': float(item.total_value),
                    'count': item.count
                } for item in status_values
            ],
            'most_valuable': [
                {
                    'asset_tag': eq.asset_tag,
                    'name': eq.name,
                    'current_value': float(eq.current_value),
                    'category': eq.category
                } for eq in most_valuable
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
        
        # Most active users -- FIXED
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
        ).join(MovementLog).filter(
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
    def get_location_heatmap():
        """Generate location-based usage heatmap data"""
        location_usage = db.session.query(
            Equipment.location,
            func.count(Equipment.id).label('equipment_count'),
            func.count(MovementLog.id).label('activity_count')
        ).outerjoin(MovementLog).filter(
            Equipment.location.isnot(None)
        ).group_by(Equipment.location).all()
        
        return [
            {
                'location': item.location,
                'equipment_count': item.equipment_count,
                'activity_count': item.activity_count or 0,
                'utilization_score': (item.activity_count or 0) / item.equipment_count if item.equipment_count > 0 else 0
            } for item in location_usage
        ]
    
    @staticmethod
    def get_chip_analysis():
        """Analyze chip-specific inventory metrics"""
        # Chip type distribution
        chip_distribution = db.session.query(
            Equipment.chip_type,
            func.count(Equipment.id).label('count')
        ).filter(
            Equipment.chip_type.isnot(None)
        ).group_by(Equipment.chip_type).all()
        
        # Package type distribution
        package_distribution = db.session.query(
            Equipment.package_type,
            func.count(Equipment.id).label('count')
        ).filter(
            Equipment.package_type.isnot(None)
        ).group_by(Equipment.package_type).all()
        
        # Testing status summary
        testing_status = db.session.query(
            Equipment.testing_status,
            func.count(Equipment.id).label('count')
        ).filter(
            Equipment.testing_status.isnot(None)
        ).group_by(Equipment.testing_status).all()
        
        # Temperature grade distribution
        temp_grades = db.session.query(
            Equipment.temperature_grade,
            func.count(Equipment.id).label('count')
        ).filter(
            Equipment.temperature_grade.isnot(None)
        ).group_by(Equipment.temperature_grade).all()
        
        return {
            'chip_types': [
                {'type': item.chip_type, 'count': item.count}
                for item in chip_distribution
            ],
            'package_types': [
                {'type': item.package_type, 'count': item.count}
                for item in package_distribution
            ],
            'testing_status': [
                {'status': item.testing_status, 'count': item.count}
                for item in testing_status
            ],
            'temperature_grades': [
                {'grade': item.temperature_grade, 'count': item.count}
                for item in temp_grades
            ]
        }