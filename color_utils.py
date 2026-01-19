SYSTEM_PALETTE = [
    "#2563EB",  # blue
    "#10B981",  # green
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#A855F7",  # purple
    "#14B8A6",  # teal
]


def build_system_color_map(session, Camera, cache=None):
    """
    Trả về map {system_type: color} với thứ tự ổn định (alphabetical)
    để dùng chung giữa dashboard và bản đồ.
    Có hỗ trợ caching để tối ưu performance.
    """
    cache_key = 'system_color_map'
    
    # Thử lấy từ cache nếu có
    if cache:
        try:
            cached_map = cache.get(cache_key)
            if cached_map:
                return cached_map
        except (AttributeError, TypeError):
            # Cache chưa được init hoặc không phải Cache object
            pass
    
    systems = [
        (row[0] or "Chưa phân loại")
        for row in session.query(Camera.system_type).distinct().all()
    ]
    systems = sorted(set(systems))

    color_map = {}
    for idx, name in enumerate(systems):
        color_map[name] = SYSTEM_PALETTE[idx % len(SYSTEM_PALETTE)]
    
    # Lưu vào cache (10 phút vì ít thay đổi)
    if cache:
        try:
            cache.set(cache_key, color_map, timeout=600)
        except (AttributeError, TypeError):
            # Cache chưa được init hoặc không phải Cache object
            pass
    
    return color_map

