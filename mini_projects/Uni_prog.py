# -*- coding: utf-8 -*-
import json
import logging
import os
import platform
import queue
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

# Third-party imports
import numpy as np
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, colorchooser, filedialog, simpledialog
from PIL import ImageGrab, Image, ImageDraw, ImageTk, ImageFont

# STT/OCR/Translate imports
import pytesseract

# ==================== LOGGER CONFIGURATION ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== LAZY IMPORTS (unchanged) ====================


class PackageManager:
    """Автоматичне встановлення та управління залежностями"""

    def __init__(self):
        self.app_dir = Path(__file__).parent
        self.models_dir = Path.home() / ".stt_ocr_translate" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def check_python_version(self):
        """Перевірка версії Python"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            logger.error(f"❌ Потрібен Python 3.8 або новіший. Ваша версія: {sys.version}")
            input("Натисніть Enter для виходу...")
            sys.exit(1)
        logger.info(f"✅ Python версія: {version.major}.{version.minor}.{version.micro}")

    def install_package(self, package_name: str):
        """Встановити пакет"""
        try:
            logger.info(f"📦 Встановлюю {package_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package_name])
            logger.info(f"✅ {package_name} встановлено")
            return True
        except Exception as e:
            logger.error(f"❌ Помилка встановлення {package_name}: {e}")
            return False

    def check_and_install(self):
        """Перевірка та встановлення необхідних пакетів"""
        required_packages = {
            "faster_whisper": "faster-whisper",
            "pytesseract": "pytesseract",
            "PIL": "Pillow",
            "deep_translator": "deep-translator",
            "pyttsx3": "pyttsx3",
            "edge_tts": "edge-tts",
            "gTTS": "gTTS",
            "playsound": "playsound",
            "sounddevice": "sounddevice",
        }

        missing_packages = []
        for module_name, package_name in required_packages.items():
            try:
                importlib.import_module(module_name)
                logger.info(f"✅ {module_name} доступний")
            except ImportError:
                missing_packages.append((module_name, package_name))
                logger.warning(f"❌ {module_name} відсутній")

        if missing_packages:
            logger.info(f"\n📋 Знайдено {len(missing_packages)} відсутніх пакетів")
            if messagebox.askyesno("Встановити пакети",
                                   f"Знайдено {len(missing_packages)} відсутніх пакетів. Встановити?"):
                for module_name, package_name in missing_packages:
                    if not self.install_package(package_name):
                        messagebox.showerror("Помилка", f"Не вдалося встановити {package_name}")
                        sys.exit(1)
                messagebox.showinfo("Успіх", "Всі пакети встановлено! Перезапустіть програму")
                sys.exit(0)
            else:
                sys.exit(1)


# ==================== DRAWING CANVAS (OPTIMIZED) ====================


class DrawingCanvas(tk.Toplevel):
    """ОПТИМІЗОВАНА малювалка без лагів"""

    TOOLS = {
        "brush": "🖌️ Кисть",
        "pencil": "✏️ Олівець",
        "eraser": "🧽 Ластик",
        "line": "📏 Лінія",
        "rectangle": "⬜ Прямокутник",
        "circle": "⭕ Коло",
        "filled_rect": "🟦 Зал. прямокутник",
        "filled_circle": "🔵 Зал. коло",
        "fill": "🪣 Заливка",
        "text": "📝 Текст"
    }

    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance

        # Налаштування вікна
        self.title("🎨 Малювалка")
        self.attributes('-fullscreen', True)
        self.configure(bg='#1e1e1e')

        # Ініціалізація
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.canvas_size = (screen_width, screen_height)
        self.current_tool = "brush"
        self.primary_color = "#000000"
        self.secondary_color = "#ffffff"
        self.brush_size = 5
        self.drawing = False
        self.last_pos = None
        self.start_pos = None

        # Історія (зберігає копії зображень)
        self.history = []
        self.history_index = -1
        self.max_history = 30  # Обмеження для уникнення витоку пам'яті

        # Основне зображення
        self.image = Image.new('RGB', self.canvas_size, (255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)

        # Створення UI
        self.create_ui()
        self.create_menu()

        # Прив'язка подій
        self.bind_events()

        # Зберегти початковий стан
        self.save_state()
        self.update_canvas()

    def create_ui(self):
        """Створення основного UI"""
        # Головний контейнер
        self.main_container = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Панель інструментів зліва
        self.left_panel = tk.Frame(self.main_container, bg='#252526', width=250)
        self.main_container.add(self.left_panel, minsize=200)

        # Canvas
        self.canvas_frame = tk.Frame(self.main_container, bg='#1e1e1e')
        self.main_container.add(self.canvas_frame, stretch='always')

        self.canvas = tk.Canvas(self.canvas_frame, bg='white',
                                cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Додати елементи на панель
        self.create_toolbar()

    def create_menu(self):
        """Створення меню"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="🗂️ Очистити", command=self.clear_canvas, accelerator="Ctrl+N")
        file_menu.add_command(label="📸 Скріншот фону", command=self.set_screenshot_bg)
        file_menu.add_command(label="💾 Зберегти", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="❌ Закрити", command=self.close_drawer, accelerator="Esc")

        # Правка
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Правка", menu=edit_menu)
        edit_menu.add_command(label="↩️ Скасувати", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="↪️ Повторити", command=self.redo, accelerator="Ctrl+Y")

    def create_toolbar(self):
        """Створення панелі інструментів"""
        # Заголовок
        tk.Label(self.left_panel, text="🎨 Малювалка", bg='#252526', fg='white',
                 font=('Segoe UI', 14, 'bold')).pack(pady=10)

        # Інстументи
        tools_frame = tk.LabelFrame(self.left_panel, text=" Інструменти ",
                                    bg='#252526', fg='white', font=('Segoe UI', 10, 'bold'))
        tools_frame.pack(fill=tk.X, padx=5, pady=5)

        self.tool_buttons = {}
        for i, (tool_key, tool_name) in enumerate(self.TOOLS.items()):
            btn = tk.Button(tools_frame, text=tool_name, bg='#3c3c3c', fg='white',
                            font=('Segoe UI', 9), relief=tk.RAISED,
                            command=lambda t=tool_key: self.select_tool(t))
            btn.pack(fill=tk.X, pady=1, padx=2)
            self.tool_buttons[tool_key] = btn

        # Кольори
        colors_frame = tk.LabelFrame(self.left_panel, text=" Кольори ",
                                     bg='#252526', fg='white', font=('Segoe UI', 10, 'bold'))
        colors_frame.pack(fill=tk.X, padx=5, pady=5)

        # Основний колір
        color1_frame = tk.Frame(colors_frame, bg='#252526')
        color1_frame.pack(pady=2, padx=5)
        self.color1_preview = tk.Button(color1_frame, bg=self.primary_color, width=6, height=2,
                                        command=self.choose_primary_color)
        self.color1_preview.pack(side=tk.LEFT, padx=5)
        tk.Label(color1_frame, text="Основний", bg='#252526', fg='white').pack(side=tk.LEFT)

        # Палітра
        preset_frame = tk.Frame(colors_frame, bg='#252526')
        preset_frame.pack(pady=5)
        preset_colors = [
            "#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff", "#ffff00",
            "#ff00ff", "#00ffff", "#ff8800", "#88ff00", "#c0c0c0", "#808080"
        ]
        for i, color in enumerate(preset_colors):
            btn = tk.Button(preset_frame, bg=color, width=2, height=1,
                            command=lambda c=color: self.set_primary_color(c))
            btn.grid(row=i // 4, column=i % 4, padx=1, pady=1)

        # Розмір кисті
        size_frame = tk.LabelFrame(self.left_panel, text=" Розмір кисті ",
                                   bg='#252526', fg='white', font=('Segoe UI', 10, 'bold'))
        size_frame.pack(fill=tk.X, padx=5, pady=5)

        self.size_var = tk.IntVar(value=self.brush_size)
        self.size_label = tk.Label(size_frame, text=f"{self.brush_size}px",
                                   bg='#252526', fg='white')
        self.size_label.pack()

        tk.Scale(size_frame, from_=1, to=50, orient=tk.HORIZONTAL,
                 variable=self.size_var, bg='#3c3c3c', fg='white',
                 troughcolor='#2d2d2d', highlightthickness=0,
                 command=self.update_brush_size).pack(fill=tk.X, padx=5)

        # Бистрі дії
        actions_frame = tk.LabelFrame(self.left_panel, text=" Дії ",
                                      bg='#252526', fg='white', font=('Segoe UI', 10, 'bold'))
        actions_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(actions_frame, text="🗑️ Очистити", bg='#d9534f', fg='white',
                  command=self.clear_canvas).pack(fill=tk.X, pady=2, padx=2)
        tk.Button(actions_frame, text="📸 Скріншот фону", bg='#5cb85c', fg='white',
                  command=self.set_screenshot_bg).pack(fill=tk.X, pady=2, padx=2)

    def bind_events(self):
        """Прив'язка подій"""
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        # Гарячі клавіші
        self.bind_all("<Control-z>", lambda event: self.undo())
        self.bind_all("<Control-y>", lambda event: self.redo())
        self.bind_all("<Control-s>", lambda event: self.save_file())
        self.bind_all("<Escape>", lambda event: self.close_drawer())

    def select_tool(self, tool: str):
        """Вибрати інструмент"""
        self.current_tool = tool
        for t, btn in self.tool_buttons.items():
            if t == tool:
                btn.config(bg='#007acc', relief=tk.SUNKEN)
            else:
                btn.config(bg='#3c3c3c', relief=tk.RAISED)

    def set_primary_color(self, color: str):
        """Встановити основний колір"""
        self.primary_color = color
        self.color1_preview.config(bg=color)

    def choose_primary_color(self):
        """Вибрати основний колір"""
        color = colorchooser.askcolor(self.primary_color)[1]
        if color:
            self.set_primary_color(color)

    def update_brush_size(self, value):
        """Оновити розмір кисті"""
        self.brush_size = int(float(value))
        self.size_label.config(text=f"{self.brush_size}px")

    def on_mouse_down(self, event):
        """Натискання миші"""
        self.drawing = True
        self.last_pos = (event.x, event.y)
        self.start_pos = (event.x, event.y)

    def on_mouse_move(self, event):
        """ОПТИМІЗОВАНИЙ рух миші з обмеженням FPS"""
        if not self.drawing:
            return

        current_time = time.time()
        self.last_update_time = current_time
        current_pos = (event.x, event.y)

        # Малювання в реальному часі
        if self.current_tool in ["brush", "pencil", "eraser"]:
            self.draw_line(self.last_pos, current_pos)

            color = self.primary_color
            width = self.brush_size
            if self.current_tool == "pencil":
                width = max(1, width // 2)
            elif self.current_tool == "eraser":
                color = "#ffffff"
                width = width * 2

            self.canvas.create_line(self.last_pos[0], self.last_pos[1],
                                    current_pos[0], current_pos[1],
                                    fill=color, width=width, capstyle=tk.ROUND)

        elif self.current_tool in ["line", "rectangle", "circle", "filled_rect", "filled_circle"]:
            self.last_pos = current_pos
            self.update_canvas()

        self.last_pos = current_pos

    def on_mouse_up(self, event):
        """Відпускання миші"""
        if not self.drawing:
            return

        end_pos = (event.x, event.y)

        if self.current_tool in ["line", "rectangle", "circle", "filled_rect", "filled_circle", "fill", "text"]:
            self.apply_tool(end_pos)

        self.drawing = False
        self.save_state()
        self.update_canvas()

    def draw_line(self, start: Tuple[int, int], end: Tuple[int, int]):
        """Малювати лінію"""
        color = self.primary_color
        width = self.brush_size

        if self.current_tool == "pencil":
            width = max(1, width // 2)
        elif self.current_tool == "eraser":
            color = "#ffffff"
            width = width * 2

        self.draw.line([start, end], fill=color, width=width)

    def apply_tool(self, end_pos: Tuple[int, int]):
        """Застосувати інструмент"""
        x0, y0 = self.start_pos
        x1, y1 = end_pos
        color = self.primary_color

        if self.current_tool == "line":
            self.draw.line([self.start_pos, end_pos], fill=color, width=self.brush_size)
        elif self.current_tool == "rectangle":
            self.draw.rectangle([x0, y0, x1, y1], outline=color, width=self.brush_size)
        elif self.current_tool == "circle":
            self.draw.ellipse([x0, y0, x1, y1], outline=color, width=self.brush_size)
        elif self.current_tool == "filled_rect":
            self.draw.rectangle([x0, y0, x1, y1], fill=color, outline=color)
        elif self.current_tool == "filled_circle":
            self.draw.ellipse([x0, y0, x1, y1], fill=color, outline=color)
        elif self.current_tool == "fill":
            self.flood_fill(self.start_pos[0], self.start_pos[1], color)
        elif self.current_tool == "text":
            self.add_text(x0, y0)

    def flood_fill(self, x: int, y: int, fill_color: str):
        """ОПТИМІЗОВАНА заливка"""
        if x < 0 or y < 0 or x >= self.image.width or y >= self.image.height:
            return

        hex_color = fill_color.lstrip('#')
        rgb_fill = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        target_color = self.image.getpixel((x, y))

        if target_color == rgb_fill:
            return

        pixels = self.image.load()
        width, height = self.image.size
        visited = set()

        # ВИКОРИСТОВУЄМО deque для кращої продуктивності
        to_fill = deque([(x, y)])

        while to_fill:
            cx, cy = to_fill.popleft()

            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            try:
                current_color = pixels[cx, cy]
            except IndexError:
                continue

            if current_color == target_color:
                pixels[cx, cy] = rgb_fill

                # Додаємо сусідів
                if cx > 0: to_fill.append((cx - 1, cy))
                if cx < width - 1: to_fill.append((cx + 1, cy))
                if cy > 0: to_fill.append((cx, cy - 1))
                if cy < height - 1: to_fill.append((cx, cy + 1))

    def add_text(self, x: int, y: int):
        """Додати текст"""
        text = simpledialog.askstring("Текст", "Введіть текст:")
        if text:
            try:
                font_size = self.brush_size * 3
                try:
                    font = ImageFont.truetype("comic.ttf", font_size)
                except OSError:
                    font = ImageFont.load_default()

                self.draw.text((x, y), text, fill=self.primary_color, font=font)
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося додати текст: {e}")

    def draw_preview(self, current_pos: Tuple[int, int]):
        """Малювати попереджуючу форму"""
        if not self.start_pos:
            return

        x0, y0 = self.start_pos
        x1, y1 = current_pos

        if self.current_tool == "line":
            self.canvas.create_line(x0, y0, x1, y1, fill=self.primary_color, width=self.brush_size)
        elif self.current_tool == "rectangle":
            self.canvas.create_rectangle(x0, y0, x1, y1, outline=self.primary_color, width=self.brush_size)
        elif self.current_tool == "circle":
            self.canvas.create_oval(x0, y0, x1, y1, outline=self.primary_color, width=self.brush_size)
        elif self.current_tool == "filled_rect":
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=self.primary_color, outline=self.primary_color)
        elif self.current_tool == "filled_circle":
            self.canvas.create_oval(x0, y0, x1, y1, fill=self.primary_color, outline=self.primary_color)

    def update_canvas(self):
        """Оновити відображення canvas"""
        try:
            # Використовуємо .copy() для запобігання витоку пам'яті
            self.tk_image = ImageTk.PhotoImage(self.image.copy())
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
            # Зберегти посилання на image
            self.canvas.image = self.tk_image

            # Малювати попереджуючу форму
            if self.drawing and self.current_tool in ["line", "rectangle", "circle", "filled_rect", "filled_circle"]:
                self.draw_preview(self.last_pos)
        except Exception as e:
            logger.error(f"❌ Помилка оновлення canvas: {e}")

    def save_state(self):
        """Зберегти стан для undo/redo"""
        self.history = self.history[:self.history_index + 1]
        self.history.append(self.image.copy())

        if len(self.history) > self.max_history:
            self.history.pop(0)
        else:
            self.history_index += 1

    def undo(self):
        """Скасувати"""
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state()

    def redo(self):
        """Повторити"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_state()

    def restore_state(self):
        """Відновити стан з історії"""
        if self.history_index < 0 or self.history_index >= len(self.history):
            return

        self.image = self.history[self.history_index].copy()
        self.draw = ImageDraw.Draw(self.image)
        self.update_canvas()

    def clear_canvas(self):
        """Очистити canvas"""
        self.image = Image.new('RGB', self.canvas_size, (255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)
        self.save_state()
        self.update_canvas()

    def set_screenshot_bg(self):
        """Встановити скріншот як фон"""
        try:
            screenshot = ImageGrab.grab().convert('RGB')
            self.image = screenshot
            self.draw = ImageDraw.Draw(self.image)
            self.canvas_size = screenshot.size
            self.save_state()
            self.update_canvas()
        except Exception as e:
            logger.error(f"❌ Помилка захоплення скріншоту: {e}")
            messagebox.showerror("Помилка", f"Не вдалося захопити скріншот: {e}")

    def save_file(self):
        """Зберегти файл"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"), ("BMP", "*.bmp")])

        if filename:
            try:
                if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    rgb_image = self.image.convert('RGB')
                    rgb_image.save(filename, quality=95)
                else:
                    self.image.save(filename)
                messagebox.showinfo("Успіх", f"Збережено: {filename}")
                logger.info(f"💾 Файл збережено: {filename}")
            except Exception as e:
                logger.error(f"❌ Помилка збереження: {e}")
                messagebox.showerror("Помилка", f"Не вдалося зберегти: {e}")

    def close_drawer(self, event=None):
        """Закрити малювалку"""
        if messagebox.askyesno("Підтвердження", "Закрити малювалку?"):
            self.destroy()
            self.app_instance.root.deiconify()


# ==================== MANAGERS (EXPANDED) ====================


class CUDAManager:
    """Управління CUDA прискоренням"""

    @staticmethod
    def check_cuda_availability() -> Tuple[bool, str]:
        try:
            import torch
        except ImportError:
            return False, "PyTorch не встановлено"

        if not torch.cuda.is_available():
            if platform.system() == "Windows":
                try:
                    subprocess.run(['nvidia-smi'], capture_output=True, check=True, timeout=5)
                    return False, "CUDA драйвери встановлені, але PyTorch не налаштовано для CUDA. " \
                                  "Запустіть: pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121"
                except (subprocess.CalledProcessError, FileNotFoundError):
                    return False, "CUDA не знайдено. Встановіть NVIDIA драйвери: https://www.nvidia.com/drivers"
            else:
                return False, "CUDA недоступний. Встановіть PyTorch з підтримкою CUDA."

        try:
            gpu_name = torch.cuda.get_device_name(0)
            total_memory = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
            cuda_version = torch.version.cuda
            return True, f"✅ CUDA доступна: {gpu_name} ({total_memory:.1f} GB, CUDA {cuda_version})"
        except Exception as e:
            return False, f"Помилка CUDA: {e}"

    @staticmethod
    def get_cuda_info() -> Dict[str, Any]:
        import torch

        info = {
            "available": torch.cuda.is_available(),
            "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "devices": []
        }

        if info["available"]:
            for i in range(info["device_count"]):
                props = torch.cuda.get_device_properties(i)
                info["devices"].append({
                    "name": props.name,
                    "total_memory_gb": props.total_memory / 1024 ** 3,
                    "major": props.major,
                    "minor": props.minor,
                    "multi_processor_count": props.multi_processor_count
                })

        return info


class WhisperModelManager:
    """Керування моделями Whisper"""

    AVAILABLE_MODELS = [
        "tiny", "tiny.en", "base", "base.en",
        "small", "small.en", "medium", "medium.en",
        "large", "large-v2", "large-v3"
    ]

    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.current_model_size = "base"
        self.model = None
        self._lock = threading.Lock()

    def get_model_path(self, model_size: str) -> Optional[Path]:
        """Отримати шлях до моделі"""
        if model_size not in self.AVAILABLE_MODELS:
            return None

        cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        model_files = list(cache_dir.rglob(f"models--Systran--faster-whisper-{model_size}*/snapshots/*"))
        if model_files:
            return model_files[0]

        our_path = self.models_dir / f"faster-whisper-{model_size}"
        if our_path.exists():
            return our_path

        return None

    def is_model_downloaded(self, model_size: str) -> bool:
        """Перевірити чи модель завантажена"""
        return self.get_model_path(model_size) is not None

    def get_downloaded_models(self) -> List[str]:
        """Отримати список завантажених моделей"""
        downloaded = []
        for model_size in self.AVAILABLE_MODELS:
            if self.is_model_downloaded(model_size):
                downloaded.append(model_size)
        return downloaded

    def delete_model(self, model_size: str) -> bool:
        """Видалити модель"""
        try:
            model_path = self.get_model_path(model_size)
            if model_path and model_path.exists():
                import shutil
                shutil.rmtree(model_path.parent)
                logger.info(f"✅ Модель {model_size} видалено")
                return True
        except Exception as e:
            logger.error(f"❌ Помилка видалення моделі {model_size}: {e}")
        return False

    def download_model(self, model_size: str, progress_callback=None) -> bool:
        """Завантажити модель"""
        if model_size not in self.AVAILABLE_MODELS:
            return False

        if self.is_model_downloaded(model_size):
            return True

        try:
            from huggingface_hub import snapshot_download

            if progress_callback:
                progress_callback(0, f"⏳ Завантаження {model_size}...")

            repo_id = f"Systran/faster-whisper-{model_size}"
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

            snapshot_download(
                repo_id,
                cache_dir=cache_dir,
                local_files_only=False,
                revision="main"
            )

            if progress_callback:
                progress_callback(100, f"✅ {model_size} завантажено")

            return True

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"❌ Помилка: {e}")
            logger.error(f"❌ Помилка завантаження моделі {model_size}: {e}")
            return False

    def validate_model(self, model_size: str) -> bool:
        """Перевірити цілісність моделі"""
        model_path = self.get_model_path(model_size)
        if not model_path:
            return False

        # Перевіряємо наявність головного файлу моделі
        model_file = model_path / "model.bin"
        if not model_file.exists():
            logger.error(f"❌ Відсутній файл model.bin в {model_path}")
            return False

        # Перевіряємо розмір (мінімум 100MB для base моделі)
        size_mb = model_file.stat().st_size / (1024 * 1024)
        if size_mb < 65:
            logger.error(f"❌ Файл model.bin занадто малий: {size_mb:.1f} MB")
            return False

        logger.info(f"✅ Модель {model_size} валідна ({size_mb:.1f} MB)")
        return True

    def load_model(self, model_size: str, device: str = "auto", progress_callback=None):
        """Завантажити модель в пам'ять з валідацією"""
        with self._lock:
            # Вивантажити стару модель перед завантаженням нової
            if self.model is not None and self.current_model_size != model_size:
                self.unload_model()

            if self.model is not None and self.current_model_size == model_size:
                return self.model

            # ЛЕНИВИЙ ІМПОРТ
            import torch
            from faster_whisper import WhisperModel

            # Перевіряємо та завантажуємо модель
            model_path = self.get_model_path(model_size)
            if not model_path or not self.validate_model(model_size):
                logger.warning(f"⚠️ Модель {model_size} не знайдена або пошкоджена, завантажуємо...")
                success = self.download_model(model_size, progress_callback)
                if not success:
                    raise RuntimeError(f"Не вдалося завантажити модель {model_size}")
                model_path = self.get_model_path(model_size)

                # Повторна валідація
                if not self.validate_model(model_size):
                    raise RuntimeError(f"Завантажена модель {model_size} пошкоджена")

            if progress_callback:
                progress_callback(50, f"⏳ Завантаження в пам'ять ({device})...")

            # Імпортуємо модель
            self.model = WhisperModel(
                str(model_path),
                device=device,
                compute_type="float16" if device == "cuda" else "int8"
            )

            self.current_model_size = model_size

            if progress_callback:
                progress_callback(100, f"✅ Модель готова ({device.upper()})")

            logger.info(f"✅ Модель Whisper {model_size} завантажена на {device}")
            return self.model

    def unload_model(self):
        """Вивантажити модель з пам'яті"""
        with self._lock:
            if self.model is not None:
                logger.info("🗑️ Вивантаження моделі з пам'яті")
                self.model = None
                self.current_model_size = None
                import gc
                gc.collect()

                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except ImportError:
                    pass


class AppConfig:
    """РОЗШИРЕНО: Збереження налаштувань з новими секціями"""

    CONFIG_PATH = Path.home() / ".stt_ocr_translate" / "config.json"

    DEFAULT_CONFIG = {
        "app": {
            "use_cuda": False,
            "models_dir": "~/.stt_ocr_translate/models",
            "theme": "dark"
        },
        "ocr": {
            "dpi": 300,
            "psm": 6,
            "contrast": 1.5,
            "sharpen": True,
            "langs": "ukr+eng"
        },
        "stt": {
            "model_size": "base",
            "beam_size": 5,
            "vad_filter": True,
            "min_silence_duration_ms": 500,
            "language": "uk",
            "device": "auto"
        },
        "tts": {
            "engine": "auto",
            "speed": 1.0,
            "volume": 1.0,
            "voice": "uk-UA-PolinaNeural",
            "cache_dir": "~/.stt_ocr_translate/tts_cache"
        },
        "translation": {
            "service": "google",
            "auto_translate": False
        }
    }

    def __init__(self):
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Завантажити конфігурацію"""
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return self._merge_config(self.DEFAULT_CONFIG, config)
            except Exception as e:
                logger.error(f"❌ Помилка завантаження конфігу: {e}")
        return self.DEFAULT_CONFIG.copy()

    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """Рекурсивне злиття конфігів"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def save_config(self):
        """Зберегти конфігурацію"""
        # Розгорнути ~ в повний шлях для збереження
        config_to_save = json.loads(json.dumps(self.config))
        if "app" in config_to_save and "models_dir" in config_to_save["app"]:
            config_to_save["app"]["models_dir"] = str(Path(config_to_save["app"]["models_dir"]).expanduser())
        if "tts" in config_to_save and "cache_dir" in config_to_save["tts"]:
            config_to_save["tts"]["cache_dir"] = str(Path(config_to_save["tts"]["cache_dir"]).expanduser())

        try:
            with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
            logger.info("✅ Конфігурацію збережено")
        except Exception as e:
            logger.error(f"❌ Помилка збереження конфігу: {e}")

    def get(self, key: str, default=None):
        """Отримати значення за ключем (крапкова нотація)"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value):
        """Встановити значення за ключем (крапкова нотація)"""
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_config()

    def get_expanded_path(self, key: str, default: str = "") -> Path:
        """Отримати розгорнутий шлях"""
        path_str = self.get(key, default)
        return Path(path_str).expanduser() if path_str else Path.home()


class TTSService:
    """Багатопровайдерна озвучка"""

    def __init__(self, config: AppConfig):
        self.config = config

    def get_available_engines(self) -> Dict[str, bool]:
        """Перевірка доступних TTS двигунів"""
        engines = {}

        try:
            import pyttsx3
            engines['pyttsx3'] = True
        except ImportError:
            engines['pyttsx3'] = False

        try:
            import gtts
            engines['gTTS'] = True
        except ImportError:
            engines['gTTS'] = False

        try:
            import edge_tts
            engines['edge-tts'] = True
        except ImportError:
            engines['edge-tts'] = False

        return engines

    def get_available_voices(self, engine: str, lang: str = 'uk') -> List[str]:
        """Отримати список доступних голосів"""
        if engine == 'edge-tts':
            return {
                'uk': ["uk-UA-PolinaNeural", "uk-UA-OstapNeural"],
                'en': ["en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural"],
                'de': ["de-DE-KatjaNeural", "de-DE-ConradNeural"],
                'pl': ["pl-PL-ZofiaNeural", "pl-PL-MarekNeural"]
            }.get(lang, [])
        return []

    def speak(self, text: str, lang: str = 'uk', callback=None):
        """Озвучити текст"""
        try:
            engine_name = self.config.get('tts.engine', 'auto')

            if engine_name == 'auto':
                engines = self.get_available_engines()
                if engines.get('edge-tts'):
                    engine_name = 'edge-tts'
                elif engines.get('gTTS'):
                    engine_name = 'gTTS'
                else:
                    engine_name = 'pyttsx3'

            if engine_name == 'pyttsx3':
                self._speak_pyttsx3(text, callback)
            elif engine_name == 'gTTS':
                self._speak_gtts(text, lang, callback)
            elif engine_name == 'edge-tts':
                self._speak_edge(text, lang, callback)

        except Exception as e:
            logger.error(f"❌ Помилка озвучки: {e}")
            if callback:
                callback(f"❌ Помилка: {e}")

    def _speak_pyttsx3(self, text: str, callback):
        """Офлайн TTS"""
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', int(200 * self.config.get('tts.speed', 1.0)))
        engine.setProperty('volume', self.config.get('tts.volume', 1.0))
        engine.say(text)
        engine.runAndWait()
        if callback:
            callback("✅ Озвучено")

    def _speak_gtts(self, text: str, lang: str, callback):
        """Онлайн TTS"""
        from gtts import gTTS
        import playsound
        import tempfile

        lang_map = {'uk': 'uk', 'en': 'en', 'de': 'de', 'pl': 'pl'}

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            tts = gTTS(text=text, lang=lang_map.get(lang, 'en'))
            tts.save(fp.name)
            playsound.playsound(fp.name)
            os.unlink(fp.name)

        if callback:
            callback("✅ Озвучено")

    def _speak_edge(self, text: str, lang: str, callback):
        """Нейронна TTS з перевіркою event loop"""
        try:
            import asyncio
            import threading

            # Перевірка чи вже є running event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Запуск в окремому thread
                threading.Thread(
                    target=self._run_async_edge,
                    args=(text, lang, callback),
                    daemon=True
                ).start()
            else:
                asyncio.run(self._speak_edge_async(text, lang, callback))
        except Exception as e:
            logger.error(f"❌ Помилка edge-tts: {e}")
            if callback:
                callback(f"❌ Помилка: {e}")

    def _run_async_edge(self, text: str, lang: str, callback):
        """Запуск асинхронної функції в окремому потоці"""
        import asyncio
        asyncio.run(self._speak_edge_async(text, lang, callback))

    async def _speak_edge_async(self, text: str, lang: str, callback):
        """Асинхронна озвучка через edge-tts"""
        import edge_tts
        import tempfile

        voices = {
            'uk': self.config.get('tts.voice', "uk-UA-PolinaNeural"),
            'en': "en-US-AriaNeural",
            'de': "de-DE-KatjaNeural",
            'pl': "pl-PL-ZofiaNeural"
        }

        communicate = edge_tts.Communicate(text, voices.get(lang, "en-US-AriaNeural"))

        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
            await communicate.save(fp.name)
            os.unlink(fp.name)

        if callback:
            callback("✅ Озвучено")

    def _tts_pyttsx3_to_wav(self, text: str, output_path: str):
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', int(200 * self.config.get('tts.speed', 1.0)))
        engine.setProperty('volume', self.config.get('tts.volume', 1.0))
        engine.save_to_file(text, output_path)
        engine.runAndWait()

    def _tts_gtts_to_wav(self, text: str, lang: str, output_path: str):
        from gtts import gTTS
        import tempfile
        import soundfile as sf
        import numpy as np
        import librosa

        lang_map = {'uk': 'uk', 'en': 'en', 'de': 'de', 'pl': 'pl'}

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3:
            gTTS(text=text, lang=lang_map.get(lang, 'en')).save(mp3.name)
            audio, sr = librosa.load(mp3.name, sr=None)
            sf.write(output_path, audio, sr)

    def _tts_edge_to_wav(self, text: str, lang: str, output_path: str):
        import asyncio
        asyncio.run(self._tts_edge_to_wav_async(text, lang, output_path))

    async def _tts_edge_to_wav_async(self, text: str, lang: str, output_path: str):
        import edge_tts
        import tempfile
        import soundfile as sf
        import librosa

        voices = {
            'uk': self.config.get('tts.voice', "uk-UA-PolinaNeural"),
            'en': "en-US-AriaNeural",
            'de': "de-DE-KatjaNeural",
            'pl': "pl-PL-ZofiaNeural"
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as mp3:
            communicate = edge_tts.Communicate(text, voices.get(lang, "en-US-AriaNeural"))
            await communicate.save(mp3.name)

            audio, sr = librosa.load(mp3.name, sr=None)
            sf.write(output_path, audio, sr)

    def synthesize_to_wav(self, text: str, lang: str = "uk") -> str:
        engine_name = self.config.get('tts.engine', 'auto')

        if engine_name == 'auto':
            engines = self.get_available_engines()
            if engines.get('edge-tts'):
                engine_name = 'edge-tts'
            elif engines.get('gTTS'):
                engine_name = 'gTTS'
            else:
                engine_name = 'pyttsx3'

        output_path = "tts_output.wav"

        if engine_name == 'pyttsx3':
            self._tts_pyttsx3_to_wav(text, output_path)

        elif engine_name == 'gTTS':
            self._tts_gtts_to_wav(text, lang, output_path)

        elif engine_name == 'edge-tts':
            self._tts_edge_to_wav(text, lang, output_path)

        return output_path


class TranslationService:
    """Перекладач з використанням безкоштовних сервісів"""

    SUPPORTED_SERVICES = ["google", "libretranslate", "mymemory"]

    @staticmethod
    def translate(text: str, service: str, source: str, target: str) -> str:
        """Загальний метод перекладу"""
        try:
            if service.lower() == "google":
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source=source, target=target)
                return translator.translate(text)

            elif service.lower() == "libretranslate":
                from deep_translator import LibreTranslator
                translator = LibreTranslator(source=source, target=target)
                return translator.translate(text)

            elif service.lower() == "mymemory":
                from deep_translator import MyMemoryTranslator
                translator = MyMemoryTranslator(source=source, target=target)
                return translator.translate(text)

            else:
                available = ", ".join(TranslationService.SUPPORTED_SERVICES)
                return f"[Невідомий сервіс: {service}. Доступні: {available}]"

        except Exception as e:
            logger.error(f"❌ Помилка перекладу: {e}")
            return f"[Помилка перекладу: {str(e)}]"


class FullRecorder:
    """Клас для запису аудіо"""

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
            logger.warning(f"⚠️ Статус запису: {status}")
        if self._recording:
            self._frames.append(indata.copy())

    def start(self):
        """Початок запису"""
        try:
            import sounddevice as sd
        except ImportError:
            raise Exception("sounddevice не встановлено")

        self._frames = []
        self._recording = True

        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype=self.dtype,
            callback=self._callback,
            blocksize=1024
        )
        self._stream.start()
        logger.info(f"✅ Запис розпочато: {self.samplerate}Hz")

    def stop(self):
        """Зупинка запису"""
        self._recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"⚠️ Помилка закриття потоку: {e}")
            finally:
                self._stream = None

        # Видалено time.sleep(0.1) для уникнення блокування UI

        if not self._frames:
            logger.warning("⚠️ Не записано жодного фрейму")
            return np.zeros(0, dtype='float32')

        try:
            audio = np.concatenate(self._frames, axis=0)
            if audio.ndim > 1:
                audio = audio.flatten()
            logger.info(f"✅ Записано {len(audio)} сампли ({len(audio) / self.samplerate:.2f} секунд)")
            return audio.astype('float32')
        except Exception as e:
            logger.error(f"❌ Помилка обробки аудіо: {e}")
            return np.zeros(0, dtype='float32')


class ScreenSelector(tk.Toplevel):
    """Вибір області для OCR"""

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

        # Перевірка мінімального розміру області
        if x2 - x1 < 10 or y2 - y1 < 10:
            messagebox.showwarning("Попередження", "Область занадто мала!")
            self.destroy()
            return

        self.withdraw()
        self.after(100, lambda: self.capture_area(x1, y1, x2, y2))

    def capture_area(self, x1, y1, x2, y2):
        """Захоплення та розпізнавання області"""
        try:
            img = ImageGrab.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))
            text = pytesseract.image_to_string(img, lang='ukr+eng', config='--psm 6')
            if not text.strip():
                text = "[Текст не розпізнано]"
            logger.info(f"✅ OCR завершено: {len(text)} символів")
        except Exception as e:
            text = f"[OCR помилка: {e}]"
            logger.error(f"❌ Помилка OCR: {e}")

        # Викликати callback з затримкою для уникнення помилок
        self.after(100, lambda: self.callback(text))


# ==================== NEW SETTINGS TAB ====================


class SettingsTab(ttk.Frame):
    """Вкладка налаштувань"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.config = app.config

        # Створити UI
        self.create_widgets()

    def create_tooltip(self, widget, text):
        """Створити підказку (оптимізовано)"""
        tooltip = None

        def enter(event):
            nonlocal tooltip
            tooltip = tk.Toplevel(widget, bg='yellow', padx=1, pady=1)
            tooltip.withdraw()
            tooltip.overrideredirect(True)
            label = tk.Label(tooltip, text=text, bg='yellow', fg='black', justify='left')
            label.pack()
            tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            tooltip.deiconify()

        def leave(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None

        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)

    def create_widgets(self):
        """Створити всі віджети налаштувань"""
        # Canvas з скролом
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Пакування
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ===== СЕКЦІЯ: ЗАГАЛЬНІ НАЛАШТУВАННЯ =====
        app_frame = ttk.LabelFrame(scrollable_frame, text=" Загальні налаштування ", padding=10)
        app_frame.pack(fill=tk.X, padx=5, pady=5)

        # CUDA
        cuda_frame = ttk.Frame(app_frame)
        cuda_frame.pack(fill=tk.X, pady=2)
        ttk.Label(cuda_frame, text="Прискорення:").pack(side=tk.LEFT, padx=5)
        self.use_cuda_var = tk.BooleanVar(value=self.config.get('app.use_cuda', False))
        cuda_check = ttk.Checkbutton(cuda_frame, text="Використовувати CUDA (GPU)",
                                     variable=self.use_cuda_var,
                                     command=self.toggle_cuda)
        cuda_check.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(cuda_check,
                            "CUDA прискорює обробку в 3-10 разів, але використовує GPU.\n"
                            "Потребує NVIDIA GPU та встановлені драйвери.\n"
                            "Без CUDA всі обчислення виконуються на CPU (повільніше, але стабільніше)")

        # Шлях до моделей
        path_frame = ttk.Frame(app_frame)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="Директорія моделей:").pack(side=tk.LEFT, padx=5)
        self.models_path_var = tk.StringVar(
            value=str(self.config.get_expanded_path('app.models_dir')))
        self.models_path_entry = ttk.Entry(path_frame, textvariable=self.models_path_var, width=40)
        self.models_path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Змінити", command=self.change_models_dir).pack(side=tk.LEFT, padx=5)

        # ===== СЕКЦІЯ: OCR =====
        ocr_frame = ttk.LabelFrame(scrollable_frame, text=" OCR (Tesseract) ", padding=10)
        ocr_frame.pack(fill=tk.X, padx=5, pady=5)

        # DPI
        dpi_frame = ttk.Frame(ocr_frame)
        dpi_frame.pack(fill=tk.X, pady=2)
        ttk.Label(dpi_frame, text="DPI:").pack(side=tk.LEFT, padx=5)
        self.dpi_var = tk.IntVar(value=self.config.get('ocr.dpi', 300))
        ttk.Scale(dpi_frame, from_=72, to=600, variable=self.dpi_var,
                  orient=tk.HORIZONTAL, length=200,
                  command=lambda v: self.update_ocr_setting('dpi', int(float(v)))).pack(side=tk.LEFT, padx=5)
        self.dpi_label = ttk.Label(dpi_frame, text=str(self.dpi_var.get()))
        self.dpi_label.pack(side=tk.LEFT)
        self.create_tooltip(dpi_frame,
                            "DPI (точок на дюйм) - вище = краща якість, але повільніше.\n"
                            "300 - стандарт для друку, 150 - для екрану, 72 - мінімум.")

        # PSM
        psm_frame = ttk.Frame(ocr_frame)
        psm_frame.pack(fill=tk.X, pady=2)
        ttk.Label(psm_frame, text="PSM (Page Segmentation):").pack(side=tk.LEFT, padx=5)
        self.psm_var = tk.IntVar(value=self.config.get('ocr.psm', 6))
        psm_combo = ttk.Combobox(psm_frame, textvariable=self.psm_var,
                                 values=[0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                                 width=5, state="readonly")
        psm_combo.pack(side=tk.LEFT, padx=5)
        psm_combo.bind('<<ComboboxSelected>>',
                       lambda e: self.update_ocr_setting('psm', self.psm_var.get()))
        self.create_tooltip(psm_frame,
                            "PSM визначає, як Tesseract аналізує макет сторінки:\n"
                            "0 - тільки OSD, 3 - повністю автоматично, 6 - один однорідний блок,\n"
                            "11 - розрізаний текст. 6 - найкраще для більшості випадків.")

        # Контраст
        contrast_frame = ttk.Frame(ocr_frame)
        contrast_frame.pack(fill=tk.X, pady=2)
        ttk.Label(contrast_frame, text="Контраст:").pack(side=tk.LEFT, padx=5)
        self.contrast_var = tk.DoubleVar(value=self.config.get('ocr.contrast', 1.5))
        ttk.Scale(contrast_frame, from_=1.0, to=3.0, variable=self.contrast_var,
                  orient=tk.HORIZONTAL, length=200,
                  command=lambda v: self.update_ocr_setting('contrast', float(v))).pack(side=tk.LEFT, padx=5)
        self.contrast_label = ttk.Label(contrast_frame, text=f"{self.contrast_var.get():.1f}x")
        self.contrast_label.pack(side=tk.LEFT)

        # Мови
        langs_frame = ttk.Frame(ocr_frame)
        langs_frame.pack(fill=tk.X, pady=2)
        ttk.Label(langs_frame, text="Мови:").pack(side=tk.LEFT, padx=5)
        self.langs_var = tk.StringVar(value=self.config.get('ocr.langs', 'ukr+eng'))
        langs_entry = ttk.Entry(langs_frame, textvariable=self.langs_var, width=20)
        langs_entry.pack(side=tk.LEFT, padx=5)
        langs_entry.bind('<FocusOut>', lambda e: self.update_ocr_setting('langs', self.langs_var.get()))
        ttk.Label(langs_frame, text="(напр.: ukr+eng+rus)", font=('Arial', 8)).pack(side=tk.LEFT)

        # Sharpen
        sharpen_frame = ttk.Frame(ocr_frame)
        sharpen_frame.pack(fill=tk.X, pady=2)
        self.sharpen_var = tk.BooleanVar(value=self.config.get('ocr.sharpen', True))
        ttk.Checkbutton(sharpen_frame, text="Використовувати sharpen фільтр",
                        variable=self.sharpen_var,
                        command=lambda: self.update_ocr_setting('sharpen', self.sharpen_var.get())).pack(side=tk.LEFT,
                                                                                                         padx=5)

        # ===== СЕКЦІЯ: STT =====
        stt_frame = ttk.LabelFrame(scrollable_frame, text=" STT (Whisper) ", padding=10)
        stt_frame.pack(fill=tk.X, padx=5, pady=5)

        # Модель
        model_frame = ttk.Frame(stt_frame)
        model_frame.pack(fill=tk.X, pady=2)
        ttk.Label(model_frame, text="Модель:").pack(side=tk.LEFT, padx=5)
        self.model_var = tk.StringVar(value=self.config.get('stt.model_size', 'base'))
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_var,
                                   values=self.app.whisper_manager.AVAILABLE_MODELS,
                                   width=15, state="readonly")
        model_combo.pack(side=tk.LEFT, padx=5)
        model_combo.bind('<<ComboboxSelected>>', lambda e: self.update_stt_setting('model_size', self.model_var.get()))

        # Beam size
        beam_frame = ttk.Frame(stt_frame)
        beam_frame.pack(fill=tk.X, pady=2)
        ttk.Label(beam_frame, text="Beam size:").pack(side=tk.LEFT, padx=5)
        self.beam_var = tk.IntVar(value=self.config.get('stt.beam_size', 5))
        ttk.Scale(beam_frame, from_=1, to=10, variable=self.beam_var,
                  orient=tk.HORIZONTAL, length=200,
                  command=lambda v: self.update_stt_setting('beam_size', int(float(v)))).pack(side=tk.LEFT, padx=5)
        self.beam_label = ttk.Label(beam_frame, text=str(self.beam_var.get()))
        self.beam_label.pack(side=tk.LEFT)
        self.create_tooltip(beam_frame,
                            "Beam size - кількість варіантів, які модель розглядає.\n"
                            "1 = швидше, менше пам'яті, але менша точність.\n"
                            "5-10 = краща якість, але повільніше.")

        # VAD
        vad_frame = ttk.Frame(stt_frame)
        vad_frame.pack(fill=tk.X, pady=2)
        ttk.Label(vad_frame, text="VAD фільтр:").pack(side=tk.LEFT, padx=5)
        self.vad_var = tk.BooleanVar(value=self.config.get('stt.vad_filter', True))
        ttk.Checkbutton(vad_frame, text="Увімкнути Voice Activity Detection",
                        variable=self.vad_var,
                        command=lambda: self.update_stt_setting('vad_filter', self.vad_var.get())).pack(side=tk.LEFT,
                                                                                                        padx=5)

        # Min silence
        silence_frame = ttk.Frame(stt_frame)
        silence_frame.pack(fill=tk.X, pady=2)
        ttk.Label(silence_frame, text="Мін. тиша (мс):").pack(side=tk.LEFT, padx=5)
        self.silence_var = tk.IntVar(value=self.config.get('stt.min_silence_duration_ms', 500))
        ttk.Scale(silence_frame, from_=100, to=2000, variable=self.silence_var,
                  orient=tk.HORIZONTAL, length=200,
                  command=lambda v: self.update_stt_setting('min_silence_duration_ms', int(float(v)))).pack(
            side=tk.LEFT, padx=5)
        self.silence_label = ttk.Label(silence_frame, text=f"{self.silence_var.get()}мс")
        self.silence_label.pack(side=tk.LEFT)

        # STT мова
        stt_lang_frame = ttk.Frame(stt_frame)
        stt_lang_frame.pack(fill=tk.X, pady=2)
        ttk.Label(stt_lang_frame, text="Мова:").pack(side=tk.LEFT, padx=5)
        self.stt_lang_var = tk.StringVar(value=self.config.get('stt.language', 'uk'))
        ttk.Combobox(stt_lang_frame, textvariable=self.stt_lang_var,
                     values=['uk', 'en', 'ru', 'pl', 'de', 'auto'],
                     width=10, state="readonly").pack(side=tk.LEFT, padx=5)

        # ===== СЕКЦІЯ: TTS =====
        tts_frame = ttk.LabelFrame(scrollable_frame, text=" TTS (Озвучка) ", padding=10)
        tts_frame.pack(fill=tk.X, padx=5, pady=5)

        # Швидкість
        tts_speed_frame = ttk.Frame(tts_frame)
        tts_speed_frame.pack(fill=tk.X, pady=2)
        ttk.Label(tts_speed_frame, text="Швидкість:").pack(side=tk.LEFT, padx=5)
        self.speed_var = tk.DoubleVar(value=self.config.get('tts.speed', 1.0))
        ttk.Scale(tts_speed_frame, from_=0.5, to=2.0, variable=self.speed_var,
                  orient=tk.HORIZONTAL, length=200,
                  command=lambda v: self.update_tts_setting('speed', float(v))).pack(side=tk.LEFT, padx=5)
        self.speed_label = ttk.Label(tts_speed_frame, text=f"{self.speed_var.get():.1f}x")
        self.speed_label.pack(side=tk.LEFT)

        # Гучність
        tts_volume_frame = ttk.Frame(tts_frame)
        tts_volume_frame.pack(fill=tk.X, pady=2)
        ttk.Label(tts_volume_frame, text="Гучність:").pack(side=tk.LEFT, padx=5)
        self.volume_var = tk.DoubleVar(value=self.config.get('tts.volume', 1.0))
        ttk.Scale(tts_volume_frame, from_=0.0, to=1.0, variable=self.volume_var,
                  orient=tk.HORIZONTAL, length=200,
                  command=lambda v: self.update_tts_setting('volume', float(v))).pack(side=tk.LEFT, padx=5)
        self.volume_label = ttk.Label(tts_volume_frame, text=f"{self.volume_var.get():.1f}")
        self.volume_label.pack(side=tk.LEFT)

        # ===== СЕКЦІЯ: ПЕРЕКЛАДАЧ =====
        trans_frame = ttk.LabelFrame(scrollable_frame, text=" Переклад ", padding=10)
        trans_frame.pack(fill=tk.X, padx=5, pady=5)

        # Авто-переклад
        trans_auto_frame = ttk.Frame(trans_frame)
        trans_auto_frame.pack(fill=tk.X, pady=2)
        self.auto_translate_var = tk.BooleanVar(value=self.config.get('translation.auto_translate', False))
        ttk.Checkbutton(trans_auto_frame, text="Автоматичний переклад після OCR/STT",
                        variable=self.auto_translate_var,
                        command=lambda: self.update_translation_setting('auto_translate',
                                                                        self.auto_translate_var.get())).pack(
            side=tk.LEFT, padx=5)

        # ===== СЕКЦІЯ: УПРАВЛІННЯ МОДЕЛЯМИ =====
        models_mgmt_frame = ttk.LabelFrame(scrollable_frame, text=" Моделі та кеш ", padding=10)
        models_mgmt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Список моделей
        list_frame = ttk.Frame(models_mgmt_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(list_frame, text="Завантажені моделі Whisper:").pack(anchor=tk.W)

        self.models_listbox = tk.Listbox(list_frame, height=6)
        self.models_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.refresh_models_list()

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Button(btn_frame, text="Оновити", command=self.refresh_models_list, width=12).pack(pady=2)
        ttk.Button(btn_frame, text="Видалити", command=self.delete_selected_model, width=12).pack(pady=2)
        ttk.Button(btn_frame, text="Очистити кеш", command=self.app.clear_all_cache, width=12).pack(pady=2)

        # НОВА КНОПКА: Перевірити моделі
        ttk.Button(btn_frame, text="Перевірити моделі",
                   command=self.validate_models, width=12).pack(pady=2)

        # Розмір кешу
        self.cache_size_label = ttk.Label(models_mgmt_frame, text="")
        self.cache_size_label.pack(anchor=tk.W, pady=5)
        self.update_cache_size()

    def validate_models(self):
        """Перевірити всі завантажені моделі"""
        corrupted_models = []

        for model_name in self.app.whisper_manager.get_downloaded_models():
            if not self.app.whisper_manager.validate_model(model_name):
                corrupted_models.append(model_name)

        if corrupted_models:
            if messagebox.askyesno("Пошкоджені моделі",
                                   f"Знайдено пошкоджені моделі: {', '.join(corrupted_models)}\n"
                                   f"Видалити та завантажити заново?"):
                for model_name in corrupted_models:
                    self.app.whisper_manager.delete_model(model_name)
                messagebox.showinfo("✅", "Пошкоджені моделі видалено. Завантажте їх заново.")
        else:
            messagebox.showinfo("✅", "Всі моделі в порядку!")

    def toggle_cuda(self):
        """Перемкнути CUDA"""
        use_cuda = self.use_cuda_var.get()
        self.config.set('app.use_cuda', use_cuda)
        messagebox.showinfo("CUDA", f"CUDA {'увімкнено' if use_cuda else 'вимкнено'}\n"
                                    f"Зміни набудуть чинності після перезапуску моделі.")

    def change_models_dir(self):
        """Змінити директорію моделей"""
        new_dir = filedialog.askdirectory(initialdir=self.models_path_var.get())
        if new_dir:
            self.models_path_var.set(new_dir)
            self.config.set('app.models_dir', new_dir)
            messagebox.showinfo("Шлях", "Шлях змінено. Перезапустіть програму для застосування.")

    def update_ocr_setting(self, key, value):
        """Оновити налаштування OCR"""
        self.config.set(f'ocr.{key}', value)
        if key == 'dpi':
            self.dpi_label.config(text=str(value))
        elif key == 'contrast':
            self.contrast_label.config(text=f"{value:.1f}x")

    def update_stt_setting(self, key, value):
        """Оновити налаштування STT"""
        self.config.set(f'stt.{key}', value)
        if key == 'beam_size':
            self.beam_label.config(text=str(value))
        elif key == 'min_silence_duration_ms':
            self.silence_label.config(text=f"{value}мс")

    def update_tts_setting(self, key, value):
        """Оновити налаштування TTS"""
        self.config.set(f'tts.{key}', value)
        if key == 'speed':
            self.speed_label.config(text=f"{value:.1f}x")
        elif key == 'volume':
            self.volume_label.config(text=f"{value:.1f}")

    def update_translation_setting(self, key, value):
        """Оновити налаштування перекладу"""
        self.config.set(f'translation.{key}', value)

    def refresh_models_list(self):
        """Оновити список моделей"""
        self.models_listbox.delete(0, tk.END)
        models = self.app.whisper_manager.get_downloaded_models()
        if models:
            for model in models:
                self.models_listbox.insert(tk.END, model)
        else:
            self.models_listbox.insert(tk.END, "(немає завантажених моделей)")

    def delete_selected_model(self):
        """Видалити вибрану модель"""
        selection = self.models_listbox.curselection()
        if not selection:
            messagebox.showwarning("Попередження", "Виберіть модель для видалення")
            return

        model_size = self.models_listbox.get(selection[0])
        if not model_size or model_size.startswith("("):
            return

        if messagebox.askyesno("Підтвердження", f"Видалити модель '{model_size}'?"):
            if self.app.whisper_manager.delete_model(model_size):
                messagebox.showinfo("✅", f"Модель '{model_size}' видалено")
                self.refresh_models_list()
            else:
                messagebox.showerror("❌", "Не вдалося видалити модель")

    def update_cache_size(self):
        """Оновити розмір кешу"""
        try:
            cache_dir = Path.home() / ".cache" / "huggingface"
            if cache_dir.exists():
                size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)
                self.cache_size_label.config(text=f"Розмір кешу: {size_mb:.1f} MB")
            else:
                self.cache_size_label.config(text="Кеш порожній")
        except Exception as e:
            logger.error(f"❌ Помилка розрахунку кешу: {e}")
            self.cache_size_label.config(text="Неможливо розрахувати розмір")


# ==================== MAIN APPLICATION (MODIFIED) ====================


class EnhancedApp:
    """Головний клас застосунку"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎤 STT + OCR + Translate Pro Ultra")
        self.root.geometry("1000x750")

        # Ініціалізація менеджерів
        self.package_manager = PackageManager()
        self.config = AppConfig()
        self.whisper_manager = WhisperModelManager(self.config.get_expanded_path('app.models_dir'))
        self.tts_service = TTSService(self.config)

        # CUDA
        self.cuda_available, self.cuda_msg = CUDAManager.check_cuda_availability()
        if self.cuda_available:
            logger.info(f"🚀 {self.cuda_msg}")

        # Стан
        self.is_recording = False
        self.recorder = None
        self.model_loading = False

        # UI черга
        self.ui_queue = queue.Queue()
        self.root.after(100, self.process_ui_queue)

        self.build_ui()
        self.check_dependencies_async()

    def process_ui_queue(self):
        """Обробка UI оновлень"""
        try:
            while True:
                func = self.ui_queue.get_nowait()
                func()
        except queue.Empty:
            pass
        self.root.after(100, self.process_ui_queue)

    def add_ui_task(self, func):
        """Додати задачу в чергу"""
        self.ui_queue.put(func)

    def build_ui(self):
        """Побудова інтерфейсу (З ЧОТИРМА ВКЛАДКАМИ)"""
        # Меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Файл меню
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="⬇️ Завантажити моделі", command=self.load_model_async)
        file_menu.add_command(label="🗑️ Очистити кеш", command=self.clear_all_cache)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 Вийти", command=self.on_close)

        # Панель інструментів
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="📸 OCR", command=self.quick_ocr, width=12).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🎤 Запис", command=self.quick_speech, width=12).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🎨 Малювати", command=self.open_drawer, width=12).pack(side='left', padx=2)
        ttk.Button(toolbar, text="🔊 Озвучити", command=self.speak_text, width=12).pack(side='left', padx=2)

        # Статус-бар
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_var = tk.StringVar(value="Готовий")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var)
        self.status_label.pack(side='left', padx=5)

        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.pack(side='right', padx=5, pady=2)

        # Вкладки (ТЕПЕР 4 ВКЛАДКИ)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        self.build_ocr_tab(notebook)
        self.build_stt_tab(notebook)
        self.build_translation_tab(notebook)
        self.build_settings_tab(notebook)  # НОВА ВКЛАДКА

    def build_ocr_tab(self, notebook):
        """Вкладка OCR"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🖼️ OCR")

        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(controls, text="📸 Розпізнати", command=self.run_ocr).pack(side='left', padx=2)
        ttk.Button(controls, text="🗑️ Очистити", command=lambda: self.ocr_text.delete(1.0, tk.END)).pack(side='left',
                                                                                                         padx=2)
        ttk.Button(controls, text="📋 Копіювати", command=lambda: self.copy_text(self.ocr_text)).pack(side='left',
                                                                                                     padx=2)
        ttk.Button(controls, text="🌍 Перекласти", command=self.translate_from_ocr).pack(side='left', padx=2)
        ttk.Button(controls, text="🔊 Озвучити", command=lambda: self.speak_text(self.ocr_text)).pack(side='left',
                                                                                                     padx=2)

        self.ocr_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=('Arial', 11))
        self.ocr_text.pack(fill='both', expand=True, padx=5, pady=5)

    def build_stt_tab(self, notebook):
        """Вкладка STT"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🎤 Аудіо")

        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, padx=5, pady=5)

        self.speech_button = ttk.Button(controls, text="🎧 Почати запис", command=self.handle_speech)
        self.speech_button.pack(side='left', padx=2)
        ttk.Button(controls, text="🗑️ Очистити", command=lambda: self.speech_text.delete(1.0, tk.END)).pack(side='left',
                                                                                                            padx=2)
        ttk.Button(controls, text="📋 Копіювати", command=lambda: self.copy_text(self.speech_text)).pack(side='left',
                                                                                                        padx=2)
        ttk.Button(controls, text="🌍 Перекласти", command=self.translate_from_speech).pack(side='left', padx=2)
        ttk.Button(controls, text="🔊 Озвучити", command=lambda: self.speak_text(self.speech_text)).pack(side='left',
                                                                                                        padx=2)

        self.mic_indicator = ttk.Label(controls, text="⚪", font=('Arial', 16))
        self.mic_indicator.pack(side='right', padx=5)

        # Налаштування моделі
        model_frame = ttk.LabelFrame(frame, text="Налаштування моделі")
        model_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(model_frame, text="Модель:").pack(side='left', padx=5)
        self.model_combo = ttk.Combobox(
            model_frame,
            values=self.whisper_manager.AVAILABLE_MODELS,
            state="readonly", width=15
        )
        self.model_combo.set(self.config.get('stt.model_size', 'base'))
        self.model_combo.pack(side='left', padx=5)
        self.model_combo.bind('<<ComboboxSelected>>', lambda e: self.change_model())

        self.model_status = ttk.Label(model_frame, text="⚪ Модель не завантажена")
        self.model_status.pack(side='left', padx=5)

        self.load_model_button = ttk.Button(model_frame, text="⬇️ Завантажити", command=self.load_model_async)
        self.load_model_button.pack(side='right', padx=5)

        self.speech_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=('Arial', 11))
        self.speech_text.pack(fill='both', expand=True, padx=5, pady=5)

    def build_translation_tab(self, notebook):
        """Вкладка перекладу"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🌍 Переклад")

        # Вхідний текст
        input_frame = ttk.LabelFrame(frame, text="Текст для перекладу")
        input_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=8, font=('Arial', 11))
        self.input_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Керування
        controls = ttk.Frame(frame)
        controls.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(controls, text="Напрямок:").pack(side='left', padx=5)
        self.lang_combo = ttk.Combobox(
            controls,
            values=[
                "Українська → Англійська",
                "Англійська → Українська",
                "Українська → Німецька",
                "Німецька → Українська",
                "Українська → Польська",
                "Польська → Українська"
            ],
            state="readonly", width=25
        )
        self.lang_combo.current(0)
        self.lang_combo.pack(side='left', padx=5)

        ttk.Button(controls, text="🌍 Перекласти", command=self.run_translate).pack(side='left', padx=5)
        ttk.Button(controls, text="🔊 Озвучити", command=lambda: self.speak_text(self.output_text)).pack(side='left',
                                                                                                        padx=5)

        # Вихідний текст
        output_frame = ttk.LabelFrame(frame, text="Переклад")
        output_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=8, font=('Arial', 11))
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)

    def build_settings_tab(self, notebook):
        """НОВА ВКЛАДКА: Налаштування"""
        self.settings_tab = SettingsTab(notebook, self)
        notebook.add(self.settings_tab, text="⚙️ Налаштування")

    def check_dependencies_async(self):
        """Асинхронна перевірка залежностей"""

        def check():
            self.add_ui_task(lambda: self.update_status("Перевірка залежностей..."))

            tesseract_ok = self.check_tesseract()
            whisper_ok = self.check_whisper()
            tts_ok = self.check_tts()

            def update_ui():
                if tesseract_ok:
                    self.update_status("✅ Tesseract готовий")
                else:
                    self.update_status("⚠️ Tesseract не встановлено")

                if whisper_ok:
                    self.update_model_status_ui()
                else:
                    self.update_status("⚠️ Whisper недоступний")

                if not tts_ok:
                    self.update_status("⚠️ TTS недоступний")

            self.add_ui_task(update_ui)

        threading.Thread(target=check, daemon=True).start()

    def check_tesseract(self) -> bool:
        """Перевірити Tesseract"""
        try:
            import pytesseract
            return True
        except ImportError:
            return False

    def check_whisper(self) -> bool:
        """Перевірити Whisper"""
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False

    def check_tts(self) -> bool:
        """Перевірити TTS"""
        return any(self.tts_service.get_available_engines().values())

    def update_status(self, message: str):
        """Оновити статус"""
        self.status_var.set(message)

    def update_model_status_ui(self):
        """Оновити статус моделі"""
        model_size = self.config.get('stt.model_size', 'base')
        if self.whisper_manager.is_model_downloaded(model_size):
            self.model_status.config(text=f"✅ Модель {model_size} готова")
            self.load_model_button.config(state='disabled')
        else:
            self.model_status.config(text=f"❌ Модель {model_size} не завантажена")
            self.load_model_button.config(state='normal')

    def load_model_async(self):
        """Асинхронне завантаження моделі"""
        if self.model_loading:
            return

        model_size = self.config.get('stt.model_size', 'base')

        def load():
            self.model_loading = True
            self.add_ui_task(lambda: self.progress_bar.start())

            try:
                # ВИКОРИСТОВУЄМО ПАРАМЕТР CUDA З НАЛАШТУВАНЬ
                use_cuda = self.config.get('app.use_cuda', False)
                device = 'cuda' if use_cuda and self.cuda_available else 'cpu'

                if use_cuda and not self.cuda_available:
                    logger.warning("⚠️ CUDA вимкнено в налаштуваннях, але GPU недоступний")

                self.whisper_manager.load_model(model_size, device, self.download_progress)
                self.add_ui_task(self.update_model_status_ui)
            except Exception as e:
                # ЗБЕРІГАЄМО ПОМИЛКУ В ЛОКАЛЬНІЙ ЗМІННІЙ
                error_msg = str(e)
                logger.error(f"❌ Помилка завантаження моделі: {error_msg}")
                self.add_ui_task(lambda: messagebox.showerror("Помилка", f"Не вдалося завантажити модель: {error_msg}"))
            finally:
                self.model_loading = False
                self.add_ui_task(lambda: self.progress_bar.stop())

        threading.Thread(target=load, daemon=True).start()


    def download_progress(self, percent: int, message: str):
        """Прогрес завантаження"""
        self.add_ui_task(lambda: self.update_status(message))

    def change_model(self):
        """Зміна моделі"""
        new_model = self.model_combo.get()
        self.config.set('stt.model_size', new_model)
        self.load_model_async()

    def quick_ocr(self):
        """Швидкий OCR"""
        self.run_ocr()

    def quick_speech(self):
        """Швидкий запис"""
        self.handle_speech()

    def open_drawer(self):
        """Відкрити малювалку"""
        try:
            self.root.withdraw()
            DrawingCanvas(self)
        except Exception as e:
            logger.error(f"❌ Помилка відкриття малювалки: {e}")
            messagebox.showerror("Помилка", f"Не вдалося відкрити малювалку: {e}")
            self.root.deiconify()

    def run_ocr(self):
        """Запустити OCR"""
        self.update_status("Виберіть область...")
        self.root.withdraw()

        def capture():
            selector = ScreenSelector(self.set_ocr_text)

        threading.Thread(target=capture, daemon=True).start()

    def set_ocr_text(self, text: str):
        """Встановити OCR текст"""
        self.add_ui_task(lambda: self._set_ocr_text_ui(text))

    def _set_ocr_text_ui(self, text: str):
        """UI частина встановлення OCR тексту"""
        self.root.deiconify()
        self.ocr_text.delete(1.0, tk.END)
        self.ocr_text.insert(tk.END, text.strip())

        if self.config.get('translation.auto_translate') and text.strip():
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, text.strip())
            self.run_translate()

    def copy_text(self, widget):
        """Копіювати текст"""
        text = widget.get(1.0, tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.update_status("Текст скопійовано")
            logger.info("📋 Текст скопійовано в буфер")

    def translate_from_ocr(self):
        """Переклад з OCR"""
        text = self.ocr_text.get(1.0, tk.END).strip()
        if text:
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, text)
            self.run_translate()

    def translate_from_speech(self):
        """Переклад з мовлення"""
        text = self.speech_text.get(1.0, tk.END).strip()
        if text:
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, text)
            self.run_translate()

    def run_translate(self):
        """Виконати переклад"""
        text = self.input_text.get(1.0, tk.END).strip()
        if not text:
            messagebox.showinfo("Помилка", "Немає тексту для перекладу")
            return

        self.update_status("Перекладаю...")

        def translate():
            try:
                service = self.config.get('translation.service', 'google')
                idx = self.lang_combo.current()
                from_lang, to_lang = self.get_translation_languages(idx)

                translated = TranslationService.translate(text, service, from_lang, to_lang)

                def update_ui():
                    self.output_text.delete(1.0, tk.END)
                    self.output_text.insert(tk.END, translated)
                    self.update_status(f"✅ Перекладено ({from_lang} → {to_lang})")
                    logger.info(f"🌍 Перекладено: {len(translated)} символів")

                self.add_ui_task(update_ui)

            except Exception as e:
                logger.error(f"❌ Помилка перекладу: {e}")

                def show_error():
                    self.update_status("❌ Помилка перекладу")
                    messagebox.showerror("Помилка", f"Помилка: {e}")

                self.add_ui_task(show_error)

        threading.Thread(target=translate, daemon=True).start()

    def get_translation_languages(self, selection: int) -> tuple:
        """Отримати мови перекладу"""
        lang_map = {
            0: ("uk", "en"),
            1: ("en", "uk"),
            2: ("uk", "de"),
            3: ("de", "uk"),
            4: ("uk", "pl"),
            5: ("pl", "uk")
        }
        return lang_map.get(selection, ("uk", "en"))

    def speak_text(self, text_widget=None):
        """Озвучити текст"""
        if text_widget is None:
            text_widget = self.output_text

        text = text_widget.get(1.0, tk.END).strip()
        if not text:
            messagebox.showinfo("Помилка", "Немає тексту для озвучки")
            return

        self.update_status("Озвучую...")

        def speak():
            try:
                idx = self.lang_combo.current()
                from_lang, to_lang = self.get_translation_languages(idx)
                target_lang = to_lang if text_widget == self.output_text else from_lang

                self.tts_service.speak(text, target_lang, self.update_status)
            except Exception as e:
                logger.error(f"❌ Помилка озвучки: {e}")

                def show_error():
                    self.update_status(f"❌ Помилка: {str(e)[:50]}")
                    messagebox.showerror("Помилка", f"Помилка озвучки: {e}")

                self.add_ui_task(show_error)

        threading.Thread(target=speak, daemon=True).start()

    def handle_speech(self):
        """Обробка запису мовлення"""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """Почати запис"""
        try:
            model_size = self.config.get('stt.model_size', 'base')
            if not self.whisper_manager.is_model_downloaded(model_size):
                messagebox.showwarning("Попередження", "Модель не завантажена. Завантаження моделі...")
                self.load_model_async()
                return

            self.is_recording = True
            self.speech_button.config(text="⏹️ Зупинити")
            self.mic_indicator.config(text="🔴", foreground="red")
            self.update_status("Запис... (говоріть зараз)")

            self.recorder = FullRecorder()
            self.recorder.start()

        except Exception as e:
            logger.error(f"❌ Помилка початку запису: {e}")
            messagebox.showerror("Помилка", f"Не вдалося почати запис: {e}")
            self.is_recording = False

    def stop_recording(self):
        """Зупинити запис і транскрибувати"""
        self.is_recording = False
        self.speech_button.config(text="🎧 Почати запис", state='disabled')
        self.mic_indicator.config(text="🟡", foreground="orange")
        self.update_status("Обробка...")

        def process():
            audio = None  # Ініціалізація змінної
            try:
                audio = self.recorder.stop()

                if len(audio) < 1600:
                    raise Exception("Занадто короткий запис")

                # Завантажуємо модель
                model_size = self.config.get('stt.model_size', 'base')
                model = self.whisper_manager.load_model(model_size)

                # Параметри з налаштувань
                segments, info = model.transcribe(
                    audio,
                    beam_size=self.config.get('stt.beam_size', 5),
                    language=self.config.get('stt.language', 'uk'),
                    vad_filter=self.config.get('stt.vad_filter', True),
                    vad_parameters=dict(
                        min_silence_duration_ms=self.config.get('stt.min_silence_duration_ms', 500)
                    )
                )

                # Збираємо текст
                parts = []
                for seg in segments:
                    if seg.text.strip():
                        parts.append(seg.text.strip())

                full_text = " ".join(parts).strip()

                if not full_text:
                    full_text = "[Мову не розпізнано]"

                def update_ui():
                    self.speech_text.insert(tk.END, full_text + "\n\n")
                    self.speech_text.see(tk.END)
                    self.mic_indicator.config(text="✅", foreground="green")
                    self.speech_button.config(state='normal')
                    self.update_status("Готово")

                    # Автоматичний переклад
                    if self.config.get('translation.auto_translate') and full_text:
                        self.input_text.delete(1.0, tk.END)
                        self.input_text.insert(tk.END, full_text)
                        self.run_translate()

                self.add_ui_task(update_ui)

            except Exception as e:
                # ЗБЕРІГАЄМО ПОМИЛКУ В ЛОКАЛЬНІЙ ЗМІННІЙ
                error_msg = str(e)
                logger.error(f"❌ Помилка обробки запису: {error_msg}")

                def show_error():
                    self.mic_indicator.config(text="❌", foreground="red")
                    self.speech_button.config(state='normal')
                    self.update_status(f"Помилка: {error_msg[:50]}")
                    messagebox.showerror("Помилка", error_msg)

                self.add_ui_task(show_error)

        threading.Thread(target=process, daemon=True).start()

    def clear_all_cache(self):
        """Очистити всі кеші"""
        if not messagebox.askyesno("Підтвердження", "Очистити кеш моделей та TTS?"):
            return

        try:
            import shutil

            cache_dir = Path.home() / ".cache" / "huggingface"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logger.info("🗑️ Кеш huggingface очищено")

            # TTS кеш
            tts_cache = self.config.get_expanded_path('tts.cache_dir')
            if tts_cache.exists():
                shutil.rmtree(tts_cache)
                logger.info("🗑️ Кеш TTS очищено")

            messagebox.showinfo("✅", "Кеш очищено")

            # Оновити вкладку налаштувань
            if hasattr(self, 'settings_tab'):
                self.settings_tab.update_cache_size()

        except Exception as e:
            logger.error(f"❌ Помилка очищення кешу: {e}")
            messagebox.showerror("Помилка", f"Не вдалося очистити кеш: {e}")

    def on_close(self):
        """Закриття програми"""
        if self.is_recording and self.recorder:
            try:
                self.recorder.stop()
            except Exception as e:
                logger.error(f"❌ Помилка зупинки запису: {e}")
        logger.info("👋 Застосунок закрито")
        self.root.destroy()


# ==================== LAUNCH (UNCHANGED) ====================


def main():
    """Головна функція"""
    cuda_available, msg = CUDAManager.check_cuda_availability()
    print(f"\n{'=' * 60}")
    print("🚀 STT + OCR + Translate Pro Ultra")
    print(f"{'=' * 60}")
    print(f"CUDA: {msg}\n")

    root = tk.Tk()
    app = EnhancedApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
