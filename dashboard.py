from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from flask_login import login_required
from models import db, Camera
from color_utils import build_system_color_map
from sqlalchemy import func
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from typing import Optional
import io

# Helper function để lấy cache an toàn
def get_cache() -> Optional[object]:
    """
    Safely retrieve cache instance from Flask extensions.
    
    Returns:
        Cache object if available, None otherwise
        
    This helper prevents AttributeError when cache is not properly initialized.
    """
    try:
        cache = current_app.extensions.get('cache')
        # Kiểm tra xem có phải Cache object không (có methods get/set)
        if cache and hasattr(cache, 'get') and hasattr(cache, 'set'):
            return cache
        return None
    except (RuntimeError, AttributeError, KeyError):
        return None

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    cache = get_cache()
    
    # Cache key cho dashboard data
    cache_key = 'dashboard_stats'
    
    # Thử lấy từ cache
    cached_data = None
    if cache:
        try:
            cached_data = cache.get(cache_key)
        except (AttributeError, TypeError):
            # Cache chưa được init hoặc không phải Cache object
            cached_data = None
    
    if cached_data:
        return render_template("dashboard/index.html", **cached_data)
    
    # Nếu không có cache, tính toán lại
    # OPTIMIZE: Load all cameras once và tính toán trong memory thay vì nhiều queries
    all_cameras = Camera.query.all()
    total = len(all_cameras)

    color_map = build_system_color_map(db.session, Camera, cache=cache)

    # OPTIMIZE: Tính toán trong memory từ all_cameras đã load
    # Thống kê theo system_type
    system_counts = {}
    ward_counts = {}
    manufacturer_counts = {}
    cameras_with_coords = 0
    cameras_with_sharing = 0
    cameras_with_static_ip = 0
    install_area_stats = {}
    monitoring_stats = {}
    
    for cam in all_cameras:
        # System type
        system = cam.system_type or "Chưa phân loại"
        system_counts[system] = system_counts.get(system, 0) + 1
        
        # Ward
        if cam.ward:
            ward_counts[cam.ward] = ward_counts.get(cam.ward, 0) + 1
        
        # Manufacturer
        if cam.manufacturer:
            manufacturer_counts[cam.manufacturer] = manufacturer_counts.get(cam.manufacturer, 0) + 1
        
        # Coordinates
        if cam.latlon:
            cameras_with_coords += 1
        
        # Sharing
        if cam.sharing_scope:
            cameras_with_sharing += 1
        
        # Static IP
        if cam.static_ip:
            cameras_with_static_ip += 1
        
        # Install areas (JSON field)
        try:
            areas = cam.get_json("install_areas")
            for area in areas:
                if area:
                    install_area_stats[area] = install_area_stats.get(area, 0) + 1
        except (ValueError, TypeError, AttributeError, KeyError):
            # JSON parsing failed or field doesn't exist - skip this camera
            pass
        
        # Monitoring modes (JSON field)
        try:
            modes = cam.get_json("monitoring_modes")
            for mode in modes:
                if mode:
                    monitoring_stats[mode] = monitoring_stats.get(mode, 0) + 1
        except (ValueError, TypeError, AttributeError, KeyError):
            # JSON parsing failed or field doesn't exist - skip this camera
            pass
    
    # Convert to list format for compatibility
    by_system = [(k, v) for k, v in sorted(system_counts.items(), key=lambda x: x[1], reverse=True)]
    by_ward = [(k, v) for k, v in sorted(ward_counts.items(), key=lambda x: x[0])]
    top_wards = [(k, v) for k, v in sorted(ward_counts.items(), key=lambda x: x[1], reverse=True)[:20]]
    top_5_wards = [(k, v) for k, v in sorted(ward_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    top_manufacturers = [(k, v) for k, v in sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    all_manufacturers = [(k, v) for k, v in sorted(manufacturer_counts.items(), key=lambda x: x[1], reverse=True)]
    
    # Sắp xếp install_area_stats
    install_area_stats = dict(sorted(install_area_stats.items(), key=lambda x: x[1], reverse=True))
    
    cameras_without_coords = total - cameras_with_coords
    cameras_without_sharing = total - cameras_with_sharing
    cameras_without_static_ip = total - cameras_with_static_ip
    
    # Chuẩn bị data để cache
    template_data = {
        'total': total,
        'by_system': by_system,
        'by_ward': by_ward,
        'top_wards': top_wards,
        'color_map': color_map,
        'cameras_with_coords': cameras_with_coords,
        'cameras_without_coords': cameras_without_coords,
        'cameras_with_sharing': cameras_with_sharing,
        'cameras_without_sharing': cameras_without_sharing,
        'cameras_with_static_ip': cameras_with_static_ip,
        'cameras_without_static_ip': cameras_without_static_ip,
        'top_5_wards': top_5_wards,
        'top_manufacturers': top_manufacturers,
        'all_manufacturers': all_manufacturers,
        'install_area_stats': install_area_stats,
        'monitoring_stats': monitoring_stats,
    }
    
    # Lưu vào cache (5 phút)
    if cache:
        try:
            cache.set(cache_key, template_data, timeout=300)
        except (AttributeError, TypeError):
            # Cache chưa được init hoặc không phải Cache object
            pass

    return render_template("dashboard/index.html", **template_data)


@dashboard_bp.route("/wards")
@login_required
def wards_list():
    """Trang hiển thị toàn bộ danh sách 166 xã/phường"""
    sort_by = request.args.get('sort', 'count_desc')  # count_desc, count_asc, name_asc, name_desc
    
    query = (
        db.session.query(Camera.ward, func.count(Camera.id).label('count'))
        .filter(Camera.ward.isnot(None), Camera.ward != "")
        .group_by(Camera.ward)
    )
    
    # Sắp xếp
    if sort_by == 'count_desc':
        query = query.order_by(func.count(Camera.id).desc())
    elif sort_by == 'count_asc':
        query = query.order_by(func.count(Camera.id).asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Camera.ward.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Camera.ward.desc())
    
    all_wards = query.all()
    
    total = Camera.query.count()
    
    return render_template(
        "dashboard/wards.html",
        all_wards=all_wards,
        total=total,
        sort_by=sort_by,
    )


@dashboard_bp.route("/api/wards")
@login_required
def api_wards():
    """API endpoint để lấy dữ liệu ward với filter và sort"""
    ward_filter = request.args.get('ward', None)  # None = toàn tỉnh, hoặc tên ward cụ thể
    sort_by = request.args.get('sort', 'count_desc')
    limit = request.args.get('limit', type=int, default=20)
    
    query = (
        db.session.query(Camera.ward, func.count(Camera.id).label('count'))
        .filter(Camera.ward.isnot(None), Camera.ward != "")
    )
    
    if ward_filter and ward_filter != 'all':
        query = query.filter(Camera.ward == ward_filter)
    
    query = query.group_by(Camera.ward)
    
    # Sắp xếp
    if sort_by == 'count_desc':
        query = query.order_by(func.count(Camera.id).desc())
    elif sort_by == 'count_asc':
        query = query.order_by(func.count(Camera.id).asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Camera.ward.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Camera.ward.desc())
    
    if limit:
        query = query.limit(limit)
    
    wards = query.all()
    
    result = [{"ward": w[0] or "Không rõ", "count": w[1]} for w in wards]
    
    return jsonify(result)


@dashboard_bp.route("/api/systems")
@login_required
def api_systems():
    """API endpoint để lấy dữ liệu hệ thống theo filter địa bàn"""
    from urllib.parse import unquote
    
    ward_filter = request.args.get('ward', None)  # None = toàn tỉnh, hoặc tên ward cụ thể
    
    # Decode URL nếu có
    if ward_filter and ward_filter != 'all':
        try:
            ward_filter = unquote(ward_filter)
            # Loại bỏ dấu ngoặc kép nếu có (từ JSON encoding)
            if ward_filter.startswith('"') and ward_filter.endswith('"'):
                ward_filter = ward_filter[1:-1]
        except (UnicodeDecodeError, ValueError, TypeError) as e:
            # URL decoding failed - use original value
            current_app.logger.warning(f"Error decoding ward_filter: {e}")
            pass
    
    query = (
        db.session.query(Camera.system_type, func.count(Camera.id).label('count'))
    )
    
    if ward_filter and ward_filter != 'all':
        # Filter theo ward cụ thể - loại bỏ khoảng trắng thừa
        ward_filter = ward_filter.strip()
        
        # Thử tìm với exact match trước
        count_exact = db.session.query(func.count(Camera.id)).filter(
            Camera.ward == ward_filter
        ).scalar()
        print(f"Found {count_exact} cameras with ward '{ward_filter}' (exact match)")
        
        # Nếu không tìm thấy, thử tìm với ward có trailing space
        if count_exact == 0:
            count_with_space = db.session.query(func.count(Camera.id)).filter(
                Camera.ward == (ward_filter + ' ')
            ).scalar()
            print(f"Found {count_with_space} cameras with ward '{ward_filter} ' (with trailing space)")
            if count_with_space > 0:
                ward_filter = ward_filter + ' '
        
        # Nếu vẫn không tìm thấy, thử tìm với LIKE (case-insensitive)
        if count_exact == 0 and not ward_filter.endswith(' '):
            # Tìm các ward tương tự (không phân biệt hoa thường)
            similar_wards = db.session.query(Camera.ward, func.count(Camera.id)).filter(
                Camera.ward.ilike(f'%{ward_filter}%')
            ).group_by(Camera.ward).limit(5).all()
            print(f"Similar wards found: {[(w[0].strip() if w[0] else '', w[1]) for w in similar_wards]}")
            
            # Nếu có ward tương tự, dùng ward đầu tiên (exact match với trimmed)
            if similar_wards:
                # Tìm ward có trimmed value khớp
                for similar_ward, count in similar_wards:
                    if similar_ward and similar_ward.strip() == ward_filter:
                        ward_filter = similar_ward
                        print(f"Using similar ward (exact trimmed match): '{ward_filter}'")
                        break
                else:
                    # Nếu không có exact trimmed match, dùng ward đầu tiên
                    ward_filter = similar_wards[0][0]
                    print(f"Using similar ward (first match): '{ward_filter}'")
        
        # Filter query - dùng exact match với ward_filter (đã được điều chỉnh)
        query = query.filter(Camera.ward == ward_filter)
        print(f"Filtering by ward: '{ward_filter}' (final)")
    else:
        print("No ward filter - showing all provinces")
    
    query = query.group_by(Camera.system_type).order_by(func.count(Camera.id).desc())
    
    systems = query.all()
    
    result = [{"system": s[0] or "Chưa phân loại", "count": s[1]} for s in systems]
    
    print(f"Returning {len(result)} systems")
    
    return jsonify(result)


@dashboard_bp.route("/export-pdf")
@login_required
def export_pdf():
    """Export dashboard report as PDF"""
    cache = get_cache()
    
    # Lấy dữ liệu dashboard
    total = Camera.query.count()
    by_system = (
        db.session.query(Camera.system_type, func.count(Camera.id))
        .group_by(Camera.system_type)
        .order_by(func.count(Camera.id).desc())
        .all()
    )
    
    top_5_wards = (
        db.session.query(Camera.ward, func.count(Camera.id).label('count'))
        .filter(Camera.ward.isnot(None), Camera.ward != "")
        .group_by(Camera.ward)
        .order_by(func.count(Camera.id).desc())
        .limit(5)
        .all()
    )
    
    top_manufacturers = (
        db.session.query(Camera.manufacturer, func.count(Camera.id).label('count'))
        .filter(Camera.manufacturer.isnot(None), Camera.manufacturer != "")
        .group_by(Camera.manufacturer)
        .order_by(func.count(Camera.id).desc())
        .limit(5)
        .all()
    )
    
    cameras_with_coords = Camera.query.filter(Camera.latlon.isnot(None), Camera.latlon != "").count()
    cameras_with_sharing = Camera.query.filter(Camera.sharing_scope == True).count()
    cameras_with_static_ip = Camera.query.filter(Camera.static_ip.isnot(None), Camera.static_ip != "").count()
    
    # Tạo PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1E40AF'),
        spaceAfter=30,
        alignment=1  # Center
    )
    story.append(Paragraph("BÁO CÁO TỔNG HỢP HỆ THỐNG CAMERA", title_style))
    story.append(Paragraph(f"Ngày xuất: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Tổng số camera', str(total)],
        ['Có tọa độ', f"{cameras_with_coords} ({cameras_with_coords/total*100:.1f}%)" if total > 0 else "0"],
        ['Cho phép chia sẻ', f"{cameras_with_sharing} ({cameras_with_sharing/total*100:.1f}%)" if total > 0 else "0"],
        ['Có IP tĩnh', f"{cameras_with_static_ip} ({cameras_with_static_ip/total*100:.1f}%)" if total > 0 else "0"],
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E40AF')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Top 5 Wards
    wards_data = [['STT', 'Xã/Phường', 'Số camera']]
    for idx, (ward, count) in enumerate(top_5_wards, 1):
        wards_data.append([str(idx), ward or 'Không rõ', str(count)])
    
    wards_table = Table(wards_data, colWidths=[0.5*inch, 3*inch, 1.5*inch])
    wards_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(Paragraph("Top 5 xã/phường có nhiều camera nhất", styles['Heading2']))
    story.append(Spacer(1, 10))
    story.append(wards_table)
    story.append(Spacer(1, 20))
    
    # Top 5 Manufacturers
    mfg_data = [['STT', 'Hãng sản xuất', 'Số camera']]
    for idx, (mfg, count) in enumerate(top_manufacturers, 1):
        mfg_data.append([str(idx), mfg or 'Không rõ', str(count)])
    
    mfg_table = Table(mfg_data, colWidths=[0.5*inch, 3*inch, 1.5*inch])
    mfg_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F59E0B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(Paragraph("Top 5 hãng sản xuất", styles['Heading2']))
    story.append(Spacer(1, 10))
    story.append(mfg_table)
    story.append(Spacer(1, 20))
    
    # System distribution
    system_data = [['Hệ thống', 'Số camera']]
    for system, count in by_system:
        system_data.append([system or 'Chưa phân loại', str(count)])
    
    system_table = Table(system_data, colWidths=[3*inch, 2*inch])
    system_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#A855F7')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(Paragraph("Phân bố theo hệ thống", styles['Heading2']))
    story.append(Spacer(1, 10))
    story.append(system_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        download_name=f'bao_cao_camera_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        as_attachment=True
    )
