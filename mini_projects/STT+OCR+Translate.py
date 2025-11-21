# -*- coding: utf-8 -*-
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
        print(f"✅ Python версія: {version.major}.{version.minor}.{version.micro}")

    def install_pip_package(self, package_name, import_name=None):
        """Встановлення Python пакету"""
        if import_name is None:
            import_name = package_name.split('[')[0]

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

        for package, import_name in packages.items():
            self.install_pip_package(package, import_name)

        # Перевірка CUDA
        cuda_available = self.check_cuda()

        # Встановлення PyTorch
        if cuda_available:
            print("🚀 Встановлюю PyTorch з підтримкою CUDA...")
            torch_cmd = "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
        else:
            print("💻 Встановлюю PyTorch (CPU версія)...")
            torch_cmd = "torch torchvision torchaudio"

        try:
            import torch
            print("✅ PyTorch вже встановлено")
        except ImportError:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + torch_cmd.split())
                print("✅ PyTorch встановлено")
            except Exception as e:
                print(f"⚠️ Помилка встановлення PyTorch: {e}")

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

    def download_portable_tesseract(self):
        """Завантаження портативної версії Tesseract"""
        if self.tesseract_exe.exists():
            print(f"✅ Tesseract вже є: {self.tesseract_exe}")
            return str(self.tesseract_exe)

        print("\n📥 Завантажую портативну версію Tesseract OCR...")
        print("⏳ Це може зайняти кілька хвилин...")

        try:
            # Створюємо директорію для Tesseract
            self.tesseract_dir.mkdir(exist_ok=True)

            # Оновлений URL портативної версії Tesseract
            zip_url = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
            installer_path = self.app_dir / "tesseract_setup.exe"

            def show_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(downloaded * 100 / total_size, 100)
                bar_length = 40
                filled = int(bar_length * percent / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f'\r[{bar}] {percent:.1f}%', end='', flush=True)

            print(f"📡 Завантажую інсталятор...")
            urllib.request.urlretrieve(zip_url, installer_path, reporthook=show_progress)
            print("\n✅ Завантаження завершено!")

            print("\n" + "=" * 60)
            print("📦 ВСТАНОВЛЕННЯ TESSERACT OCR")
            print("=" * 60)
            print("\n⚠️ ВАЖЛИВО! Під час встановлення:")
            print("   1. Виберіть шлях: ", end="")
            print(str(self.tesseract_dir))
            print("   2. Обов'язково встановіть ДОДАТКОВІ МОВНІ ПАКЕТИ:")
            print("      ✓ Ukrainian")
            print("      ✓ English")
            print("   3. Після встановлення закрийте інсталятор")
            print("\n" + "=" * 60)

            input("\n➤ Натисніть Enter для запуску інсталятора...")

            # Запуск інсталятора
            subprocess.run([str(installer_path)])

            # Видалення інсталятора
            try:
                installer_path.unlink()
            except:
                pass

            # Перевірка чи встановлено
            if not self.tesseract_exe.exists():
                # Шукаємо в стандартних місцях
                standard_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
                if standard_path.exists():
                    print(f"\n✅ Tesseract знайдено: {standard_path}")
                    return str(standard_path)
                else:
                    print("\n⚠️ Tesseract не знайдено після встановлення")
                    print("Будь ласка, вкажіть шлях вручну")
                    return None
            else:
                print(f"\n✅ Tesseract встановлено: {self.tesseract_exe}")
                return str(self.tesseract_exe)

        except Exception as e:
            print(f"\n❌ Помилка: {e}")
            print("\n🔍 Альтернатива - встановіть Tesseract вручну:")
            print("   1. Відвідайте: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   2. Завантажте 'tesseract-ocr-w64-setup-5.x.x.exe'")
            print("   3. Встановіть з мовами Ukrainian + English")
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
            path = result.stdout.strip().split('\n')[0]
            if path:
                return path

        return None

    def setup(self):
        """Головна функція налаштування"""
        print("=" * 60)
        print("🚀 Автоматичне налаштування STT + OCR + Translate")
        print("=" * 60)

        self.check_python_version()
        self.install_python_dependencies()

        print("\n🔍 Шукаю Tesseract OCR...")
        tesseract_path = self.find_tesseract()

        if tesseract_path:
            print(f"✅ Tesseract знайдено: {tesseract_path}")
        else:
            print("❌ Tesseract не знайдено")
            choice = input("\nБажаєте завантажити та встановити Tesseract? (y/n): ").lower()
            if choice == 'y':
                tesseract_path = self.download_portable_tesseract()

        print("\n" + "=" * 60)
        print("✅ Налаштування завершено!")
        print("=" * 60)

        return tesseract_path


# ==================== ОСНОВНИЙ КОД ПРОГРАМИ ====================

import io
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import ImageGrab, ImageEnhance, ImageFilter, Image
import pytesseract
import threading
from deep_translator import GoogleTranslator
from pynput import keyboard
import time
import numpy as np
import sounddevice as sd
import queue


# Налаштування Tesseract
def setup_tesseract():
    """Налаштування шляху до Tesseract"""
    installer = AutoInstaller()
    tesseract_path = installer.find_tesseract()

    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"✅ Tesseract налаштовано: {tesseract_path}")
        return True
    else:
        print("⚠️ Tesseract не знайдено. OCR буде недоступний.")
        print("Запустіть setup для встановлення.")
        return False


TESSERACT_AVAILABLE = False
try:
    TESSERACT_AVAILABLE = setup_tesseract()
except Exception as e:
    print(f"⚠️ Помилка налаштування Tesseract: {e}")

# Перевірка Whisper
WHISPER_AVAILABLE = False
CUDA_AVAILABLE = False
try:
    from faster_whisper import WhisperModel
    import torch

    WHISPER_AVAILABLE = True
    CUDA_AVAILABLE = torch.cuda.is_available()

    if CUDA_AVAILABLE:
        print(f"✅ CUDA доступна! GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚡ Whisper використовуватиме CPU")
except ImportError:
    print("⚠️ Whisper недоступний")


class FullRecorder:
    """Клас для запису аудіо з покращеною обробкою"""

    def __init__(self, samplerate=16000, channels=1, dtype='float32'):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self._frames = []
        self._stream = None
        self._recording = False

    def _callback(self, indata, frames, time_info, status):
        """Callback для запису аудіо"""
        if status:
            print(f"⚠️ Статус запису: {status}")
        if self._recording:
            # Копіюємо дані одразу в список
            self._frames.append(indata.copy())

    def start(self):
        """Початок запису"""
        self._frames = []
        self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype=self.dtype,
                callback=self._callback,
                blocksize=1024  # Оптимальний розмір блоку
            )
            self._stream.start()
            print(f"✅ Запис розпочато: {self.samplerate}Hz, {self.channels} канал(и)")
        except Exception as e:
            print(f"❌ Помилка початку запису: {e}")
            self._recording = False
            raise

    def stop(self):
        """Зупинка запису та повернення аудіо"""
        self._recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"⚠️ Помилка закриття потоку: {e}")
            finally:
                self._stream = None

        # Даємо час на завершення callback
        time.sleep(0.1)

        if not self._frames:
            print("⚠️ Не записано жодного фрейму")
            return np.zeros(0, dtype='float32')

        try:
            # Об'єднуємо всі фрейми
            audio = np.concatenate(self._frames, axis=0)

            # Переводимо в одновимірний масив якщо потрібно
            if audio.ndim > 1:
                audio = audio.flatten()

            print(f"✅ Записано {len(audio)} сампли ({len(audio) / self.samplerate:.2f} секунд)")
            return audio.astype('float32')
        except Exception as e:
            print(f"❌ Помилка обробки аудіо: {e}")
            return np.zeros(0, dtype='float32')


class ScreenSelector(tk.Toplevel):
    """Віджет для вибору області екрану"""

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
        """Захоплення та розпізнавання області"""
        if not TESSERACT_AVAILABLE:
            text = "[OCR недоступний: Tesseract не встановлено]\n\nДля встановлення:\n1. Завантажте з https://github.com/UB-Mannheim/tesseract/wiki\n2. Встановіть з мовами Ukrainian + English"
            self.callback(text)
            self.destroy()
            return

        try:
            img = ImageGrab.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))
            # Покращення зображення
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = img.filter(ImageFilter.SHARPEN)
            text = pytesseract.image_to_string(img, lang='ukr+eng', config='--psm 6')
            if not text.strip():
                text = "[Текст не розпізнано. Спробуйте виділити область чіткіше]"
        except Exception as e:
            text = f"[OCR помилка: {e}]\n\nПеревірте, що Tesseract встановлено правильно."

        self.callback(text)
        self.destroy()


class ScreenDrawer(tk.Toplevel):
    """Малювалка на весь екран з повноцінним боковим меню"""

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance

        self.attributes('-fullscreen', True)
        self.attributes('-alpha', 0.95)
        self.configure(bg='#1a1a1a')

        self.current_tool = "brush"
        self.current_color = "#ff0000"
        self.brush_size = 5
        self.eraser_size = 20
        self.start_x = self.start_y = 0
        self.shapes = []
        self.temp_shape = None
        self.drawing = False
        self.tool_buttons = {}

        # Canvas для малювання
        self.canvas = tk.Canvas(self, highlightthickness=0, bg='#0d0d0d', cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)

        self.bind_all("<Escape>", self.close_drawer)
        self.bind_all("<Control-z>", self.undo)
        self.bind_all("<Control-c>", self.clear_canvas)

        self.focus_set()
        self.create_sidebar()

    def create_sidebar(self):
        """Створення бічної панелі інструментів"""
        self.sidebar = tk.Frame(self, bg='#2b2b2b', width=280, height=self.winfo_screenheight())
        self.sidebar.place(relx=1.0, rely=0, anchor="ne", relheight=1.0)
        self.sidebar.pack_propagate(False)

        # Заголовок
        title = tk.Label(self.sidebar, text="🎨 Малювалка", bg='#2b2b2b',
                         fg='white', font=('Arial', 14, 'bold'))
        title.pack(pady=15)

        # Інструменти
        tools_frame = tk.LabelFrame(self.sidebar, text="📐 Інструменти",
                                    bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold'))
        tools_frame.pack(fill=tk.X, padx=10, pady=5)

        tools = [
            ("🖌️ Пензель", "brush", "#404040"),
            ("✏️ Олівець", "pencil", "#404040"),
            ("📏 Лінія", "line", "#404040"),
            ("⬜ Прямокутник", "rectangle", "#404040"),
            ("⭕ Коло", "circle", "#404040"),
            ("🧽 Ластик", "eraser", "#404040"),
        ]

        for text, tool, color in tools:
            btn = tk.Button(tools_frame, text=text, bg=color, fg='white',
                            font=('Arial', 10), relief=tk.RAISED, bd=2,
                            command=lambda t=tool: self.set_tool(t))
            btn.pack(fill=tk.X, pady=3, padx=5)
            self.tool_buttons[tool] = btn

        # Виділяємо активний інструмент
        self.tool_buttons["brush"].config(bg='#00aa00', relief=tk.SUNKEN)

        # Колір
        color_frame = tk.LabelFrame(self.sidebar, text="🎨 Колір",
                                    bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold'))
        color_frame.pack(fill=tk.X, padx=10, pady=5)

        # Попередній перегляд кольору
        self.color_preview = tk.Canvas(color_frame, width=200, height=40,
                                       bg=self.current_color, highlightthickness=2,
                                       highlightbackground='white')
        self.color_preview.pack(pady=5, padx=5)

        # Швидкі кольори
        quick_colors_frame = tk.Frame(color_frame, bg='#2b2b2b')
        quick_colors_frame.pack(pady=5)

        colors = [
            "#ff0000", "#00ff00", "#0000ff", "#ffff00",
            "#ff00ff", "#00ffff", "#ffffff", "#000000",
            "#ff8800", "#88ff00", "#0088ff", "#8800ff"
        ]

        for i, color in enumerate(colors):
            btn = tk.Button(quick_colors_frame, bg=color, width=3, height=1,
                            command=lambda c=color: self.set_color(c))
            btn.grid(row=i // 4, column=i % 4, padx=2, pady=2)

        # Кнопка вибору кольору
        tk.Button(color_frame, text="🎨 Вибрати колір", bg='#404040', fg='white',
                  command=self.choose_color).pack(pady=5, padx=5, fill=tk.X)

        # Розмір пензля
        size_frame = tk.LabelFrame(self.sidebar, text="📏 Розмір",
                                   bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold'))
        size_frame.pack(fill=tk.X, padx=10, pady=5)

        self.size_var = tk.IntVar(value=self.brush_size)
        self.size_label = tk.Label(size_frame, text=f"Розмір: {self.brush_size}px",
                                   bg='#2b2b2b', fg='white')
        self.size_label.pack(pady=5)

        tk.Scale(size_frame, from_=1, to=50, orient=tk.HORIZONTAL,
                 variable=self.size_var, bg='#2b2b2b', fg='white',
                 troughcolor='#404040', highlightthickness=0,
                 command=self.update_size).pack(fill=tk.X, padx=5, pady=5)

        # Дії
        actions_frame = tk.LabelFrame(self.sidebar, text="⚙️ Дії",
                                      bg='#2b2b2b', fg='white', font=('Arial', 10, 'bold'))
        actions_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(actions_frame, text="↩️ Скасувати (Ctrl+Z)", bg='#ff8800', fg='white',
                  font=('Arial', 9), command=self.undo).pack(fill=tk.X, pady=3, padx=5)

        tk.Button(actions_frame, text="🗑️ Очистити все (Ctrl+C)", bg='#cc4400', fg='white',
                  font=('Arial', 9), command=self.clear_canvas).pack(fill=tk.X, pady=3, padx=5)

        tk.Button(actions_frame, text="💾 Зберегти зображення", bg='#0088ff', fg='white',
                  font=('Arial', 9), command=self.save_canvas).pack(fill=tk.X, pady=3, padx=5)

        # Інфо
        info_frame = tk.Frame(self.sidebar, bg='#2b2b2b')
        info_frame.pack(fill=tk.X, padx=10, pady=10)

        info_text = "⌨️ Гарячі клавіші:\nEsc - Закрити\nCtrl+Z - Скасувати\nCtrl+C - Очистити"
        tk.Label(info_frame, text=info_text, bg='#2b2b2b', fg='#aaaaaa',
                 font=('Arial', 8), justify=tk.LEFT).pack()

        # Кнопка закриття
        tk.Button(self.sidebar, text="❌ Закрити малювалку", bg='#ff4444', fg='white',
                  font=('Arial', 11, 'bold'), command=self.close_drawer).pack(
            side=tk.BOTTOM, fill=tk.X, padx=10, pady=15)

    def set_tool(self, tool):
        """Зміна інструменту"""
        # Скидаємо підсвічування всіх кнопок
        for btn in self.tool_buttons.values():
            btn.config(bg='#404040', relief=tk.RAISED)

        # Підсвічуємо обраний інструмент
        self.tool_buttons[tool].config(bg='#00aa00', relief=tk.SUNKEN)

        self.current_tool = tool

        # Змінюємо курсор залежно від інструменту
        if tool == "eraser":
            self.canvas.config(cursor="circle")
        else:
            self.canvas.config(cursor="crosshair")

    def set_color(self, color):
        """Зміна кольору"""
        self.current_color = color
        self.color_preview.config(bg=color)

    def choose_color(self):
        """Вибір кольору через діалог"""
        from tkinter import colorchooser
        color = colorchooser.askcolor(self.current_color)[1]
        if color:
            self.set_color(color)

    def update_size(self, value):
        """Оновлення розміру пензля"""
        size = int(float(value))
        self.brush_size = size
        self.size_label.config(text=f"Розмір: {size}px")

    def start_draw(self, event):
        """Початок малювання"""
        self.drawing = True
        self.start_x, self.start_y = event.x, event.y

        if self.current_tool in ["line", "rectangle", "circle"]:
            # Для фігур створюємо тимчасовий об'єкт
            if self.current_tool == "line":
                self.temp_shape = self.canvas.create_line(
                    self.start_x, self.start_y, self.start_x, self.start_y,
                    fill=self.current_color, width=self.brush_size)
            elif self.current_tool == "rectangle":
                self.temp_shape = self.canvas.create_rectangle(
                    self.start_x, self.start_y, self.start_x, self.start_y,
                    outline=self.current_color, width=self.brush_size)
            elif self.current_tool == "circle":
                self.temp_shape = self.canvas.create_oval(
                    self.start_x, self.start_y, self.start_x, self.start_y,
                    outline=self.current_color, width=self.brush_size)

    def draw(self, event):
        """Малювання"""
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
            # Ластик малює білим кольором
            eraser_size = max(self.brush_size, 10)
            line_id = self.canvas.create_line(
                self.start_x, self.start_y, event.x, event.y,
                fill='#0d0d0d', width=eraser_size,
                capstyle=tk.ROUND, smooth=True)
            self.shapes.append(line_id)
            self.start_x, self.start_y = event.x, event.y

        elif self.temp_shape:
            # Оновлюємо тимчасову фігуру
            if self.current_tool == "line":
                self.canvas.coords(self.temp_shape,
                                   self.start_x, self.start_y, event.x, event.y)
            elif self.current_tool in ["rectangle", "circle"]:
                self.canvas.coords(self.temp_shape,
                                   self.start_x, self.start_y, event.x, event.y)

    def end_draw(self, event):
        """Завершення малювання"""
        self.drawing = False
        if self.temp_shape:
            self.shapes.append(self.temp_shape)
            self.temp_shape = None

    def undo(self, event=None):
        """Скасування останньої дії"""
        if self.shapes:
            self.canvas.delete(self.shapes.pop())

    def clear_canvas(self, event=None):
        """Очищення всього полотна"""
        for shape in self.shapes:
            self.canvas.delete(shape)
        self.shapes = []

    def save_canvas(self):
        """Збереження малюнку"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")])

            if filename:
                # Отримуємо координати canvas
                x = self.canvas.winfo_rootx()
                y = self.canvas.winfo_rooty()
                x1 = x + self.canvas.winfo_width() - 280  # Віднімаємо ширину sidebar
                y1 = y + self.canvas.winfo_height()

                # Захоплюємо зображення
                img = ImageGrab.grab(bbox=(x, y, x1, y1))
                img.save(filename)
                messagebox.showinfo("Успіх", f"Зображення збережено: {filename}")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося зберегти: {e}")

    def close_drawer(self, event=None):
        """Закриття малювалки"""
        self.destroy()
        self.app_instance.root.deiconify()


class EnhancedApp:
    """Головний клас застосунку"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎤 STT + OCR + Translate Pro")
        self.root.geometry("600x550")

        self.whisper_model = None
        self.whisper_model_size = "tiny"
        self.recorder = None
        self.is_recording = False
        self.auto_translate = tk.BooleanVar()

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        """Побудова інтерфейсу"""
        # Меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Налаштування", menu=settings_menu)
        settings_menu.add_checkbutton(label="Авто-переклад", variable=self.auto_translate)
        settings_menu.add_separator()
        settings_menu.add_command(label="🎨 Малювалка", command=self.open_drawer)
        settings_menu.add_separator()
        settings_menu.add_command(label="Очистити історію", command=self.clear_history)
        settings_menu.add_separator()
        settings_menu.add_command(label="⚙️ Встановити Tesseract", command=self.run_setup)

        # Панель швидкого доступу
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(toolbar, text="🔥 Швидкий доступ:").pack(side=tk.LEFT)
        ttk.Button(toolbar, text="📷 OCR", command=self.quick_ocr, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎤 Аудіо", command=self.quick_speech, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎨 Малювати", command=self.open_drawer, width=10).pack(side=tk.LEFT, padx=2)

        # Статус-бар
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
        ttk.Button(ocr_controls, text="📸 Розпізнати текст",
                   command=self.run_ocr).pack(side=tk.LEFT, padx=2)
        ttk.Button(ocr_controls, text="🗑️ Очистити",
                   command=lambda: self.clear_text(self.ocr_text)).pack(side=tk.LEFT, padx=2)
        ttk.Button(ocr_controls, text="📋 Копіювати",
                   command=lambda: self.copy_text(self.ocr_text)).pack(side=tk.LEFT, padx=2)

        self.ocr_text.pack(expand=True, fill='both', padx=5, pady=5)

        # === STT TAB ===
        stt_tab = ttk.Frame(tab_control)
        stt_controls = ttk.Frame(stt_tab)
        stt_controls.pack(fill=tk.X, padx=5, pady=5)

        self.speech_text = scrolledtext.ScrolledText(stt_tab, wrap=tk.WORD, font=('Arial', 11))
        self.speech_button = ttk.Button(stt_controls, text="🎧 Почати запис",
                                        command=self.handle_speech)
        self.speech_clear_btn = ttk.Button(stt_controls, text="🗑️ Очистити",
                                           command=lambda: self.clear_text(self.speech_text))
        self.speech_copy_btn = ttk.Button(stt_controls, text="📋 Копіювати",
                                          command=lambda: self.copy_text(self.speech_text))

        self.mic_status = ttk.Label(stt_controls, text="⚪", font=('Arial', 16))

        self.speech_button.pack(side=tk.LEFT, padx=2)
        self.speech_clear_btn.pack(side=tk.LEFT, padx=2)
        self.speech_copy_btn.pack(side=tk.LEFT, padx=2)
        self.mic_status.pack(side=tk.RIGHT, padx=5)
        self.speech_text.pack(expand=True, fill='both', padx=5, pady=5)

        # Вибір розміру моделі
        model_frame = ttk.Frame(stt_tab)
        model_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(model_frame, text="Модель Whisper:").pack(side=tk.LEFT)
        self.model_combo = ttk.Combobox(model_frame, values=["tiny", "base", "small", "medium"],
                                        state="readonly", width=10)
        self.model_combo.set("tiny")
        self.model_combo.pack(side=tk.LEFT, padx=5)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_change)

        # === TRANSLATE TAB ===
        trans_tab = ttk.Frame(tab_control)
        trans_controls = ttk.Frame(trans_tab)
        trans_controls.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(trans_controls, text="Текст для перекладу:").pack(anchor=tk.W)
        self.input_text = scrolledtext.ScrolledText(trans_tab, wrap=tk.WORD, height=8, font=('Arial', 11))
        self.input_text.pack(fill='both', padx=5, pady=5)

        lang_frame = ttk.Frame(trans_tab)
        lang_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(lang_frame, text="Напрямок:").pack(side=tk.LEFT)
        self.lang_combo = ttk.Combobox(lang_frame, values=[
            "Українська → Англійська",
            "Англійська → Українська",
            "Українська → Німецька",
            "Німецька → Українська"
        ], state="readonly", width=25)
        self.lang_combo.current(0)
        self.lang_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(trans_tab, text="🌍 Перекласти",
                   command=self.run_translate).pack(pady=5)

        ttk.Label(trans_tab, text="Переклад:").pack(anchor=tk.W, padx=5)
        self.output_text = scrolledtext.ScrolledText(trans_tab, wrap=tk.WORD, height=8, font=('Arial', 11))
        self.output_text.pack(expand=True, fill='both', padx=5, pady=5)

        # Додавання вкладок
        tab_control.add(ocr_tab, text="🖼️ OCR")
        tab_control.add(stt_tab, text="🎤 Аудіо (Whisper)")
        tab_control.add(trans_tab, text="🌍 Переклад")
        tab_control.pack(expand=True, fill='both', padx=5, pady=5)

    def on_model_change(self, event=None):
        """Зміна моделі Whisper"""
        self.whisper_model_size = self.model_combo.get()
        self.whisper_model = None  # Скидаємо модель для перезавантаження
        self.update_status(f"Модель змінено на: {self.whisper_model_size}")

    def run_setup(self):
        """Запуск процесу встановлення"""
        self.update_status("Запуск налаштування...")

        def setup_thread():
            installer = AutoInstaller()
            tesseract_path = installer.download_portable_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                global TESSERACT_AVAILABLE
                TESSERACT_AVAILABLE = True
                self.root.after(0, lambda: self.update_status("✅ Tesseract встановлено!"))
                self.root.after(0, lambda: messagebox.showinfo("Успіх", "Tesseract успішно встановлено!"))
            else:
                self.root.after(0, lambda: self.update_status("❌ Помилка встановлення"))

        threading.Thread(target=setup_thread, daemon=True).start()

    def open_drawer(self):
        """Відкриття малювалки"""
        try:
            self.root.withdraw()
            self.update_status("Малювалка відкрита")
            ScreenDrawer(self)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити малювалку: {e}")
            self.root.deiconify()

    def quick_ocr(self):
        """Швидкий доступ до OCR"""
        self.run_ocr()

    def quick_speech(self):
        """Швидкий доступ до розпізнавання мови"""
        self.handle_speech()

    def clear_text(self, text_widget):
        """Очищення текстового поля"""
        text_widget.delete(1.0, tk.END)

    def copy_text(self, text_widget):
        """Копіювання тексту в буфер обміну"""
        content = text_widget.get(1.0, tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.update_status("Текст скопійовано!")

    def clear_history(self):
        """Очищення всієї історії"""
        for widget in [self.ocr_text, self.speech_text, self.input_text, self.output_text]:
            widget.delete(1.0, tk.END)
        self.update_status("Історія очищена")

    def run_ocr(self):
        """Запуск OCR розпізнавання"""
        if not TESSERACT_AVAILABLE:
            response = messagebox.askyesno(
                "Tesseract не встановлено",
                "Tesseract OCR не знайдено на вашому комп'ютері.\n\n"
                "Бажаєте встановити його зараз?"
            )
            if response:
                self.run_setup()
            return

        self.update_status("Виберіть область для розпізнавання...")
        self.root.withdraw()
        time.sleep(0.1)
        ScreenSelector(self.set_ocr_text)

    def set_ocr_text(self, text):
        """Встановлення розпізнаного тексту"""
        self.root.deiconify()
        self.ocr_text.delete(1.0, tk.END)
        self.ocr_text.insert(tk.END, text.strip())

        if self.auto_translate.get() and text.strip() and "[" not in text:
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, text.strip())
            self.run_translate()

        self.update_status(f"Розпізнано {len(text)} символів")

    def handle_speech(self):
        """Обробка запису та розпізнавання мови"""
        if not WHISPER_AVAILABLE:
            response = messagebox.askyesno(
                "Whisper не встановлено",
                "Whisper недоступний. Бажаєте встановити необхідні бібліотеки?\n\n"
                "Це може зайняти кілька хвилин."
            )
            if response:
                def install():
                    installer = AutoInstaller()
                    installer.install_python_dependencies()
                    self.root.after(0, lambda: messagebox.showinfo("Готово", "Перезапустіть програму"))

                threading.Thread(target=install, daemon=True).start()
            return

        if self.is_recording:
            # Зупинка запису
            self.is_recording = False
            self.speech_button.config(text="🎧 Почати запис")
            self.speech_button.config(state='disabled')
            self.update_mic_status("⏳ Зупинено. Транскрибую...")

            def stop_and_transcribe():
                try:
                    # Зупиняємо запис
                    audio = self.recorder.stop()

                    if len(audio) < 1600:  # Менше 0.1 секунди
                        self.root.after(0, lambda: self.update_mic_status("⚠️ Занадто короткий запис"))
                        self.root.after(0, lambda: self.speech_button.config(state='normal'))
                        return

                    # Нормалізація аудіо
                    audio = audio / np.max(np.abs(audio) + 1e-8)

                    print(f"📊 Аудіо: {len(audio)} сампли, {len(audio) / 16000:.2f} сек")

                    # Завантаження моделі
                    self.load_whisper_model()

                    # Транскрипція
                    print("🎯 Починаю транскрипцію...")
                    segments, info = self.whisper_model.transcribe(
                        audio,
                        beam_size=5,
                        language="uk",
                        task="transcribe",
                        vad_filter=True,
                        vad_parameters=dict(min_silence_duration_ms=500),
                    )

                    # Збираємо текст
                    parts = []
                    for seg in segments:
                        txt = seg.text.strip()
                        if txt:
                            parts.append(txt)
                            print(f"  📝 [{seg.start:.2f}s - {seg.end:.2f}s]: {txt}")

                    full_text = " ".join(parts).strip()

                    if not full_text:
                        full_text = "[Мову не розпізнано. Спробуйте:\n- Говорити голосніше\n- Тримати мікрофон ближче\n- Записувати довше (мін 1-2 сек)]"

                    print(f"✅ Результат: {full_text[:100]}...")

                    # Оновлення GUI
                    def gui_update():
                        self.speech_text.insert(tk.END, full_text + "\n\n")
                        self.speech_text.see(tk.END)
                        self.update_mic_status("✅ Готово")
                        self.speech_button.config(state='normal')

                        # Автоматичний переклад
                        if self.auto_translate.get() and "[" not in full_text:
                            self.input_text.delete(1.0, tk.END)
                            self.input_text.insert(tk.END, full_text)
                            self.run_translate()

                    self.root.after(0, gui_update)

                except Exception as error_s:
                    import traceback
                    error_msg = str(error_s)
                    print(f"❌ Помилка транскрипції:\n{traceback.format_exc()}")

                    def show_error():
                        self.update_mic_status(f"❌ Помилка: {error_msg[:50]}")
                        self.speech_button.config(state='normal')

                    self.root.after(0, show_error)

            threading.Thread(target=stop_and_transcribe, daemon=True).start()
            return

        # Початок запису
        try:
            print("\n🎤 Початок запису...")
            self.recorder = FullRecorder(samplerate=16000, channels=1)
            self.recorder.start()
            self.is_recording = True
            self.speech_button.config(text="⏹️ Зупинити і розпізнати")
            self.update_mic_status("🔴 Запис... (говоріть зараз)")
        except Exception as e:
            print(f"❌ Помилка початку запису: {e}")
            self.update_mic_status(f"❌ Помилка мікрофону: {e}")
            self.is_recording = False

    def load_whisper_model(self):
        """Завантаження моделі Whisper"""
        if self.whisper_model is None:
            self.root.after(0, lambda: self.update_status(f"⏳ Завантаження Whisper ({self.whisper_model_size})..."))

            try:
                from faster_whisper import WhisperModel
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"

                # Завантаження моделі
                self.whisper_model = WhisperModel(
                    self.whisper_model_size,
                    device=device,
                    compute_type=compute_type,
                    download_root=str(Path.home() / ".cache" / "whisper")
                )

                dev_info = f"GPU ({torch.cuda.get_device_name(0)})" if device == "cuda" else "CPU"
                self.root.after(0, lambda: self.update_status(f"✅ Whisper готовий ({dev_info})"))

            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"❌ Помилка Whisper: {e}"))
                raise

    def update_status(self, message):
        """Оновлення статус-бару"""
        self.status_var.set(message)
        self.root.update_idletasks()

    def update_mic_status(self, message):
        """Оновлення статусу мікрофону"""
        if "Запис" in message:
            self.mic_status.config(text="🔴", foreground="red")
        elif "Транскриб" in message or "Зупинено" in message:
            self.mic_status.config(text="🟡", foreground="orange")
        elif "Готово" in message or "✅" in message:
            self.mic_status.config(text="✅", foreground="green")
        elif "помилка" in message.lower() or "❌" in message:
            self.mic_status.config(text="❌", foreground="red")
        elif "Завантаження" in message:
            self.mic_status.config(text="⏳", foreground="blue")
        else:
            self.mic_status.config(text="⚪", foreground="gray")

        self.update_status(message)

    def get_translation_languages(self, selection):
        """Отримання мов для перекладу"""
        lang_map = {
            0: ("uk", "en"),
            1: ("en", "uk"),
            2: ("uk", "de"),
            3: ("de", "uk"),
        }
        return lang_map.get(selection, ("uk", "en"))

    def run_translate(self):
        """Виконання перекладу"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showinfo("Помилка", "Немає тексту для перекладу")
            return

        self.update_status("Перекладаю...")

        def translate_thread():
            try:
                from_lang, to_lang = self.get_translation_languages(self.lang_combo.current())

                translator = GoogleTranslator(source=from_lang, target=to_lang)
                translated = translator.translate(text)

                def gui_update():
                    self.output_text.delete(1.0, tk.END)
                    self.output_text.insert(tk.END, translated)
                    self.update_status(f"Переклад завершено ({from_lang} → {to_lang})")

                self.root.after(0, gui_update)

            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror("Помилка перекладу",
                                                                f"Не вдалося перекласти:\n{error_msg}"))
                self.root.after(0, lambda: self.update_status("Помилка перекладу"))

        threading.Thread(target=translate_thread, daemon=True).start()

    def on_close(self):
        """Обробник закриття вікна"""
        if self.is_recording and self.recorder:
            try:
                self.recorder.stop()
            except:
                pass
        self.root.destroy()


# Головна функція запуску
def main():
    """Головна функція програми"""
    print("=" * 60)
    print("🚀 STT + OCR + Translate Pro - Portable Edition")
    print("=" * 60)

    # Перевірка необхідних бібліотек
    missing_libs = []

    try:
        import tkinter
    except ImportError:
        missing_libs.append("tkinter")

    try:
        import PIL
    except ImportError:
        missing_libs.append("Pillow")

    try:
        import pytesseract
    except ImportError:
        missing_libs.append("pytesseract")

    if missing_libs:
        print("\n⚠️ Відсутні необхідні бібліотеки!")
        print("Запускаю автоматичне встановлення...\n")

        installer = AutoInstaller()
        installer.check_python_version()
        installer.install_python_dependencies()

        print("\n✅ Встановлення завершено!")
        print("🔄 Будь ласка, перезапустіть програму\n")
        input("Натисніть Enter для виходу...")
        sys.exit(0)

    # Запуск програми
    print("\n✅ Всі бібліотеки знайдено")
    print("🚀 Запускаю програму...\n")

    root = tk.Tk()
    app = EnhancedApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()