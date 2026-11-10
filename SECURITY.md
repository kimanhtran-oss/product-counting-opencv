# Chính sách bảo mật

## Phiên bản được hỗ trợ

Chỉ nhánh `main` (bản mới nhất) được cập nhật bản vá bảo mật.

| Phiên bản | Hỗ trợ |
|---|:---:|
| `main` | ✅ |
| Các commit cũ hơn | ❌ |

## Báo cáo lỗ hổng

**Vui lòng không mở Issue công khai cho lỗ hổng bảo mật.**

Hãy báo cáo riêng qua tính năng *Private vulnerability reporting* của GitHub:

1. Vào tab **Security and quality** của repo.
2. Chọn **Report a vulnerability**, hoặc mở trực tiếp: <https://github.com/kimanhtran-oss/product-counting-opencv/security/advisories/new>

Nội dung báo cáo nên có:

- Mô tả lỗ hổng và ảnh hưởng có thể xảy ra.
- Các bước tái hiện, kèm file mẫu nếu có (ví dụ một file ảnh làm chương trình lỗi).
- Phiên bản Python, OpenCV và hệ điều hành đang dùng.

Mình sẽ phản hồi trong vòng **7 ngày** và thông báo tiến độ khắc phục. Người báo cáo sẽ được ghi nhận trong bản vá nếu đồng ý.

## Phạm vi

Thuộc phạm vi:

- Code trong repo: `modules/count.py`, `count_gui.py`, `evaluate.py`.
- Cách chương trình xử lý file ảnh/video đầu vào.

Không thuộc phạm vi:

- Lỗ hổng bên trong thư viện bên thứ ba (OpenCV, NumPy, Pillow). Hãy báo cho dự án gốc. Repo này theo dõi các lỗ hổng đó qua Dependabot và sẽ nâng phiên bản khi có bản vá.

## Mô hình đe dọa

Đây là ứng dụng desktop chạy cục bộ, không có mạng, không lưu dữ liệu người dùng. Điểm tiếp xúc chính với dữ liệu không tin cậy là **file ảnh/video người dùng mở**.

| Mối đe dọa | Biện pháp |
|---|---|
| File độc hại đổi đuôi thành `.jpg`, `.png`... | Kiểm tra **magic bytes**, từ chối file có đuôi không khớp nội dung |
| *Decompression bomb*: file nhỏ nhưng khai báo kích thước ảnh cực lớn | Đọc kích thước từ header trước khi giải nén, giới hạn 50 triệu điểm ảnh |
| File quá lớn làm cạn bộ nhớ | Giới hạn 50 MB với ảnh, 500 MB với video |
| Lỗ hổng trong bộ giải mã ảnh/video của thư viện | Dependabot cảnh báo và tự đề xuất nâng cấp thư viện |
| Thư viện có CVE đã công bố | `pip-audit` quét `requirements.txt` mỗi lần push và hằng tuần |
| Lỗi bảo mật trong code Python | CodeQL và Bandit (phân tích mã tĩnh) |
| Lộ khóa bí mật (token, mật khẩu) khi commit | GitHub Secret scanning |
| Workflow CI bị lạm dụng quyền | Workflow chỉ cấp quyền `contents: read` |

Các biện pháp kiểm tra file đầu vào được kiểm thử tự động trong `tests/test_kiem_tra_file.py`.