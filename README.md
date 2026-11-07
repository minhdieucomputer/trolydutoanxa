# Trợ lý dự toán ngân sách xã 0.5 – bản thử nghiệm

- Chọn nguồn gốc cấp dự toán bằng danh sách, xem hướng dẫn bên cạnh.
- Gợi ý tài khoản Nợ/Có chỉ với tình huống cấp 0 được mô tả trong CV 15602 (2017); cần kiểm tra hiệu lực hiện hành.
- Tìm từ khóa Loại/Khoản từ danh mục trích chọn TT130/2025, sửa đổi TT123/2026.
- Chọn Chương và mã loại dự toán thủ công; không tự điền khi thiếu căn cứ.
- Bốn mẫu C6 nguyên bản người dùng gửi nằm trong templates và có nút Mở mẫu C6 gốc. **Chưa tự điền trực tiếp lên biểu mẫu C6**. Xuất bảng đối chiếu từ nghiệp vụ vẫn là bản dự thảo.
- Mẫu C và phụ lục 47/48 theo TT26 chưa được ánh xạ chính thức.
- Dữ liệu lưu ở ~/TroLyDuToanXa/du_toan_xa.sqlite3; hãy sao lưu trước khi nâng cấp.

## Tạo Setup.exe
Tải toàn bộ mã nguồn lên GitHub (bao gồm thư mục templates và .github), chọn Actions → Build Windows installer → Run workflow, tải artifact sau khi hoàn thành. Chưa kiểm thử trên Windows.


## 0.5.1 – Danh mục mã loại dự toán + tooltip
- Thêm `budget_catalog.py` (thư viện chuẩn Python, không cần cài thêm).
- Di chuột lên các ô mã để xem tên/căn cứ; chọn mã từ cửa sổ tra cứu.
- Tự phân tích nguồn từ diễn giải và tự chọn mã loại dự toán **chỉ khi** danh mục CSV có quy tắc đã đối chiếu.
- CSV lưu trong thư mục dữ liệu cá nhân, không bị mất khi nâng cấp ứng dụng.
- Danh mục mã loại dự toán ban đầu để trống vì chưa có bảng mã chính thức được xác minh; cần bổ sung trước khi dùng tự chọn mã.
- Các mẫu C6 gốc giữ nguyên, chưa tự điền theo ô chính thức.


## 0.5.2 – Tra cứu Loại/Khoản theo diễn giải
- Danh mục `mlns_loai_khoan.csv`: 110 Khoản được trích từ Phụ lục II văn bản hợp nhất do người dùng cung cấp, có tên và ghi chú.
- `mlns_matcher.py` xếp hạng các Khoản theo diễn giải, từ đồng nghĩa, tên và ghi chú.
- Các mã 121, 314, 315 đã bị bãi bỏ theo TT123/2026 không đưa vào gợi ý.
- Kết quả chỉ là đề xuất, phải xác nhận trước khi điền mã. Tên mã hiển thị khi di chuột.
- Không tự xác nhận trường hợp đa lĩnh vực, mua sắm hoặc sửa chữa có bản chất nhiệm vụ chưa rõ.
- Mã loại dự toán TABMIS tiếp tục dựa vào danh mục CSV do cán bộ kiểm tra và bổ sung; không suy đoán mã số.
- Phiếu C6 gốc được lưu nguyên trạng, chưa có tự động điền đầy đủ vào biểu mẫu.
