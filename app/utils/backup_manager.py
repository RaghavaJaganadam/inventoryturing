import os
import shutil
import sqlite3
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from flask import current_app
from app import db
from app.models import Equipment, User, MovementLog, AuditLog

class BackupManager:
    """Handle database backups and restoration"""
    
    def __init__(self):
        self.backup_dir = Path(current_app.config.get('BACKUP_DIR', 'backups'))
        self.backup_dir.mkdir(exist_ok=True)
        self.retention_days = current_app.config.get('BACKUP_RETENTION_DAYS', 30)
    
    def create_backup(self, backup_type='full'):
        """Create a database backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if backup_type == 'full':
            return self._create_full_backup(timestamp)
        elif backup_type == 'data_only':
            return self._create_data_backup(timestamp)
        else:
            raise ValueError("Backup type must be 'full' or 'data_only'")
    
    def _create_full_backup(self, timestamp):
        """Create a full database backup (schema + data)"""
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        backup_filename = f"full_backup_{timestamp}.db.gz"
        backup_path = self.backup_dir / backup_filename
        
        # Copy database file and compress
        with open(db_path, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Create metadata file
        metadata = {
            'backup_type': 'full',
            'timestamp': timestamp,
            'database_size': os.path.getsize(db_path),
            'compressed_size': os.path.getsize(backup_path),
            'tables': self._get_table_counts()
        }
        
        metadata_path = self.backup_dir / f"full_backup_{timestamp}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            'backup_file': backup_filename,
            'metadata_file': f"full_backup_{timestamp}.json",
            'size': os.path.getsize(backup_path),
            'timestamp': timestamp
        }
    
    def _create_data_backup(self, timestamp):
        """Create a data-only backup (JSON export)"""
        backup_filename = f"data_backup_{timestamp}.json.gz"
        backup_path = self.backup_dir / backup_filename
        
        # Export all data to JSON
        data = {
            'users': [self._serialize_user(user) for user in User.query.all()],
            'equipment': [self._serialize_equipment(eq) for eq in Equipment.query.all()],
            'movement_logs': [self._serialize_movement_log(log) for log in MovementLog.query.all()],
            'audit_logs': [self._serialize_audit_log(log) for log in AuditLog.query.all()]
        }
        
        # Compress and save
        json_data = json.dumps(data, indent=2, default=str)
        with gzip.open(backup_path, 'wt') as f:
            f.write(json_data)
        
        # Create metadata
        metadata = {
            'backup_type': 'data_only',
            'timestamp': timestamp,
            'compressed_size': os.path.getsize(backup_path),
            'tables': self._get_table_counts()
        }
        
        metadata_path = self.backup_dir / f"data_backup_{timestamp}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return {
            'backup_file': backup_filename,
            'metadata_file': f"data_backup_{timestamp}.json",
            'size': os.path.getsize(backup_path),
            'timestamp': timestamp
        }
    
    def list_backups(self):
        """List all available backups"""
        backups = []
        
        for metadata_file in self.backup_dir.glob("*_backup_*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                backup_file = metadata_file.name.replace('.json', '.db.gz' if metadata['backup_type'] == 'full' else '.json.gz')
                backup_path = self.backup_dir / backup_file
                
                if backup_path.exists():
                    backups.append({
                        'filename': backup_file,
                        'metadata': metadata,
                        'size': os.path.getsize(backup_path),
                        'created': datetime.strptime(metadata['timestamp'], '%Y%m%d_%H%M%S')
                    })
            except Exception as e:
                current_app.logger.error(f"Error reading backup metadata {metadata_file}: {e}")
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        removed_count = 0
        
        for backup in self.list_backups():
            if backup['created'] < cutoff_date:
                try:
                    # Remove backup file
                    backup_path = self.backup_dir / backup['filename']
                    if backup_path.exists():
                        backup_path.unlink()
                    
                    # Remove metadata file
                    metadata_file = backup['filename'].replace('.db.gz', '.json').replace('.json.gz', '.json')
                    metadata_path = self.backup_dir / metadata_file
                    if metadata_path.exists():
                        metadata_path.unlink()
                    
                    removed_count += 1
                except Exception as e:
                    current_app.logger.error(f"Error removing old backup {backup['filename']}: {e}")
        
        return removed_count
    
    def restore_backup(self, backup_filename):
        """Restore from a backup file"""
        backup_path = self.backup_dir / backup_filename
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file {backup_filename} not found")
        
        if backup_filename.endswith('.db.gz'):
            return self._restore_full_backup(backup_path)
        elif backup_filename.endswith('.json.gz'):
            return self._restore_data_backup(backup_path)
        else:
            raise ValueError("Invalid backup file format")
    
    def _restore_full_backup(self, backup_path):
        """Restore from a full database backup"""
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        
        # Create backup of current database
        current_backup = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_path, self.backup_dir / current_backup)
        
        try:
            # Restore from backup
            with gzip.open(backup_path, 'rb') as f_in:
                with open(db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            return {'status': 'success', 'current_backup': current_backup}
        
        except Exception as e:
            # Restore original database
            shutil.copy2(self.backup_dir / current_backup, db_path)
            raise Exception(f"Restore failed: {e}")
    
    def _get_table_counts(self):
        """Get record counts for all tables"""
        return {
            'users': User.query.count(),
            'equipment': Equipment.query.count(),
            'movement_logs': MovementLog.query.count(),
            'audit_logs': AuditLog.query.count()
        }
    
    def _serialize_user(self, user):
        """Serialize user object to dict"""
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'password_hash': user.password_hash,
            'role': user.role,
            'created_at': user.created_at.isoformat(),
            'is_active': user.is_active
        }
    
    def _serialize_equipment(self, equipment):
        """Serialize equipment object to dict"""
        return {
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
            'created_at': equipment.created_at.isoformat(),
            'updated_at': equipment.updated_at.isoformat(),
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
            'assigned_to_id': equipment.assigned_to_id,
            'tags': equipment.tags,
            'notes': equipment.notes,
            'purchase_cost': float(equipment.purchase_cost) if equipment.purchase_cost else None,
            'current_value': float(equipment.current_value) if equipment.current_value else None
        }
    
    def _serialize_movement_log(self, log):
        """Serialize movement log object to dict"""
        return {
            'id': log.id,
            'equipment_id': log.equipment_id,
            'user_id': log.user_id,
            'action': log.action,
            'from_location': log.from_location,
            'to_location': log.to_location,
            'from_user_id': log.from_user_id,
            'to_user_id': log.to_user_id,
            'timestamp': log.timestamp.isoformat(),
            'notes': log.notes
        }
    
    def _serialize_audit_log(self, log):
        """Serialize audit log object to dict"""
        return {
            'id': log.id,
            'user_id': log.user_id,
            'equipment_id': log.equipment_id,
            'action': log.action,
            'table_name': log.table_name,
            'record_id': log.record_id,
            'old_values': log.old_values,
            'new_values': log.new_values,
            'timestamp': log.timestamp.isoformat(),
            'ip_address': log.ip_address,
            'user_agent': log.user_agent
        }