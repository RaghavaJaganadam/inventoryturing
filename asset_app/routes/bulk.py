import os
import tempfile
import datetime
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, session, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from asset_app.utils.bulk_operations import BulkOperations

bulk_bp = Blueprint('bulk', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'xlsx', 'xls'}

@bulk_bp.route('/import', methods=['GET', 'POST'])
@login_required
def bulk_import():
    if not current_user.has_permission('bulk_import'):
        flash('You do not have permission to perform bulk imports', 'error')
        return redirect(url_for('assets.index'))

    if request.method == 'POST':
        dry_run = request.form.get('dry_run') == 'on'
        proceed_import = request.form.get('proceed_import') == 'true'
        temp_file_path = session.get('bulk_import_temp_file')
        file = request.files.get('file')

        # Handle "Proceed with Import" after dry run
        if proceed_import and temp_file_path and os.path.exists(temp_file_path):
            file_ext = os.path.splitext(temp_file_path)[1].lower()
            try:
                if file_ext == '.csv':
                    df = pd.read_csv(temp_file_path)
                elif file_ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(temp_file_path)
                else:
                    flash('Unsupported file type for bulk import', 'error')
                    return render_template('bulk/import.html')
                results = BulkOperations.import_from_dataframe(df, current_user.id, dry_run=False)
                session.pop('bulk_import_temp_file', None)
                if results['success'] > 0 and not results['errors']:
                    flash(f"Successfully imported {results['success']} asset items!", "success")
                    return redirect(url_for('assets.index'))
                return render_template('bulk/import_results.html', results=results, dry_run=False)
            except Exception as e:
                flash(f"Import failed: {str(e)}", 'error')
                return render_template('bulk/import.html')

        # Handle new file upload (dry run or direct import)
        if not file or file.filename == '':
            flash('No file selected', 'error')
            return render_template('bulk/import.html')
        if not allowed_file(file.filename):
            flash('Please upload a CSV or Excel file (.csv, .xlsx, .xls)', 'error')
            return render_template('bulk/import.html')
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        file.save(temp_file.name)
        session['bulk_import_temp_file'] = temp_file.name

        try:
            if file_ext == '.csv':
                df = pd.read_csv(temp_file.name)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(temp_file.name)
            else:
                flash('Only CSV or Excel files are supported!', 'error')
                return render_template('bulk/import.html')
            results = BulkOperations.import_from_dataframe(df, current_user.id, dry_run=dry_run)
            return render_template('bulk/import_results.html', results=results, dry_run=dry_run)
        except Exception as e:
            flash(f"Failed to process file: {str(e)}", 'error')
            return render_template('bulk/import.html')

    return render_template('bulk/import.html')

@bulk_bp.route('/export')
@login_required
def bulk_export():
    if not current_user.has_permission('bulk_import'):
        flash('You do not have permission to export data', 'error')
        return redirect(url_for('assets.index'))

    try:
        csv_data = BulkOperations.export_to_csv()
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        response.headers['Content-Disposition'] = f'attachment; filename=assets_export_{timestamp}.csv'
        return response

    except Exception as e:
        flash(f"Export failed: {str(e)}", 'error')
        return redirect(url_for('assets.index'))

@bulk_bp.route('/export_excel')
@login_required
def bulk_export_excel():
    if not current_user.has_permission('bulk_import'):
        flash('You do not have permission to export data', 'error')
        return redirect(url_for('assets.index'))

    try:
        excel_data = BulkOperations.export_to_excel()
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        response.headers['Content-Disposition'] = f'attachment; filename=assets_export_{timestamp}.xlsx'
        return response
    except Exception as e:
        flash(f"Export failed: {str(e)}", 'error')
        return redirect(url_for('assets.index'))

@bulk_bp.route('/template')
@login_required
def download_template():
    try:
        csv_data = BulkOperations.get_template_csv()
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=assets_import_template.csv'
        return response

    except Exception as e:
        flash(f"Template generation failed: {str(e)}", 'error')
        return redirect(url_for('bulk.bulk_import'))

@bulk_bp.route('/template_excel')
@login_required
def download_template_excel():
    try:
        excel_data = BulkOperations.get_template_excel()
        response = make_response(excel_data)
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=assets_import_template.xlsx'
        return response
    except Exception as e:
        flash(f"Template generation failed: {str(e)}", 'error')
        return redirect(url_for('bulk.bulk_import'))