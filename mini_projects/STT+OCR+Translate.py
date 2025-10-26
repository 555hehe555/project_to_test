import sys
import subprocess
import importlib
import platform
import os
import urllib.request
import zipfile
import shutil
from pathlib import Path


class AutoInstaller:
    """Автоматичний інсталятор всіх необхідних компонентів"""

    def __init__(self):
        self.system = platform.system()
        self.app_dir = Path(__file__).parent if hasattr(Path(__file__), 'parent') else Path.cwd()
        self.tesseract_dir = self.app_dir / "tesseract"
        self.tesseract_exe = self.tesseract_dir / "tesseract.exe"

    def check_python_version(self):
        """Перевірка версії Python"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 7):
            print(f"❌ Потрібен Python 3.7 або новіший. Ваша версія: {sys.version}")
            input("Натисніть Enter для виходу...")
            sys.exit(1)
        print(f"✅ Python версія: {sys.version}")

    def install_pip_package(self, package_name, import_name=None):
        """Встановлення Python пакету"""
        if import_name is None:
            import_name = package_name.split('[')[0]  # для пакетів типу package[extra]

        try:
            importlib.import_module(import_name)
            print(f"✅ {package_name} вже встановлено")
            return True
        except ImportError:
            print(f"📦 Встановлюю {package_name}...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    package_name, "--quiet", "--disable-pip-version-check"
                ])
                print(f"✅ {package_name} успішно встановлено")
                return True
            except Exception as e:
                print(f"❌ Помилка встановлення {package_name}: {e}")
                return False

    def install_python_dependencies(self):
        """Встановлення всіх Python залежностей"""
        print("\n🔧 Перевірка та встановлення Python бібліотек...")

        packages = {
            'Pillow': 'PIL',
            'pytesseract': 'pytesseract',
            'pynput': 'pynput',
            'deep-translator': 'deep_translator',
            'sounddevice': 'sounddevice',
            'scipy': 'scipy',
            'numpy': 'numpy',
        }

        # Спочатку встановлюємо основні пакети
        for package, import_name in packages.items():
            self.install_pip_package(package, import_name)

        # Перевірка CUDA для torch
        cuda_available = self.check_cuda()

        # Встановлення PyTorch
        if cuda_available:
            print("🚀 Встановлюю PyTorch з підтримкою CUDA...")
            torch_cmd = "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
        else:
            print("💻 Встановлюю PyTorch (CPU версія)...")
            torch_cmd = "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu"

        try:
            import torch
            print("✅ PyTorch вже встановлено")
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + torch_cmd.split())
                print("✅ PyTorch встановлено")
            except Exception as e:
                print(f"⚠️ Не вдалося встановити PyTorch: {e}")

        # Встановлення Whisper
        try:
            importlib.import_module('faster_whisper')
            print("✅ faster-whisper вже встановлено")
        except ImportError:
            print("📦 Встановлюю faster-whisper...")
            self.install_pip_package('faster-whisper', 'faster_whisper')

    def check_cuda(self):
        """Перевірка доступності CUDA"""
        try:
            if self.system == "Windows":
                result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, shell=True)
                return result.returncode == 0
            elif self.system in ["Linux", "Darwin"]:
                result = subprocess.run(['which', 'nvidia-smi'], capture_output=True, text=True)
                if result.returncode == 0:
                    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
                    return result.returncode == 0
        except:
            pass
        return False

    def download_tesseract(self):
        """Завантаження Tesseract OCR"""
        if self.system != "Windows":
            print("\n⚠️ Автоматичне встановлення Tesseract доступне тільки для Windows")
            print("\nДля Linux виконайте: sudo apt-get install tesseract-ocr tesseract-ocr-ukr tesseract-ocr-eng")
            print("Для macOS виконайте: brew install tesseract tesseract-lang")
            input("\nНатисніть Enter після встановлення...")
            return None

        if self.tesseract_exe.exists():
            print(f"✅ Tesseract вже встановлено: {self.tesseract_exe}")
            return str(self.tesseract_exe)

        print("\n📥 Завантажую Tesseract OCR...")
        print("⏳ Це може зайняти кілька хвилин...")

        try:
            # URL для завантаження Tesseract (портативна версія)
            tesseract_url = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
            installer_path = self.app_dir / "tesseract_installer.exe"

            print(f"📡 Завантажую з {tesseract_url}")

            # Завантаження файлу з прогрес-баром
            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(downloaded * 100 / total_size, 100)
                bar_length = 40
                filled = int(bar_length * percent / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f'\r[{bar}] {percent:.1f}%', end='', flush=True)

            urllib.request.urlretrieve(tesseract_url, installer_path, reporthook=download_progress)
            print("\n✅ Завантаження завершено")

            # Запуск інсталятора
            print("\n📦 Запускаю інсталятор Tesseract...")
            print("⚠️ ВАЖЛИВО: Під час встановлення:")
            print("   1. Виберіть шлях встановлення або використайте стандартний")
            print("   2. Обов'язково виберіть мови: English та Ukrainian")
            print("   3. Запам'ятайте шлях встановлення!")

            input("\nНатисніть Enter для запуску інсталятора...")

            subprocess.run([str(installer_path)], check=False)

            # Видалення інсталятора
            try:
                installer_path.unlink()
            except:
                pass

            print("\n✅ Tesseract встановлено")
            print("\n📝 Тепер мені потрібен шлях до tesseract.exe")
            print("Стандартний шлях: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

            tesseract_path = input(
                "\nВведіть повний шлях до tesseract.exe (або натисніть Enter для стандартного): ").strip()

            if not tesseract_path:
                tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

            if Path(tesseract_path).exists():
                print(f"✅ Знайдено Tesseract: {tesseract_path}")
                return tesseract_path
            else:
                print(f"❌ Файл не знайдено: {tesseract_path}")
                print("Спробуйте знайти tesseract.exe вручну та запустіть програму знову")
                return None

        except Exception as e:
            print(f"\n❌ Помилка завантаження Tesseract: {e}")
            print("\n📝 Будь ласка, завантажте Tesseract вручну:")
            print("   1. Відвідайте: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   2. Завантажте інсталятор для Windows")
            print("   3. Встановіть з мовами Ukrainian та English")
            print("   4. Запустіть цю програму знову")
            return None

    def find_tesseract(self):
        """Пошук встановленого Tesseract"""
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            self.tesseract_exe,
        ]

        for path in possible_paths:
            if Path(path).exists():
                return str(path)

        # Пошук в PATH
        if self.system == "Windows":
            result = subprocess.run(['where', 'tesseract'], capture_output=True, text=True, shell=True)
        else:
            result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True)

        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]

        return None

    def setup(self):
        """Головна функція налаштування"""
        print("=" * 60)
        print("🚀 Автоматичне налаштування STT + OCR + Translate")
        print("=" * 60)

        # Перевірка Python
        self.check_python_version()

        # Встановлення Python бібліотек
        self.install_python_dependencies()

        # Налаштування Tesseract
        print("\n🔍 Шукаю Tesseract OCR...")
        tesseract_path = self.find_tesseract()

        if tesseract_path:
            print(f"✅ Tesseract знайдено: {tesseract_path}")
        else:
            print("❌ Tesseract не знайдено на вашому комп'ютері")
            tesseract_path = self.download_tesseract()

            if not tesseract_path:
                print("\n⚠️ Програма може працювати без Tesseract, але OCR функції будуть недоступні")
                input("Натисніть Enter для продовження...")

        print("\n" + "=" * 60)
        print("✅ Налаштування завершено!")
        print("=" * 60)

        return tesseract_path


# Автоматичне налаштування при першому запуску
def auto_setup():
    """Функція автоматичного налаштування"""
    installer = AutoInstaller()
    return installer.setup()


# Запуск налаштування
if __name__ != "__main__":
    print("🔧 Перевірка залежностей...")
    try:
        # Швидка перевірка основних бібліотек
        import tkinter
        import PIL
        import pytesseract

        TESSERACT_PATH = None
    except ImportError:
        print("⚠️ Потрібне налаштування системи...")
        TESSERACT_PATH = auto_setup()
        print("\n🔄 Перезапустіть програму для застосування змін")
        input("Натисніть Enter для виходу...")
        sys.exit(0)

# ==================== ОСНОВНИЙ КОД ПРОГРАМИ ====================

import io
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, colorchooser, font
from PIL import ImageGrab, ImageEnhance, ImageFilter, Image, ImageDraw, ImageTk
import pytesseract
import threading
from deep_translator import GoogleTranslator
from pynput import keyboard
import time
import math
from datetime import datetime
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import queue


# Автоматичне визначення шляху до Tesseract
def setup_tesseract():
    """Налаштування шляху до Tesseract"""
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        Path(__file__).parent / "tesseract" / "tesseract.exe",
    ]

    for path in possible_paths:
        if Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = str(path)
            print(f"✅ Tesseract знайдено: {path}")
            return True

    # Пошук в системному PATH
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.run(['where', 'tesseract'], capture_output=True, text=True, shell=True)
        else:
            result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True)

        if result.returncode == 0:
            tesseract_path = result.stdout.strip().split('\n')[0]
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✅ Tesseract знайдено: {tesseract_path}")
            return True
    except:
        pass

    print("⚠️ Tesseract не знайдено. OCR функції будуть недоступні.")
    print("Завантажте Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
    return False


# Налаштування Tesseract
TESSERACT_AVAILABLE = setup_tesseract()

# Перевірка Whisper і CUDA
try:
    from faster_whisper import WhisperModel
    import torch

    WHISPER_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()

    if CUDA_AVAILABLE:
        print(f"✅ CUDA доступна! GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚡ Використовується CPU для Whisper")
except ImportError:
    WHISPER_AVAILABLE = False
    CUDA_AVAILABLE = False
    print("⚠️ Whisper недоступний. STT функції будуть обмежені.")


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
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2)

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
        if not TESSERACT_AVAILABLE:
            text = "[OCR недоступний: Tesseract не встановлено]"
        else:
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
        self.sidebar = tk.Frame(self, bg='#2b2b2b', width=250, height=self.winfo_screenheight())
        self.sidebar.place(relx=1.0, rely=0, anchor="ne")
        self.sidebar.pack_propagate(False)

        title = tk.Label(self.sidebar, text="🎨 Малювалка", bg='#2b2b2b',
                         fg='white', font=('Arial', 12, 'bold'))
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

        actions_frame = tk.LabelFrame(self.sidebar, text="Дії", bg='#2b2b2b', fg='white')
        actions_frame.pack(fill=tk.X, padx=10, pady=5)

        actions = [
            ("↩️ Скасувати (Ctrl+Z)", self.undo),
            ("🗑️ Очистити все (Del)", self.clear_all),
            ("💾 Зберегти (Ctrl+S)", self.save_drawing),
            ("❌ Закрити (Esc)", self.close_drawer)
        ]

        for text, command in actions:
            tk.Button(actions_frame, text=text, bg='#404040', fg='white',
                      command=command).pack(fill=tk.X, pady=2, padx=5)

    def set_tool(self, tool):
        self.current_tool = tool
        for widget in self.sidebar.winfo_children():
            if isinstance(widget, tk.LabelFrame) and widget.cget('text') == 'Інструменти':
                for btn in widget.winfo_children():
                    if isinstance(btn, tk.Button):
                        if tool in btn.cget('text').lower():
                            btn.configure(bg='#ff4444')
                        else:
                            btn.configure(bg='#404040')

    def set_color(self, color):
        self.current_color = color
        self.color_preview.configure(bg=color)

    def choose_color(self):
        color = colorchooser.askcolor(title="Виберіть колір")[1]
        if color:
            self.set_color(color)

    def update_size(self, value):
        self.brush_size = int(value)

    def update_alpha(self, value):
        self.attributes('-alpha', float(value))

    def start_draw(self, event):
        self.drawing = True
        self.start_x, self.start_y = event.x, event.y

        if self.current_tool == "text":
            self.add_text(event.x, event.y)
        elif self.current_tool == "eraser":
            self.erase_at_point(event.x, event.y)
        elif self.current_tool in ["brush", "pencil"]:
            width = self.brush_size if self.current_tool == "brush" else max(1, self.brush_size // 2)
            point = self.canvas.create_oval(
                event.x - width // 2, event.y - width // 2,
                event.x + width // 2, event.y + width // 2,
                fill=self.current_color, outline=self.current_color)
            self.shapes.append(point)

    def draw(self, event):
        if not self.drawing:
            return

        if self.current_tool in ["brush", "pencil"]:
            width = self.brush_size if self.current_tool == "brush" else max(1, self.brush_size // 2)
            line_id = self.canvas.create_line(
                self.start_x, self.start_y, event.x, event.y,
                fill=self.current_color, width=width,
                capstyle=tk.ROUND, smooth=True)
            self.shapes.append(line_id)
            self.start_x, self.start_y = event.x, event.y

        elif self.current_tool == "eraser":
            self.erase_at_point(event.x, event.y)

        elif self.current_tool in ["line", "rectangle", "circle", "ellipse", "arrow"]:
            if self.temp_shape:
                self.canvas.delete(self.temp_shape)
            self.temp_shape = self.draw_shape(self.start_x, self.start_y, event.x, event.y)

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
        # self.setup_hotkey()  # Закоментовано для швидкого запуску
        self.load_settings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # self.root.after(100, self.initial_show_hide)  # Закоментовано для швидкого запуску

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
        self.status_var.set("Готовий до роботи | Whisper: Завантажиться при потребі")
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

    # def initial_show_hide(self):
    #     """Правильна ініціалізація стану вікна"""
    #
    #     def do_hide():
    #         # Спочатку показуємо вікно, щоб воно було доступне
    #         self.root.deiconify()
    #         self.root.update_idletasks()
    #
    #         # Потім приховуємо його для фонового режиму
    #         self.root.withdraw()
    #         print("[Init] Програма запущена в фоновому режимі. Натисніть Ctrl+Shift+Q для показу.")
    #
    #     # Викликаємо з невеликою затримкою, щоб усе ініціалізувалося
    #     self.root.after(500, do_hide)

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
            # self.root.withdraw()  # Закоментовано - закриваємо повністю
            self.root.destroy()  # Повне закриття замість приховування
            print("✅ Програма закрита.")

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

    # def setup_hotkey(self):
    #     """Налаштування гарячих клавіш (без виклику GUI з чужого потоку)"""
    #     import queue
    #     self.hotkey_queue = queue.Queue()

    #     def on_activate():
    #         # кладемо подію в чергу, а не викликаємо GUI прямо
    #         self.hotkey_queue.put("toggle")

    #     def listen():
    #         try:
    #             hotkey = keyboard.HotKey(
    #                 keyboard.HotKey.parse('<ctrl>+<shift>+q'),
    #                 on_activate
    #             )

    #             self.hotkey_listener = keyboard.Listener(
    #                 on_press=lambda k: hotkey.press(self.hotkey_listener.canonical(k)),
    #                 on_release=lambda k: hotkey.release(self.hotkey_listener.canonical(k))
    #             )
    #             self.hotkey_listener.start()
            #     print("Гарячі клавіши активовані: Ctrl+Shift+Q")
            # except Exception as e:
            #     print(f"Помилка гарячих клавіш: {e}")
            #     time.sleep(5)
            #     listen()

        # Фоновий потік для pynput
        # threading.Thread(target=listen, daemon=True).start()

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
                        language="uk",  # авто
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

                except Exception as error_s:
                    error_msg = str(error_s)
                    if "Whisper не доступний" in error_msg:
                        self.root.after(0, lambda: self.update_mic_status("❌ Whisper не встановлено. Використовуйте OCR або введіть текст вручну."))
                    else:
                        self.root.after(0, lambda: self.update_mic_status(f"❌ Помилка транскрипції: {error_msg}"))

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
            try:
                # Спробуємо імпортувати Whisper
                from faster_whisper import WhisperModel
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"

                self.whisper_model = WhisperModel(
                    self.whisper_model_size,
                    device=device,
                    compute_type=compute_type
                )
                dev_info = f"GPU ({torch.cuda.get_device_name(0)})" if device == "cuda" else "CPU"
                self.update_status(f"✅ Whisper готовий ({dev_info})")
            except ImportError:
                self.update_status("❌ Whisper не встановлено. Встановіть: pip install faster-whisper torch")
                raise Exception("Whisper не доступний")
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
    # root.after(100, app.initial_show_hide)  # Закоментовано для швидкого запуску
    root.mainloop()




