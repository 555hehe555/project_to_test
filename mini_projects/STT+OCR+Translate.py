import io
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, colorchooser, font
from PIL import ImageGrab, ImageEnhance, ImageFilter, Image, ImageDraw, ImageTk
import pytesseract
import threading
import speech_recognition as sr
from deep_translator import GoogleTranslator
from pynput import keyboard
import time
import math
from datetime import datetime

# === Вкажи шлях до tesseract.exe, якщо потрібно ===
pytesseract.pytesseract.tesseract_cmd = r"D:\\Games\\tesseract_ocr\\tesseract.exe"

# Перевірка PyAudio
try:
    import pyaudio

    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    print("PyAudio не встановлено. Встановіть командою: pip install pyaudio")


class ScreenSelector(tk.Toplevel):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.attributes('-fullscreen', True)
        self.attributes('-alpha', 0.3)
        self.canvas = tk.Canvas(self, cursor="cross", bg='black')
        self.canvas.pack(fill="both", expand=True)
        self.start_x = self.start_y = 0
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", self.cancel_selection)

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def on_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def cancel_selection(self, event):
        self.destroy()

    def on_release(self, event):
        x1 = min(self.start_x, self.canvas.canvasx(event.x))
        y1 = min(self.start_y, self.canvas.canvasy(event.y))
        x2 = max(self.start_x, self.canvas.canvasx(event.x))
        y2 = max(self.start_y, self.canvas.canvasy(event.y))
        self.withdraw()
        self.after(100, lambda: self.capture_area(x1, y1, x2, y2))

    def capture_area(self, x1, y1, x2, y2):
        try:
            # Захоплюємо область
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))

            # Простіший OCR без агресивної обробки
            text = pytesseract.image_to_string(img, lang='ukr+eng')

        except Exception as e:
            text = f"[OCR помилка: {e}]"

        self.callback(text)
        self.destroy()


class ScreenDrawer(tk.Toplevel):
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance

        # Налаштування вікна
        self.attributes('-fullscreen', True)
        self.attributes('-alpha', 0.9)  # Менш прозорий для кращої видимості
        self.attributes('-topmost', False)  # НЕ завжди зверху
        self.configure(bg='gray20')  # Темно-сірий фон

        # Змінні для малювання
        self.current_tool = "brush"
        self.current_color = "#ff0000"
        self.brush_size = 3
        self.start_x = self.start_y = 0
        self.shapes = []
        self.temp_shape = None
        self.text_objects = []
        self.drawing = False  # Додаємо флаг малювання

        # Створюємо Canvas з видимим фоном
        self.canvas = tk.Canvas(self, highlightthickness=0, bg='gray10', cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        # Прив'язуємо події
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)
        self.canvas.bind("<Button-3>", self.show_context_menu)

        # Гарячі клавіші
        self.bind_all("<Escape>", self.close_drawer)
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-s>", self.save_drawing)
        self.bind_all("<Delete>", self.clear_all)

        self.focus_set()

        # Створюємо бокову панель
        self.after(100, self.create_sidebar)

    def create_sidebar(self):
        """Створення бокової панелі з інструментами"""
        sidebar_width = 250
        self.sidebar = tk.Frame(self, bg='#2b2b2b', width=250, height=self.winfo_screenheight())
        self.sidebar.place(relx=1.0, rely=0, anchor="ne")
        self.sidebar.pack_propagate(False)

        # Заголовок
        title = tk.Label(self.sidebar, text="🎨 Малювалка", bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        title.pack(pady=10)

        # === ІНСТРУМЕНТИ ===
        tools_frame = tk.LabelFrame(self.sidebar, text="Інструменти", bg='#2b2b2b', fg='white')
        tools_frame.pack(fill=tk.X, padx=10, pady=5)

        tools = [
            ("🖌️ Пензель", "brush"),
            ("✏️ Олівець", "pencil"),
            ("📏 Лінія", "line"),
            ("⬜ Прямокутник", "rectangle"),
            ("⭕ Коло", "circle"),
            ("🔸 Еліпс", "ellipse"),
            ("➡️ Стрілка", "arrow"),
            ("📝 Текст", "text"),
            ("🧽 Ластик", "eraser")
        ]

        for i, (text, tool) in enumerate(tools):
            btn = tk.Button(tools_frame, text=text, bg='#404040', fg='white',
                            command=lambda t=tool: self.set_tool(t))
            btn.pack(fill=tk.X, pady=2, padx=5)
            if tool == "brush":
                btn.configure(bg='#ff4444')
                self.current_tool_btn = btn

        # === КОЛЬОРИ ===
        colors_frame = tk.LabelFrame(self.sidebar, text="Кольори", bg='#2b2b2b', fg='white')
        colors_frame.pack(fill=tk.X, padx=10, pady=5)

        # Швидкі кольори
        colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff",
                  "#ffffff", "#000000", "#ff8000", "#8000ff", "#808080", "#008000"]

        color_grid = tk.Frame(colors_frame, bg='#2b2b2b')
        color_grid.pack(fill=tk.X, padx=5, pady=5)

        for i, color in enumerate(colors):
            row, col = i // 4, i % 4
            btn = tk.Button(color_grid, bg=color, width=3, height=1,
                            command=lambda c=color: self.set_color(c))
            btn.grid(row=row, column=col, padx=2, pady=2)

        # Кнопка вибору кольору
        choose_btn = tk.Button(colors_frame, text="🎨 Вибрати колір", bg='#404040', fg='white',
                               command=self.choose_color)
        choose_btn.pack(fill=tk.X, padx=5, pady=5)

        # Поточний колір
        self.color_preview = tk.Label(colors_frame, bg=self.current_color, text="Поточний",
                                      fg='white', font=('Arial', 8))
        self.color_preview.pack(fill=tk.X, padx=5, pady=2)

        # === РОЗМІР ===
        size_frame = tk.LabelFrame(self.sidebar, text="Розмір", bg='#2b2b2b', fg='white')
        size_frame.pack(fill=tk.X, padx=10, pady=5)

        self.size_var = tk.IntVar(value=self.brush_size)
        size_scale = tk.Scale(size_frame, from_=1, to=20, orient=tk.HORIZONTAL,
                              variable=self.size_var, bg='#2b2b2b', fg='white',
                              command=self.update_size)
        size_scale.pack(fill=tk.X, padx=5, pady=5)

        # === ПРОЗОРІСТЬ ===
        alpha_frame = tk.LabelFrame(self.sidebar, text="Прозорість екрана", bg='#2b2b2b', fg='white')
        alpha_frame.pack(fill=tk.X, padx=10, pady=5)

        self.alpha_var = tk.DoubleVar(value=0.9)
        alpha_scale = tk.Scale(alpha_frame, from_=0.3, to=1.0, orient=tk.HORIZONTAL,
                               variable=self.alpha_var, bg='#2b2b2b', fg='white',
                               resolution=0.1, command=self.update_alpha)
        alpha_scale.pack(fill=tk.X, padx=5, pady=5)

        # Кнопка переключення режиму прозорості
        self.transparent_mode = tk.BooleanVar(value=False)
        tk.Checkbutton(alpha_frame, text="Прозорий режим", variable=self.transparent_mode,
                       bg='#2b2b2b', fg='white', selectcolor='#404040',
                       command=self.toggle_transparent_mode).pack(padx=5, pady=2)

        # === ДІЇ ===
        actions_frame = tk.LabelFrame(self.sidebar, text="Дії", bg='#2b2b2b', fg='white')
        actions_frame.pack(fill=tk.X, padx=10, pady=5)

        actions = [
            ("↩️ Скасувати (Ctrl+Z)", self.undo),
            ("🗑️ Очистити все (Ctrl+C)", self.clear_all),
            ("💾 Зберегти (Ctrl+S)", self.save_drawing),
            ("❌ Закрити (Esc)", self.close_drawer)
        ]

        for text, command in actions:
            tk.Button(actions_frame, text=text, bg='#404040', fg='white',
                      command=command).pack(fill=tk.X, pady=2, padx=5)

        # === ІНФО ===
        info_frame = tk.LabelFrame(self.sidebar, text="Інформація", bg='#2b2b2b', fg='white')
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        info_text = "Гарячі клавіші:\nEsc - Закрити\nCtrl+Z - Скасувати\nCtrl+C - Очистити\nCtrl+S - Зберегти"
        tk.Label(info_frame, text=info_text, bg='#2b2b2b', fg='white',
                 justify=tk.LEFT, font=('Arial', 8)).pack(padx=5, pady=5)

    def set_tool(self, tool):
        """Встановлення поточного інструменту"""
        self.current_tool = tool

        # Оновлюємо вигляд кнопок (простий спосіб - можна покращити)
        for widget in self.sidebar.winfo_children():
            if isinstance(widget, tk.LabelFrame) and widget.cget('text') == 'Інструменти':
                for btn in widget.winfo_children():
                    if isinstance(btn, tk.Button):
                        if tool in btn.cget('text').lower():
                            btn.configure(bg='#ff4444')
                            self.current_tool_btn = btn
                        else:
                            btn.configure(bg='#404040')

    def set_color(self, color):
        """Встановлення кольору"""
        self.current_color = color
        self.color_preview.configure(bg=color)

    def choose_color(self):
        """Вибір кольору через діалог"""
        # Тимчасово знімаємо topmost для діалогу
        self.attributes('-topmost', False)

        # Створюємо власний діалог вибору кольору
        color_window = tk.Toplevel(self)
        color_window.title("Вибір кольору")
        color_window.geometry("400x300")
        color_window.configure(bg='#2b2b2b')
        color_window.attributes('-topmost', True)
        color_window.grab_set()  # Модальне вікно

        # Палітра кольорів
        colors_grid = [
            ['#FF0000', '#FF4500', '#FF8C00', '#FFD700', '#FFFF00', '#ADFF2F', '#00FF00', '#00FA9A'],
            ['#00FFFF', '#00BFFF', '#0080FF', '#0000FF', '#4169E1', '#8A2BE2', '#9400D3', '#FF00FF'],
            ['#FF1493', '#DC143C', '#B22222', '#A0522D', '#8B4513', '#2F4F4F', '#708090', '#778899'],
            ['#FFFFFF', '#F5F5F5', '#DCDCDC', '#C0C0C0', '#808080', '#696969', '#2F2F2F', '#000000']
        ]

        tk.Label(color_window, text="Виберіть колір:", bg='#2b2b2b', fg='white',
                 font=('Arial', 12)).pack(pady=10)

        colors_frame = tk.Frame(color_window, bg='#2b2b2b')
        colors_frame.pack(pady=10)

        def select_color(color):
            self.set_color(color)
            color_window.destroy()

        for row_idx, row in enumerate(colors_grid):
            for col_idx, color in enumerate(row):
                btn = tk.Button(colors_frame, bg=color, width=4, height=2,
                                command=lambda c=color: select_color(c),
                                relief='raised', bd=2)
                btn.grid(row=row_idx, column=col_idx, padx=2, pady=2)

        # Кнопка закриття
        tk.Button(color_window, text="Закрити", bg='#404040', fg='white',
                  command=color_window.destroy).pack(pady=20)

    def update_size(self, value):
        """Оновлення розміру пензля"""
        self.brush_size = int(value)

    def update_alpha(self, value):
        """Оновлення прозорості"""
        alpha = float(value)
        self.attributes('-alpha', alpha)

        # Оновлюємо фон Canvas в залежності від прозорості
        if alpha < 0.7:
            self.canvas.configure(bg='gray5')
            self.configure(bg='gray5')
        else:
            self.canvas.configure(bg='gray10')
            self.configure(bg='gray20')

    def toggle_transparent_mode(self):
        """Переключення прозорого режиму"""
        if self.transparent_mode.get():
            # Прозорий режим - ховаємо фон але лишаємо малюнки
            self.alpha_var.set(0.3)
            self.update_alpha(0.3)
            self.canvas.configure(bg='')
            self.configure(bg='')
        else:
            # Звичайний режим
            self.alpha_var.set(0.9)
            self.update_alpha(0.9)

    def start_draw(self, event):
        """Початок малювання"""
        self.drawing = True
        self.start_x, self.start_y = event.x, event.y

        print(f"Start draw at {event.x}, {event.y} with tool {self.current_tool}")  # Дебаг

        if self.current_tool == "text":
            self.add_text(event.x, event.y)
        elif self.current_tool == "eraser":
            self.erase_at_point(event.x, event.y)
        elif self.current_tool in ["brush", "pencil"]:
            # Малюємо початкову точку
            width = self.brush_size if self.current_tool == "brush" else max(1, self.brush_size // 2)
            point = self.canvas.create_oval(event.x - width // 2, event.y - width // 2,
                                            event.x + width // 2, event.y + width // 2,
                                            fill=self.current_color, outline=self.current_color)
            self.shapes.append(point)

    def draw(self, event):
        """Процес малювання"""
        if not self.drawing:
            return

        print(f"Drawing at {event.x}, {event.y}")  # Дебаг

        if self.current_tool in ["brush", "pencil"]:
            width = self.brush_size if self.current_tool == "brush" else max(1, self.brush_size // 2)
            line_id = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y,
                                              fill=self.current_color, width=width,
                                              capstyle=tk.ROUND, smooth=True)
            self.shapes.append(line_id)
            self.start_x, self.start_y = event.x, event.y

        elif self.current_tool == "eraser":
            self.erase_at_point(event.x, event.y)

        elif self.current_tool in ["line", "rectangle", "circle", "ellipse", "arrow"]:
            # Видаляємо попередню тимчасову фігуру
            if self.temp_shape:
                self.canvas.delete(self.temp_shape)

            # Малюємо нову тимчасову фігуру
            self.temp_shape = self.draw_shape(self.start_x, self.start_y, event.x, event.y, temp=True)

    def end_draw(self, event):
        """Закінчення малювання"""
        self.drawing = False

        if self.current_tool in ["line", "rectangle", "circle", "ellipse", "arrow"]:
            if self.temp_shape:
                self.canvas.delete(self.temp_shape)

            # Створюємо остаточну фігуру
            shape_id = self.draw_shape(self.start_x, self.start_y, event.x, event.y)
            if shape_id:
                self.shapes.append(shape_id)
            self.temp_shape = None

    def draw_shape(self, x1, y1, x2, y2, temp=False):
        """Малювання різних фігур"""
        if self.current_tool == "line":
            return self.canvas.create_line(x1, y1, x2, y2, fill=self.current_color, width=self.brush_size)

        elif self.current_tool == "rectangle":
            return self.canvas.create_rectangle(x1, y1, x2, y2, outline=self.current_color, width=self.brush_size)

        elif self.current_tool == "circle":
            # Робимо коло (квадратну область)
            radius = max(abs(x2 - x1), abs(y2 - y1)) // 2
            cx, cy = x1, y1
            return self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                           outline=self.current_color, width=self.brush_size)

        elif self.current_tool == "ellipse":
            return self.canvas.create_oval(x1, y1, x2, y2, outline=self.current_color, width=self.brush_size)

        elif self.current_tool == "arrow":
            # Малюємо стрілку
            arrow_id = self.canvas.create_line(x1, y1, x2, y2, fill=self.current_color,
                                               width=self.brush_size, arrow=tk.LAST, arrowshape=(16, 20, 6))
            return arrow_id

    def add_text(self, x, y):
        """Додавання тексту"""

        def submit_text():
            text = text_entry.get()
            if text:
                text_id = self.canvas.create_text(x, y, text=text, fill=self.current_color,
                                                  font=('Arial', self.brush_size + 8), anchor='nw')
                self.shapes.append(text_id)
                self.text_objects.append((text_id, text, x, y))
            dialog.destroy()

        # Діалог введення тексту
        dialog = tk.Toplevel(self)
        dialog.title("Введіть текст")
        dialog.geometry("300x100")
        dialog.attributes('-topmost', True)

        tk.Label(dialog, text="Текст:").pack(pady=5)
        text_entry = tk.Entry(dialog, width=40)
        text_entry.pack(pady=5)
        text_entry.focus()

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="OK", command=submit_text).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Скасувати", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        text_entry.bind('<Return>', lambda e: submit_text())
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def erase_at_point(self, x, y):
        """Стирання в точці"""
        # Знаходимо об'єкти поблизу курсора
        nearby = self.canvas.find_overlapping(x - self.brush_size, y - self.brush_size,
                                              x + self.brush_size, y + self.brush_size)
        for item in nearby:
            if item in self.shapes:
                self.canvas.delete(item)
                self.shapes.remove(item)

    def show_context_menu(self, event):
        """Контекстне меню"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Очистити все", command=self.clear_all)
        menu.add_command(label="Скасувати", command=self.undo)
        menu.add_separator()
        menu.add_command(label="Зберегти", command=self.save_drawing)
        menu.add_separator()
        menu.add_command(label="Закрити", command=self.close_drawer)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def undo(self, event=None):
        """Скасування останньої дії"""
        if self.shapes:
            last_shape = self.shapes.pop()
            self.canvas.delete(last_shape)

    def clear_all(self, event=None):
        """Очищення всього"""
        for shape in self.shapes:
            self.canvas.delete(shape)
        self.shapes.clear()
        self.text_objects.clear()

    def save_drawing(self, event=None):
        """Збереження малюнка напряму з Canvas"""
        try:
            # Шлях до файлу
            filename = f"drawing_{int(time.time())}.png"

            # Генеруємо PostScript із Canvas
            ps = self.canvas.postscript(colormode='color')

            # Конвертуємо PS → PNG через Pillow
            img = Image.open(io.BytesIO(ps.encode('utf-8')))
            img.save(filename, 'png')

            # Повідомлення про успішне збереження
            info_window = tk.Toplevel(self)
            info_window.title("Збережено")
            info_window.geometry("300x100")
            info_window.attributes('-topmost', True)

            tk.Label(info_window, text=f"Малюнок збережено як:\n{filename}").pack(pady=20)
            tk.Button(info_window, text="OK", command=info_window.destroy).pack()

            info_window.after(3000, info_window.destroy)

        except Exception as e:
            error_window = tk.Toplevel(self)
            error_window.title("Помилка")
            error_window.geometry("300x100")
            error_window.attributes('-topmost', True)

            tk.Label(error_window, text=f"Не вдалося зберегти:\n{str(e)[:50]}...").pack(pady=20)
            tk.Button(error_window, text="OK", command=error_window.destroy).pack()

    def close_drawer(self, event=None):
        self.unbind_all("<Escape>")
        self.destroy()
        self.app_instance.root.deiconify()


class AdvancedScreenSelector(tk.Toplevel):
    def __init__(self, callback):
        super().__init__()
        self.root = root
        self.callback = callback
        self.attributes('-fullscreen', True)
        self.attributes('-alpha', 0.3)
        self.canvas = tk.Canvas(self, cursor="cross", bg='black')
        self.canvas.pack(fill="both", expand=True)
        self.start_x = self.start_y = 0
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", self.cancel_selection)

    def on_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2, dash=(5, 5))

    def on_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def cancel_selection(self, event):
        self.destroy()

    def on_release(self, event):
        x1 = min(self.start_x, self.canvas.canvasx(event.x))
        y1 = min(self.start_y, self.canvas.canvasy(event.y))
        x2 = max(self.start_x, self.canvas.canvasx(event.x))
        y2 = max(self.start_y, self.canvas.canvasy(event.y))

        # Мінімальний розмір області
        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.destroy()
            return

        self.withdraw()
        self.after(200, lambda: self.capture_area(x1, y1, x2, y2))

    def preprocess_image(self, img):
        """Покращення зображення для кращого OCR"""
        # Збільшуємо контрастність помірно
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Збільшуємо різкість легко
        img = img.filter(ImageFilter.SHARPEN)

        return img

    def capture_area(self, x1, y1, x2, y2):
        try:
            # Захоплюємо область
            img = ImageGrab.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))

            # Покращуємо зображення м'яко
            img = self.preprocess_image(img)

            # Простіші параметри OCR
            text = pytesseract.image_to_string(img, lang='ukr+eng', config='--psm 6')

            # Очищуємо текст
            text = text.strip()
            if not text:
                text = "[Текст не розпізнано]"

        except Exception as e:
            text = f"[OCR помилка: {e}]"

        self.callback(text)
        self.destroy()

        self.root.deiconify()


class GoogleSpeechThread(threading.Thread):
    def __init__(self, callback, status_callback=None):
        super().__init__(daemon=True)
        self.callback = callback
        self.status_callback = status_callback
        self._running = True

    def run(self):
        if not PYAUDIO_AVAILABLE:
            self.callback("[Помилка: PyAudio не встановлено. Встановіть: pip install pyaudio]")
            return

        recognizer = sr.Recognizer()

        try:
            with sr.Microphone() as source:
                if self.status_callback:
                    self.status_callback("🔧 Налаштування мікрофону...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)

            if self.status_callback:
                self.status_callback("🎤 Слухаю...")

            while self._running:
                try:
                    with sr.Microphone() as source:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                    if self.status_callback:
                        self.status_callback("🔄 Розпізнаю...")

                    # Спочатку пробуємо українською
                    try:
                        text = recognizer.recognize_google(audio, language="uk-UA")
                    except sr.UnknownValueError:
                        # Якщо не вдалося, пробуємо англійською
                        try:
                            text = recognizer.recognize_google(audio, language="en-US")
                        except sr.UnknownValueError:
                            if self.status_callback:
                                self.status_callback("❌ Не розпізнано")
                            continue

                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted_text = f"[{timestamp}] {text}"
                    self.callback(formatted_text)

                    if self.status_callback:
                        self.status_callback("✅ Розпізнано!")

                except sr.RequestError as e:
                    self.callback(f"[Google API помилка: {e}]")
                    if self.status_callback:
                        self.status_callback("🚫 Помилка API")
                except sr.WaitTimeoutError:
                    if self.status_callback:
                        self.status_callback("🎤 Слухаю...")
                    continue
                except Exception as e:
                    self.callback(f"[Інша помилка: {e}]")
                    if self.status_callback:
                        self.status_callback("❌ Помилка")

        except Exception as e:
            self.callback(f"[Помилка мікрофону: {e}]")

    def stop(self):
        self._running = False


class EnhancedApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎤 STT + OCR + Translate Pro")
        self.root.geometry("400x550")
        self.root.minsize(500, 400)

        # Змінні стану
        self.speech_thread = None
        self.speech_active = False
        self.auto_translate = tk.BooleanVar()
        self.save_history = tk.BooleanVar()

        self.build_enhanced_ui()
        self.setup_hotkey()
        self.load_settings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.initial_show_hide)

    def build_enhanced_ui(self):
        # Головне меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Налаштування", menu=settings_menu)
        settings_menu.add_checkbutton(label="Авто-переклад", variable=self.auto_translate)
        settings_menu.add_checkbutton(label="Зберігати історію", variable=self.save_history)
        settings_menu.add_separator()
        settings_menu.add_command(label="🎨 Малювалка", command=self.open_drawer)
        settings_menu.add_separator()
        settings_menu.add_command(label="Очистити історію", command=self.clear_history)

        # Панель інструментів
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(toolbar, text="🔥 Швидкий доступ:").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="📷", command=self.quick_ocr, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎤", command=self.quick_speech, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎨", command=self.open_drawer, width=3).pack(side=tk.LEFT, padx=2)

        # Статус бар
        self.status_var = tk.StringVar()
        self.status_var.set("Готовий до роботи")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Вкладки
        tab_control = ttk.Notebook(self.root)

        # === OCR TAB ===
        ocr_tab = ttk.Frame(tab_control)

        ocr_controls = ttk.Frame(ocr_tab)
        ocr_controls.pack(fill=tk.X, padx=5, pady=5)

        self.ocr_text = scrolledtext.ScrolledText(ocr_tab, wrap=tk.WORD, font=('Arial', 11))
        self.ocr_advanced_btn = ttk.Button(ocr_controls, text="🔍 OCR", command=self.run_advanced_ocr)
        self.ocr_clear_btn = ttk.Button(ocr_controls, text="🗑️ Очистити",
                                        command=lambda: self.clear_text(self.ocr_text))
        self.ocr_copy_btn = ttk.Button(ocr_controls, text="📋 Копіювати", command=lambda: self.copy_text(self.ocr_text))

        self.ocr_advanced_btn.pack(side=tk.LEFT, padx=2)
        self.ocr_clear_btn.pack(side=tk.LEFT, padx=2)
        self.ocr_copy_btn.pack(side=tk.LEFT, padx=2)
        self.ocr_text.pack(expand=True, fill='both', padx=5, pady=5)

        # === STT TAB ===
        stt_tab = ttk.Frame(tab_control)

        stt_controls = ttk.Frame(stt_tab)
        stt_controls.pack(fill=tk.X, padx=5, pady=5)

        self.speech_text = scrolledtext.ScrolledText(stt_tab, wrap=tk.WORD, font=('Arial', 11))
        self.speech_button = ttk.Button(stt_controls, text="🎧 Почати запис", command=self.handle_speech)
        self.speech_clear_btn = ttk.Button(stt_controls, text="🗑️ Очистити",
                                           command=lambda: self.clear_text(self.speech_text))
        self.speech_copy_btn = ttk.Button(stt_controls, text="📋 Копіювати",
                                          command=lambda: self.copy_text(self.speech_text))

        # Індикатор статусу мікрофону
        self.mic_status = ttk.Label(stt_controls, text="🔴", font=('Arial', 16))

        self.speech_button.pack(side=tk.LEFT, padx=2)
        self.speech_clear_btn.pack(side=tk.LEFT, padx=2)
        self.speech_copy_btn.pack(side=tk.LEFT, padx=2)
        self.mic_status.pack(side=tk.RIGHT, padx=5)
        self.speech_text.pack(expand=True, fill='both', padx=5, pady=5)

        # === TRANSLATE TAB ===
        trans_tab = ttk.Frame(tab_control)

        trans_controls = ttk.Frame(trans_tab)
        trans_controls.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(trans_controls, text="Текст для перекладу:").pack(anchor=tk.W)
        self.input_text = scrolledtext.ScrolledText(trans_tab, wrap=tk.WORD, height=8, font=('Arial', 11))
        self.input_text.pack(fill='both', padx=5, pady=5)

        lang_frame = ttk.Frame(trans_tab)
        lang_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(lang_frame, text="Напрямок перекладу:").pack(side=tk.LEFT)
        self.lang_combo = ttk.Combobox(lang_frame, values=[
            "Українська → Англійська",
            "Англійська → Українська",
            "Українська → Німецька",
            "Німецька → Українська",
            "Українська → Французька",
            "Французька → Українська"
        ], state="readonly", width=25)
        self.lang_combo.current(0)
        self.lang_combo.pack(side=tk.LEFT, padx=5)

        translate_btn_frame = ttk.Frame(trans_tab)
        translate_btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.translate_button = ttk.Button(translate_btn_frame, text="🌐 Перекласти", command=self.run_translate)
        self.translate_button.pack(side=tk.LEFT, padx=2)

        ttk.Label(trans_tab, text="Переклад:").pack(anchor=tk.W, padx=5)
        self.output_text = scrolledtext.ScrolledText(trans_tab, wrap=tk.WORD, height=8, font=('Arial', 11))
        self.output_text.pack(expand=True, fill='both', padx=5, pady=5)

        # Додаємо вкладки
        tab_control.add(ocr_tab, text="🖼️ Розпізнавання тексту")
        tab_control.add(stt_tab, text="🎤 Голосовий ввід")
        tab_control.add(trans_tab, text="🌐 Переклад")
        tab_control.pack(expand=True, fill='both', padx=5, pady=5)

        # Налаштовуємо гарячі клавіші для всіх текстових полів
        for widget in [self.ocr_text, self.speech_text, self.input_text, self.output_text]:
            widget.bind("<Control-c>", self.copy_event)
            widget.bind("<Control-v>", self.paste_event)
            widget.bind("<Control-a>", self.select_all_event)

    def update_status(self, message):
        """Оновлення статус бару"""
        self.status_var.set(message)
        self.root.update_idletasks()

    def update_mic_status(self, message):
        """Оновлення статусу мікрофону"""
        if "Слухаю" in message:
            self.mic_status.config(text="🟢", foreground="green")
        elif "Розпізнаю" in message:
            self.mic_status.config(text="🟡", foreground="orange")
        elif "Розпізнано" in message:
            self.mic_status.config(text="✅", foreground="green")
        elif "помилка" in message.lower() or "Не розпізнано" in message:
            self.mic_status.config(text="🔴", foreground="red")
        else:
            self.mic_status.config(text="⚪", foreground="gray")

        self.update_status(message)

    def open_drawer(self):
        """Відкриття малювалки"""
        try:
            self.root.withdraw()  # Ховаємо головне вікно
            self.update_status("Малювалка відкрита")
            ScreenDrawer(self)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити малювалку: {e}")
            self.root.deiconify()  # Повертаємо вікно якщо помилка

    def quick_ocr(self):
        """Швидкий OCR"""
        self.run_ocr()

    def quick_speech(self):
        """Швидкий голосовий ввід"""
        self.handle_speech()

    def quick_translate(self):
        """Швидкий переклад"""
        if self.input_text.get(1.0, tk.END).strip():
            self.run_translate()

    def clear_text(self, text_widget):
        """Очищення текстового поля"""
        text_widget.delete(1.0, tk.END)

    def copy_text(self, text_widget):
        """Копіювання всього тексту"""
        content = text_widget.get(1.0, tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.update_status("Текст скопійовано!")

    def clear_history(self):
        """Очищення історії"""
        for widget in [self.ocr_text, self.speech_text, self.input_text, self.output_text]:
            widget.delete(1.0, tk.END)
        self.update_status("Історія очищена")

    def run_ocr(self):
        """Запуск звичайного розпізнавання тексту"""
        self.update_status("Виберіть область для розпізнавання...")
        ScreenSelector(self.set_ocr_text)

    def run_advanced_ocr(self):
        """Запуск покращеного розпізнавання тексту"""
        self.root.withdraw()
        self.update_status("Виберіть область для покращеного OCR...")
        time.sleep(0.1)
        AdvancedScreenSelector(self.set_ocr_text)


    def set_ocr_text(self, text):
        """Встановлення розпізнаного тексту"""
        self.ocr_text.delete(1.0, tk.END)
        self.ocr_text.insert(tk.END, text.strip())

        # Авто-переклад якщо увімкнено
        if self.auto_translate.get() and text.strip():
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, text.strip())
            self.run_translate()

        self.update_status(f"Розпізнано {len(text)} символів")

    def handle_speech(self):
        """Обробка голосового вводу"""
        if self.speech_active:
            self.speech_active = False
            if self.speech_thread:
                self.speech_thread.stop()
            self.speech_button.config(text="🎧 Почати запис")
            self.update_mic_status("Зупинено")
            return

        def speech_callback(text):
            self.speech_text.insert(tk.END, text + '\n')
            self.speech_text.see(tk.END)

            # Авто-переклад якщо увімкнено
            if self.auto_translate.get():
                clean_text = text.split('] ', 1)[-1] if '] ' in text else text
                if clean_text.strip():
                    self.input_text.delete(1.0, tk.END)
                    self.input_text.insert(tk.END, clean_text.strip())
                    self.root.after(500, self.run_translate)

        self.speech_active = True
        self.speech_button.config(text="⏹️ Зупинити")
        self.speech_thread = GoogleSpeechThread(speech_callback, self.update_mic_status)
        self.speech_thread.start()

    def get_translation_languages(self, selection):
        """Отримання кодів мов для перекладу"""
        lang_map = {
            0: ("uk", "en"),  # Українська → Англійська
            1: ("en", "uk"),  # Англійська → Українська
            2: ("uk", "de"),  # Українська → Німецька
            3: ("de", "uk"),  # Німецька → Українська
            4: ("uk", "fr"),  # Українська → Французька
            5: ("fr", "uk"),  # Французька → Українська
        }
        return lang_map.get(selection, ("uk", "en"))

    def run_translate(self):
        """Запуск перекладу"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showinfo("Помилка", "Немає тексту для перекладу")
            return

        self.update_status("Перекладаю...")

        try:
            from_lang, to_lang = self.get_translation_languages(self.lang_combo.current())

            translator = GoogleTranslator(source=from_lang, target=to_lang)
            translated = translator.translate(text)

            self.output_text.config(state='normal')
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, translated)
            self.output_text.config(state='disabled')

            self.update_status(f"Переклад завершено ({from_lang} → {to_lang})")

        except Exception as e:
            messagebox.showerror("Помилка перекладу", f"Не вдалося перекласти текст:\n{str(e)}")
            self.update_status("Помилка перекладу")

    def copy_event(self, event):
        """Копіювання виділеного тексту"""
        try:
            selected = event.widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
            return "break"
        except tk.TclError:
            pass

    def paste_event(self, event):
        """Вставка тексту"""
        try:
            content = self.root.clipboard_get()
            if event.widget.winfo_class() == 'Text':
                event.widget.insert(tk.INSERT, content)
            return "break"
        except tk.TclError:
            pass

    def select_all_event(self, event):
        """Виділення всього тексту"""
        event.widget.tag_add(tk.SEL, "1.0", tk.END)
        return "break"

    def hide_window(self):
        """Приховування вікна"""
        self.root.withdraw()
        self.update_status("Вікно приховано (Ctrl+Shift+Q для показу)")

    def initial_show_hide(self):
        def do_hide():
            self.root.deiconify()
            self.root.update_idletasks()
            self.root.withdraw()
            print("[Init] Програма запущена в фоновому режимі")

        self.root.after(100, do_hide)

    def toggle_visibility(self):
        """Переключення видимості вікна"""
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.update_status("Вікно відновлено")
        else:
            self.hide_window()

    def setup_hotkey(self):
        """Налаштування глобальних гарячих клавіш"""

        def on_activate():
            self.root.after(0, self.toggle_visibility)

        def listen():
            try:
                hotkey = keyboard.HotKey(
                    keyboard.HotKey.parse('<ctrl>+<shift>+q'),
                    on_activate
                )

                def for_canonical(f):
                    return lambda k: f(listener.canonical(k))

                with keyboard.Listener(
                        on_press=for_canonical(hotkey.press),
                        on_release=for_canonical(hotkey.release)
                ) as listener:
                    listener.join()
            except Exception as e:
                print(f"Помилка hotkey: {e}")

        threading.Thread(target=listen, daemon=True).start()

    def load_settings(self):
        """Завантаження налаштувань"""
        # Можна додати збереження/завантаження налаштувань у файл
        pass

    def save_settings(self):
        """Збереження налаштувань"""
        # Можна додати збереження налаштувань у файл
        pass

    def on_close(self):
        """Закриття програми"""
        if self.speech_active and self.speech_thread:
            self.speech_thread.stop()
        self.save_settings()
        self.root.withdraw()  # Ховаємо замість закриття


if __name__ == "__main__":
    print("[Запуск] Запускаємо покращену версію...")
    root = tk.Tk()

    # Налаштовуємо стиль
    style = ttk.Style()
    style.theme_use('clam')  # Сучасніший вигляд

    app = EnhancedApp(root)
    root.mainloop()