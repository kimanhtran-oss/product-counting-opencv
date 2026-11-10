"""
Đánh giá độ chính xác trên toàn bộ dataset.

Chạy mỗi ảnh hai lần: với tham số mặc định và với tham số đã chỉnh
(lưu trong dataset/ground_truth.json), rồi in bảng kết quả dạng Markdown.

Cách dùng:
    python evaluate.py                 # in bảng kết quả
    python evaluate.py --save results  # lưu thêm ảnh kết quả vào thư mục results/
"""
import os
import json
import argparse

from modules.count import doc_anh, ghi_anh, dem_san_pham

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")


def do_chinh_xac(n, t):
    # Cùng công thức với giao diện: max(0, 1 - |N - T| / T)
    return max(0.0, 1 - abs(n - t) / t) * 100


def mo_ta_tham_so(tham_so):
    if not tham_so:
        return "mặc định"
    ten = {"min_area": "min_area", "k": "k", "phep_toan": "", "connectivity": "lân cận", "vat_sang": "vật sáng"}
    phan = []
    for khoa, gia_tri in tham_so.items():
        if khoa == "phep_toan":
            phan.append(str(gia_tri))
        elif khoa == "vat_sang":
            phan.append("vật sáng hơn nền" if gia_tri else "vật tối hơn nền")
        else:
            phan.append(f"{ten.get(khoa, khoa)} = {gia_tri}")
    return ", ".join(phan)


def main():
    parser = argparse.ArgumentParser(description="Đánh giá độ chính xác đếm sản phẩm trên dataset")
    parser.add_argument("--save", metavar="THU_MUC", help="lưu ảnh kết quả (tham số đã chỉnh) vào thư mục này")
    args = parser.parse_args()

    with open(os.path.join(DATASET_DIR, "ground_truth.json"), encoding="utf-8") as f:
        nhan = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

    if args.save:
        os.makedirs(args.save, exist_ok=True)

    dong = []
    tong_md = tong_cx = 0.0
    dung_md = dung_cx = 0
    for ten_file, thong_tin in sorted(nhan.items()):
        anh = doc_anh(os.path.join(DATASET_DIR, ten_file))
        if anh is None:
            print(f"Bỏ qua {ten_file}: không đọc được ảnh")
            continue
        t = thong_tin["so_thuc_te"]
        tham_so = thong_tin.get("tham_so", {})

        n_md = dem_san_pham(anh)["so_san_pham"]
        kq = dem_san_pham(anh, **tham_so)
        n_cx = kq["so_san_pham"]

        cx_md, cx_cx = do_chinh_xac(n_md, t), do_chinh_xac(n_cx, t)
        tong_md += cx_md
        tong_cx += cx_cx
        dung_md += n_md == t
        dung_cx += n_cx == t
        dong.append(f"| `{ten_file}` | {t} | {n_md} ({cx_md:.1f}%) | {n_cx} ({cx_cx:.1f}%) | {mo_ta_tham_so(tham_so)} |")

        if args.save:
            ghi_anh(os.path.join(args.save, ten_file.rsplit(".", 1)[0] + "_ket_qua.png"), kq["ket_qua"])

    so_anh = len(dong)
    print("| Ảnh | Thực tế | Mặc định | Đã chỉnh | Tham số đã chỉnh |")
    print("|---|:---:|:---:|:---:|---|")
    print("\n".join(dong))
    print(f"| **Tổng kết** | | **{dung_md}/{so_anh} đúng · TB {tong_md / so_anh:.1f}%** "
          f"| **{dung_cx}/{so_anh} đúng · TB {tong_cx / so_anh:.1f}%** | |")


if __name__ == "__main__":
    main()
