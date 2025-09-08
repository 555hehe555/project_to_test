import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageFilter
import os

WINDOW_WIDTH = 600
WINDOW_HEIGHT = 500


class PixelArtConverter:
    def __init__(self, root):
        self.root = root
        self.original_img = None
        self.processed_img = None
        self.displayed_img = None
        self.preview_mode = "original"

        self.setup_ui()

    def setup_ui(self):
        self.root.title("Покращений Pixel Art Converter")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT + 200}")
        self.root.resizable(True, True)
        self.root.configure(bg='#f0f0f0')

        # Стиль для ttk віджетів
        style = ttk.Style()
        style.theme_use('clam')

        # Головна рамка
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Налаштування сітки
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Панель керування
        control_frame = ttk.LabelFrame(main_frame, text="Налаштування", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Кнопки файлових операцій
        file_frame = ttk.Frame(control_frame)
        file_frame.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        ttk.Button(file_frame, text="📁 Відкрити зображення",
                   command=self.open_image).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(file_frame, text="💾 Зберегти результат",
                   command=self.save_image).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="🔄 Скинути",
                   command=self.reset_image).grid(row=0, column=2, padx=(5, 0))

        # Налаштування пікселізації
        ttk.Label(control_frame, text="Розмір пікселя:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.pixel_size_var = tk.StringVar(value="16")
        pixel_size_scale = ttk.Scale(control_frame, from_=4, to=64,
                                     variable=self.pixel_size_var, orient=tk.HORIZONTAL,
                                     command=self.on_scale_change)
        pixel_size_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 5))
        self.pixel_size_label = ttk.Label(control_frame, text="16")
        self.pixel_size_label.grid(row=1, column=2)

        # Кількість кольорів
        ttk.Label(control_frame, text="Кількість кольорів:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.num_colors_var = tk.StringVar(value="16")
        colors_scale = ttk.Scale(control_frame, from_=2, to=256,
                                 variable=self.num_colors_var, orient=tk.HORIZONTAL,
                                 command=self.on_colors_change)
        colors_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 5))
        self.colors_label = ttk.Label(control_frame, text="16")
        self.colors_label.grid(row=2, column=2)

        # Додаткові ефекти
        effects_frame = ttk.LabelFrame(control_frame, text="Ефекти", padding="5")
        effects_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        self.blur_var = tk.BooleanVar()
        self.sharpen_var = tk.BooleanVar()
        self.dither_var = tk.BooleanVar(value=True)

        ttk.Checkbutton(effects_frame, text="Розмиття",
                        variable=self.blur_var, command=self.apply_pixel_art).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(effects_frame, text="Підвищення різкості",
                        variable=self.sharpen_var, command=self.apply_pixel_art).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(effects_frame, text="Дизеринг",
                        variable=self.dither_var, command=self.apply_pixel_art).grid(row=0, column=2, sticky=tk.W)

        # Налаштування колонок для effects_frame
        effects_frame.columnconfigure(0, weight=1)
        effects_frame.columnconfigure(1, weight=1)
        effects_frame.columnconfigure(2, weight=1)

        # Кнопка застосування
        ttk.Button(control_frame, text="🎨 Застосувати Pixel Art",
                   command=self.apply_pixel_art).grid(row=4, column=0, columnspan=3, pady=(10, 0))

        # Панель перемикання режимів перегляду
        view_frame = ttk.Frame(main_frame)
        view_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10))

        ttk.Button(view_frame, text="📷 Оригінал",
                   command=lambda: self.switch_view("original")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(view_frame, text="🎮 Pixel Art",
                   command=lambda: self.switch_view("processed")).pack(side=tk.LEFT)

        # Область перегляду зображення
        self.canvas_frame = ttk.Frame(main_frame)
        self.canvas_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.canvas = tk.Canvas(self.canvas_frame, bg='white', relief=tk.SUNKEN, borderwidth=2)

        # Скролбари для канваса
        v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        self.canvas_frame.columnconfigure(0, weight=1)
        self.canvas_frame.rowconfigure(0, weight=1)

        # Інформаційний рядок
        self.info_var = tk.StringVar(value="Виберіть зображення для початку роботи")
        info_label = ttk.Label(main_frame, textvariable=self.info_var, relief=tk.SUNKEN)
        info_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

    def on_scale_change(self, value):
        """Оновлення лейбла при зміні розміру пікселя"""
        self.pixel_size_label.config(text=str(int(float(value))))
        if self.original_img:
            self.apply_pixel_art()

    def on_colors_change(self, value):
        """Оновлення лейбла при зміні кількості кольорів"""
        self.colors_label.config(text=str(int(float(value))))
        if self.original_img:
            self.apply_pixel_art()

    def open_image(self):
        """Відкриття файлу зображення"""
        filetypes = [
            ("Всі підтримувані", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.tiff"),
            ("PNG файли", "*.png"),
            ("JPEG файли", "*.jpg;*.jpeg"),
            ("Всі файли", "*.*")
        ]

        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            try:
                self.original_img = Image.open(path)
                # Конвертуємо в RGB якщо потрібно
                if self.original_img.mode in ('RGBA', 'LA', 'P'):
                    self.original_img = self.original_img.convert('RGB')

                self.info_var.set(f"Завантажено: {os.path.basename(path)} | "
                                  f"Розмір: {self.original_img.width}x{self.original_img.height}")

                self.preview_mode = "original"
                self.update_display()

            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося відкрити файл:\n{str(e)}")

    def to_pixel_art(self, img, pixel_size=16, num_colors=16):
        """Конвертація зображення в піксельну графіку"""
        # Застосування ефектів перед пікселізацією
        processed = img.copy()

        if self.blur_var.get():
            processed = processed.filter(ImageFilter.BLUR)

        if self.sharpen_var.get():
            processed = processed.filter(ImageFilter.SHARPEN)

        # Обчислюємо новий розмір для стискання
        new_width = max(1, processed.width // pixel_size)
        new_height = max(1, processed.height // pixel_size)

        # Стискаємо зображення з використанням BOX фільтра для пікселізації
        pixel_art = processed.resize((new_width, new_height), resample=Image.Resampling.BOX)

        # Збільшуємо назад до оригінального розміру без згладжування
        pixel_art = pixel_art.resize((processed.width, processed.height), resample=Image.Resampling.NEAREST)

        # Квантизація кольорів
        if self.dither_var.get():
            pixel_art = pixel_art.quantize(colors=num_colors, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        else:
            pixel_art = pixel_art.quantize(colors=num_colors, method=Image.MEDIANCUT, dither=0)

        return pixel_art.convert('RGB')

    def apply_pixel_art(self):
        """Застосування ефекту піксельної графіки"""
        if not self.original_img:
            return

        try:
            pixel_size = max(1, int(float(self.pixel_size_var.get())))
            num_colors = max(2, min(256, int(float(self.num_colors_var.get()))))

            self.processed_img = self.to_pixel_art(self.original_img, pixel_size, num_colors)

            if self.preview_mode == "processed":
                self.update_display()

            self.info_var.set(f"Застосовано: пікселі {pixel_size}x{pixel_size}, кольорів: {num_colors}")

        except Exception as e:
            messagebox.showerror("Помилка", f"Помилка при обробці:\n{str(e)}")

    def switch_view(self, mode):
        """Перемикання між оригіналом та обробленим зображенням"""
        if mode == "original" and self.original_img:
            self.preview_mode = "original"
            self.update_display()
        elif mode == "processed" and self.processed_img:
            self.preview_mode = "processed"
            self.update_display()

    def update_display(self):
        """Оновлення відображення зображення на канвасі"""
        if self.preview_mode == "original" and self.original_img:
            img_to_show = self.original_img
        elif self.preview_mode == "processed" and self.processed_img:
            img_to_show = self.processed_img
        else:
            return

        # Підготовка зображення для відображення
        display_img = self.prepare_for_display(img_to_show)
        self.displayed_img = ImageTk.PhotoImage(display_img)

        # Очищення канваса і додавання нового зображення
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.displayed_img)

        # Оновлення області прокрутки
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def prepare_for_display(self, img):
        """Підготовка зображення для відображення з урахуванням розмірів вікна"""
        # Отримуємо доступні розміри канваса
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Якщо канвас ще не відображений, використовуємо стандартні розміри
        if canvas_width <= 1:
            canvas_width = WINDOW_WIDTH - 50
            canvas_height = WINDOW_HEIGHT - 50

        # Масштабуємо зображення, зберігаючи пропорції
        w_ratio = (canvas_width - 20) / img.width
        h_ratio = (canvas_height - 20) / img.height
        ratio = min(w_ratio, h_ratio, 1)  # Не збільшуємо понад оригінальний розмір

        if ratio < 1:
            new_size = (int(img.width * ratio), int(img.height * ratio))
            return img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            return img

    def reset_image(self):
        """Скидання до оригінального зображення"""
        if self.original_img:
            self.preview_mode = "original"
            self.processed_img = None
            self.update_display()
            self.info_var.set("Скинуто до оригіналу")

    def save_image(self):
        """Збереження обробленого зображення"""
        if not self.processed_img:
            messagebox.showwarning("Попередження", "Спочатку застосуйте ефект Pixel Art")
            return

        filetypes = [
            ("PNG файли", "*.png"),
            ("JPEG файли", "*.jpg"),
            ("Всі файли", "*.*")
        ]

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=filetypes
        )

        if path:
            try:
                # Конвертуємо в RGB для JPEG
                if path.lower().endswith(('.jpg', '.jpeg')):
                    save_img = self.processed_img.convert('RGB')
                else:
                    save_img = self.processed_img

                save_img.save(path)
                self.info_var.set(f"Збережено: {os.path.basename(path)}")

            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося зберегти файл:\n{str(e)}")


def main():
    root = tk.Tk()
    app = PixelArtConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()