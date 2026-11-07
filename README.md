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


## Phiên bản 0.5.3 — danh sách gợi ý trực tiếp trên màn hình nghiệp vụ
- Mã Loại và mã Khoản là Combobox: danh sách mã và tên, sắp xếp gợi ý từ diễn giải lên đầu.
- Với gợi ý đủ điểm và không mơ hồ, phần mềm tự điền Loại/Khoản; người dùng có thể chọn lại.
- Mã loại dự toán là Combobox từ danh mục CSV đã kiểm chứng nằm tại `~/TroLyDuToanXa/danh_muc_ma_loai_du_toan.csv`. Danh mục này **chưa có mã chính thức**, nên không có mã để tự điền cho đến khi người sử dụng bổ sung dữ liệu đã kiểm tra. Không được tự đặt mã.
- Di chuột lên các ô mã để xem tên/ghi chú. Không tự xác nhận hạch toán.
- GitHub Actions kiểm tra có CSV và đóng gói thư mục templates nếu có.


## Bản 0.5.4 — gom nhiều nghiệp vụ trước khi tạo phiếu

- Trong tab **Nhập nghiệp vụ**, nhập diễn giải và số tiền rồi chọn **Thêm nghiệp vụ vào bộ phiếu**. Dòng sẽ chuyển vào tab **Bộ 3 chứng từ / Phụ lục QĐ**.
- Lặp lại cho từng nghiệp vụ. Có thể xóa dòng trong bảng tổng hợp.
- Sau khi đủ dòng, nhập số và ngày quyết định, chọn **Tạo phiếu và quyết định từ toàn bộ nghiệp vụ**, chọn C6/Quyết định/Phụ lục muốn xuất.
- Các file Excel xuất ra là **bảng dự thảo để đối chiếu**, không phải mẫu C6 hoặc quyết định đã ánh xạ chuẩn. Có thêm các cột mã loại dự toán, TK Nợ/Có và nguồn gốc dự toán để kiểm soát.
- **Quan trọng:** `MA_LOAI_DU_TOAN_HUONG_DAN.csv` và `~/TroLyDuToanXa/danh_muc_ma_loai_du_toan.csv` hiện chỉ có tiêu đề, chưa có mã số đã kiểm chứng. Do đó không thể tự suy ra **mã số loại dự toán** dù đã nhận diện được cụm “giao đầu năm”, “bổ sung”, “tăng thu”. Phải bổ sung mã chính thức và điều kiện áp dụng vào CSV, sau đó nhấn **Nạp lại danh mục CSV**. Không tự gán mã giả.
- Trước khi sử dụng thực tế, cần đối chiếu hiệu lực quy tắc Công văn 15602 và các văn bản hiện hành.


## Bản 0.5.8 – xem trước và gom nghiệp vụ
- Nút đưa từng nghiệp vụ vào bộ phiếu/quyết định, xem trước nghiệp vụ hiện tại.
- Xem trước danh sách nghiệp vụ tổng hợp, tổng tiền, tô hồng dòng thiếu mã.
- Sửa dòng đã chọn trước khi xuất, chọn mẫu C6/Mẫu C/47/48 trong cửa sổ xuất.
- Xem trước là **bảng dữ liệu dự thảo**, không phải bản xem trước bố cục mẫu chứng từ chính thức.
