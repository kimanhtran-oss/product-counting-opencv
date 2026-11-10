import os
import cv2
import numpy as np
from PIL import Image


# ---------------- KIỂM TRA FILE ĐẦU VÀO (BẢO MẬT) ----------------
# Không tin vào đuôi file: đọc vài byte đầu (magic bytes) để biết file thật sự là gì.
CHU_KY_ANH = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"BM": "bmp",
    b"II*\x00": "tif",
    b"MM\x00*": "tif",
}
DUOI_HOP_LE = {
    "png": (".png",), "jpg": (".jpg", ".jpeg"), "bmp": (".bmp",), "tif": (".tif", ".tiff"),
    "mp4": (".mp4", ".mov"), "avi": (".avi",),
}
MAX_DUNG_LUONG_ANH = 50 * 1024 * 1024       # 50 MB
MAX_DUNG_LUONG_VIDEO = 500 * 1024 * 1024    # 500 MB
MAX_SO_DIEM_ANH = 50_000_000                # 50 triệu điểm ảnh (~ 8000 x 6000)


def nhan_dang_file(dau_file):
    # Trả về loại file dựa trên magic bytes, không khớp thì trả về None
    for chu_ky, loai in CHU_KY_ANH.items():
        if dau_file.startswith(chu_ky):
            return loai
    if dau_file[4:8] in (b"ftyp", b"moov", b"mdat", b"wide", b"free"):
        return "mp4"
    if dau_file[:4] == b"RIFF" and dau_file[8:12] == b"AVI ":
        return "avi"
    return None


def kiem_tra_file(path):
    # Kiểm tra file trước khi đưa cho OpenCV xử lý.
    # Trả về (hợp lệ, loại file, thông báo lỗi)
    if not os.path.isfile(path):
        return False, None, "File không tồn tại."
    dung_luong = os.path.getsize(path)
    if dung_luong == 0:
        return False, None, "File rỗng."

    with open(path, "rb") as f:
        dau_file = f.read(16)
    loai = nhan_dang_file(dau_file)
    if loai is None:
        return False, None, "Nội dung file không phải ảnh/video được hỗ trợ."

    duoi = os.path.splitext(path)[1].lower()
    if duoi not in DUOI_HOP_LE[loai]:
        return False, loai, f"Đuôi file {duoi} không khớp với nội dung thật ({loai})."

    la_video = loai in ("mp4", "avi")
    gioi_han = MAX_DUNG_LUONG_VIDEO if la_video else MAX_DUNG_LUONG_ANH
    if dung_luong > gioi_han:
        return False, loai, f"File quá lớn (giới hạn {gioi_han // (1024 * 1024)} MB)."

    if not la_video:
        # Đọc kích thước từ phần đầu file, chưa giải nén ảnh,
        # để chặn "decompression bomb" (file nhỏ nhưng giải nén ra cực lớn)
        try:
            with Image.open(path) as im:
                rong, cao = im.size
        except Image.DecompressionBombError:
            return False, loai, "Ảnh quá lớn, nghi là decompression bomb."
        except Exception:
            return False, loai, "File ảnh bị hỏng hoặc không đọc được."
        if rong * cao > MAX_SO_DIEM_ANH:
            return False, loai, f"Ảnh quá lớn ({rong} x {cao} điểm ảnh)."

    return True, loai, ""


def doc_anh(path):
    # Đọc ảnh, chạy được cả đường dẫn có dấu tiếng Việt (cv2.imread bị lỗi trên Windows)
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def ghi_anh(path, anh):
    # Ghi ảnh, chạy được cả đường dẫn có dấu tiếng Việt
    duoi = os.path.splitext(path)[1]
    if duoi == "":
        duoi = ".png"
    ok, buf = cv2.imencode(duoi, anh)
    if ok:
        buf.tofile(path)
    return ok


def to_mau_nhan(labels, n):
    # Tô mỗi nhãn một màu ngẫu nhiên, nhãn 0 (nền) để đen
    np.random.seed(3)
    mau = np.random.randint(60, 256, (n, 3)).astype(np.uint8)
    mau[0] = 0
    return mau[labels]


def dem_san_pham(anh, min_area=300, k=3, phep_toan="Opening + Closing",
                 connectivity=8, vat_sang=False):
    # 1. Chuyển ảnh xám và làm mờ khử nhiễu
    gray = cv2.cvtColor(anh, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Ngưỡng Otsu: vật tối trên nền sáng dùng BINARY_INV, vật sáng trên nền tối dùng BINARY
    if vat_sang:
        kieu = cv2.THRESH_BINARY + cv2.THRESH_OTSU
    else:
        kieu = cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    _, mask_otsu = cv2.threshold(gray, 0, 255, kieu)

    # 3. Morphology theo phép toán và kích thước kernel
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    mask = mask_otsu.copy()
    if phep_toan in ("Opening", "Opening + Closing"):
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    if phep_toan in ("Closing", "Opening + Closing"):
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    if phep_toan == "Erode":
        mask = cv2.erode(mask, kernel)
    if phep_toan == "Dilate":
        mask = cv2.dilate(mask, kernel)

    # 4. Connected Components (4 hoặc 8 lân cận)
    n, labels, stats, centers = cv2.connectedComponentsWithStats(mask, connectivity=connectivity)

    # 5. Lọc vùng nhỏ hơn min_area, vẽ bounding box và đánh số
    ket_qua = anh.copy()
    co_chu = max(0.6, anh.shape[1] / 900)      # cỡ chữ theo kích thước ảnh
    do_day = max(2, anh.shape[1] // 300)
    dien_tich = []
    for i in range(1, n):  # Nhãn 0 là nền
        x, y, w, h, area = stats[i]
        if area < min_area:
            continue
        dien_tich.append(int(area))
        so = len(dien_tich)
        cv2.rectangle(ket_qua, (x, y), (x + w, y + h), (0, 200, 0), do_day)
        cv2.putText(ket_qua, str(so), (x, max(20, y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, co_chu, (0, 0, 255), do_day)

    # 6. Trả về kết quả từng bước để hiển thị trước/sau
    kq = {
        "so_san_pham": len(dien_tich),
        "so_vung": n - 1,              # số vùng trước khi lọc min_area
        "dien_tich": dien_tich,
        "mask_otsu": mask_otsu,
        "mask": mask,
        "anh_nhan": to_mau_nhan(labels, n),
        "ket_qua": ket_qua,
    }
    return kq


def thong_ke(dien_tich):
    # Thống kê diện tích các sản phẩm: tổng, trung bình, nhỏ nhất, lớn nhất, độ lệch chuẩn
    if len(dien_tich) == 0:
        return 0, 0, 0, 0, 0
    a = np.array(dien_tich)
    return int(a.sum()), float(a.mean()), int(a.min()), int(a.max()), float(a.std())