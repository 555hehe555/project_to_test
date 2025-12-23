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
import threading
import queue
import concurrent.futures
import time
import json
from typing import Optional, Dict, Any, Tuple, List
import io
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, colorchooser, filedialog, simpledialog
from PIL import ImageGrab, ImageEnhance, ImageFilter, Image, ImageDraw, ImageTk, ImageFont, ImageOps
import pytesseract
from pynput import keyboard
import numpy as np
import sounddevice as sd
import torch
import math
from datetime import datetime
from collections import deque
import time


# ==================== ПРОСТА МАЛЮВАЛЬНЯ БЕЗ АЛЬФА-КАНАЛУ ====================

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

        # ОПТИМІЗАЦІЯ: Обмеження FPS для зменшення лагів
        self.last_update_time = time.time()
        self.min_frame_time = 0  # Максимум 60 FPS

        # Історія (проста)
        self.history = []
        self.history_index = -1
        self.max_history = 30

        # Основне зображення (RGB, без альфа-каналу)
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

        # Інструменти
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
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())
        self.bind_all("<Control-s>", lambda e: self.save_file())
        self.bind_all("<Escape>", lambda e: self.close_drawer())

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

        # ОБМЕЖЕННЯ FPS: пропускаємо події, якщо йдуть занадто швидко
        current_time = time.time()
        if current_time - self.last_update_time < self.min_frame_time:
            # Оновлюємо позицію, але не малюємо
            self.last_pos = (event.x, event.y)
            return

        self.last_update_time = current_time

        current_pos = (event.x, event.y)

        # Малювання в реальному часі
        if self.current_tool in ["brush", "pencil", "eraser"]:
            # 1. Малюємо на Image
            self.draw_line(self.last_pos, current_pos)

            # 2. ШВИДКЕ оновлення: тільки додаємо лінію на canvas, без повного redraw
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
            # Для форм - повне оновлення (рідко викликається)
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

        # ОПТИМІЗАЦІЯ: зберігаємо стан тільки після завершення дії
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
        """ОПТИМІЗОВАНА заливка з deque"""
        if x < 0 or y < 0 or x >= self.image.width or y >= self.image.height:
            return

        # Конвертувати hex в RGB
        hex_color = fill_color.lstrip('#')
        rgb_fill = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        target_color = self.image.getpixel((x, y))

        # Якщо колір вже такий - виходимо
        if target_color == rgb_fill:
            return

        pixels = self.image.load()
        width, height = self.image.size
        visited = set()
        to_fill = deque([(x, y)])  # ВИКОРИСТОВУЄМО DEQUE замість списку

        while to_fill:
            cx, cy = to_fill.popleft()  # O(1) операція

            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            try:
                current_color = pixels[cx, cy]
            except:
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
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
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
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # Малювати попереджуючу форму
        if self.drawing and self.current_tool in ["line", "rectangle", "circle", "filled_rect", "filled_circle"]:
            self.draw_preview(self.last_pos)

    def save_state(self):
        """Зберегти стан для undo/redo"""
        # Видаляємо майбутню історію
        self.history = self.history[:self.history_index + 1]

        # Зберігаємо копію зображення
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
        screenshot = ImageGrab.grab().convert('RGB')
        self.image = screenshot
        self.draw = ImageDraw.Draw(self.image)
        self.canvas_size = screenshot.size
        self.save_state()
        self.update_canvas()

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
            except Exception as e:
                messagebox.showerror("Помилка", f"Не вдалося зберегти: {e}")

    def close_drawer(self, event=None):
        """Закрити малювалку"""
        if messagebox.askyesno("Підтвердження", "Закрити малювалку?"):
            self.destroy()
            self.app_instance.root.deiconify()

# ==================== ОСНОВНІ КЛАСИ ====================

class CUDAManager:
    """Управління CUDA прискоренням"""

    @staticmethod
    def check_cuda_availability() -> Tuple[bool, str]:
        """Повна перевірка CUDA з інформативним повідомленням"""
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
        """Отримати детальну інформацію про CUDA"""
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


class PackageManager:
    """Автоматичне встановлення та управління залежностями"""

    def __init__(self):
        self.system = platform.system()
        self.app_dir = Path(__file__).parent
        self.models_dir = Path.home() / ".stt_ocr_translate" / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def check_python_version(self):
        """Перевірка версії Python"""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"❌ Потрібен Python 3.8 або новіший. Ваша версія: {sys.version}")
            input("Натисніть Enter для виходу...")
            sys.exit(1)
        print(f"✅ Python версія: {version.major}.{version.minor}.{version.micro}")

    def install_package(self, package_name: str, import_name: str = None) -> bool:
        """Встановлення Python пакету"""
        if import_name is None:
            import_name = package_name.split('[')[0].split('==')[0]

        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            print(f"📦 Встановлюю {package_name}...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    package_name, "--quiet", "--disable-pip-version-check"
                ], timeout=600)
                return True
            except Exception as e:
                print(f"❌ Помилка встановлення {package_name}: {e}")
                return False

    def check_cuda(self) -> bool:
        """Перевірка CUDA"""
        return CUDAManager.check_cuda_availability()[0]


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
            return False

    def load_model(self, model_size: str, device: str = "auto", progress_callback=None):
        """Завантажити модель в пам'ять"""
        with self._lock:
            if self.model is not None and self.current_model_size == model_size:
                return self.model

            # Визначаємо пристрій
            if device == "auto":
                cuda_available, _ = CUDAManager.check_cuda_availability()
                device = "cuda" if cuda_available else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
            else:
                compute_type = "int8"

            # Перевіряємо наявність моделі
            model_path = self.get_model_path(model_size)
            if not model_path:
                success = self.download_model(model_size, progress_callback)
                if not success:
                    raise RuntimeError(f"Не вдалося отримати модель {model_size}")
                model_path = self.get_model_path(model_size)

            if progress_callback:
                progress_callback(50, f"⏳ Завантаження в пам'ять ({device})...")

            # Імпортуємо модель
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                str(model_path),
                device=device,
                compute_type=compute_type
            )

            self.current_model_size = model_size

            if progress_callback:
                progress_callback(100, f"✅ Модель готова ({device.upper()})")

            return self.model

    def unload_model(self):
        """Вивантажити модель з пам'яті"""
        with self._lock:
            self.model = None
            self.current_model_size = None
            import gc
            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()


class AppConfig:
    """Збереження налаштувань"""

    CONFIG_PATH = Path.home() / ".stt_ocr_translate" / "config.json"

    DEFAULT_CONFIG = {
        "whisper": {
            "model_size": "base",
            "beam_size": 5,
            "vad_filter": True,
            "min_silence_duration_ms": 500,
            "language": "uk",
            "device": "auto"
        },
        "tesseract": {
            "dpi": 300,
            "psm": 6,
            "contrast": 1.5,
            "sharpen": True,
            "langs": "ukr+eng"
        },
        "translation": {
            "service": "google",
            "auto_translate": False,
            "api_key": ""
        },
        "tts": {
            "engine": "auto",
            "speed": 1.0,
            "volume": 1.0,
            "voice": "uk-UA-PolinaNeural",
            "cache_dir": str(Path.home() / ".stt_ocr_translate" / "tts_cache")
        },
        "canvas": {
            "background_alpha": 0.95,
            "background_brightness": 0.0,
            "save_transparency": True
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
            except:
                pass
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
        with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        """Отримати значення за ключем"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value):
        """Встановити значення за ключем"""
        keys = key.split('.')
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_config()


class TTSService:
    """Багатопровайдерна озвучка"""

    def __init__(self, config: AppConfig):
        self.config = config
        self.cache_dir = Path(config.get('tts.cache_dir'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_available_engines(self) -> Dict[str, bool]:
        """Перевірка доступних TTS двигунів"""
        engines = {}
        try:
            import pyttsx3
            engines['pyttsx3'] = True
        except:
            engines['pyttsx3'] = False

        try:
            import gtts
            engines['gTTS'] = True
        except:
            engines['gTTS'] = False

        try:
            import edge_tts
            engines['edge-tts'] = True
        except:
            engines['edge-tts'] = False

        try:
            import torch
            import torchaudio
            engines['silero'] = True
        except:
            engines['silero'] = False

        try:
            import TTS
            engines['coqui'] = True
        except:
            engines['coqui'] = False

        return engines

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
        """Нейронна TTS"""
        import asyncio
        import edge_tts
        import tempfile
        import playsound

        async def speak_async():
            voices = {
                'uk': self.config.get('tts.voice', "uk-UA-PolinaNeural"),
                'en': "en-US-AriaNeural",
                'de': "de-DE-KatjaNeural",
                'pl': "pl-PL-ZofiaNeural"
            }

            communicate = edge_tts.Communicate(text, voices.get(lang, "en-US-AriaNeural"))

            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                await communicate.save(fp.name)
                playsound.playsound(fp.name)
                os.unlink(fp.name)

        asyncio.run(speak_async())

        if callback:
            callback("✅ Озвучено")


class TranslationService:
    """Перекладач з використанням безкоштовних сервісів"""

    SUPPORTED_SERVICES = ["google", "libretranslate", "mymemory"]

    @staticmethod
    def translate(text: str, service: str, source: str, target: str) -> str:
        """Загальний метод перекладу (без API ключа)"""
        try:
            if service.lower() == "google":
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source=source, target=target)
                return translator.translate(text)

            elif service.lower() == "libretranslate":
                from deep_translator import LibreTranslator
                # Використовуємо публічний інстанс LibreTranslate
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
            print(f"⚠️ Статус запису: {status}")
        if self._recording:
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
                blocksize=1024
            )
            self._stream.start()
            print(f"✅ Запис розпочато: {self.samplerate}Hz")
        except Exception as e:
            print(f"❌ Помилка початку запису: {e}")
            self._recording = False
            raise

    def stop(self):
        """Зупинка запису"""
        self._recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"⚠️ Помилка закриття потоку: {e}")
            finally:
                self._stream = None

        time.sleep(0.1)

        if not self._frames:
            print("⚠️ Не записано жодного фрейму")
            return np.zeros(0, dtype='float32')

        try:
            audio = np.concatenate(self._frames, axis=0)
            if audio.ndim > 1:
                audio = audio.flatten()
            print(f"✅ Записано {len(audio)} сампли ({len(audio) / self.samplerate:.2f} секунд)")
            return audio.astype('float32')
        except Exception as e:
            print(f"❌ Помилка обробки аудіо: {e}")
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
        self.withdraw()
        self.after(100, lambda: self.capture_area(x1, y1, x2, y2))

    def capture_area(self, x1, y1, x2, y2):
        """Захоплення та розпізнавання області"""
        try:
            img = ImageGrab.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = img.filter(ImageFilter.SHARPEN)
            text = pytesseract.image_to_string(img, lang='ukr+eng', config='--psm 6')
            if not text.strip():
                text = "[Текст не розпізнано]"
        except Exception as e:
            text = f"[OCR помилка: {e}]"

        self.callback(text)
        self.destroy()


# ==================== ГОЛОВНИЙ ДОДАТОК ====================

class EnhancedApp:
    """Головний клас застосунку"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎤 STT + OCR + Translate Pro Ultra")
        self.root.geometry("1000x750")

        # Ініціалізація менеджерів
        self.package_manager = PackageManager()
        self.config = AppConfig()
        self.whisper_manager = WhisperModelManager(self.package_manager.models_dir)
        self.tts_service = TTSService(self.config)

        # CUDA
        self.cuda_available, self.cuda_msg = CUDAManager.check_cuda_availability()
        if self.cuda_available:
            print(f"🚀 {self.cuda_msg}")

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
        """Побудова інтерфейсу (БЕЗ ПРАВОЇ ПАНЕЛІ)"""
        # Меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Файл меню
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="⚙️ Налаштування", command=self.open_settings)
        file_menu.add_separator()
        file_menu.add_command(label="⬇️ Завантажити моделі", command=self.open_settings)
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

        # Вкладки (без правої панелі)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        self.build_ocr_tab(notebook)
        self.build_stt_tab(notebook)
        self.build_translation_tab(notebook)  # Тут додамо слайдери

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
        self.model_combo.set(self.config.get('whisper.model_size', 'base'))
        self.model_combo.pack(side='left', padx=5)
        self.model_combo.bind('<<ComboboxSelected>>', lambda e: self.change_model())

        self.model_status = ttk.Label(model_frame, text="⚪ Модель не завантажена")
        self.model_status.pack(side='left', padx=5)

        self.load_model_button = ttk.Button(model_frame, text="⬇️ Завантажити", command=self.load_model_async)
        self.load_model_button.pack(side='right', padx=5)

        self.speech_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=('Arial', 11))
        self.speech_text.pack(fill='both', expand=True, padx=5, pady=5)

    def build_translation_tab(self, notebook):
        """Вкладка перекладу (З СЛАЙДЕРАМИ ЗНИЗУ)"""
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

        # НАЛАШТУВАННЯ ОЗВУЧКИ (знизу)
        tts_settings_frame = tk.LabelFrame(frame, text=" Налаштування озвучки ", bg='#2b2b2b', fg='white')
        tts_settings_frame.pack(fill=tk.X, padx=5, pady=5)

        # Швидкість
        speed_frame = tk.Frame(tts_settings_frame, bg='#2b2b2b')
        speed_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(speed_frame, text="Швидкість:", bg='#2b2b2b', fg='white').pack(side='left')
        self.speed_var = tk.DoubleVar(value=self.config.get('tts.speed', 1.0))
        tk.Scale(speed_frame, from_=0.5, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.speed_var, bg='#3c3c3c', fg='white', troughcolor='#1e1e1e',
                 highlightthickness=0, command=self.update_tts_settings).pack(side='left',
                                                                              fill=tk.X, expand=True, padx=5)

        # Гучність
        volume_frame = tk.Frame(tts_settings_frame, bg='#2b2b2b')
        volume_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(volume_frame, text="Гучність:", bg='#2b2b2b', fg='white').pack(side='left')
        self.volume_var = tk.DoubleVar(value=self.config.get('tts.volume', 1.0))
        tk.Scale(volume_frame, from_=0.0, to=1.0, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.volume_var, bg='#3c3c3c', fg='white', troughcolor='#1e1e1e',
                 highlightthickness=0, command=self.update_tts_settings).pack(side='left',
                                                                              fill=tk.X, expand=True, padx=5)

    def update_tts_settings(self, value=None):
        """Оновити налаштування TTS"""
        self.config.set('tts.speed', self.speed_var.get())
        self.config.set('tts.volume', self.volume_var.get())

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
        except:
            return False

    def check_whisper(self) -> bool:
        """Перевірити Whisper"""
        try:
            from faster_whisper import WhisperModel
            return True
        except:
            return False

    def check_tts(self) -> bool:
        """Перевірити TTS"""
        return any(self.tts_service.get_available_engines().values())

    def update_status(self, message: str):
        """Оновити статус"""
        self.status_var.set(message)

    def update_model_status_ui(self):
        """Оновити статус моделі"""
        model_size = self.config.get('whisper.model_size', 'base')
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

        model_size = self.config.get('whisper.model_size', 'base')

        def load():
            self.model_loading = True
            self.add_ui_task(lambda: self.progress_bar.start())

            try:
                device = 'cpu' if self.config.get('whisper.force_cpu') else 'auto'
                self.whisper_manager.load_model(model_size, device, self.download_progress)
                self.add_ui_task(self.update_model_status_ui)
            except Exception as e:
                self.add_ui_task(lambda: messagebox.showerror("Помилка", f"Не вдалося завантажити модель: {e}"))
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
        self.config.set('whisper.model_size', new_model)
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
            DrawingCanvas(self)  # Використовуємо новий DrawingCanvas
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити малювалку: {e}")
            self.root.deiconify()

    def open_settings(self):
        """Відкрити налаштування"""
        messagebox.showinfo("ℹ️", "Налаштування вбудовані в праву панель!")

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

                # ВИДАЛИЛИ api_key, бо LibreTranslate не потребує його
                translated = TranslationService.translate(text, service, from_lang, to_lang)

                def update_ui():
                    self.output_text.delete(1.0, tk.END)
                    self.output_text.insert(tk.END, translated)
                    self.update_status(f"✅ Перекладено ({from_lang} → {to_lang})")

                self.add_ui_task(update_ui)

            except Exception as e:
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
            model_size = self.config.get('whisper.model_size', 'base')
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
            messagebox.showerror("Помилка", f"Не вдалося почати запис: {e}")
            self.is_recording = False

    def stop_recording(self):
        """Зупинити запис і транскрибувати"""
        self.is_recording = False
        self.speech_button.config(text="🎧 Почати запис", state='disabled')
        self.mic_indicator.config(text="🟡", foreground="orange")
        self.update_status("Обробка...")

        def process():
            try:
                audio = self.recorder.stop()

                if len(audio) < 1600:
                    raise Exception("Занадто короткий запис")

                # Завантажуємо модель
                model_size = self.config.get('whisper.model_size', 'base')
                model = self.whisper_manager.load_model(model_size)

                # Параметри
                segments, info = model.transcribe(
                    audio,
                    beam_size=self.config.get('whisper.beam_size', 5),
                    language=self.config.get('whisper.language', 'uk'),
                    vad_filter=self.config.get('whisper.vad_filter', True),
                    vad_parameters=dict(
                        min_silence_duration_ms=self.config.get('whisper.min_silence_duration_ms', 500)
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
                def show_error():
                    self.mic_indicator.config(text="❌", foreground="red")
                    self.speech_button.config(state='normal')
                    self.update_status(f"Помилка: {str(e)[:50]}")
                    messagebox.showerror("Помилка", str(e))

                self.add_ui_task(show_error)

        threading.Thread(target=process, daemon=True).start()

    def clear_all_cache(self):
        """Очистити всі кеші"""
        if not messagebox.askyesno("Підтвердження", "Очистити кеш моделей та TTS?"):
            return

        try:
            cache_dir = Path.home() / ".cache" / "huggingface"
            if cache_dir.exists():
                shutil.rmtree(cache_dir)

            tts_cache = Path(self.config.get('tts.cache_dir'))
            if tts_cache.exists():
                shutil.rmtree(tts_cache)

            messagebox.showinfo("✅", "Кеш очищено")
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося очистити кеш: {e}")

    def on_close(self):
        """Закриття програми"""
        if self.is_recording and self.recorder:
            try:
                self.recorder.stop()
            except:
                pass
        self.root.destroy()


# ==================== ЗАПУСК ====================

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