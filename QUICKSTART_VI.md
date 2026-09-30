# Chạy nhanh trên Windows

Mở PowerShell tại thư mục repo. Cần Python 3.10 trở lên; không cần `pip install`.

```powershell
py --version
py analyze.py sample.csv --out out --data-kind synthetic
Start-Process .\out\report.html
py -m unittest discover -s tests -v
```

Nếu không có `py`, dùng `python` tương ứng. Nếu `out` đã chứa report thì chọn thư mục mới,
ví dụ `--out out2`; chương trình không ghi đè report hiện có.

Sample có 8 frame và 3 ID, hoàn toàn tổng hợp. Đọc định dạng CSV và giới hạn trong README.md.
Khoảng thời gian giữa bản ghi cùng ID không phải processing time trên MCU.

Workflow GitHub được cấu hình chạy trên Windows và Linux. Trạng thái CI chỉ được xác nhận
sau khi workflow thực sự chạy; kết quả local trước đó nằm trong VERIFICATION.md.
