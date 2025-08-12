import csv
import io
from datetime import datetime
from flask import current_app
from werkzeug.datastructures import FileStorage
from asset_app import db
from asset_app.models import Asset, User, log_audit_event
import pandas as pd
import numpy as np

class BulkImportError(Exception):
    """Custom exception for bulk import errors"""
    pass

class BulkOperations:
    """Handle bulk import/export operations for assets"""

    REQUIRED_FIELDS = ['invoice_no', 'serial_number', 'description', 'owner_email']
    OPTIONAL_FIELDS = [
        'invoice_date', 'purchase_order_no', 'received_date', 'manufacturer',
        'model', 'vendor', 'mfg_country', 'hsn_code', 'is_bonded',
        'last_calibrated', 'next_calibration', 'notes', 'entry_no',
        'returnable', 'cap_x', 'amortization_period', 'status',
        'team', 'recipient_name', 'recipient_email', 'category',
        'sub_category', 'location'
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
        """Import assets from a pandas DataFrame"""
        results = {'success': 0, 'errors': [], 'warnings': [], 'total': 0}
        asset_list = []

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
                serial_number = getattr(row, 'serial_number', None)
                if serial_number is None or str(serial_number).strip() == '':
                    results['errors'].append(f"Row {row_num}: serial_number is required.")
                    continue
                serial_number = str(serial_number).strip()
                
                existing = Asset.query.filter_by(serial_number=serial_number).first()
                if existing:
                    results['errors'].append(f"Row {row_num}: Serial number '{serial_number}' already exists")
                    continue

                asset = Asset()
                asset.serial_number = serial_number
                asset.invoice_no = str(getattr(row, 'invoice_no', '')).strip()
                asset.description = str(getattr(row, 'description', '')).strip()
                asset.owner_email = str(getattr(row, 'owner_email', '')).strip()
                
                # Validate required fields
                if not asset.invoice_no:
                    results['errors'].append(f"Row {row_num}: invoice_no is required.")
                    continue
                if not asset.description:
                    results['errors'].append(f"Row {row_num}: description is required.")
                    continue
                if not asset.owner_email:
                    results['errors'].append(f"Row {row_num}: owner_email is required.")
                    continue

                for field in BulkOperations.OPTIONAL_FIELDS:
                    value = getattr(row, field, None)
                    if pd.isna(value) or value in ('', 'NA'):
                        value = None
                    if field in ['invoice_date', 'received_date', 'last_calibrated', 'next_calibration'] and value is not None:
                        value = BulkOperations.parse_date(value)
                    elif isinstance(value, str):
                        value = value.strip()
                    setattr(asset, field, value)

                asset_list.append(asset)
                results['success'] += 1

            except Exception as e:
                results['errors'].append(f"Row {row_num}: {str(e)}")

        # Save to DB if not dry run
        if not dry_run and asset_list:
            try:
                for asset in asset_list:
                    db.session.add(asset)
                db.session.commit()
                log_audit_event(
                    user_id,
                    'bulk_import',
                    'assets',
                    None,
                    None,
                    {'count': len(asset_list)}
                )
            except Exception as e:
                db.session.rollback()
                results['errors'].append(f"Database error: {str(e)}")

        return results

    @staticmethod
    def export_to_csv():
        """Export all assets to CSV format"""
        asset_list = Asset.query.all()
        output = io.StringIO()
        writer = csv.writer(output)
        headers = BulkOperations.REQUIRED_FIELDS + BulkOperations.OPTIONAL_FIELDS
        writer.writerow(headers)
        for asset in asset_list:
            row = []
            for h in headers:
                value = getattr(asset, h, '')
                if h in ['invoice_date', 'received_date', 'last_calibrated', 'next_calibration'] and value:
                    value = value.strftime('%Y-%m-%d')
                row.append(value or '')
            writer.writerow(row)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_to_excel():
        """Export all assets to Excel format"""
        asset_list = Asset.query.all()
        headers = BulkOperations.REQUIRED_FIELDS + BulkOperations.OPTIONAL_FIELDS
        data = []
        for asset in asset_list:
            row = []
            for h in headers:
                value = getattr(asset, h, '')
                if h in ['invoice_date', 'received_date', 'last_calibrated', 'next_calibration'] and value:
                    value = value.strftime('%Y-%m-%d')
                row.append(value or '')
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
            'INV-2024-001', 'SN-SAMPLE-001', 'Sample Asset Description', 'owner@company.com',
            '2024-01-01', 'PO-2024-001', '2024-01-15', 'Sample Manufacturer',
            'Model-123', 'Sample Vendor', 'India', 'HSN123', 'no',
            '2024-01-01', '2025-01-01', 'Sample notes', 'ENTRY-001',
            'yes', 'no', '', 'Active',
            'Team A', 'John Doe', 'john@company.com', 'Electronics',
            'Test Equipment', 'Building 1 / Lab 1'
        ]
        writer.writerow(sample_row)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def get_template_excel():
        """Generate a template Excel file for import"""
        headers = BulkOperations.REQUIRED_FIELDS + BulkOperations.OPTIONAL_FIELDS
        sample_row = {
            'invoice_no': 'INV-2024-001',
            'serial_number': 'SN-SAMPLE-001',
            'description': 'Sample Asset Description',
            'owner_email': 'owner@company.com',
            'invoice_date': '2024-01-01',
            'purchase_order_no': 'PO-2024-001',
            'received_date': '2024-01-15',
            'manufacturer': 'Sample Manufacturer',
            'model': 'Model-123',
            'vendor': 'Sample Vendor',
            'mfg_country': 'India',
            'hsn_code': 'HSN123',
            'is_bonded': 'no',
            'last_calibrated': '2024-01-01',
            'next_calibration': '2025-01-01',
            'notes': 'Sample notes',
            'entry_no': 'ENTRY-001',
            'returnable': 'yes',
            'cap_x': 'no',
            'amortization_period': '',
            'status': 'Active',
            'team': 'Team A',
            'recipient_name': 'John Doe',
            'recipient_email': 'john@company.com',
            'category': 'Electronics',
            'sub_category': 'Test Equipment',
            'location': 'Building 1 / Lab 1'
        }
        df = pd.DataFrame([sample_row], columns=headers)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output.getvalue()