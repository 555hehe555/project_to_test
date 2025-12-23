import os
import sys
from pathlib import Path
from PIL import Image
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
import queue


class MediaConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 Конвертер Медіафайлів Pro")
        self.root.geometry("900x700")
        self.root.configure(bg="#f0f4f8")

        # Черга для оновлення прогресу
        self.progress_queue = queue.Queue()

        # Список файлів
        self.files_data = []

        # Формати
        self.formats = {
            "image": ["PNG", "JPEG", "WEBP", "BMP", "TIFF"],
            "video": ["MP4", "AVI", "MOV", "WEBM", "GIF"],
            "audio": ["MP3", "WAV", "OGG", "AAC", "FLAC"]
        }

        self.setup_ui()
        self.check_progress_queue()

    def setup_ui(self):
        # Заголовок
        header_frame = tk.Frame(self.root, bg="#6366f1", height=100)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)

        title = tk.Label(
            header_frame,
            text="🎬 Конвертер Медіафайлів Pro",
            font=("Segoe UI", 24, "bold"),
            bg="#6366f1",
            fg="white"
        )
        title.pack(pady=20)

        subtitle = tk.Label(
            header_frame,
            text="Конвертуйте зображення, відео та аудіо у будь-який формат",
            font=("Segoe UI", 11),
            bg="#6366f1",
            fg="#e0e7ff"
        )
        subtitle.pack()

        # Контейнер для основного вмісту
        main_container = tk.Frame(self.root, bg="#f0f4f8")
        main_container.pack(fill="both", expand=True, padx=20, pady=0)

        # Кнопки вибору файлів
        button_frame = tk.Frame(main_container, bg="#f0f4f8")
        button_frame.pack(pady=(0, 15))

        add_btn = tk.Button(
            button_frame,
            text="➕ Додати файли",
            command=self.add_files,
            font=("Segoe UI", 12, "bold"),
            bg="#10b981",
            fg="white",
            relief="flat",
            padx=30,
            pady=12,
            cursor="hand2",
            activebackground="#059669"
        )
        add_btn.pack(side="left", padx=5)

        clear_btn = tk.Button(
            button_frame,
            text="🗑️ Очистити",
            command=self.clear_all,
            font=("Segoe UI", 12, "bold"),
            bg="#ef4444",
            fg="white",
            relief="flat",
            padx=30,
            pady=12,
            cursor="hand2",
            activebackground="#dc2626"
        )
        clear_btn.pack(side="left", padx=5)

        # Фрейм для списку файлів
        list_frame = tk.Frame(main_container, bg="white", relief="flat", bd=0)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))

        # Canvas для прокрутки
        self.canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Фрейм налаштувань
        settings_frame = tk.LabelFrame(
            main_container,
            text="⚙️ Налаштування виводу",
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#334155",
            relief="flat",
            bd=2,
            padx=15,
            pady=10
        )
        settings_frame.pack(fill="x", pady=(0, 15))

        # Вибір папки виводу
        output_row = tk.Frame(settings_frame, bg="white")
        output_row.pack(fill="x", pady=5)

        tk.Label(
            output_row,
            text="📁 Папка для збереження:",
            font=("Segoe UI", 10),
            bg="white"
        ).pack(side="left", padx=(0, 10))

        self.output_dir = tk.StringVar(value="converted")
        output_entry = tk.Entry(
            output_row,
            textvariable=self.output_dir,
            font=("Segoe UI", 10),
            width=40,
            relief="solid",
            bd=1
        )
        output_entry.pack(side="left", padx=5)

        browse_btn = tk.Button(
            output_row,
            text="Огляд",
            command=self.browse_output,
            font=("Segoe UI", 9),
            bg="#94a3b8",
            fg="white",
            relief="flat",
            cursor="hand2"
        )
        browse_btn.pack(side="left", padx=5)

        # Кнопка конвертації
        self.convert_btn = tk.Button(
            main_container,
            text="🚀 КОНВЕРТУВАТИ ВСІ ФАЙЛИ",
            command=self.start_conversion,
            font=("Segoe UI", 14, "bold"),
            bg="#6366f1",
            fg="white",
            relief="flat",
            pady=15,
            cursor="hand2",
            activebackground="#4f46e5",
            state="disabled"
        )
        self.convert_btn.pack(fill="x")

        # Статус бар
        self.status_var = tk.StringVar(value="Готовий до роботи")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            fg="#475569",
            anchor="w",
            padx=10,
            pady=5
        )
        status_bar.pack(fill="x", side="bottom")

    def get_file_type(self, filename):
        ext = filename.lower().split(".")[-1]
        if ext in ["png", "jpg", "jpeg", "jfif", "bmp", "webp", "tiff"]:
            return "image"
        if ext in ["mp4", "mov", "avi", "mkv", "webm", "flv"]:
            return "video"
        if ext in ["mp3", "wav", "ogg", "aac", "m4a", "flac"]:
            return "audio"
        return None

    def get_icon(self, file_type):
        icons = {
            "image": "🖼️",
            "video": "🎥",
            "audio": "🎵"
        }
        return icons.get(file_type, "📄")

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Виберіть файли",
            filetypes=[
                ("Всі підтримувані", "*.png *.jpg *.jpeg *.webp *.bmp *.mp4 *.mov *.avi *.mp3 *.wav *.ogg"),
                ("Зображення", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("Відео", "*.mp4 *.mov *.avi *.mkv"),
                ("Аудіо", "*.mp3 *.wav *.ogg *.aac"),
                ("Всі файли", "*.*")
            ]
        )

        for file_path in files:
            if not os.path.exists(file_path):
                continue

            file_type = self.get_file_type(file_path)
            if not file_type:
                continue

            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB

            file_data = {
                "path": file_path,
                "name": os.path.basename(file_path),
                "type": file_type,
                "size": f"{file_size:.2f} MB",
                "format": tk.StringVar(value=self.formats[file_type][0]),
                "status": "pending",
                "progress": 0
            }

            self.files_data.append(file_data)
            self.create_file_widget(file_data)

        if self.files_data:
            self.convert_btn.config(state="normal")
            self.status_var.set(f"Додано {len(self.files_data)} файл(ів)")

    def create_file_widget(self, file_data):
        frame = tk.Frame(self.scrollable_frame, bg="#f8fafc", relief="solid", bd=1)
        frame.pack(fill="x", padx=10, pady=5)

        file_data["widget"] = frame

        # Верхній рядок
        top_row = tk.Frame(frame, bg="#f8fafc")
        top_row.pack(fill="x", padx=10, pady=10)

        # Іконка + інфо
        icon_label = tk.Label(
            top_row,
            text=self.get_icon(file_data["type"]),
            font=("Segoe UI", 24),
            bg="#f8fafc"
        )
        icon_label.pack(side="left", padx=(0, 10))

        info_frame = tk.Frame(top_row, bg="#f8fafc")
        info_frame.pack(side="left", fill="x", expand=True)

        name_label = tk.Label(
            info_frame,
            text=file_data["name"],
            font=("Segoe UI", 11, "bold"),
            bg="#f8fafc",
            fg="#1e293b",
            anchor="w"
        )
        name_label.pack(anchor="w")

        size_label = tk.Label(
            info_frame,
            text=f"Розмір: {file_data['size']} | Тип: {file_data['type'].upper()}",
            font=("Segoe UI", 9),
            bg="#f8fafc",
            fg="#64748b",
            anchor="w"
        )
        size_label.pack(anchor="w")

        # Вибір формату
        format_label = tk.Label(
            top_row,
            text="Конвертувати в:",
            font=("Segoe UI", 9),
            bg="#f8fafc",
            fg="#475569"
        )
        format_label.pack(side="left", padx=(10, 5))

        format_menu = ttk.Combobox(
            top_row,
            textvariable=file_data["format"],
            values=self.formats[file_data["type"]],
            state="readonly",
            width=10,
            font=("Segoe UI", 10)
        )
        format_menu.pack(side="left", padx=5)

        # Статус
        file_data["status_label"] = tk.Label(
            top_row,
            text="⏳ Очікує",
            font=("Segoe UI", 9),
            bg="#fef3c7",
            fg="#92400e",
            padx=8,
            pady=3,
            relief="flat"
        )
        file_data["status_label"].pack(side="left", padx=10)

        # Кнопка видалення
        delete_btn = tk.Button(
            top_row,
            text="❌",
            command=lambda: self.remove_file(file_data),
            font=("Segoe UI", 10),
            bg="#fee2e2",
            fg="#991b1b",
            relief="flat",
            cursor="hand2",
            padx=8,
            pady=2
        )
        delete_btn.pack(side="left", padx=5)

        # Прогрес бар
        file_data["progress_bar"] = ttk.Progressbar(
            frame,
            length=860,
            mode="determinate"
        )

    def remove_file(self, file_data):
        file_data["widget"].destroy()
        self.files_data.remove(file_data)

        if not self.files_data:
            self.convert_btn.config(state="disabled")
            self.status_var.set("Готовий до роботи")
        else:
            self.status_var.set(f"Залишилось {len(self.files_data)} файл(ів)")

    def clear_all(self):
        if not self.files_data:
            return

        if messagebox.askyesno("Підтвердження", "Видалити всі файли зі списку?"):
            for file_data in self.files_data[:]:
                file_data["widget"].destroy()

            self.files_data.clear()
            self.convert_btn.config(state="disabled")
            self.status_var.set("Готовий до роботи")

    def browse_output(self):
        folder = filedialog.askdirectory(title="Виберіть папку для збереження")
        if folder:
            self.output_dir.set(folder)

    def start_conversion(self):
        output_dir = self.output_dir.get()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        self.convert_btn.config(state="disabled")
        self.status_var.set("🔄 Конвертація...")

        # Запуск конвертації в окремому потоці
        thread = Thread(target=self.convert_files, args=(output_dir,))
        thread.daemon = True
        thread.start()

    def convert_files(self, output_dir):
        total = len(self.files_data)

        for idx, file_data in enumerate(self.files_data, 1):
            self.progress_queue.put(("status", file_data, "converting", "🔄 Конвертація..."))

            try:
                output_format = file_data["format"].get().lower()
                base_name = os.path.splitext(file_data["name"])[0]
                output_path = os.path.join(output_dir, f"{base_name}.{output_format}")

                # Конвертація
                if file_data["type"] == "image":
                    self.convert_image(file_data["path"], output_path, output_format)
                elif file_data["type"] == "video":
                    self.convert_video(file_data["path"], output_path, output_format)
                elif file_data["type"] == "audio":
                    self.convert_audio(file_data["path"], output_path, output_format)

                self.progress_queue.put(("status", file_data, "completed", "✅ Готово"))
                self.progress_queue.put(("progress", idx, total))

            except Exception as e:
                self.progress_queue.put(("status", file_data, "error", f"❌ Помилка"))
                print(f"Помилка: {e}")

        self.progress_queue.put(("done",))

    def convert_image(self, src, output, format):
        img = Image.open(src)
        if format == "jpeg":
            img = img.convert("RGB")
        img.save(output)

    def convert_video(self, src, output, format):
        clip = VideoFileClip(src)
        if format == "gif":
            clip.write_gif(output, fps=10)
        else:
            clip.write_videofile(output, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        clip.close()

    def convert_audio(self, src, output, format):
        audio = AudioSegment.from_file(src)
        audio.export(output, format=format)

    def check_progress_queue(self):
        try:
            while True:
                msg = self.progress_queue.get_nowait()

                if msg[0] == "status":
                    _, file_data, status, text = msg
                    file_data["status"] = status
                    file_data["status_label"].config(text=text)

                    if status == "converting":
                        file_data["status_label"].config(bg="#dbeafe", fg="#1e40af")
                        file_data["progress_bar"].pack(fill="x", padx=10, pady=(0, 10))
                        file_data["progress_bar"].start(10)
                    elif status == "completed":
                        file_data["status_label"].config(bg="#dcfce7", fg="#166534")
                        file_data["progress_bar"].stop()
                        file_data["progress_bar"]["value"] = 100
                    elif status == "error":
                        file_data["status_label"].config(bg="#fee2e2", fg="#991b1b")
                        file_data["progress_bar"].stop()

                elif msg[0] == "progress":
                    _, current, total = msg
                    self.status_var.set(f"🔄 Конвертовано {current} з {total}")

                elif msg[0] == "done":
                    self.convert_btn.config(state="normal")
                    self.status_var.set("✅ Конвертація завершена!")
                    messagebox.showinfo("Готово", "Всі файли успішно конвертовано!")

        except queue.Empty:
            pass

        self.root.after(100, self.check_progress_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = MediaConverterGUI(root)
    root.mainloop()