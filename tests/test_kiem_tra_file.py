"""
Kiểm thử hàm kiem_tra_file() với các file hợp lệ và file độc hại giả lập.

Chạy: python -m unittest discover tests -v
"""
import os
import sys
import struct
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.count import kiem_tra_file  # noqa: E402

DATASET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")


def tao_png_gia(rong, cao):
    # Tạo file PNG chỉ có phần đầu (header) khai báo kích thước rong x cao.
    # Dùng để giả lập "decompression bomb": file vài chục byte nhưng tự nhận là ảnh khổng lồ.
    def chunk(loai, du_lieu):
        return struct.pack(">I", len(du_lieu)) + loai + du_lieu + struct.pack(">I", zlib.crc32(loai + du_lieu))
    ihdr = struct.pack(">IIBBBBB", rong, cao, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")


class TestKiemTraFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def ghi(self, ten, noi_dung):
        path = os.path.join(self.tmp.name, ten)
        with open(path, "wb") as f:
            f.write(noi_dung)
        return path

    def test_anh_dataset_hop_le(self):
        for ten in os.listdir(DATASET):
            if ten.lower().endswith((".jpg", ".png")):
                hop_le, _, loi = kiem_tra_file(os.path.join(DATASET, ten))
                self.assertTrue(hop_le, f"{ten}: {loi}")

    def test_file_khong_ton_tai(self):
        self.assertFalse(kiem_tra_file(os.path.join(self.tmp.name, "khong_co.jpg"))[0])

    def test_file_rong(self):
        self.assertFalse(kiem_tra_file(self.ghi("rong.jpg", b""))[0])

    def test_file_text_doi_duoi_thanh_jpg(self):
        # Kẻ tấn công đổi tên script thành .jpg để lừa người dùng mở
        path = self.ghi("virus.jpg", b"import os\nos.system('echo hacked')\n")
        hop_le, loai, _ = kiem_tra_file(path)
        self.assertFalse(hop_le)
        self.assertIsNone(loai)

    def test_duoi_khong_khop_noi_dung(self):
        # Nội dung là PNG nhưng đuôi là .bmp
        hop_le, loai, _ = kiem_tra_file(self.ghi("anh.bmp", tao_png_gia(10, 10)))
        self.assertFalse(hop_le)
        self.assertEqual(loai, "png")

    def test_decompression_bomb(self):
        # Header khai báo 100000 x 100000 = 10 tỷ điểm ảnh
        hop_le, _, loi = kiem_tra_file(self.ghi("bomb.png", tao_png_gia(100_000, 100_000)))
        self.assertFalse(hop_le)
        self.assertIn("quá lớn", loi)

    def test_anh_vua_gioi_han_van_hop_le(self):
        hop_le, _, loi = kiem_tra_file(self.ghi("vua.png", tao_png_gia(1920, 1080)))
        self.assertTrue(hop_le, loi)


if __name__ == "__main__":
    unittest.main()