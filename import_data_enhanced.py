"""
Enhanced import functionality with CSV, JSON support and progress tracking
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import re
import pandas as pd
import json
import csv
from io import StringIO

from models import db, Camera
from parse_m2 import parse_m2_to_records
from security_utils import log_audit, sanitize_input
from data_quality.validation_rules import ValidationRulesConfig

import_bp_enhanced = Blueprint("import_enhanced", __name__, url_prefix="/import")


def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if not filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if allowed_extensions is None:
        allowed_extensions = {'xls', 'xlsx', 'csv', 'json'}
    return ext in allowed_extensions


def parse_csv_to_records(filepath):
    """Parse CSV file to camera records"""
    records = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert CSV row to camera record format
            record = {}
            for key, value in row.items():
                # Map CSV columns to camera fields
                key_clean = key.strip().lower()
                if value:
                    record[key_clean] = value.strip()
            if record:
                records.append(record)
    return records


def parse_json_to_records(filepath):
    """Parse JSON file to camera records"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and 'cameras' in data:
        records = data['cameras']
    elif isinstance(data, dict):
        records = [data]
    
    return records


def import_with_progress(filepath, file_type, progress_key):
    """
    Import data with progress tracking
    
    Args:
        filepath: Path to file
        file_type: 'excel', 'csv', or 'json'
        progress_key: Key for storing progress in session
    """
    # Initialize progress
    session[progress_key] = {
        'status': 'parsing',
        'total': 0,
        'processed': 0,
        'success': 0,
        'errors': 0,
        'error_details': []
    }
    
    try:
        # Parse file
        if file_type == 'excel':
            records = parse_m2_to_records(filepath)
        elif file_type == 'csv':
            records = parse_csv_to_records(filepath)
        elif file_type == 'json':
            records = parse_json_to_records(filepath)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        total = len(records)
        session[progress_key]['total'] = total
        session[progress_key]['status'] = 'importing'
        session.modified = True
        
        success = 0
        errors = 0
        error_details = []
        
        # Process records
        for idx, record in enumerate(records):
            try:
                # Validate using validation rules
                is_valid, validation_errors = ValidationRulesConfig.validate_row(record)
                if not is_valid:
                    errors += 1
                    error_details.append({
                        'row': idx + 1,
                        'error': '; '.join(validation_errors),
                        'info': f"Owner: {record.get('owner_name', 'N/A')}"
                    })
                    continue
                
                # Create camera (similar to existing logic)
                # This is simplified - actual implementation should match existing import logic
                camera = Camera(
                    owner_name=sanitize_input(record.get('owner_name')),
                    organization_name=sanitize_input(record.get('organization_name')),
                    address_street=sanitize_input(record.get('address_street')),
                    ward=sanitize_input(record.get('ward')),
                    province=sanitize_input(record.get('province')),
                    phone=sanitize_input(record.get('phone')),
                    camera_index=record.get('camera_index') or None,
                    system_type=sanitize_input(record.get('system_type')),
                    latlon=sanitize_input(record.get('latlon')),
                )
                
                db.session.add(camera)
                success += 1
                
            except Exception as e:
                errors += 1
                error_details.append({
                    'row': idx + 1,
                    'error': str(e),
                    'info': f"Owner: {record.get('owner_name', 'N/A')}"
                })
            
            # Update progress
            session[progress_key]['processed'] = idx + 1
            session[progress_key]['success'] = success
            session[progress_key]['errors'] = errors
            session[progress_key]['error_details'] = error_details
            session.modified = True
        
        # Commit all at once
        db.session.commit()
        
        session[progress_key]['status'] = 'completed'
        session.modified = True
        
        return success, errors, error_details
        
    except Exception as e:
        session[progress_key]['status'] = 'error'
        session[progress_key]['error'] = str(e)
        session.modified = True
        raise


@import_bp_enhanced.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Enhanced import page with CSV/JSON support"""
    if request.method == "POST":
        file = request.files.get("file")
        
        if not file or file.filename == "":
            flash("❌ Chưa chọn file", "danger")
            return redirect(url_for("import_enhanced.index"))
        
        # Determine file type
        filename = file.filename.lower()
        if filename.endswith(('.xls', '.xlsx')):
            file_type = 'excel'
            allowed_ext = {'xls', 'xlsx'}
        elif filename.endswith('.csv'):
            file_type = 'csv'
            allowed_ext = {'csv'}
        elif filename.endswith('.json'):
            file_type = 'json'
            allowed_ext = {'json'}
        else:
            flash("❌ Chỉ chấp nhận file Excel, CSV hoặc JSON", "danger")
            return redirect(url_for("import_enhanced.index"))
        
        if not allowed_file(file.filename, allowed_ext):
            flash(f"❌ File không hợp lệ. Chỉ chấp nhận: {', '.join(allowed_ext)}", "danger")
            return redirect(url_for("import_enhanced.index"))
        
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        filename_secure = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename_secure)
        file.save(filepath)
        
        # Generate progress key
        import uuid
        progress_key = f"import_progress_{uuid.uuid4().hex[:8]}"
        
        # Start import in background (simplified - in production use Celery or similar)
        try:
            success, errors, error_details = import_with_progress(filepath, file_type, progress_key)
            
            # Store errors in session
            if errors:
                session['import_errors'] = error_details
                flash(f"⚠️ Import xong: {success} camera, {errors} dòng lỗi", "warning")
            else:
                session.pop('import_errors', None)
                flash(f"✅ Import thành công {success} camera", "success")
            
            # Log audit
            log_audit('import', 'camera', None, {
                'file': filename_secure,
                'file_type': file_type,
                'success': success,
                'errors': errors
            })
            
        except Exception as e:
            flash(f"❌ Lỗi import: {str(e)}", "danger")
        
        # Clean up progress
        session.pop(progress_key, None)
        
        return redirect(url_for("import_enhanced.index"))
    
    return render_template("import/index_enhanced.html")


@import_bp_enhanced.route("/progress/<progress_key>")
@login_required
def get_progress(progress_key):
    """Get import progress"""
    progress = session.get(progress_key, {})
    return jsonify(progress)
