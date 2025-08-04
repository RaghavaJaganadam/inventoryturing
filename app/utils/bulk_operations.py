import csv
import io
from datetime import datetime
from flask import current_app
from werkzeug.datastructures import FileStorage
from app import db
from app.models import Equipment, User, log_audit_event
import pandas as pd
import numpy as np

class BulkImportError(Exception):
    """Custom exception for bulk import errors"""
    pass

class BulkOperations:
    """Handle bulk import/export operations for equipment"""

    REQUIRED_FIELDS = ['asset_tag', 'name', 'category']
    OPTIONAL_FIELDS = [
        'description', 'model_number', 'manufacturer', 'serial_number',
        'procurement_date', 'warranty_expiry', 'status', 'condition',
        'chip_type', 'package_type', 'pin_count', 'temperature_grade',
        'testing_status', 'revision_info', 'design_files', 'location',
        'purchase_cost', 'current_value', 'tags', 'notes'
    ]

    @staticmethod
    def validate_headers(headers):
        """Validate headers contain required fields"""
        missing = [f for f in BulkOperations.REQUIRED_FIELDS if f not in headers]
        if missing:
            raise BulkImportError(f"Missing required fields: {', '.join(missing)}")
        return True

    @staticmethod
    def parse_date(date_str):
        """Parse date string in various formats"""
        if pd.isna(date_str) or not date_str or str(date_str).strip() == '':
            return None
        # Accept both str or pandas Timestamp/date types
        if isinstance(date_str, (datetime, pd.Timestamp)):
            return date_str.date() if hasattr(date_str, "date") else date_str
        date_str = str(date_str).strip()
        date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except Exception:
                continue
        raise BulkImportError(f"Invalid date format: {date_str}")

    @staticmethod
    def import_from_dataframe(df: pd.DataFrame, user_id: int, dry_run: bool = False):
        """
        Import equipment from a pandas DataFrame (supports both CSV and Excel uploads)
        """
        results = {'success': 0, 'errors': [], 'warnings': [], 'total': 0}
        equipment_list = []

        # Ensure required fields exist
        for field in BulkOperations.REQUIRED_FIELDS:
            if field not in df.columns:
                results['errors'].append(f"Missing required field in file: {field}")
        if results['errors']:
            return results

        # Replace NA/NaN/None with None for all values
        df = df.replace({np.nan: None, pd.NA: None, "NA": None, "": None})

        for row_num, row in enumerate(df.itertuples(index=False), start=2):
            results['total'] += 1
            try:
                asset_tag = getattr(row, 'asset_tag', None)
                if asset_tag is None or str(asset_tag).strip() == '':
                    results['errors'].append(f"Row {row_num}: asset_tag is required.")
                    continue
                asset_tag = str(asset_tag).strip()
                existing = Equipment.query.filter_by(asset_tag=asset_tag).first()
                if existing:
                    results['errors'].append(f"Row {row_num}: Asset tag '{asset_tag}' already exists")
                    continue

                equipment = Equipment()
                equipment.asset_tag = asset_tag
                equipment.name = str(getattr(row, 'name', '')).strip()
                equipment.category = str(getattr(row, 'category', '')).strip()
                for field in BulkOperations.OPTIONAL_FIELDS:
                    value = getattr(row, field, None)
                    # Field-specific conversions
                    if field in ['pin_count']:
                        value = int(value) if value not in (None, '', pd.NA, np.nan) else None
                    elif field in ['purchase_cost', 'current_value']:
                        value = float(value) if value not in (None, '', pd.NA, np.nan) else None
                    elif field in ['procurement_date', 'warranty_expiry']:
                        value = BulkOperations.parse_date(value) if value not in (None, '', pd.NA, np.nan) else None
                    elif isinstance(value, str):
                        value = value.strip()
                    if value in ('', 'NA', pd.NA, np.nan):
                        value = None
                    setattr(equipment, field, value)
                equipment_list.append(equipment)
                results['success'] += 1

            except Exception as e:
                results['errors'].append(f"Row {row_num}: {str(e)}")

        # Save to DB if not dry run
        if not dry_run and equipment_list:
            try:
                for equipment in equipment_list:
                    db.session.add(equipment)
                db.session.commit()
                log_audit_event(
                    user_id,
                    'bulk_import',
                    'equipment',
                    None,
                    None,
                    {'count': len(equipment_list)}
                )
            except Exception as e:
                db.session.rollback()
                results['errors'].append(f"Database error: {str(e)}")

        return results

    @staticmethod
    def import_from_file(file: FileStorage, user_id: int, dry_run: bool = False):
        """Handle import from uploaded file (CSV or Excel)"""
        filename = file.filename.lower()
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(file)
            else:
                raise BulkImportError('Unsupported file type for import.')
            return BulkOperations.import_from_dataframe(df, user_id, dry_run=dry_run)
        except Exception as e:
            raise BulkImportError(f"Import failed: {str(e)}")

    @staticmethod
    def export_to_csv():
        """Export all equipment to CSV format"""
        equipment_list = Equipment.query.all()
        output = io.StringIO()
        writer = csv.writer(output)
        headers = BulkOperations.REQUIRED_FIELDS + BulkOperations.OPTIONAL_FIELDS
        writer.writerow(headers)
        for equipment in equipment_list:
            row = [
                getattr(equipment, h, '') if h != "procurement_date" and h != "warranty_expiry" else (
                    getattr(equipment, h).strftime('%Y-%m-%d') if getattr(equipment, h) else ""
                )
                for h in headers
            ]
            writer.writerow(row)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_to_excel():
        """Export all equipment to Excel format"""
        equipment_list = Equipment.query.all()
        headers = BulkOperations.REQUIRED_FIELDS + BulkOperations.OPTIONAL_FIELDS
        data = []
        for equipment in equipment_list:
            row = [
                getattr(equipment, h, '') if h != "procurement_date" and h != "warranty_expiry" else (
                    getattr(equipment, h).strftime('%Y-%m-%d') if getattr(equipment, h) else ""
                )
                for h in headers
            ]
            data.append(row)
        df = pd.DataFrame(data, columns=headers)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def get_template_csv():
        """Generate a template CSV file for import"""
        output = io.StringIO()
        writer = csv.writer(output)
        headers = BulkOperations.REQUIRED_FIELDS + BulkOperations.OPTIONAL_FIELDS
        writer.writerow(headers)
        # Sample row
        sample_row = [
            'EQ-SAMPLE', 'Sample Equipment', 'Test Equipment', 'Sample description',
            'MODEL-123', 'Sample Manufacturer', 'SN-123456', '2024-01-01', '2027-01-01',
            'Available', 'New', 'FPGA', 'BGA', '256', 'Industrial', 'Untested',
            'Rev 1.0', 'https://example.com/files', 'Building 1 / Lab 1 / Shelf A',
            '1500.00', '1500.00', 'sample, template', 'This is a sample row'
        ]
        writer.writerow(sample_row)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def get_template_excel():
        """Generate a template Excel file for import"""
        headers = BulkOperations.REQUIRED_FIELDS + BulkOperations.OPTIONAL_FIELDS
        sample_row = {
            'asset_tag': 'EQ-SAMPLE',
            'name': 'Sample Equipment',
            'category': 'Test Equipment',
            'description': 'Sample description',
            'model_number': 'MODEL-123',
            'manufacturer': 'Sample Manufacturer',
            'serial_number': 'SN-123456',
            'procurement_date': '2024-01-01',
            'warranty_expiry': '2027-01-01',
            'status': 'Available',
            'condition': 'New',
            'chip_type': 'FPGA',
            'package_type': 'BGA',
            'pin_count': 256,
            'temperature_grade': 'Industrial',
            'testing_status': 'Untested',
            'revision_info': 'Rev 1.0',
            'design_files': 'https://example.com/files',
            'location': 'Building 1 / Lab 1 / Shelf A',
            'purchase_cost': 1500.00,
            'current_value': 1500.00,
            'tags': 'sample, template',
            'notes': 'This is a sample row'
        }
        # Ensure all headers present
        for h in headers:
            if h not in sample_row:
                sample_row[h] = ""
        df = pd.DataFrame([sample_row], columns=headers)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output.getvalue()
