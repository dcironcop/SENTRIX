"""
Data Quality Dashboard Blueprint
"""
from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from models import Camera, db
from data_quality.duplicate_detector import DuplicateDetector
from data_quality.quality_score import DataQualityScore
from data_quality.auto_fix import AutoFixEngine

data_quality_bp = Blueprint("data_quality", __name__, url_prefix="/data-quality")


@data_quality_bp.route("/")
@login_required
def dashboard():
    """Data quality dashboard"""
    # Get quality scores
    quality_scores = DataQualityScore.calculate_overall_score()
    
    # Get duplicates
    duplicates = DuplicateDetector.find_all_duplicates()
    duplicate_summary = DuplicateDetector.get_duplicate_summary()
    
    # Get total cameras
    total_cameras = Camera.query.count()
    
    return render_template(
        "data_quality/dashboard.html",
        quality_scores=quality_scores,
        duplicates=duplicates,
        duplicate_summary=duplicate_summary,
        total_cameras=total_cameras
    )


@data_quality_bp.route("/duplicates")
@login_required
def duplicates():
    """View all duplicates"""
    duplicates = DuplicateDetector.find_all_duplicates()
    return render_template("data_quality/duplicates.html", duplicates=duplicates)


@data_quality_bp.route("/suggestions/<int:camera_id>")
@login_required
def get_suggestions(camera_id):
    """Get auto-fix suggestions for a camera"""
    camera = Camera.query.get_or_404(camera_id)
    suggestions = AutoFixEngine.suggest_fixes_for_camera(camera)
    
    return jsonify({
        'camera_id': camera_id,
        'suggestions': [
            {
                'field': s.field,
                'current_value': s.current_value,
                'suggested_value': s.suggested_value,
                'reason': s.reason,
                'confidence': s.confidence
            }
            for s in suggestions
        ]
    })


@data_quality_bp.route("/apply-fix", methods=["POST"])
@login_required
def apply_fix():
    """Apply an auto-fix suggestion"""
    from flask import request
    from security_utils import log_audit
    
    camera_id = request.json.get('camera_id')
    field = request.json.get('field')
    suggested_value = request.json.get('suggested_value')
    
    camera = Camera.query.get_or_404(camera_id)
    
    if hasattr(camera, field):
        old_value = getattr(camera, field)
        setattr(camera, field, suggested_value)
        db.session.commit()
        
        log_audit('edit', 'camera', camera_id, {
            'field': field,
            'old_value': old_value,
            'new_value': suggested_value,
            'auto_fix': True
        })
        
        return jsonify({'success': True, 'message': 'Đã áp dụng sửa lỗi'})
    
    return jsonify({'success': False, 'message': 'Trường không tồn tại'}), 400
