TÁCH APP.JS THÀNH CÁC MODULE NHỎ

Cấu trúc trong FE:
  js/
    app.js                         # file khởi động chính, ít chỉnh sửa
    services/
      ocrDataService.js            # chuẩn hóa payload OCR
      ocrAddressService.js         # phân tích địa chỉ, mapping, điền form OCR
    controllers/
      profileController.js         # mở/đóng modal, sửa và lưu hồ sơ
    components/                    # giữ nguyên
    addressMapping.js              # giữ nguyên

CÁCH CÀI:
1. Sao lưu FE/js/app.js hiện tại.
2. Thay FE/js/app.js bằng app.js trong gói.
3. Chép thư mục services/ vào FE/js/services/.
4. Chép thư mục controllers/ vào FE/js/controllers/.
5. Không thay đổi components/, addressMapping.js hoặc dữ liệu JSON.
6. Đảm bảo HTML vẫn nạp app.js bằng type="module", ví dụ:
   <script type="module" src="./js/app.js"></script>

QUY TẮC CHỈNH SỬA:
- OCR trả dữ liệu sai cấu trúc: services/ocrDataService.js
- Địa chỉ/mapping/điền trường OCR: services/ocrAddressService.js
- Modal, sửa hồ sơ, lưu hồ sơ: controllers/profileController.js
- app.js: chủ yếu giữ vai trò nối các module và khởi động ứng dụng.

KIỂM TRA:
Mở terminal tại thư mục FE và chạy:
  node --check js/app.js
  node --check js/services/ocrDataService.js
  node --check js/services/ocrAddressService.js
  node --check js/controllers/profileController.js

node --check chỉ kiểm tra cú pháp. Sau đó chạy bằng Live Server/HTTP server,
mở F12 > Console và thử upload CCCD, chỉnh sửa và lưu hồ sơ.
