import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps, ImageFilter, ImageEnhance

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 500


class PixelArtApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixel Art Converter Pro Max")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT + 250}")
        self.root.resizable(False, False)

        self.original_img = None
        self.pixel_img = None
        self.displayed_original = None
        self.displayed_pixel = None

        self._build_ui()

    # ----------------- Основні функції -----------------
    @staticmethod
    def to_pixel_art(img, pixel_size=16, num_colors=16):
        new_width = max(1, img.width // pixel_size)
        new_height = max(1, img.height // pixel_size)

        pixel_art = img.resize((new_width, new_height), resample=Image.Resampling.BOX)
        pixel_art = pixel_art.convert('P', palette=Image.ADAPTIVE, colors=num_colors)
        return pixel_art

    @staticmethod
    def resize_for_display(img, max_w, max_h):
        w_ratio = max_w / img.width
        h_ratio = max_h / img.height
        ratio = min(w_ratio, h_ratio)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        return img.resize(new_size, Image.Resampling.LANCZOS)

    def update_preview(self):
        if not self.original_img:
            return

        # Базовий піксель-арт
        pixel_size = self.pixel_size_scale.get()
        num_colors = self.num_colors_scale.get()
        self.pixel_img = self.to_pixel_art(self.original_img, pixel_size, num_colors)
        self.pixel_img = self.pixel_img.convert("RGB")

        # Додаткові ефекти
        if self.var_grayscale.get():
            self.pixel_img = self.pixel_img.convert("L").convert("RGB")
        if self.var_invert.get():
            self.pixel_img = ImageOps.invert(self.pixel_img)
        if self.var_outline.get():
            self.pixel_img = self.pixel_img.filter(ImageFilter.CONTOUR)
        if self.var_blur.get():
            self.pixel_img = self.pixel_img.filter(ImageFilter.BLUR)
        if self.var_sharpen.get():
            self.pixel_img = self.pixel_img.filter(ImageFilter.SHARPEN)
        if self.var_edge.get():
            self.pixel_img = self.pixel_img.filter(ImageFilter.EDGE_ENHANCE)
        if self.var_emboss.get():
            self.pixel_img = self.pixel_img.filter(ImageFilter.EMBOSS)
        if self.var_solarize.get():
            self.pixel_img = ImageOps.solarize(self.pixel_img, threshold=128)
        if self.var_posterize.get():
            self.pixel_img = ImageOps.posterize(self.pixel_img, bits=3)
        if self.var_mirror.get():
            self.pixel_img = ImageOps.mirror(self.pixel_img)
        if self.var_flip.get():
            self.pixel_img = ImageOps.flip(self.pixel_img)

        # Масштабування для прев’ю
        orig_disp = self.resize_for_display(self.original_img, WINDOW_WIDTH // 2, WINDOW_HEIGHT)
        pix_disp = self.resize_for_display(self.pixel_img, WINDOW_WIDTH // 2, WINDOW_HEIGHT)

        self.displayed_original = ImageTk.PhotoImage(orig_disp)
        self.displayed_pixel = ImageTk.PhotoImage(pix_disp)

        self.preview_original.config(image=self.displayed_original)
        self.preview_pixel.config(image=self.displayed_pixel)

    # ----------------- Події -----------------
    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg")]
        )
        if path:
            self.original_img = Image.open(path)
            self.update_preview()

    def save_image(self):
        if not self.pixel_img:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG files", "*.png")]
        )
        if path:
            self.pixel_img.save(path)
            messagebox.showinfo("Успіх", f"Збережено: {path}")

    def reset_image(self):
        if self.original_img:
            for var in self.effects_vars:
                var.set(False)
            self.pixel_size_scale.set(16)
            self.num_colors_scale.set(16)
            self.update_preview()

    # ----------------- GUI -----------------
    def _build_ui(self):
        tk.Button(self.root, text="Відкрити зображення", command=self.open_image).pack(pady=5)

        # Слайдери
        self.pixel_size_scale = tk.Scale(self.root, from_=1, to=64, orient="horizontal",
                                         label="Розмір пікселя", command=lambda e: self.update_preview())
        self.pixel_size_scale.set(16)
        self.pixel_size_scale.pack(fill="x", padx=20)

        self.num_colors_scale = tk.Scale(self.root, from_=2, to=256, orient="horizontal",
                                         label="Кількість кольорів", command=lambda e: self.update_preview())
        self.num_colors_scale.set(16)
        self.num_colors_scale.pack(fill="x", padx=20)

        # Ефекти
        effects_frame = tk.LabelFrame(self.root, text="Ефекти")
        effects_frame.pack(pady=5, fill="x", padx=20)

        self.var_grayscale = tk.BooleanVar()
        self.var_invert = tk.BooleanVar()
        self.var_outline = tk.BooleanVar()
        self.var_blur = tk.BooleanVar()
        self.var_sharpen = tk.BooleanVar()
        self.var_edge = tk.BooleanVar()
        self.var_emboss = tk.BooleanVar()
        self.var_solarize = tk.BooleanVar()
        self.var_posterize = tk.BooleanVar()
        self.var_mirror = tk.BooleanVar()
        self.var_flip = tk.BooleanVar()

        self.effects_vars = [
            self.var_grayscale, self.var_invert, self.var_outline,
            self.var_blur, self.var_sharpen, self.var_edge,
            self.var_emboss, self.var_solarize, self.var_posterize,
            self.var_mirror, self.var_flip
        ]

        effects = [
            ("Grayscale", self.var_grayscale),
            ("Invert", self.var_invert),
            ("Outline", self.var_outline),
            ("Blur", self.var_blur),
            ("Sharpen", self.var_sharpen),
            ("Edge Enhance", self.var_edge),
            ("Emboss", self.var_emboss),
            ("Solarize", self.var_solarize),
            ("Posterize", self.var_posterize),
            ("Mirror", self.var_mirror),
            ("Flip", self.var_flip)
        ]

        for i, (label, var) in enumerate(effects):
            tk.Checkbutton(effects_frame, text=label, variable=var,
                           command=self.update_preview).grid(row=i // 4, column=i % 4, padx=10, pady=3)

        # Кнопки
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Зберегти", command=self.save_image).grid(row=0, column=0, padx=10)
        tk.Button(btn_frame, text="Reset", command=self.reset_image).grid(row=0, column=1, padx=10)

        # Прев’ю
        preview_frame = tk.Frame(self.root)
        preview_frame.pack(pady=10)

        self.preview_original = tk.Label(preview_frame, text="Оригінал")
        self.preview_original.pack(side="left", padx=10)

        self.preview_pixel = tk.Label(preview_frame, text="Pixel Art")
        self.preview_pixel.pack(side="right", padx=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = PixelArtApp(root)
    root.mainloop()
