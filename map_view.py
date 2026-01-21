from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from models import db, Camera
from sqlalchemy import text
from color_utils import build_system_color_map
import math
import requests

map_bp = Blueprint("map", __name__, url_prefix="/map")


def parse_latlon(latlon):
    """
    Chuyển 'lat,lon' -> (lat, lon)
    """
    try:
        lat, lon = latlon.split(",")
        return float(lat.strip()), float(lon.strip())
    except Exception:
        return None, None


def get_camera_coordinates(camera):
    if camera.latitude is not None and camera.longitude is not None:
        return camera.latitude, camera.longitude
    return parse_latlon(camera.latlon or "")


def bounding_box(lat, lon, radius_m):
    lat_rad = math.radians(lat)
    lat_delta = radius_m / 111320
    lon_delta = radius_m / (111320 * math.cos(lat_rad)) if math.cos(lat_rad) else 0
    return (
        lat - lat_delta,
        lat + lat_delta,
        lon - lon_delta,
        lon + lon_delta,
    )


def distance_m(lat1, lon1, lat2, lon2):
    """
    Khoảng cách 2 điểm (m) – Haversine
    """
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@map_bp.route("/")
@login_required
def index():
    focus_id = request.args.get("camera_id", type=int)
    return_url = request.args.get("return_url")  # Lấy return_url từ query string
    cameras = Camera.query.filter(
        (Camera.latitude.isnot(None) & Camera.longitude.isnot(None))
        | Camera.latlon.isnot(None)
    ).all()
    # Luôn trả về color_map với 6 hệ thống cố định (có cache)
    cache = None
    try:
        cache = current_app.extensions.get('cache')
    except (RuntimeError, AttributeError, KeyError):
        pass
    color_map = build_system_color_map(db.session, Camera, cache=cache)

    # Optimize: Parse all cameras in batch using list comprehension
    # This avoids N+1 query problem and improves performance
    cam_data = []
    for c in cameras:
        lat, lon = get_camera_coordinates(c)
        if lat is not None and lon is not None:
            system_type = c.system_type or "Chưa phân loại"
            cam_data.append({
                "id": c.id,
                "lat": lat,
                "lon": lon,
                "system": system_type,
                "color": color_map.get(system_type, "#94A3B8"),
                "owner": c.owner_name,
                "org": c.organization_name,
                "address": c.address_street,
                "ward": c.ward,
                "province": c.province,
                "phone": c.phone,
                "manufacturer": c.manufacturer
            })

    return render_template(
        "map/index.html",
        cameras=cam_data,
        focus_id=focus_id,
        color_map=color_map,
        return_url=return_url or "",  # Truyền return_url vào template
    )


@map_bp.route("/radius")
@login_required
def search_radius():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    radius = request.args.get("radius", type=float)

    results = []

    if lat is None or lon is None or radius is None:
        return jsonify([])

    min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius)
    if db.engine.dialect.name == "postgresql":
        cameras = Camera.query.filter(
            Camera.latitude.isnot(None),
            Camera.longitude.isnot(None),
            text(
                "ST_DWithin("
                "ST_SetSRID(ST_MakePoint(camera.longitude, camera.latitude), 4326)::geography, "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, "
                ":radius"
                ")"
            ),
        ).params(lat=lat, lon=lon, radius=radius).all()
    else:
        cameras = Camera.query.filter(
            Camera.latitude.isnot(None),
            Camera.longitude.isnot(None),
            Camera.latitude.between(min_lat, max_lat),
            Camera.longitude.between(min_lon, max_lon),
        ).all()
    # OPTIMIZE: Parse latlon once per camera
    for c in cameras:
        clat, clon = get_camera_coordinates(c)
        if clat is None or clon is None:
            continue
        d = distance_m(lat, lon, clat, clon)
        if d <= radius:
                results.append({
                    "id": c.id,
                    "lat": clat,
                    "lon": clon,
                    "name": c.owner_name or c.organization_name,
                    "distance": round(d)
                })

    return jsonify(results)


def point_to_line_distance(point_lat, point_lon, line_start_lat, line_start_lon, line_end_lat, line_end_lon):
    """
    Tính khoảng cách từ điểm đến đoạn thẳng trên mặt cầu (sử dụng Haversine)
    Tìm điểm gần nhất trên đoạn thẳng và tính khoảng cách đến điểm đó
    """
    # Nếu đoạn thẳng là một điểm, tính khoảng cách trực tiếp
    if abs(line_start_lat - line_end_lat) < 1e-6 and abs(line_start_lon - line_end_lon) < 1e-6:
        return distance_m(point_lat, point_lon, line_start_lat, line_start_lon)
    
    # Chia đoạn thẳng thành nhiều điểm và tìm điểm gần nhất
    # Sử dụng phương pháp chia nhỏ đoạn thẳng để tính gần đúng
    num_points = max(10, int(distance_m(line_start_lat, line_start_lon, line_end_lat, line_end_lon) / 10))
    min_dist = float('inf')
    
    for i in range(num_points + 1):
        t = i / num_points
        # Interpolate trên đường thẳng
        interp_lat = line_start_lat + t * (line_end_lat - line_start_lat)
        interp_lon = line_start_lon + t * (line_end_lon - line_start_lon)
        
        dist = distance_m(point_lat, point_lon, interp_lat, interp_lon)
        min_dist = min(min_dist, dist)
    
    return min_dist


@map_bp.route("/route")
@login_required
def search_route():
    """
    Tìm tuyến đường từ điểm A đến điểm B và các camera trên tuyến đường
    Sử dụng OSRM để tính toán tuyến đường
    """
    lat_a = request.args.get("lat_a", type=float)
    lon_a = request.args.get("lon_a", type=float)
    lat_b = request.args.get("lat_b", type=float)
    lon_b = request.args.get("lon_b", type=float)
    
    if not all([lat_a, lon_a, lat_b, lon_b]):
        return jsonify({"error": "Thiếu tọa độ điểm A hoặc B"}), 400
    
    # Sử dụng OSRM để tính toán tuyến đường
    # OSRM format: lon,lat (chú ý thứ tự)
    try:
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{lon_a},{lat_a};{lon_b},{lat_b}?overview=full&geometries=geojson"
        response = requests.get(osrm_url, timeout=10)
        route_data = response.json()
        
        if route_data.get("code") != "Ok" or not route_data.get("routes"):
            return jsonify({"error": "Không thể tính toán tuyến đường"}), 400
        
        route = route_data["routes"][0]
        geometry = route["geometry"]
        coordinates = geometry["coordinates"]  # [[lon, lat], ...]
        
        # Chuyển đổi sang format [lat, lon] cho Leaflet
        route_points = [[coord[1], coord[0]] for coord in coordinates]
        
        # Tìm các camera trên tuyến đường (trong phạm vi 50m từ tuyến)
        cameras_on_route = []
        cameras = Camera.query.filter(Camera.latlon.isnot(None)).all()
        
        for c in cameras:
            clat, clon = parse_latlon(c.latlon)
            if not clat or not clon:
                continue
            
            # Kiểm tra khoảng cách từ camera đến từng đoạn của tuyến đường
            min_distance = float('inf')
            for i in range(len(route_points) - 1):
                point1 = route_points[i]  # [lat, lon]
                point2 = route_points[i + 1]  # [lat, lon]
                
                # Tính khoảng cách từ camera đến đoạn thẳng
                dist = point_to_line_distance(clat, clon, point1[0], point1[1], point2[0], point2[1])
                min_distance = min(min_distance, dist)
            
            # Nếu camera nằm trong phạm vi 50m từ tuyến đường
            if min_distance <= 50:
                cameras_on_route.append({
                    "id": c.id,
                    "lat": clat,
                    "lon": clon,
                    "system": c.system_type or "Chưa phân loại",
                    "owner": c.owner_name,
                    "org": c.organization_name,
                    "address": c.address_street,
                    "ward": c.ward,
                    "province": c.province,
                    "distance_to_route": round(min_distance)
                })
        
        return jsonify({
            "route": route_points,
            "distance": round(route["distance"]),  # mét
            "duration": round(route["duration"]),  # giây
            "cameras": cameras_on_route
        })
        
    except (ValueError, KeyError, requests.RequestException, ConnectionError) as e:
        current_app.logger.error(f"Route calculation error: {e}", exc_info=True)
        return jsonify({"error": f"Lỗi khi tính toán tuyến đường: {str(e)}"}), 500
    except Exception as e:
        # Catch-all for unexpected errors
        current_app.logger.error(f"Unexpected error in route calculation: {e}", exc_info=True)
        return jsonify({"error": "Lỗi không xác định khi tính toán tuyến đường"}), 500
