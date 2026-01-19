# 📷 SENTRIX - Hệ thống Quản lý Camera An ninh

Hệ thống quản lý và tra cứu camera an ninh được xây dựng bằng Flask, hỗ trợ import/export dữ liệu theo định dạng M2 chuẩn.

## ✨ Tính năng

- 📊 **Dashboard**: Thống kê tổng quan về camera theo hệ thống và địa phương
- 🔍 **Tra cứu camera**: Tìm kiếm với nhiều bộ lọc nâng cao
- 🗺️ **Bản đồ số**: Hiển thị vị trí camera trên bản đồ, tìm kiếm theo bán kính
- 📥 **Import dữ liệu**: Import từ file Excel (định dạng M2)
- 📤 **Export dữ liệu**: Export với tùy chọn các trường cần thiết
- 👥 **Quản lý người dùng**: Phân quyền admin/viewer

## 🚀 Cài đặt

### Yêu cầu hệ thống

- Python 3.8+
- pip (Python package manager)

### Các bước cài đặt

1. **Clone repository hoặc tải source code**

2. **Tạo virtual environment (khuyến nghị)**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Cài đặt dependencies**
```bash
pip install -r requirements.txt
```

4. **Cấu hình môi trường (tùy chọn)**
Tạo file `.env` hoặc set environment variables:
```bash
# Windows (PowerShell)
$env:SECRET_KEY="your-secret-key-here"
$env:FLASK_ENV="development"
$env:DATABASE_URL="sqlite:///sentrix.db"

# Linux/Mac
export SECRET_KEY="your-secret-key-here"
export FLASK_ENV="development"
export DATABASE_URL="sqlite:///sentrix.db"
```

**Lưu ý**: Trong production, **BẮT BUỘC** phải set `SECRET_KEY` qua environment variable!

5. **Khởi tạo database và tạo admin**
```bash
# Tạo database
python -c "from app import app; from models import db; app.app_context().push(); db.create_all()"

# Tạo tài khoản admin mặc định (username: admin, password: 123456)
python create_admin.py
```

6. **Chạy ứng dụng**
```bash
python app.py
```

Ứng dụng sẽ chạy tại: `http://localhost:5000`

## 🔐 Đăng nhập

- **Tài khoản admin mặc định** (sau khi chạy `create_admin.py`):
  - Username: `admin`
  - Password: `123456`
  
**⚠️ QUAN TRỌNG**: Hãy đổi mật khẩu ngay sau lần đăng nhập đầu tiên!

## 📁 Cấu trúc thư mục

```
Sentrix/
├── app.py                 # File chính khởi tạo ứng dụng
├── config.py              # Cấu hình ứng dụng
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── create_admin.py        # Script tạo admin user
│
├── auth.py                # Authentication (login/logout)
├── dashboard.py           # Dashboard thống kê
├── camera.py              # Tra cứu camera
├── map_view.py            # Bản đồ số
├── import_data.py         # Import dữ liệu
├── export.py              # Export dữ liệu
├── user_admin.py          # Quản lý người dùng
├── about.py               # Trang giới thiệu
├── parse_m2.py            # Parser file M2
│
├── templates/             # HTML templates
│   ├── layout/
│   │   └── base.html      # Base template
│   ├── auth/
│   ├── dashboard/
│   ├── camera/
│   ├── map/
│   ├── import/
│   ├── export/
│   ├── user/
│   ├── about/
│   └── errors/
│
├── static/                # Static files (CSS, images)
│   ├── css/
│   └── images/
│
├── uploads/               # Thư mục lưu file upload
└── instance/
    └── sentrix.db        # SQLite database
```

## 🔧 Cấu hình

File `config.py` chứa các cấu hình cho ứng dụng:

- **Development**: Debug mode bật, secret key mặc định
- **Production**: Debug mode tắt, yêu cầu SECRET_KEY từ env
- **Testing**: Database trong memory

Để chọn môi trường, set biến `FLASK_ENV`:
```bash
export FLASK_ENV=production  # hoặc development, testing
```

## 📝 Sử dụng

### Import dữ liệu

1. Vào menu **Quản lý dữ liệu > Import dữ liệu**
2. Chọn file Excel (định dạng M2)
3. Click **Upload** và chờ xử lý
4. Hệ thống sẽ báo số lượng camera đã import thành công/lỗi

### Tra cứu camera

1. Vào menu **Tra cứu camera**
2. Điền các thông tin cần tìm (tên chủ sở hữu, địa chỉ, tỉnh/thành, v.v.)
3. Click **Tìm kiếm**
4. Xem kết quả và click vào camera để xem chi tiết

### Export dữ liệu

1. Vào menu **Quản lý dữ liệu > Export dữ liệu**
2. Chọn các trường cần export
3. Click **Export** để tải file Excel

### Bản đồ số

1. Vào menu **Bản đồ số**
2. Xem các camera trên bản đồ (camera có tọa độ)
3. Click vào marker để xem thông tin
4. Tìm kiếm theo bán kính: Click vào bản đồ, nhập bán kính (mét)

## 🛠️ Development

### Chạy với debug mode
```bash
export FLASK_ENV=development
python app.py
```

### Tạo migration (nếu cần)
Hiện tại sử dụng `db.create_all()`. Để production tốt hơn, nên dùng Flask-Migrate:
```bash
pip install Flask-Migrate
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## 🐛 Xử lý lỗi

Ứng dụng có các error handlers:
- **404**: Trang không tồn tại
- **403**: Không có quyền truy cập
- **500**: Lỗi máy chủ

## 🔒 Bảo mật

### Checklist cho Production

- [ ] ✅ Đặt `SECRET_KEY` qua environment variable (BẮT BUỘC)
- [ ] ✅ Đổi mật khẩu admin mặc định
- [ ] ✅ Sử dụng HTTPS/SSL
- [ ] ✅ Tắt debug mode (`FLASK_ENV=production`)
- [ ] ✅ Cấu hình database phù hợp (không dùng SQLite cho production lớn)
- [ ] ✅ Backup database định kỳ
- [ ] ✅ Thiết lập rate limiting (có thể dùng Flask-Limiter)
- [ ] ✅ Logging và monitoring

## 📦 Dependencies

- **Flask**: Web framework
- **Flask-Login**: Authentication
- **Flask-SQLAlchemy**: ORM
- **Werkzeug**: Security utilities (password hashing)
- **pandas**: Xử lý dữ liệu Excel
- **openpyxl**: Đọc file Excel
- **xlsxwriter**: Ghi file Excel

Xem chi tiết trong `requirements.txt`

## 👥 Phân quyền

- **Admin**: 
  - Xem tất cả chức năng
  - Import/Export dữ liệu
  - Quản lý người dùng
  
- **Viewer**: 
  - Xem dashboard
  - Tra cứu camera
  - Xem bản đồ số
  - Không thể import/export hoặc quản lý user

## 📄 License

Dự án này được phát triển cho KT7 – PA06 Thanh Hóa

## 🤝 Đóng góp

Nếu phát hiện bug hoặc có đề xuất cải thiện, vui lòng tạo issue hoặc pull request.

## 📞 Liên hệ

SENTRIX © 2025
KT7 – PA06 Thanh Hóa

---

**Lưu ý**: Đây là phiên bản đã được cải thiện với các bug đã được sửa và các tính năng nâng cao hơn. Xem file `DANH_GIA_CHUONG_TRINH.md` để biết chi tiết về các cải thiện.

