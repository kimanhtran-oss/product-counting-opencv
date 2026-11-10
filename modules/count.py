import os
import cv2
import numpy as np


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
