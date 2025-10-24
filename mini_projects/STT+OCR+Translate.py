import sys
import subprocess
import importlib
import platform
import os


def check_and_install_libraries():
    """Перевіряє та автоматично встановлює необхідні бібліотеки"""

    required_libraries = {
        'PIL': 'Pillow',
        'pytesseract': 'pytesseract',
        'pynput': 'pynput',
        'deep_translator': 'deep_translator',
        'sounddevice': 'sounddevice',
        'scipy': 'scipy',
        'numpy': 'numpy',
        'torch': 'torch',
    }

    # Спеціальні бібліотеки для Whisper
    whisper_libraries = {
        'faster_whisper': 'faster-whisper'
    }

    # Перевірка ОС та доступності CUDA
    system = platform.system()
    cuda_available = False

    print("🔍 Перевірка системи...")
    print(f"📋 ОС: {system}")
    print(f"🐍 Версія Python: {sys.version}")

    # Перевірка наявності NVIDIA GPU та CUDA
    try:
        if system == "Windows":
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, shell=True)
            cuda_available = result.returncode == 0
        elif system in ["Linux", "Darwin"]:
            result = subprocess.run(['which', 'nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
                cuda_available = result.returncode == 0
    except:
        cuda_available = False

    print(f"🎮 CUDA доступна: {'✅' if cuda_available else '❌'}")

    # Визначення версії torch для встановлення
    if cuda_available:
        torch_package = "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
        print("🚀 Використовується версія Torch з підтримкою CUDA")
    else:
        torch_package = "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"
        print("⚡ Використовується CPU-версія Torch")

    required_libraries['torch'] = torch_package

    # Список бібліотек для встановлення
    libraries_to_install = []

    print("\n🔍 Перевірка бібліотек...")

    # Перевірка основних бібліотек
    for lib_name, pip_name in required_libraries.items():
        try:
            importlib.import_module(lib_name)
            print(f"✅ {lib_name} вже встановлено")
        except ImportError:
            print(f"❌ {lib_name} не знайдено, додано до встановлення")
            libraries_to_install.append(pip_name)

    # Перевірка бібліотек Whisper
    whisper_missing = []
    for lib_name, pip_name in whisper_libraries.items():
        try:
            importlib.import_module(lib_name)
            print(f"✅ {lib_name} вже встановлено")
        except ImportError:
            print(f"❌ {lib_name} не знайдено")
            whisper_missing.append(pip_name)

    # Встановлення відсутніх бібліотек
    if libraries_to_install or whisper_missing:
        print(f"\n📦 Встановлення {len(libraries_to_install) + len(whisper_missing)} бібліотек...")

        # Встановлення основних бібліотек
        for lib in libraries_to_install:
            try:
                print(f"⬇️ Встановлення {lib}...")
                if lib.startswith("torch"):
                    # Спеціальна обробка для torch
                    subprocess.check_call([sys.executable, "-m", "pip", "install"] + lib.split())
                else:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                print(f"✅ {lib} успішно встановлено")
            except subprocess.CalledProcessError as e:
                print(f"❌ Помилка встановлення {lib}: {e}")

        # Встановлення бібліотек Whisper після torch
        for lib in whisper_missing:
            try:
                print(f"⬇️ Встановлення {lib}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                print(f"✅ {lib} успішно встановлено")
            except subprocess.CalledProcessError as e:
                print(f"❌ Помилка встановлення {lib}: {e}")

        print("\n🔄 Перезавантажте програму для застосування змін")
        input("Натисніть Enter для виходу...")
        sys.exit(0)
    else:
        print("\n✅ Всі бібліотеки встановлено та готові до роботи!")


# Виконання перевірки бібліотек
if __name__ != "__main__":
    check_and_install_libraries()

import io
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, colorchooser, font
from PIL import ImageGrab, ImageEnhance, ImageFilter, Image, ImageDraw, ImageTk
import pytesseract
import threading
import pkg_resources
from deep_translator import GoogleTranslator
from pynput import keyboard
import time
import math
from datetime import datetime
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import queue

# === Вкажи шлях до tesseract.exe, якщо потрібно ===
pytesseract.pytesseract.tesseract_cmd = r"D:\\Games\\tesseract_ocr\\tesseract.exe"

# Перевірка Whisper і CUDA
try:
    from faster_whisper import WhisperModel
    import torch

    WHISPER_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()

    if CUDA_AVAILABLE:
        print(f"✅ CUDA доступна! GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ CUDA недоступна, використовується CPU")

except ImportError as e:
    WHISPER_AVAILABLE = False
    CUDA_AVAILABLE = False
    print(f"❌ Whisper не встановлено: {e}")
    print("Встановіть командою: pip install faster-whisper torch sounddevice scipy")


class FullRecorder:
    def __init__(self, samplerate=16000, channels=1, dtype='float32'):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self._frames = []
        self._stream = None
        self._q = queue.Queue()

    def _callback(self, indata, frames, time, status):
        if status:
            print("Record status:", status)
        # copy to avoid referencing same buffer
        self._q.put(indata.copy())

    def start(self):
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self._callback
        )
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        # drain queue into frames list
        while not self._q.empty():
            self._frames.append(self._q.get())

        if not self._frames:
            return np.zeros(0, dtype='float32')

        audio = np.concatenate([f.reshape(-1) if f.ndim > 1 else f for f in self._frames])
        return audio.astype('float32')


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
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            text = pytesseract.image_to_string(img, lang='ukr+eng')
        except Exception as e:
            text = f"[OCR помилка: {e}]"

        self.callback(text)
        self.destroy()


class ScreenDrawer(tk.Toplevel):
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance

        self.attributes('-fullscreen', True)
        self.attributes('-alpha', 0.9)
        self.attributes('-topmost', False)
        self.configure(bg='gray20')

        self.current_tool = "brush"
        self.current_color = "#ff0000"
        self.brush_size = 3
        self.start_x = self.start_y = 0
        self.shapes = []
        self.temp_shape = None
        self.text_objects = []
        self.drawing = False

        self.canvas = tk.Canvas(self, highlightthickness=0, bg='gray10', cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)
        self.canvas.bind("<Button-3>", self.show_context_menu)

        self.bind_all("<Escape>", self.close_drawer)
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-s>", self.save_drawing)
        self.bind_all("<Delete>", self.clear_all)

        self.focus_set()
        self.after(100, self.create_sidebar)

    def create_sidebar(self):
        """Створення бокової панелі з інструментами"""
        sidebar_width = 250
        self.sidebar = tk.Frame(self, bg='#2b2b2b', width=250, height=self.winfo_screenheight())
        self.sidebar.place(relx=1.0, rely=0, anchor="ne")
        self.sidebar.pack_propagate(False)

        title = tk.Label(self.sidebar, text="🎨 Малювалка", bg='#2b2b2b', fg='white', font=('Arial', 12, 'bold'))
        title.pack(pady=10)

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

        colors_frame = tk.LabelFrame(self.sidebar, text="Кольори", bg='#2b2b2b', fg='white')
        colors_frame.pack(fill=tk.X, padx=10, pady=5)

        colors = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff",
                  "#ffffff", "#000000", "#ff8000", "#8000ff", "#808080", "#008000"]

        color_grid = tk.Frame(colors_frame, bg='#2b2b2b')
        color_grid.pack(fill=tk.X, padx=5, pady=5)

        for i, color in enumerate(colors):
            row, col = i // 4, i % 4
            btn = tk.Button(color_grid, bg=color, width=3, height=1,
                            command=lambda c=color: self.set_color(c))
            btn.grid(row=row, column=col, padx=2, pady=2)

        choose_btn = tk.Button(colors_frame, text="🎨 Вибрати колір", bg='#404040', fg='white',
                               command=self.choose_color)
        choose_btn.pack(fill=tk.X, padx=5, pady=5)

        self.color_preview = tk.Label(colors_frame, bg=self.current_color, text="Поточний",
                                      fg='white', font=('Arial', 8))
        self.color_preview.pack(fill=tk.X, padx=5, pady=2)

        size_frame = tk.LabelFrame(self.sidebar, text="Розмір", bg='#2b2b2b', fg='white')
        size_frame.pack(fill=tk.X, padx=10, pady=5)

        self.size_var = tk.IntVar(value=self.brush_size)
        size_scale = tk.Scale(size_frame, from_=1, to=20, orient=tk.HORIZONTAL,
                              variable=self.size_var, bg='#2b2b2b', fg='white',
                              command=self.update_size)
        size_scale.pack(fill=tk.X, padx=5, pady=5)

        alpha_frame = tk.LabelFrame(self.sidebar, text="Прозорість екрана", bg='#2b2b2b', fg='white')
        alpha_frame.pack(fill=tk.X, padx=10, pady=5)

        self.alpha_var = tk.DoubleVar(value=0.9)
        alpha_scale = tk.Scale(alpha_frame, from_=0.3, to=1.0, orient=tk.HORIZONTAL,
                               variable=self.alpha_var, bg='#2b2b2b', fg='white',
                               resolution=0.1, command=self.update_alpha)
        alpha_scale.pack(fill=tk.X, padx=5, pady=5)

        self.transparent_mode = tk.BooleanVar(value=False)
        tk.Checkbutton(alpha_frame, text="Прозорий режим", variable=self.transparent_mode,
                       bg='#2b2b2b', fg='white', selectcolor='#404040',
                       command=self.toggle_transparent_mode).pack(padx=5, pady=2)

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

        info_frame = tk.LabelFrame(self.sidebar, text="Інформація", bg='#2b2b2b', fg='white')
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        info_text = "Гарячі клавіші:\nEsc - Закрити\nCtrl+Z - Скасувати\nCtrl+C - Очистити\nCtrl+S - Зберегти"
        tk.Label(info_frame, text=info_text, bg='#2b2b2b', fg='white',
                 justify=tk.LEFT, font=('Arial', 8)).pack(padx=5, pady=5)

    def set_tool(self, tool):
        self.current_tool = tool
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
        self.current_color = color
        self.color_preview.configure(bg=color)

    def choose_color(self):
        self.attributes('-topmost', False)
        color_window = tk.Toplevel(self)
        color_window.title("Вибір кольору")
        color_window.geometry("400x300")
        color_window.configure(bg='#2b2b2b')
        color_window.attributes('-topmost', True)
        color_window.grab_set()

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

        tk.Button(color_window, text="Закрити", bg='#404040', fg='white',
                  command=color_window.destroy).pack(pady=20)

    def update_size(self, value):
        self.brush_size = int(value)

    def update_alpha(self, value):
        alpha = float(value)
        self.attributes('-alpha', alpha)
        if alpha < 0.7:
            self.canvas.configure(bg='gray5')
            self.configure(bg='gray5')
        else:
            self.canvas.configure(bg='gray10')
            self.configure(bg='gray20')

    def toggle_transparent_mode(self):
        if self.transparent_mode.get():
            self.alpha_var.set(0.3)
            self.update_alpha(0.3)
            self.canvas.configure(bg='')
            self.configure(bg='')
        else:
            self.alpha_var.set(0.9)
            self.update_alpha(0.9)

    def start_draw(self, event):
        self.drawing = True
        self.start_x, self.start_y = event.x, event.y

        if self.current_tool == "text":
            self.add_text(event.x, event.y)
        elif self.current_tool == "eraser":
            self.erase_at_point(event.x, event.y)
        elif self.current_tool in ["brush", "pencil"]:
            width = self.brush_size if self.current_tool == "brush" else max(1, self.brush_size // 2)
            point = self.canvas.create_oval(event.x - width // 2, event.y - width // 2,
                                            event.x + width // 2, event.y + width // 2,
                                            fill=self.current_color, outline=self.current_color)
            self.shapes.append(point)

    def draw(self, event):
        if not self.drawing:
            return

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
            if self.temp_shape:
                self.canvas.delete(self.temp_shape)
            self.temp_shape = self.draw_shape(self.start_x, self.start_y, event.x, event.y, temp=True)

    def end_draw(self, event):
        self.drawing = False

        if self.current_tool in ["line", "rectangle", "circle", "ellipse", "arrow"]:
            if self.temp_shape:
                self.canvas.delete(self.temp_shape)

            shape_id = self.draw_shape(self.start_x, self.start_y, event.x, event.y)
            if shape_id:
                self.shapes.append(shape_id)
            self.temp_shape = None

    def draw_shape(self, x1, y1, x2, y2, temp=False):
        if self.current_tool == "line":
            return self.canvas.create_line(x1, y1, x2, y2, fill=self.current_color, width=self.brush_size)

        elif self.current_tool == "rectangle":
            return self.canvas.create_rectangle(x1, y1, x2, y2, outline=self.current_color, width=self.brush_size)

        elif self.current_tool == "circle":
            radius = max(abs(x2 - x1), abs(y2 - y1)) // 2
            cx, cy = x1, y1
            return self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                           outline=self.current_color, width=self.brush_size)

        elif self.current_tool == "ellipse":
            return self.canvas.create_oval(x1, y1, x2, y2, outline=self.current_color, width=self.brush_size)

        elif self.current_tool == "arrow":
            arrow_id = self.canvas.create_line(x1, y1, x2, y2, fill=self.current_color,
                                               width=self.brush_size, arrow=tk.LAST, arrowshape=(16, 20, 6))
            return arrow_id

    def add_text(self, x, y):
        def submit_text():
            text = text_entry.get()
            if text:
                text_id = self.canvas.create_text(x, y, text=text, fill=self.current_color,
                                                  font=('Arial', self.brush_size + 8), anchor='nw')
                self.shapes.append(text_id)
                self.text_objects.append((text_id, text, x, y))
            dialog.destroy()

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
        nearby = self.canvas.find_overlapping(x - self.brush_size, y - self.brush_size,
                                              x + self.brush_size, y + self.brush_size)
        for item in nearby:
            if item in self.shapes:
                self.canvas.delete(item)
                self.shapes.remove(item)

    def show_context_menu(self, event):
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
        if self.shapes:
            last_shape = self.shapes.pop()
            self.canvas.delete(last_shape)

    def clear_all(self, event=None):
        for shape in self.shapes:
            self.canvas.delete(shape)
        self.shapes.clear()
        self.text_objects.clear()

    def save_drawing(self, event=None):
        try:
            filename = f"drawing_{int(time.time())}.png"
            ps = self.canvas.postscript(colormode='color')
            img = Image.open(io.BytesIO(ps.encode('utf-8')))
            img.save(filename, 'png')

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

        if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
            self.destroy()
            return

        self.withdraw()
        self.after(200, lambda: self.capture_area(x1, y1, x2, y2))

    def preprocess_image(self, img):
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        img = img.filter(ImageFilter.SHARPEN)
        return img

    def capture_area(self, x1, y1, x2, y2):
        try:
            img = ImageGrab.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))
            img = self.preprocess_image(img)
            text = pytesseract.image_to_string(img, lang='ukr+eng', config='--psm 6')
            text = text.strip()
            if not text:
                text = "[Текст не розпізнано]"
        except Exception as e:
            text = f"[OCR помилка: {e}]"

        self.callback(text)
        self.destroy()
        self.root.deiconify()


class EnhancedApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎤 STT + OCR + Translate Pro (Whisper CUDA)")
        self.root.geometry("400x550")
        self.root.minsize(500, 400)

        # Додаткові атрибути для нової системи запису
        self.whisper_model = None
        self.whisper_model_size = "medium"
        self.recorder = None
        self.transcribe_thread = None
        self.is_recording = False

        # Прапорці стану
        self.speech_active = False
        self.auto_translate = tk.BooleanVar()
        self.save_history = tk.BooleanVar()
        self.is_closing = False
        self.hotkey_listener = None

        self.build_enhanced_ui()
        self.setup_hotkey()
        self.load_settings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.initial_show_hide)

    def build_enhanced_ui(self):
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

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(toolbar, text="🔥 Швидкий доступ:").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="📷", command=self.quick_ocr, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎤", command=self.quick_speech, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎨", command=self.open_drawer, width=3).pack(side=tk.LEFT, padx=2)

        self.status_var = tk.StringVar()
        self.status_var.set("Готовий до роботи | Whisper: " + ("CUDA ✅" if CUDA_AVAILABLE else "CPU ⚠️"))
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        tab_control = ttk.Notebook(self.root)

        # OCR TAB
        ocr_tab = ttk.Frame(tab_control)
        ocr_controls = ttk.Frame(ocr_tab)
        ocr_controls.pack(fill=tk.X, padx=5, pady=5)

        self.ocr_text = scrolledtext.ScrolledText(ocr_tab, wrap=tk.WORD, font=('Arial', 11))
        self.ocr_advanced_btn = ttk.Button(ocr_controls, text="📸 OCR", command=self.run_advanced_ocr)
        self.ocr_clear_btn = ttk.Button(ocr_controls, text="🗑️ Очистити",
                                        command=lambda: self.clear_text(self.ocr_text))
        self.ocr_copy_btn = ttk.Button(ocr_controls, text="📋 Копіювати", command=lambda: self.copy_text(self.ocr_text))

        self.ocr_advanced_btn.pack(side=tk.LEFT, padx=2)
        self.ocr_clear_btn.pack(side=tk.LEFT, padx=2)
        self.ocr_copy_btn.pack(side=tk.LEFT, padx=2)
        self.ocr_text.pack(expand=True, fill='both', padx=5, pady=5)

        # STT TAB
        stt_tab = ttk.Frame(tab_control)
        stt_controls = ttk.Frame(stt_tab)
        stt_controls.pack(fill=tk.X, padx=5, pady=5)

        self.speech_text = scrolledtext.ScrolledText(stt_tab, wrap=tk.WORD, font=('Arial', 11))
        self.speech_button = ttk.Button(stt_controls, text="🎧 Почати запис (Whisper)", command=self.handle_speech)
        self.speech_clear_btn = ttk.Button(stt_controls, text="🗑️ Очистити",
                                           command=lambda: self.clear_text(self.speech_text))
        self.speech_copy_btn = ttk.Button(stt_controls, text="📋 Копіювати",
                                          command=lambda: self.copy_text(self.speech_text))

        self.mic_status = ttk.Label(stt_controls, text="🔴", font=('Arial', 16))

        self.speech_button.pack(side=tk.LEFT, padx=2)
        self.speech_clear_btn.pack(side=tk.LEFT, padx=2)
        self.speech_copy_btn.pack(side=tk.LEFT, padx=2)
        self.mic_status.pack(side=tk.RIGHT, padx=5)
        self.speech_text.pack(expand=True, fill='both', padx=5, pady=5)

        # TRANSLATE TAB
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

        self.translate_button = ttk.Button(translate_btn_frame, text="🌍 Перекласти", command=self.run_translate)
        self.translate_button.pack(side=tk.LEFT, padx=2)

        ttk.Label(trans_tab, text="Переклад:").pack(anchor=tk.W, padx=5)
        self.output_text = scrolledtext.ScrolledText(trans_tab, wrap=tk.WORD, height=8, font=('Arial', 11))
        self.output_text.pack(expand=True, fill='both', padx=5, pady=5)

        tab_control.add(ocr_tab, text="🖼️ Розпізнавання тексту")
        tab_control.add(stt_tab, text="🎤 Голосовий ввід (Whisper)")
        tab_control.add(trans_tab, text="🌍 Переклад")
        tab_control.pack(expand=True, fill='both', padx=5, pady=5)

        for widget in [self.ocr_text, self.speech_text, self.input_text, self.output_text]:
            widget.bind("<Control-c>", self.copy_event)
            widget.bind("<Control-v>", self.paste_event)
            widget.bind("<Control-a>", self.select_all_event)

    def initial_show_hide(self):
        """Правильна ініціалізація стану вікна"""

        def do_hide():
            # Спочатку показуємо вікно, щоб воно було доступне
            self.root.deiconify()
            self.root.update_idletasks()

            # Потім приховуємо його для фонового режиму
            self.root.withdraw()
            print("[Init] Програма запущена в фоновому режимі. Натисніть Ctrl+Shift+Q для показу.")

        # Викликаємо з невеликою затримкою, щоб усе ініціалізувалося
        self.root.after(500, do_hide)

    def auto_close(self, delay_seconds=0):
        """Автоматичне закриття програми через вказаний час"""

        def close_sequence():
            if delay_seconds > 0:
                print(f"🔄 Автоматичне закриття через {delay_seconds} секунд...")
                # Оновлюємо статус у GUI
                self.root.after(0, lambda: self.update_status(f"🔒 Автозакриття через {delay_seconds}с..."))
                time.sleep(delay_seconds)

            print("🔒 Виконуємо автоматичне закриття...")
            self.root.after(0, self.safe_close)

        # Запускаємо в окремому потоці
        close_thread = threading.Thread(target=close_sequence, daemon=True)
        close_thread.start()

    def safe_close(self):
        """Безпечне закриття програми"""
        if self.is_closing:
            return

        self.is_closing = True
        print("🔒 Запущено процедуру закриття...")

        try:
            self.update_status("🔒 Приховуємо вікно (фоновий режим)...")

            if self.is_recording and self.recorder:
                self.recorder.stop()

            if self.speech_active and hasattr(self, 'speech_thread'):
                self.speech_thread.stop()

            if self.hotkey_listener:
                # не зупиняємо, щоб гаряча клавіша залишалась активною
                pass

            self.save_settings()
            self.root.withdraw()
            print("✅ Вікно приховано, процес активний у фоні.")

        except Exception as e:
            print(f"⚠️ Помилка при закритті: {e}")
            import os
            os._exit(0)

    def toggle_visibility(self):
        """Перемикач видимості вікна"""
        try:
            if not self.root.winfo_exists():
                print("⚠️ Вікно знищено, неможливо показати повторно.")
                return

            if self.root.state() == 'withdrawn' or not self.root.winfo_viewable():
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.attributes('-topmost', True)
                self.update_status("Вікно активовано")
                self.root.after(1000, lambda: self.root.attributes('-topmost', False))
            else:
                self.root.withdraw()
                self.update_status("Вікно приховано (Ctrl+Shift+Q для показу)")
        except Exception as e:
            print(f"Помилка перемикання видимості: {e}")

    def hide_window(self):
        """Надійне приховування вікна"""
        try:
            self.root.withdraw()
            self.update_status("Вікно приховано (Ctrl+Shift+Q для показу)")
        except Exception as e:
            print(f"Помилка приховування вікна: {e}")

    def setup_hotkey(self):
        """Налаштування гарячих клавіш (без виклику GUI з чужого потоку)"""
        import queue
        self.hotkey_queue = queue.Queue()

        def on_activate():
            # кладемо подію в чергу, а не викликаємо GUI прямо
            self.hotkey_queue.put("toggle")

        def listen():
            try:
                hotkey = keyboard.HotKey(
                    keyboard.HotKey.parse('<ctrl>+<shift>+q'),
                    on_activate
                )

                self.hotkey_listener = keyboard.Listener(
                    on_press=lambda k: hotkey.press(self.hotkey_listener.canonical(k)),
                    on_release=lambda k: hotkey.release(self.hotkey_listener.canonical(k))
                )
                self.hotkey_listener.start()
                print("Гарячі клавіши активовані: Ctrl+Shift+Q")
            except Exception as e:
                print(f"Помилка гарячих клавіш: {e}")
                time.sleep(5)
                listen()

        # Фоновий потік для pynput
        threading.Thread(target=listen, daemon=True).start()

        # Перевіряємо чергу з головного потоку кожні 200 мс
        def check_queue():
            try:
                while True:
                    action = self.hotkey_queue.get_nowait()
                    if action == "toggle":
                        self.toggle_visibility()
            except queue.Empty:
                pass
            self.root.after(200, check_queue)

        self.root.after(200, check_queue)

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def update_mic_status(self, message):
        if "Запис" in message:
            self.mic_status.config(text="🔴", foreground="red")
        elif "Транскрибую" in message:
            self.mic_status.config(text="🟡", foreground="orange")
        elif "Транскрибування завершено" in message:
            self.mic_status.config(text="✅", foreground="green")
        elif "помилка" in message.lower():
            self.mic_status.config(text="❌", foreground="red")
        elif "Завантаження" in message:
            self.mic_status.config(text="⏳", foreground="blue")
        else:
            self.mic_status.config(text="⚪", foreground="gray")

        self.update_status(message)

    def open_drawer(self):
        try:
            self.root.withdraw()
            self.update_status("Малювалка відкрита")
            ScreenDrawer(self)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити малювалку: {e}")
            self.root.deiconify()

    def quick_ocr(self):
        self.run_ocr()

    def quick_speech(self):
        self.handle_speech()

    def quick_translate(self):
        if self.input_text.get(1.0, tk.END).strip():
            self.run_translate()

    def clear_text(self, text_widget):
        text_widget.delete(1.0, tk.END)

    def copy_text(self, text_widget):
        content = text_widget.get(1.0, tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.update_status("Текст скопійовано!")

    def clear_history(self):
        for widget in [self.ocr_text, self.speech_text, self.input_text, self.output_text]:
            widget.delete(1.0, tk.END)
        self.update_status("Історія очищена")

    def run_ocr(self):
        self.update_status("Виберіть область для розпізнавання...")
        ScreenSelector(self.set_ocr_text)

    def run_advanced_ocr(self):
        self.root.withdraw()
        self.update_status("Виберіть область для покращеного OCR...")
        time.sleep(0.1)
        AdvancedScreenSelector(self.set_ocr_text)

    def set_ocr_text(self, text):
        self.ocr_text.delete(1.0, tk.END)
        self.ocr_text.insert(tk.END, text.strip())

        if self.auto_translate.get() and text.strip():
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, text.strip())
            self.run_translate()

        self.update_status(f"Розпізнано {len(text)} символів")

    def handle_speech(self):
        # нова логіка: старт/стоп -> транскрибуємо весь запис при стопі
        if getattr(self, "is_recording", False):
            # зупиняємо запис і запускаємо транскрипцію в окремому потоці
            self.is_recording = False
            self.speech_button.config(text="🎧 Почати запис (Whisper)")
            self.update_mic_status("Зупинено. Транскрибую...")
            try:
                audio = self.recorder.stop()
            except Exception as e:
                self.update_mic_status(f"❌ Помилка запису: {e}")
                return

            def transcribe_job(audio_array):
                try:
                    # завантажуємо модель якщо потрібно
                    self.load_whisper_model()

                    if audio_array.shape[0] == 0:
                        self.update_mic_status("⚠️ Пустий запис")
                        return

                    # faster-whisper приймає numpy float32 з sample_rate=16000
                    segments, info = self.whisper_model.transcribe(
                        audio_array,
                        beam_size=5,
                        language=None,  # авто
                        task="transcribe",
                    )

                    # збираємо текст
                    parts = []
                    for seg in segments:
                        txt = seg.text.strip()
                        if txt:
                            parts.append(txt)

                    full_text = " ".join(parts).strip()

                    # Вставка в текстове поле разом з розміткою часу/мова
                    final = full_text

                    # оновлюємо GUI в головному потоці
                    def gui_update():
                        self.speech_text.insert(tk.END, final + "\n\n")
                        self.speech_text.see(tk.END)
                        self.update_mic_status("✅ Транскрибування завершено")

                    self.root.after(0, gui_update)

                except Exception as e:
                    self.root.after(0, lambda: self.update_mic_status(f"❌ Помилка транскрипції: {e}"))

            self.transcribe_thread = threading.Thread(target=transcribe_job, args=(audio,), daemon=True)
            self.transcribe_thread.start()
            return

        # якщо не записуємо — старт запису
        try:
            self.recorder = FullRecorder(samplerate=16000, channels=1)
            self.recorder.start()
            self.is_recording = True
            self.speech_button.config(text="⏹️ Зупинити і транскрибувати")
            self.update_mic_status("🎤 Запис...")
        except Exception as e:
            self.update_mic_status(f"❌ Помилка старту запису: {e}")
            self.is_recording = False

    def load_whisper_model(self):
        if self.whisper_model is None:
            self.update_status("⏳ Завантаження Whisper моделі...")
            device = "cuda" if CUDA_AVAILABLE else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
            try:
                self.whisper_model = WhisperModel(
                    self.whisper_model_size,
                    device=device,
                    compute_type=compute_type
                )
                dev_info = f"GPU ({torch.cuda.get_device_name(0)})" if device == "cuda" else "CPU"
                self.update_status(f"✅ Whisper готовий ({dev_info})")
            except Exception as e:
                self.update_status(f"❌ Помилка завантаження Whisper: {e}")
                raise

    def get_translation_languages(self, selection):
        lang_map = {
            0: ("uk", "en"),
            1: ("en", "uk"),
            2: ("uk", "de"),
            3: ("de", "uk"),
            4: ("uk", "fr"),
            5: ("fr", "uk"),
        }
        return lang_map.get(selection, ("uk", "en"))

    def run_translate(self):
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
        try:
            selected = event.widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
            return "break"
        except tk.TclError:
            pass

    def paste_event(self, event):
        try:
            content = self.root.clipboard_get()
            if event.widget.winfo_class() == 'Text':
                event.widget.insert(tk.INSERT, content)
            return "break"
        except tk.TclError:
            pass

    def select_all_event(self, event):
        event.widget.tag_add(tk.SEL, "1.0", tk.END)
        return "break"

    def load_settings(self):
        """Завантаження налаштувань"""
        pass

    def save_settings(self):
        """Збереження налаштувань"""
        pass

    def on_close(self):
        """Обробник закриття вікна"""
        print("🔒 Закриття програми...")
        self.safe_close()


if __name__ == "__main__":
    print("[Запуск] Запускаємо покращену версію з Whisper CUDA...")
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    app = EnhancedApp(root)
    root.after(100, app.initial_show_hide)
    root.mainloop()




