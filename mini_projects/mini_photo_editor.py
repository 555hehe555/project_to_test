import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageOps, ImageFilter, ImageEnhance, ImageDraw
import cv2
import numpy as np

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700


class PhotoEditorPro:
    def __init__(self, root):
        self.root = root
        self.root.title("Професійний фоторедактор Pro Max Ultra")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(True, False)

        self.original_img = None
        self.current_img = None
        self.displayed_img = None
        self.history = []
        self.history_position = -1

        # Для Paint
        self.drawing = False
        self.last_x = None
        self.last_y = None
        self.brush_color = "#000000"
        self.brush_size = 5
        self.canvas_img = None
        self.draw_obj = None

        self._build_ui()

    # ==================== ОСНОВНІ ФУНКЦІЇ ====================

    def add_to_history(self, img):
        """Додає зображення в історію для undo/redo"""
        if self.history_position < len(self.history) - 1:
            self.history = self.history[:self.history_position + 1]
        self.history.append(img.copy())
        self.history_position += 1
        if len(self.history) > 20:  # Обмеження історії
            self.history.pop(0)
            self.history_position -= 1

    def undo(self):
        if self.history_position > 0:
            self.history_position -= 1
            self.current_img = self.history[self.history_position].copy()
            self.update_preview()

    def redo(self):
        if self.history_position < len(self.history) - 1:
            self.history_position += 1
            self.current_img = self.history[self.history_position].copy()
            self.update_preview()

    @staticmethod
    def resize_for_display(img, max_w, max_h):
        w_ratio = max_w / img.width
        h_ratio = max_h / img.height
        ratio = min(w_ratio, h_ratio)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        return img.resize(new_size, Image.Resampling.LANCZOS)

    def update_preview(self):
        if not self.current_img:
            return

        display_img = self.resize_for_display(self.current_img, WINDOW_WIDTH - 50, WINDOW_HEIGHT - 200)
        self.displayed_img = ImageTk.PhotoImage(display_img)
        self.preview_label.config(image=self.displayed_img)
        self.update_info_label()

    def update_info_label(self):
        if self.current_img:
            info = f"Розмір: {self.current_img.width}x{self.current_img.height} | Режим: {self.current_img.mode}"
            self.info_label.config(text=info)

    # ==================== РОБОТА З ФАЙЛАМИ ====================

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Зображення", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp")]
        )
        if path:
            self.original_img = Image.open(path)
            self.current_img = self.original_img.copy()
            self.history = [self.current_img.copy()]
            self.history_position = 0
            self.update_preview()

    def save_image(self):
        if not self.current_img:
            messagebox.showwarning("Увага", "Немає зображення для збереження!")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")]
        )
        if path:
            self.current_img.save(path)
            messagebox.showinfo("Успіх", f"Збережено: {path}")

    def reset_image(self):
        if self.original_img:
            self.current_img = self.original_img.copy()
            self.history = [self.current_img.copy()]
            self.history_position = 0
            self.update_preview()

    # ==================== ВКЛАДКА 1: ОСНОВНИЙ РЕДАКТОР ====================

    def resize_image(self):
        if not self.current_img:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Змінити розмір")
        dialog.geometry("300x200")

        tk.Label(dialog, text="Ширина:").pack(pady=5)
        width_entry = tk.Entry(dialog)
        width_entry.insert(0, str(self.current_img.width))
        width_entry.pack()

        tk.Label(dialog, text="Висота:").pack(pady=5)
        height_entry = tk.Entry(dialog)
        height_entry.insert(0, str(self.current_img.height))
        height_entry.pack()

        keep_ratio = tk.BooleanVar(value=True)
        tk.Checkbutton(dialog, text="Зберігати пропорції", variable=keep_ratio).pack(pady=5)

        def apply_resize():
            try:
                w = int(width_entry.get())
                h = int(height_entry.get())
                self.add_to_history(self.current_img)
                self.current_img = self.current_img.resize((w, h), Image.Resampling.LANCZOS)
                self.update_preview()
                dialog.destroy()
            except:
                messagebox.showerror("Помилка", "Невірні значення!")

        tk.Button(dialog, text="Застосувати", command=apply_resize).pack(pady=10)

    def upscale_image(self):
        """AI upscaling через OpenCV"""
        if not self.current_img:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("AI Upscale")
        dialog.geometry("300x150")

        tk.Label(dialog, text="Множник збільшення:").pack(pady=10)
        scale_var = tk.IntVar(value=2)
        tk.Spinbox(dialog, from_=2, to=4, textvariable=scale_var).pack()

        def apply_upscale():
            try:
                scale = scale_var.get()
                self.add_to_history(self.current_img)

                # Конвертація PIL -> OpenCV
                img_cv = cv2.cvtColor(np.array(self.current_img), cv2.COLOR_RGB2BGR)

                # Upscaling через EDSR або Bicubic
                h, w = img_cv.shape[:2]
                upscaled = cv2.resize(img_cv, (w * scale, h * scale),
                                      interpolation=cv2.INTER_CUBIC)

                # Конвертація назад у PIL
                self.current_img = Image.fromarray(cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB))
                self.update_preview()
                dialog.destroy()
                messagebox.showinfo("Готово", f"Зображення збільшено в {scale}x")
            except Exception as e:
                messagebox.showerror("Помилка", str(e))

        tk.Button(dialog, text="Збільшити", command=apply_upscale).pack(pady=10)

    def crop_image(self):
        if not self.current_img:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Обрізати зображення")
        dialog.geometry("400x200")

        tk.Label(dialog, text="Ліво:").grid(row=0, column=0, padx=5, pady=5)
        left_entry = tk.Entry(dialog)
        left_entry.insert(0, "0")
        left_entry.grid(row=0, column=1)

        tk.Label(dialog, text="Верх:").grid(row=1, column=0, padx=5, pady=5)
        top_entry = tk.Entry(dialog)
        top_entry.insert(0, "0")
        top_entry.grid(row=1, column=1)

        tk.Label(dialog, text="Право:").grid(row=2, column=0, padx=5, pady=5)
        right_entry = tk.Entry(dialog)
        right_entry.insert(0, str(self.current_img.width))
        right_entry.grid(row=2, column=1)

        tk.Label(dialog, text="Низ:").grid(row=3, column=0, padx=5, pady=5)
        bottom_entry = tk.Entry(dialog)
        bottom_entry.insert(0, str(self.current_img.height))
        bottom_entry.grid(row=3, column=1)

        def apply_crop():
            try:
                box = (int(left_entry.get()), int(top_entry.get()),
                       int(right_entry.get()), int(bottom_entry.get()))
                self.add_to_history(self.current_img)
                self.current_img = self.current_img.crop(box)
                self.update_preview()
                dialog.destroy()
            except:
                messagebox.showerror("Помилка", "Невірні координати!")

        tk.Button(dialog, text="Обрізати", command=apply_crop).grid(row=4, column=0, columnspan=2, pady=10)

    def rotate_image(self):
        if not self.current_img:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Повернути зображення")
        dialog.geometry("300x150")

        tk.Label(dialog, text="Кут (градуси):").pack(pady=10)
        angle_var = tk.IntVar(value=90)
        tk.Scale(dialog, from_=-180, to=180, orient="horizontal", variable=angle_var).pack(fill="x", padx=20)

        def apply_rotate():
            self.add_to_history(self.current_img)
            self.current_img = self.current_img.rotate(angle_var.get(), expand=True)
            self.update_preview()
            dialog.destroy()

        tk.Button(dialog, text="Повернути", command=apply_rotate).pack(pady=10)

    def flip_horizontal(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = ImageOps.mirror(self.current_img)
            self.update_preview()

    def flip_vertical(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = ImageOps.flip(self.current_img)
            self.update_preview()

    def adjust_brightness(self):
        if not self.current_img:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Яскравість")
        dialog.geometry("300x100")

        brightness_var = tk.DoubleVar(value=1.0)
        tk.Scale(dialog, from_=0.1, to=3.0, resolution=0.1, orient="horizontal",
                 variable=brightness_var, label="Яскравість").pack(fill="x", padx=20)

        def apply_brightness():
            self.add_to_history(self.current_img)
            enhancer = ImageEnhance.Brightness(self.current_img)
            self.current_img = enhancer.enhance(brightness_var.get())
            self.update_preview()
            dialog.destroy()

        tk.Button(dialog, text="Застосувати", command=apply_brightness).pack(pady=10)

    def adjust_contrast(self):
        if not self.current_img:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Контраст")
        dialog.geometry("300x100")

        contrast_var = tk.DoubleVar(value=1.0)
        tk.Scale(dialog, from_=0.1, to=3.0, resolution=0.1, orient="horizontal",
                 variable=contrast_var, label="Контраст").pack(fill="x", padx=20)

        def apply_contrast():
            self.add_to_history(self.current_img)
            enhancer = ImageEnhance.Contrast(self.current_img)
            self.current_img = enhancer.enhance(contrast_var.get())
            self.update_preview()
            dialog.destroy()

        tk.Button(dialog, text="Застосувати", command=apply_contrast).pack(pady=10)

    def adjust_saturation(self):
        if not self.current_img:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Насиченість")
        dialog.geometry("300x100")

        saturation_var = tk.DoubleVar(value=1.0)
        tk.Scale(dialog, from_=0.0, to=3.0, resolution=0.1, orient="horizontal",
                 variable=saturation_var, label="Насиченість").pack(fill="x", padx=20)

        def apply_saturation():
            self.add_to_history(self.current_img)
            enhancer = ImageEnhance.Color(self.current_img)
            self.current_img = enhancer.enhance(saturation_var.get())
            self.update_preview()
            dialog.destroy()

        tk.Button(dialog, text="Застосувати", command=apply_saturation).pack(pady=10)

    def apply_blur(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = self.current_img.filter(ImageFilter.BLUR)
            self.update_preview()

    def apply_sharpen(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = self.current_img.filter(ImageFilter.SHARPEN)
            self.update_preview()

    def apply_edge_enhance(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = self.current_img.filter(ImageFilter.EDGE_ENHANCE)
            self.update_preview()

    def apply_emboss(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = self.current_img.filter(ImageFilter.EMBOSS)
            self.update_preview()

    def convert_grayscale(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = self.current_img.convert("L").convert("RGB")
            self.update_preview()

    def invert_colors(self):
        if self.current_img:
            self.add_to_history(self.current_img)
            self.current_img = ImageOps.invert(self.current_img)
            self.update_preview()

    # ==================== ВКЛАДКА 2: PIXEL ART ====================

    @staticmethod
    def to_pixel_art(img, pixel_size=16, num_colors=16):
        new_width = max(1, img.width // pixel_size)
        new_height = max(1, img.height // pixel_size)
        pixel_art = img.resize((new_width, new_height), resample=Image.Resampling.BOX)
        pixel_art = pixel_art.convert('P', palette=Image.ADAPTIVE, colors=num_colors)
        return pixel_art.convert("RGB")

    def apply_pixel_art(self):
        if not self.current_img:
            return

        pixel_size = self.pixel_size_scale.get()
        num_colors = self.num_colors_scale.get()

        self.add_to_history(self.current_img)
        self.current_img = self.to_pixel_art(self.current_img, pixel_size, num_colors)
        self.update_preview()

    # ==================== ВКЛАДКА 3: PAINT ====================

    def init_paint_canvas(self):
        if not self.current_img:
            messagebox.showwarning("Увага", "Спочатку відкрийте зображення!")
            return

        self.canvas_img = self.current_img.copy()
        self.draw_obj = ImageDraw.Draw(self.canvas_img)

        # Очистити canvas і налаштувати
        self.paint_canvas.delete("all")

        # Масштабування для відображення
        display_img = self.resize_for_display(self.canvas_img, 800, 500)
        self.paint_photo = ImageTk.PhotoImage(display_img)
        self.paint_canvas.create_image(0, 0, anchor="nw", image=self.paint_photo)

        self.paint_canvas.config(width=display_img.width, height=display_img.height)

    def start_draw(self, event):
        self.drawing = True
        self.last_x = event.x
        self.last_y = event.y

    def draw(self, event):
        if self.drawing and self.canvas_img:
            # Масштабування координат
            scale_x = self.canvas_img.width / self.paint_canvas.winfo_width()
            scale_y = self.canvas_img.height / self.paint_canvas.winfo_height()

            x = int(event.x * scale_x)
            y = int(event.y * scale_y)

            if self.last_x and self.last_y:
                prev_x = int(self.last_x * scale_x)
                prev_y = int(self.last_y * scale_y)

                # Малювання на оригінальному зображенні
                self.draw_obj.line([prev_x, prev_y, x, y],
                                   fill=self.brush_color, width=self.brush_size)

                # Малювання на canvas
                self.paint_canvas.create_line(self.last_x, self.last_y, event.x, event.y,
                                              fill=self.brush_color, width=self.brush_size)

            self.last_x = event.x
            self.last_y = event.y

    def stop_draw(self, event):
        self.drawing = False
        self.last_x = None
        self.last_y = None
        if self.canvas_img:
            self.current_img = self.canvas_img.copy()

    def choose_color(self):
        color = colorchooser.askcolor(title="Виберіть колір")[1]
        if color:
            self.brush_color = color
            self.color_display.config(bg=color)

    def clear_canvas(self):
        if self.canvas_img:
            self.add_to_history(self.current_img)
            self.init_paint_canvas()

    def apply_paint_changes(self):
        if self.canvas_img:
            self.add_to_history(self.current_img)
            self.current_img = self.canvas_img.copy()
            self.update_preview()
            messagebox.showinfo("Успіх", "Зміни застосовано!")

    # ==================== ІНТЕРФЕЙС ====================

    def _build_ui(self):
        # Верхня панель з кнопками
        top_frame = tk.Frame(self.root)
        top_frame.pack(side="top", fill="x", pady=5)

        tk.Button(top_frame, text="📂 Відкрити", command=self.open_image, font=("Arial", 10)).pack(side="left", padx=5)
        tk.Button(top_frame, text="💾 Зберегти", command=self.save_image, font=("Arial", 10)).pack(side="left", padx=5)
        tk.Button(top_frame, text="🔄 Reset", command=self.reset_image, font=("Arial", 10)).pack(side="left", padx=5)
        tk.Button(top_frame, text="↶ Undo", command=self.undo, font=("Arial", 10)).pack(side="left", padx=5)
        tk.Button(top_frame, text="↷ Redo", command=self.redo, font=("Arial", 10)).pack(side="left", padx=5)

        self.info_label = tk.Label(top_frame, text="Інформація: немає зображення", font=("Arial", 9))
        self.info_label.pack(side="right", padx=10)

        # Вкладки
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # ВКЛАДКА 1: Основний редактор
        tab1 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text="📷 Редактор")

        # Ліва панель інструментів
        left_panel = tk.Frame(tab1, width=250, bg="#f0f0f0")
        left_panel.pack(side="left", fill="y", padx=5, pady=5)

        tk.Label(left_panel, text="🔧 ТРАНСФОРМАЦІЯ", font=("Arial", 11, "bold"), bg="#f0f0f0").pack(pady=10)
        tk.Button(left_panel, text="Змінити розмір", command=self.resize_image, width=20).pack(pady=3)
        tk.Button(left_panel, text="AI Upscale", command=self.upscale_image, width=20).pack(pady=3)
        tk.Button(left_panel, text="Обрізати", command=self.crop_image, width=20).pack(pady=3)
        tk.Button(left_panel, text="Повернути", command=self.rotate_image, width=20).pack(pady=3)
        tk.Button(left_panel, text="Дзеркало ↔", command=self.flip_horizontal, width=20).pack(pady=3)
        tk.Button(left_panel, text="Дзеркало ↕", command=self.flip_vertical, width=20).pack(pady=3)

        tk.Label(left_panel, text="🎨 КОЛЬОРИ", font=("Arial", 11, "bold"), bg="#f0f0f0").pack(pady=10)
        tk.Button(left_panel, text="Яскравість", command=self.adjust_brightness, width=20).pack(pady=3)
        tk.Button(left_panel, text="Контраст", command=self.adjust_contrast, width=20).pack(pady=3)
        tk.Button(left_panel, text="Насиченість", command=self.adjust_saturation, width=20).pack(pady=3)
        tk.Button(left_panel, text="Чорно-біле", command=self.convert_grayscale, width=20).pack(pady=3)
        tk.Button(left_panel, text="Інвертувати", command=self.invert_colors, width=20).pack(pady=3)

        tk.Label(left_panel, text="✨ ФІЛЬТРИ", font=("Arial", 11, "bold"), bg="#f0f0f0").pack(pady=10)
        tk.Button(left_panel, text="Blur", command=self.apply_blur, width=20).pack(pady=3)
        tk.Button(left_panel, text="Sharpen", command=self.apply_sharpen, width=20).pack(pady=3)
        tk.Button(left_panel, text="Edge Enhance", command=self.apply_edge_enhance, width=20).pack(pady=3)
        tk.Button(left_panel, text="Emboss", command=self.apply_emboss, width=20).pack(pady=3)

        # Панель перегляду
        preview_frame = tk.Frame(tab1)
        preview_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.preview_label = tk.Label(preview_frame, text="Відкрийте зображення для редагування",
                                      font=("Arial", 14), bg="#e0e0e0")
        self.preview_label.pack(fill="both", expand=True)

        # ВКЛАДКА 2: Pixel Art
        tab2 = ttk.Frame(self.notebook)
        self.notebook.add(tab2, text="🎮 Pixel Art")

        control_frame = tk.Frame(tab2)
        control_frame.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(control_frame, text="PIXEL ART КОНВЕРТЕР", font=("Arial", 12, "bold")).pack(pady=10)

        self.pixel_size_scale = tk.Scale(control_frame, from_=1, to=64, orient="horizontal",
                                         label="Розмір пікселя", length=200)
        self.pixel_size_scale.set(16)
        self.pixel_size_scale.pack(pady=10)

        self.num_colors_scale = tk.Scale(control_frame, from_=2, to=256, orient="horizontal",
                                         label="Кількість кольорів", length=200)
        self.num_colors_scale.set(16)
        self.num_colors_scale.pack(pady=10)

        tk.Button(control_frame, text="Застосувати Pixel Art",
                  command=self.apply_pixel_art, width=20, height=2).pack(pady=20)

        # ВКЛАДКА 3: Paint
        tab3 = ttk.Frame(self.notebook)
        self.notebook.add(tab3, text="🖌️ Paint")

        paint_controls = tk.Frame(tab3)
        paint_controls.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(paint_controls, text="ІНСТРУМЕНТИ МАЛЮВАННЯ", font=("Arial", 12, "bold")).pack(pady=10)

        tk.Label(paint_controls, text="Розмір пензля:").pack(pady=5)
        self.brush_size_scale = tk.Scale(paint_controls, from_=1, to=50, orient="horizontal",
                                         command=lambda v: setattr(self, 'brush_size', int(v)))
        self.brush_size_scale.set(5)
        self.brush_size_scale.pack()

        tk.Label(paint_controls, text="Колір:").pack(pady=10)
        self.color_display = tk.Label(paint_controls, bg="#000000", width=10, height=2)
        self.color_display.pack()
        tk.Button(paint_controls, text="Вибрати колір", command=self.choose_color).pack(pady=5)

        tk.Button(paint_controls, text="Очистити", command=self.clear_canvas, width=15).pack(pady=10)
        tk.Button(paint_controls, text="Застосувати зміни",
                  command=self.apply_paint_changes, width=15).pack(pady=5)

        # Canvas для малювання
        canvas_frame = tk.Frame(tab3, bg="#ffffff")
        canvas_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.paint_canvas = tk.Canvas(canvas_frame, bg="#ffffff", cursor="cross")
        self.paint_canvas.pack(fill="both", expand=True)

        self.paint_canvas.bind("<Button-1>", self.start_draw)
        self.paint_canvas.bind("<B1-Motion>", self.draw)
        self.paint_canvas.bind("<ButtonRelease-1>", self.stop_draw)

        # Ініціалізувати paint canvas при переключенні вкладки
        self.notebook.bind("<<NotebookTabChanged>>", lambda e:
        self.init_paint_canvas() if self.notebook.index("current") == 2 and self.current_img else None)


if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoEditorPro(root)
    root.mainloop()