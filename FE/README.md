# Quản lý hồ sơ nhân sự CCCD

## Chạy local

Chạy backend Flask theo hướng dẫn tại `BE/README.md`, sau đó mở
`http://localhost:8000/`. Không mở các tệp HTML bằng `file://`.

Để nhiều thiết bị cùng Wi-Fi dùng chung dữ liệu, chạy backend trên một máy
chủ và mở `http://<IPv4-máy-chủ>:8000/` từ các thiết bị khác. Cấu hình `HOST`,
`LOCAL_ONLY`, `ALLOWED_CLIENT_NETWORKS` và `ALLOWED_ORIGINS` trong `BE/.env`
theo hướng dẫn tại `BE/README.md`; dữ liệu được lưu tại cơ sở dữ liệu của máy
chủ, không phải trên từng thiết bị.

Nếu muốn phục vụ giao diện riêng ở cổng 5500, cần chạy đồng thời backend ở
cổng 8000 và frontend server trong `FE`:

```cmd
cd /d D:\cmnd\FE
python -m http.server 5500
```

Mở `http://localhost:5500/`. `ALLOWED_ORIGINS` trong `BE/.env` là các địa chỉ
frontend được phép gọi API; nó không tự khởi chạy server ở các cổng đó. Dùng
đúng cùng tên máy chủ cho giao diện và API (`localhost` với `localhost`, hoặc
`127.0.0.1` với `127.0.0.1`), đăng nhập, rồi thao tác như khi mở ở cổng 8000.

## Các trang

- `folders.html` / `js/folders.js` / `css/folder.css`: tìm, tạo, xóa và xuất
  danh sách thư mục; hệ thống giới hạn 100 thư mục.
- `profiles.html` / `js/profiles.js` / `css/profiles.css`: tìm hồ sơ, chọn và
  xóa nhiều hồ sơ, xuất Excel; mỗi thư mục tối đa 50 hồ sơ.
- `index.html` / `js/scan.js` / `css/scan.css`: quét CCCD, OCR, tạo hoặc sửa
  hồ sơ. Phần xử lý biểu mẫu và địa chỉ được dùng chung trong `js/app.js`.
- Luồng OCR đọc hai mặt, dùng QR để cập nhật các trường được hỗ trợ và kiểm
  tra MRZ TD1 khi check digit hợp lệ. Banner chỉ hiển thị địa chỉ HKTT từ OCR
  và QR; thông báo MRZ không hiển thị. Người dùng cần xác nhận đã rà soát kết
  quả trước khi lưu.
- Banner kết quả quét hiển thị HKTT OCR và địa chỉ trong QR; nếu hai địa chỉ
  khác nhau, địa chỉ QR được dùng cho HKTT. Thông tin đối chiếu MRZ không hiển
  thị trên banner.
- Dân tộc có danh sách đầy đủ 54 dân tộc; quốc tịch và địa chỉ dùng combobox
  tìm kiếm, tỉnh/thành và phường/xã lấy từ dữ liệu địa chỉ hiện có.
- Biểu mẫu hiển thị một trường “Nơi sinh / Nguyên quán”; dữ liệu hồ sơ cũ có
  hai trường riêng được gộp khi mở để không mất thông tin. OCR nhận diện
  “Quê quán / Place of origin” trên CCCD cũ và “Nơi đăng ký khai sinh /
  Place of birth” trên thẻ mới cho trường nguyên quán.
- Khi quét địa chỉ theo địa giới cũ, HKTT giữ nguyên địa chỉ trên giấy tờ;
  `addressMapping.json` chỉ chuyển địa chỉ tương ứng vào phần Chỗ ở hiện nay
  khi mapping có đích duy nhất; tự điền được bật mặc định. Tên phường, huyện
  và tỉnh được đối chiếu trực tiếp từ các phần chính xác trong chuỗi HKTT
  đầy đủ để sửa trường OCR tách sai. Nếu địa chỉ cũ thực sự bị chia thành
  nhiều phường mà dữ liệu không có chi tiết ranh giới, hệ thống không hỏi
  nhân viên và cũng không tự gán một đích thiếu căn cứ.
- Excel trong trang hồ sơ dùng thứ tự cột: STT, Họ, và, Tên, Ngày sinh, Giới tính,
  Nơi sinh / Nguyên quán, Quốc tịch, SĐT, Số CCCD, Ngày cấp, Nơi cấp, Địa chỉ
  thường trú, Địa chỉ hiện tại, Nhà thầu, Loại thợ, Bằng cấp/CC, Kinh nghiệm,
  Note. Toàn bộ ô dùng Times New Roman cỡ 13. Họ và đệm cũ được tách bằng từ
  đầu tiên làm Họ, phần còn lại làm cột “và”.

Mỗi trang gọi API backend để đọc và ghi dữ liệu nghiệp vụ. Dữ liệu CCCD không
được lưu trong `localStorage` hoặc `sessionStorage`. `config.js` chỉ chứa URL
API công khai; không đặt API key hay thông tin kết nối database tại frontend.
