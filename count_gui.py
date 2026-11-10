import os
import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from modules.count import doc_anh, ghi_anh, dem_san_pham, thong_ke

# Thư mục chứa file code: dataset luôn tìm theo đường dẫn này, chạy từ thư mục nào cũng được
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CHE_DO_XEM = ("Kết quả đếm", "Mask Otsu (trước Morphology)", "Mask sau Morphology", "Ảnh nhãn (Connected Components)")


class DemSanPhamApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ỨNG DỤNG ĐẾM SẢN PHẨM - XỬ LÝ ẢNH SỐ (PROJECT 2)")
        # Kích thước cửa sổ vừa với màn hình (laptop 1366x768 hoặc màn hình phóng to 125-150%)
        rong = min(1350, self.root.winfo_screenwidth() - 40)
        cao = min(860, self.root.winfo_screenheight() - 80)
        self.root.geometry(f"{rong}x{cao}+10+10")
        self.root.minsize(900, 560)
        self.root.configure(bg="#fff5f7")

        self.dataset_dir = os.path.join(BASE_DIR, "dataset")
        if not os.path.exists(self.dataset_dir):
            os.makedirs(self.dataset_dir)

        self.anh_goc = None
        self.kq = None
        self.photo_goc = self.photo_kq = None
        self.is_video = False
        self.video_path = None
        self._hen_gio = None

        self._giao_dien()
        self.load_dataset_files()

    def _giao_dien(self):
        # --- CỘT TRÁI: BẢNG ĐIỀU KHIỂN & CHỌN DATASET (có thanh cuộn khi màn hình thấp) ---
        khung_trai = tk.Frame(self.root, bg="#fce7f0", width=300)
        khung_trai.pack(side="left", fill="y")
        khung_trai.pack_propagate(False)
        self.canvas_menu = tk.Canvas(khung_trai, bg="#fce7f0", highlightthickness=0, width=282)
        thanh_cuon = tk.Scrollbar(khung_trai, orient="vertical", command=self.canvas_menu.yview)
        self.canvas_menu.configure(yscrollcommand=thanh_cuon.set)
        thanh_cuon.pack(side="right", fill="y")
        self.canvas_menu.pack(side="left", fill="both", expand=True)
        menu = tk.Frame(self.canvas_menu, bg="#fce7f0")
        self.canvas_menu.create_window((0, 0), window=menu, anchor="nw", width=282)
        menu.bind("<Configure>", self._cap_nhat_cuon)
        self.canvas_menu.bind_all("<MouseWheel>", self._lan_chuot)

        tk.Label(menu, text="ĐẾM SẢN PHẨM", bg="#fce7f0", fg="#831843",
                 font=("Arial", 16, "bold")).pack(pady=(12, 0))
        tk.Label(menu, text="Chủ đề 4 - Project 2", bg="#fce7f0", fg="#db2777", font=("Arial", 9)).pack(pady=(0, 6))

        # Nhóm chọn Dataset và Tệp
        self._tieu_de(menu, "NGUỒN DỮ LIỆU")
        ds_frame = tk.Frame(menu, bg="#fce7f0")
        ds_frame.pack(fill="x", padx=15, pady=2)
        self.combo_dataset = ttk.Combobox(ds_frame, state="readonly", width=19)
        self.combo_dataset.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.combo_dataset.bind("<<ComboboxSelected>>", self.chon_anh_dataset)
        tk.Button(ds_frame, text="🔄", command=self.load_dataset_files, bg="#f472b6", fg="white", relief="flat", width=3).pack(side="right")

        self._button(menu, "📁  Mở ảnh/video từ máy", self.mo_file_ngoai)
        self._button(menu, "▶  Thực thi đếm sản phẩm", self.xu_ly)
        self._button(menu, "💾  Lưu ảnh kết quả", self.luu_ket_qua)
        self._button(menu, "▦  Lưu Mask nhị phân", self.luu_mask)

        # Tham số xử lý (đổi tham số là tự chạy lại)
        self._tieu_de(menu, "THAM SỐ XỬ LÝ")
        self._nhan(menu, "Diện tích tối thiểu (Min Area):")
        self.min_area = tk.StringVar(value="300")
        o_min = tk.Entry(menu, textvariable=self.min_area, width=25)
        o_min.pack(anchor="w", padx=15, pady=2)
        o_min.bind("<Return>", self.cap_nhat)
        o_min.bind("<FocusOut>", self.cap_nhat)

        self._nhan(menu, "Kích thước Kernel:")
        self.kernel = tk.IntVar(value=3)
        self._combo(menu, self.kernel, (3, 5, 7, 9))

        self._nhan(menu, "Phép toán Morphology:")
        self.morph = tk.StringVar(value="Opening + Closing")
        self._combo(menu, self.morph, ("Không", "Opening", "Closing", "Opening + Closing", "Erode", "Dilate"))

        self._nhan(menu, "Liên thông (Connected Components):")
        self.connectivity = tk.IntVar(value=8)
        self._combo(menu, self.connectivity, (4, 8))

        self.vat_sang = tk.BooleanVar(value=False)
        tk.Checkbutton(menu, text="Vật sáng hơn nền (đảo ngưỡng)", variable=self.vat_sang,
                       command=self.cap_nhat, bg="#fce7f0", fg="#831843", activebackground="#fce7f0",
                       font=("Arial", 9)).pack(anchor="w", padx=12, pady=(4, 0))

        self._nhan(menu, "Hiển thị bên phải:")
        self.che_do = tk.StringVar(value=CHE_DO_XEM[0])
        self._combo(menu, self.che_do, CHE_DO_XEM)

        # Số lượng thực tế để đánh giá độ chính xác
        self._nhan(menu, "Số sản phẩm thực tế (để đánh giá):")
        self.so_thuc_te = tk.StringVar(value="")
        o_nhap = tk.Entry(menu, textvariable=self.so_thuc_te, width=25)
        o_nhap.pack(anchor="w", padx=15, pady=2)
        o_nhap.bind("<Return>", self.cap_nhat)
        o_nhap.bind("<FocusOut>", self.cap_nhat)

        self._button(menu, "↻  Đặt lại tham số mặc định", self.dat_lai)

        # --- KHUNG BÊN PHẢI: HIỂN THỊ HÌNH ẢNH & THỐNG KÊ ---
        main = tk.Frame(self.root, bg="#fff5f7")
        main.pack(side="right", fill="both", expand=True)

        head = tk.Frame(main, bg="#fff5f7")
        head.pack(fill="x", padx=20, pady=(15, 10))
        tk.Label(head, text="Giao diện Phân tích & Trực quan hóa", bg="#fff5f7",
                 fg="#831843", font=("Arial", 18, "bold")).pack(side="left")
        self.status = tk.Label(head, text="Chưa chọn tệp dữ liệu", bg="#fff5f7", fg="#9d174d", font=("Arial", 10))
        self.status.pack(side="right")

        # Thanh thống kê đặt ở đáy trước, để luôn hiện dù ảnh lớn
        footer = tk.Frame(main, bg="white", highlightbackground="#fbcfe8", highlightthickness=1)
        footer.pack(side="bottom", fill="x", padx=18, pady=(8, 12))

        self.dem_label = tk.Label(footer, text="Số sản phẩm: --", bg="white",
                                  fg="#9d174d", font=("Arial", 14, "bold"))
        self.dem_label.pack(side="left", padx=16, pady=10)

        self.info = tk.Label(footer, text="Vui lòng chọn ảnh trong Dataset hoặc mở file từ máy.", bg="white",
                             fg="#701a75", font=("Arial", 10), justify="left", anchor="w", wraplength=700)
        self.info.pack(side="left", fill="x", expand=True, padx=(0, 16), pady=6)
        footer.bind("<Configure>", self._chinh_dong_chu)

        panels = tk.Frame(main, bg="#fff5f7")
        panels.pack(fill="both", expand=True, padx=18, pady=5)
        panels.columnconfigure((0, 1), weight=1)
        panels.rowconfigure(0, weight=1)

        self.khung_goc = self._panel(panels, "ẢNH ĐẦU VÀO (INPUT)")
        self.khung_goc.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.khung_kq = self._panel(panels, "KẾT QUẢ ĐẾM & BOUNDING BOX")
        self.khung_kq.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # Đổi kích thước cửa sổ thì vẽ lại ảnh cho vừa khung
        panels.bind("<Configure>", self._ve_lai)

    def _chinh_dong_chu(self, event):
        # Dòng thống kê tự xuống hàng theo độ rộng cửa sổ
        self.info.configure(wraplength=max(300, event.width - 260))

    def _cap_nhat_cuon(self, event):
        self.canvas_menu.configure(scrollregion=self.canvas_menu.bbox("all"))

    def _lan_chuot(self, event):
        self.canvas_menu.yview_scroll(int(-event.delta / 120), "units")

    def _ve_lai(self, event=None):
        # Chờ 0.2 giây sau khi kéo cửa sổ xong mới vẽ lại
        if self._hen_gio is not None:
            self.root.after_cancel(self._hen_gio)
        self._hen_gio = self.root.after(200, self._ve_lai_anh)

    def _ve_lai_anh(self):
        self._hen_gio = None
        if self.khung_goc.anh is not None:
            self.hien_anh(self.khung_goc, self.khung_goc.anh, "goc")
        if self.khung_kq.anh is not None:
            self.hien_anh(self.khung_kq, self.khung_kq.anh, "kq")

    def _tieu_de(self, parent, text):
        tk.Label(parent, text=text, bg="#fce7f0", fg="#9d174d",
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=15, pady=(8, 2))

    def _nhan(self, parent, text):
        tk.Label(parent, text=text, bg="#fce7f0", fg="#831843", font=("Arial", 9)).pack(anchor="w", padx=15, pady=(3, 0))

    def _combo(self, parent, bien, gia_tri):
        cb = ttk.Combobox(parent, textvariable=bien, values=gia_tri, state="readonly", width=32)
        cb.pack(anchor="w", padx=15, pady=2)
        cb.bind("<<ComboboxSelected>>", self.cap_nhat)

    def _button(self, parent, text, command):
        tk.Button(parent, text=text, command=command, anchor="w", bg="#db2777",
                  fg="white", activebackground="#be185d", relief="flat",
                  font=("Arial", 9, "bold"), padx=12, pady=5,
                  cursor="hand2").pack(fill="x", padx=15, pady=2)

    def _panel(self, parent, title):
        frame = tk.Frame(parent, bg="white", highlightbackground="#fbcfe8", highlightthickness=1)
        frame.pack_propagate(False)   # ảnh không làm khung phình to
        frame.anh = None
        frame.title = tk.Label(frame, text=title, bg="white", fg="#831843", font=("Arial", 10, "bold"))
        frame.title.pack(anchor="w", padx=12, pady=8)
        frame.label = tk.Label(frame, text="[ Chưa có dữ liệu hiển thị ]", bg="#fffbfe",
                               fg="#db2777", font=("Arial", 11))
        frame.label.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return frame

    def hien_anh(self, frame, anh, ben):
        # Co ảnh vừa với khung đang hiển thị
        frame.anh = anh
        self.root.update_idletasks()
        max_w = frame.label.winfo_width() - 10
        max_h = frame.label.winfo_height() - 10
        if max_w < 100 or max_h < 100:
            max_w, max_h = 480, 420
        h, w = anh.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        anh_rs = cv2.resize(anh, (int(w * scale), int(h * scale)))
        if len(anh_rs.shape) == 2:
            pil = Image.fromarray(anh_rs)
        else:
            pil = Image.fromarray(cv2.cvtColor(anh_rs, cv2.COLOR_BGR2RGB))
        photo = ImageTk.PhotoImage(pil)
        frame.label.configure(image=photo, text="")
        frame.label.image = photo
        if ben == "goc":
            self.photo_goc = photo
        else:
            self.photo_kq = photo

    def load_dataset_files(self):
        if os.path.exists(self.dataset_dir):
            valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".mp4", ".avi", ".mov")
            files = [f for f in os.listdir(self.dataset_dir) if f.lower().endswith(valid_exts)]
            files.sort()
            self.combo_dataset['values'] = files
            if files:
                self.combo_dataset.current(0)
                self.chon_anh_dataset(None)

    def chon_anh_dataset(self, event):
        file_name = self.combo_dataset.get()
        if file_name:
            path = os.path.join(self.dataset_dir, file_name)
            self.doc_va_hien_thi_file(path)

    def mo_file_ngoai(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Tệp Ảnh & Video", "*.png *.jpg *.jpeg *.bmp *.mp4 *.avi *.mov"),
            ("Ảnh", "*.png *.jpg *.jpeg *.bmp"),
            ("Video", "*.mp4 *.avi *.mov")
        ])
        if path:
            self.doc_va_hien_thi_file(path)

    def doc_va_hien_thi_file(self, path):
        ext = path.lower()
        if ext.endswith(('.mp4', '.avi', '.mov')):
            # Video: lấy khung hình đầu tiên để xử lý
            cap = cv2.VideoCapture(path)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                messagebox.showerror("Lỗi", "Không thể đọc khung hình từ video.")
                return
            self.is_video = True
            self.video_path = path
            self.anh_goc = frame
            self.status.configure(text=f"[Video] {os.path.basename(path)} - khung hình đầu")
        else:
            anh = doc_anh(path)
            if anh is None:
                messagebox.showerror("Lỗi", "Không thể đọc được tệp hình ảnh.")
                return
            self.is_video = False
            self.video_path = None
            self.anh_goc = anh
            self.status.configure(text=os.path.basename(path))

        self.kq = None
        self.hien_anh(self.khung_goc, self.anh_goc, "goc")
        self.khung_kq.anh = None
        self.khung_kq.title.configure(text="KẾT QUẢ ĐẾM & BOUNDING BOX")
        self.khung_kq.label.configure(image="", text="Nhấn 'Thực thi đếm sản phẩm' để chạy thuật toán")
        self.dem_label.configure(text="Số sản phẩm: --")
        self.info.configure(text=f"Kích thước: {self.anh_goc.shape[1]} × {self.anh_goc.shape[0]} px")

    def lay_tham_so(self):
        return dict(min_area=self.doc_min_area(), k=int(self.kernel.get()), phep_toan=self.morph.get(),
                    connectivity=int(self.connectivity.get()), vat_sang=self.vat_sang.get())

    def doc_min_area(self):
        # Đọc ô Min Area, nhập sai (chữ, số âm) thì dùng mặc định 300
        gia_tri = self.min_area.get().strip()
        if gia_tri.isdigit():
            return int(gia_tri)
        self.min_area.set("300")
        return 300

    def cap_nhat(self, *args):
        # Đổi tham số thì tự chạy lại nếu đã có kết quả
        if self.anh_goc is not None and self.kq is not None:
            self.xu_ly()

    def xu_ly(self):
        if self.anh_goc is None:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng chọn ảnh từ Dataset hoặc mở tệp từ máy trước.")
            return

        self.kq = dem_san_pham(self.anh_goc, **self.lay_tham_so())

        # Hiển thị ảnh theo chế độ xem (trước/sau từng kỹ thuật)
        che_do = self.che_do.get()
        if che_do == CHE_DO_XEM[1]:
            anh, ten = self.kq["mask_otsu"], "MASK OTSU - TRƯỚC MORPHOLOGY"
        elif che_do == CHE_DO_XEM[2]:
            anh, ten = self.kq["mask"], f"MASK SAU MORPHOLOGY ({self.morph.get()}, k = {self.kernel.get()})"
        elif che_do == CHE_DO_XEM[3]:
            anh, ten = self.kq["anh_nhan"], f"ẢNH NHÃN - {self.kq['so_vung']} VÙNG ({self.connectivity.get()}-LÂN CẬN)"
        else:
            anh, ten = self.kq["ket_qua"], "KẾT QUẢ ĐẾM & BOUNDING BOX"
        self.khung_kq.title.configure(text=ten)
        self.hien_anh(self.khung_kq, anh, "kq")

        # Thống kê diện tích
        count = self.kq["so_san_pham"]
        tong, tb, nho, lon, lech = thong_ke(self.kq["dien_tich"])
        self.dem_label.configure(text=f"Số sản phẩm: {count}")
        dong1 = f"Vùng trước lọc: {self.kq['so_vung']}  |  Sau lọc min_area: {count}  |  Tổng diện tích: {tong} px²"
        dong2 = f"Trung bình: {tb:.1f} px²  |  Nhỏ nhất: {nho}  |  Lớn nhất: {lon}  |  Độ lệch chuẩn: {lech:.1f}"

        # Đánh giá độ chính xác nếu có nhập số thực tế
        thuc_te = self.so_thuc_te.get().strip()
        if thuc_te.isdigit() and int(thuc_te) > 0:
            t = int(thuc_te)
            do_chinh_xac = max(0, 1 - abs(count - t) / t) * 100
            dong2 += f"  |  Thực tế: {t} → độ chính xác {do_chinh_xac:.1f}%"
        self.info.configure(text=dong1 + "\n" + dong2)

    def luu_ket_qua(self):
        if self.kq is None:
            messagebox.showwarning("Chưa có kết quả", "Hãy chạy đếm sản phẩm trước khi lưu.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not path:
            return
        # Lưu ảnh kết quả đang hiển thị bên phải (kết quả đếm, mask hoặc ảnh nhãn)
        che_do = self.che_do.get()
        if che_do == CHE_DO_XEM[1]:
            anh = self.kq["mask_otsu"]
        elif che_do == CHE_DO_XEM[2]:
            anh = self.kq["mask"]
        elif che_do == CHE_DO_XEM[3]:
            anh = self.kq["anh_nhan"]
        else:
            anh = self.kq["ket_qua"]
        if ghi_anh(path, anh):
            messagebox.showinfo("Thành công", "Đã lưu ảnh thành công.")

    def luu_mask(self):
        if self.kq is None:
            messagebox.showwarning("Chưa có Mask", "Hãy chạy đếm sản phẩm trước khi lưu Mask.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path and ghi_anh(path, self.kq["mask"]):
            messagebox.showinfo("Thành công", "Đã lưu ảnh Mask nhị phân thành công.")

    def dat_lai(self):
        self.min_area.set("300")
        self.kernel.set(3)
        self.morph.set("Opening + Closing")
        self.connectivity.set(8)
        self.vat_sang.set(False)
        self.che_do.set(CHE_DO_XEM[0])
        if self.anh_goc is not None:
            self.xu_ly()


if __name__ == "__main__":
    root = tk.Tk()
    app = DemSanPhamApp(root)
    root.mainloop()
