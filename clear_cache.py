"""
Script để clear cache khi cần (ví dụ sau khi import dữ liệu mới)

Usage:
    python clear_cache.py
"""

from app import app

def clear_all_cache():
    """Clear tất cả cache"""
    with app.app_context():
        try:
            cache = app.extensions.get('cache')
            if cache and hasattr(cache, 'clear'):
                cache.clear()
                print("✅ Đã xóa tất cả cache!")
            else:
                print("⚠️ Cache chưa được khởi tạo")
        except Exception as e:
            print(f"❌ Lỗi khi xóa cache: {e}")

def clear_specific_cache():
    """Clear các cache keys cụ thể"""
    with app.app_context():
        try:
            cache = app.extensions.get('cache')
            if cache and hasattr(cache, 'delete'):
                cache.delete('dashboard_stats')
                cache.delete('system_color_map')
                print("✅ Đã xóa cache cho dashboard và system color map!")
            else:
                print("⚠️ Cache chưa được khởi tạo")
        except Exception as e:
            print(f"❌ Lỗi khi xóa cache: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--specific':
        clear_specific_cache()
    else:
        clear_all_cache()
