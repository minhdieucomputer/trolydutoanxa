# Trợ lý dự toán ngân sách xã — dự án tạo Setup.exe

Đây là **dự án đóng gói**, không phải tệp Setup.exe đã biên dịch. Môi trường tạo gói hiện tại không phải Windows, nên chưa thể tạo và kiểm thử tệp cài đặt Windows.

## Tạo Setup.exe bằng GitHub Actions (không cần cài Python trên máy của người sử dụng)

1. Tạo repository GitHub mới, tải toàn bộ nội dung thư mục này lên repository, giữ nguyên thư mục `.github/workflows`.
2. Mở tab **Actions**, chọn **Build Windows installer**, bấm **Run workflow**.
3. Sau khi hoàn tất, tải artifact `Setup_TroLyDuToanXa_Win11` và giải nén lấy `Setup_TroLyDuToanXa_Win11.exe`.
4. Chép file Setup.exe sang máy Windows 11, nhấp đúp để cài. Máy cài **không cần Python** và không cần mạng để cài.

GitHub Actions cần kết nối mạng để tải thư viện lúc xây dựng. Gói này chưa được ký mã (code signing), nên Windows có thể cảnh báo nhà phát hành không xác định.

## Tạo Setup.exe trên Windows trực tiếp

Cài Python 3.12 và Inno Setup 6 trên máy **dùng để đóng gói** (không phải máy cài), rồi chạy `TAO_SETUP_TREN_WINDOWS.bat`.

## Dữ liệu và giới hạn

Dữ liệu lưu trong thư mục `TroLyDuToanXa` của tài khoản Windows, không bị xóa khi gỡ ứng dụng. Đây là bản thử nghiệm 0.1; chưa có bộ quy tắc hạch toán tự động đã được thẩm định, chưa nhập đầy đủ danh mục MLNS và chưa xuất mẫu C6 chính thức. Không kết nối TABMIS.

## Cập nhật 0.2 (06/11/2026)
- Nút **Thoát** có xác nhận; nút X của cửa sổ cũng đóng kết nối cơ sở dữ liệu.
- Tab **Tra cứu MLNS / Gợi ý mã ngành**: tra cứu mẫu mã Loại/Khoản, tìm bằng mã, tên hoặc từ khóa nghiệp vụ.
- Trong tab nhập nghiệp vụ, bấm **Gợi ý mã ngành từ diễn giải**, sau đó chọn mã và **Đưa mã Loại / Khoản vào phiếu**.
- Dữ liệu Loại/Khoản hiện là **danh mục mẫu có giới hạn**; chưa bao gồm toàn bộ Phụ lục II hoặc các phần Chương, Mục/Tiểu mục. Không tự coi kết quả là định khoản chính thức.
- Để có Setup.exe: build trên Windows 10/11 x64 bằng TAO_SETUP_TREN_WINDOWS.bat hoặc GitHub Actions. ZIP này **không chứa Setup.exe đã biên dịch**.
