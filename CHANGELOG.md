# 📝 CHANGELOG - Các thay đổi và cải thiện

## 🚀 Các Cải Thiện Mới Nhất (2025)

### 1. **Pagination cho kết quả tìm kiếm và danh sách users**
- ✅ **camera.py**: Thêm pagination cho kết quả tìm kiếm camera (50 items/trang)
- ✅ **user_admin.py**: Thêm pagination cho danh sách users
- ✅ **templates/camera/search.html**: 
  - Chuyển form từ POST sang GET để hỗ trợ pagination tốt hơn
  - Thêm pagination controls với navigation buttons
  - Giữ lại tất cả filter khi chuyển trang
  - Hiển thị tổng số kết quả và số trang
- ✅ **templates/user/manage.html**: Thêm pagination controls cho danh sách users
- ✅ Cải thiện UX: Form giữ lại giá trị đã nhập sau khi search

### 2. **Logging System**
- ✅ **app.py**: Thêm logging với RotatingFileHandler
- ✅ Log file được lưu trong thư mục `logs/sentrix.log`
- ✅ Tự động rotate khi file đạt 10MB, giữ lại 10 file backup
- ✅ Chỉ enable logging trong production (không phải debug mode)

### 3. **Bug Fixes**
- ✅ **camera.py**: Thêm import `jsonify` từ flask (thiếu import gây lỗi khi gọi API stream-info)

---

## ✅ Đã sửa các Bug Nghiêm Trọng

### 1. **user_admin.py** - Lỗi tên field password
- **Vấn đề**: Dòng 41 sử dụng `password_hash` nhưng model có field `password`
- **Hậu quả**: Không thể tạo user mới từ admin panel
- **Đã sửa**: ✅ Đổi `password_hash` → `password`

### 2. **camera.py** - Trường không tồn tại trong export
- **Vấn đề**: 
  - Dòng 85: `c.storage_days` → nên là `c.retention_days`
  - Dòng 98: `c.share_methods` → nên là `c.sharing_scope`
- **Hậu quả**: Export sẽ bị lỗi AttributeError
- **Đã sửa**: ✅ Sửa tên field và format đúng cho sharing_scope

### 3. **templates/camera/detail2.html** - Trường không tồn tại
- **Vấn đề**: Dòng 34 sử dụng `camera.storage_days` → nên là `camera.retention_days`
- **Hậu quả**: Hiển thị lỗi khi xem chi tiết camera
- **Đã sửa**: ✅ Đổi thành `camera.retention_days`

---

## 🎨 Các Cải Thiện Đã Thực Hiện

### 1. **Cải thiện hiển thị JSON fields**
- ✅ **camera.py**: Thêm logic format JSON fields trong detail view
- ✅ **templates/camera/detail2.html**: Hiển thị JSON fields dưới dạng danh sách có dấu phẩy thay vì raw JSON string
- ✅ Thêm hiển thị "—" cho các trường rỗng
- ✅ Thêm hiển thị field "Khu vực lắp đặt" và "Chia sẻ" trong template

### 2. **Configuration Management**
- ✅ **Tạo config.py**: 
  - Hỗ trợ Development, Production, Testing configs
  - Secret key từ environment variable
  - Các cấu hình tập trung (upload folder, max file size, etc.)
- ✅ **app.py**: Sử dụng config từ config.py thay vì hardcode

### 3. **Bảo mật**
- ✅ **Secret Key**: Sử dụng environment variable với fallback
- ✅ **Production Config**: Yêu cầu SECRET_KEY trong production
- ✅ **File Upload**: Thêm validation kích thước file

### 4. **Error Handling**
- ✅ **Tạo error templates**: 
  - `templates/errors/404.html` - Trang không tồn tại
  - `templates/errors/500.html` - Lỗi máy chủ
  - `templates/errors/403.html` - Không có quyền
- ✅ **app.py**: Thêm error handlers (@app.errorhandler)

### 5. **Validation dữ liệu**
- ✅ **import_data.py**: 
  - Thêm validate latlon format
  - Thêm validate phone number
  - Validate file size
  - Sử dụng config cho upload folder và allowed extensions

### 6. **Export**
- ✅ **export.py**: Cải thiện hiển thị tên cột bằng tiếng Việt trong Excel

### 7. **Documentation**
- ✅ **requirements.txt**: Tạo file với tất cả dependencies
- ✅ **README.md**: Hướng dẫn chi tiết cài đặt, sử dụng, và deployment
- ✅ **CHANGELOG.md**: File này - ghi lại tất cả thay đổi

---

## 📦 Files Mới Được Tạo

1. `config.py` - Configuration management
2. `requirements.txt` - Python dependencies
3. `README.md` - Documentation
4. `CHANGELOG.md` - Change log (file này)
5. `templates/errors/404.html` - 404 error page
6. `templates/errors/500.html` - 500 error page
7. `templates/errors/403.html` - 403 error page

---

## 📝 Files Đã Được Sửa Đổi

1. `app.py` - Sử dụng config, thêm error handlers
2. `user_admin.py` - Fix bug password field
3. `camera.py` - Fix export bug, cải thiện detail view
4. `templates/camera/detail2.html` - Fix bug, cải thiện hiển thị JSON
5. `import_data.py` - Thêm validation, sử dụng config
6. `export.py` - Cải thiện hiển thị tên cột

---

## 🔄 Breaking Changes

**KHÔNG CÓ** - Tất cả các thay đổi đều tương thích ngược.

Tuy nhiên, khi deploy production:
- **Cần set** `SECRET_KEY` qua environment variable
- **Nên set** `FLASK_ENV=production`
- **Nên đổi** mật khẩu admin mặc định

---

## 🚀 Migration Guide

### Từ phiên bản cũ sang phiên bản mới:

1. **Cài đặt dependencies mới** (nếu có):
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables** (production):
   ```bash
   export SECRET_KEY="your-secret-key"
   export FLASK_ENV="production"
   ```

3. **Database không cần migrate** - Schema giữ nguyên

4. **Chạy lại ứng dụng**:
   ```bash
   python app.py
   ```

---

## ⚠️ Lưu Ý

- **Secret Key**: Trong development vẫn dùng default key, nhưng production **BẮT BUỘC** phải set qua env
- **Error Pages**: Các error pages mới cần có base template, nên đảm bảo `templates/layout/base.html` tồn tại
- **Validation**: Validation mới có thể từ chối một số dữ liệu cũ không hợp lệ khi import lại

---

## 📅 Ngày cập nhật

**Phiên bản hiện tại**: 2.1 (Pagination & Logging)
**Ngày**: 2025

### Phiên bản 2.1 (2025)
- ✅ Thêm pagination cho camera search và user list
- ✅ Thêm logging system
- ✅ Fix missing import jsonify

### Phiên bản 2.0 (2025)
- ✅ Fix các bugs nghiêm trọng
- ✅ Cải thiện configuration management
- ✅ Thêm error handling
- ✅ Cải thiện validation
