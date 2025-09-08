import os
import stat
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import datetime
import webbrowser
from pathlib import Path
import mimetypes
import subprocess

from colorama import init, Fore, Style

init(autoreset=True)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class TreeConfig:
    def __init__(self):
        self.config = {
            'excluded_folders': [".git", "__pycache__", "venv", ".idea", "node_modules", "bin", "obj"],
            'excluded_extensions': ['.tmp', '.log', '.cache'],
            'max_depth': 0,
            'show_files': True,
            'show_hidden': True,
            'file_icons': True,
            'show_sizes': True,
            'show_dates': True,
            'show_permissions': False,
            'group_by_type': False,
            'last_path': SCRIPT_DIR,
            'output_format': 'tree'  # 'tree', 'json', 'csv'
        }

    def save_config(self):
        """Зберігає конфігурацію у файл"""
        config_path = os.path.join(SCRIPT_DIR, "scanner_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def load_config(self):
        """Завантажує конфігурацію з файлу"""
        config_path = os.path.join(SCRIPT_DIR, "scanner_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
        except Exception:
            pass


# Визначаємо SCRIPT_DIR коректно для .exe
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class FileTypeAnalyzer:
    """Аналізатор типів файлів для кращої категоризації"""

    @staticmethod
    def get_file_category(filepath):
        """Визначає категорію файлу за розширенням"""
        ext = os.path.splitext(filepath)[1].lower()

        categories = {
            'code': ['.py', '.js', '.html', '.css', '.cpp', '.c', '.java', '.php', '.rb', '.go', '.rs', '.ts'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'],
            'video': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'],
            'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'],
            'document': ['.pdf', '.doc', '.docx', '.txt', '.md', '.rtf', '.odt'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'data': ['.json', '.xml', '.csv', '.xlsx', '.db', '.sql']
        }

        for category, extensions in categories.items():
            if ext in extensions:
                return category
        return 'other'

    @staticmethod
    def get_file_icon(filepath, is_dir=False):
        """Повертає відповідну іконку для файлу або папки"""
        if is_dir:
            return "📁"

        category = FileTypeAnalyzer.get_file_category(filepath)
        icons = {
            'code': '💻',
            'image': '🖼️',
            'video': '🎬',
            'audio': '🎵',
            'document': '📄',
            'archive': '📦',
            'data': '📊',
            'other': '📄'
        }
        return icons.get(category, '📄')


class App(tk.Tk):
    def __init__(self, config):
        super().__init__()
        self.title("Розширений сканер структури папок v2.0")
        self.geometry("900x700")
        self.config_obj = config
        self.config_obj.load_config()

        # Змінні для GUI
        self.path_var = tk.StringVar(value=self.config_obj.config.get('last_path', SCRIPT_DIR))
        self.excluded_var = tk.StringVar(value=",".join(self.config_obj.config['excluded_folders']))
        self.excluded_ext_var = tk.StringVar(value=",".join(self.config_obj.config['excluded_extensions']))

        # Результати сканування
        self.scan_results = None
        self.file_paths = {}  # Словник для швидкого пошуку шляхів

        self.create_widgets()
        self.create_menu()

    def create_menu(self):
        """Створює меню програми"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Експорт у JSON", command=self.export_json)
        file_menu.add_command(label="Експорт у CSV", command=self.export_csv)
        file_menu.add_command(label="Експорт у HTML", command=self.export_html)
        file_menu.add_separator()
        file_menu.add_command(label="Зберегти налаштування", command=self.config_obj.save_config)
        file_menu.add_command(label="Вихід", command=self.quit)

        # Меню Інструменти
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Інструменти", menu=tools_menu)
        tools_menu.add_command(label="Знайти дублікати файлів", command=self.find_duplicates)
        tools_menu.add_command(label="Аналіз розмірів файлів", command=self.analyze_file_sizes)
        tools_menu.add_command(label="Статистика типів файлів", command=self.file_type_statistics)

    def choose_directory(self):
        path = filedialog.askdirectory(initialdir=self.config_obj.config.get('last_path', SCRIPT_DIR))
        if path:
            self.path_var.set(path)

    def create_widgets(self):
        # Створюємо notebook для вкладок
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Вкладка налаштувань
        self.create_settings_tab()

        # Вкладка результатів
        self.create_results_tab()

        # Вкладка аналітики
        self.create_analytics_tab()

    def create_settings_tab(self):
        """Створює вкладку з налаштуваннями"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Налаштування")

        padding = {'padx': 5, 'pady': 5}

        # Цільова папка
        path_frame = ttk.LabelFrame(settings_frame, text="🎯 Цільова папка")
        path_frame.pack(fill='x', **padding)

        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill='x', **padding)

        ttk.Entry(path_entry_frame, textvariable=self.path_var, width=50).pack(side='left', fill='x', expand=True,
                                                                               **padding)
        ttk.Button(path_entry_frame, text="Обрати...", command=self.choose_directory).pack(side='left', **padding)
        ttk.Button(path_entry_frame, text="Відкрити в провіднику", command=self.open_in_explorer).pack(side='left',
                                                                                                       **padding)

        # Основні налаштування
        main_options = ttk.LabelFrame(settings_frame, text="🔧 Основні налаштування")
        main_options.pack(fill='x', **padding)

        # Глибина
        depth_frame = ttk.Frame(main_options)
        depth_frame.pack(fill='x', **padding)
        ttk.Label(depth_frame, text="Максимальна глибина (0 = без обмежень):").pack(side='left')
        self.depth_spin = ttk.Spinbox(depth_frame, from_=0, to=100, width=5)
        self.depth_spin.pack(side='right')
        self.depth_spin.insert(0, str(self.config_obj.config['max_depth']))

        # Чекбокси
        self.hidden_var = tk.BooleanVar(value=self.config_obj.config['show_hidden'])
        ttk.Checkbutton(main_options, text="🔍 Показувати приховані файли/папки", variable=self.hidden_var).pack(
            anchor='w', **padding)

        self.files_var = tk.BooleanVar(value=self.config_obj.config['show_files'])
        ttk.Checkbutton(main_options, text="📄 Показувати файли", variable=self.files_var).pack(anchor='w', **padding)

        self.icons_var = tk.BooleanVar(value=self.config_obj.config['file_icons'])
        ttk.Checkbutton(main_options, text="🎨 Показувати іконки", variable=self.icons_var).pack(anchor='w', **padding)

        self.sizes_var = tk.BooleanVar(value=self.config_obj.config['show_sizes'])
        ttk.Checkbutton(main_options, text="📏 Показувати розміри файлів", variable=self.sizes_var).pack(anchor='w',
                                                                                                        **padding)

        self.dates_var = tk.BooleanVar(value=self.config_obj.config['show_dates'])
        ttk.Checkbutton(main_options, text="📅 Показувати дати модифікації", variable=self.dates_var).pack(anchor='w',
                                                                                                          **padding)

        self.permissions_var = tk.BooleanVar(value=self.config_obj.config['show_permissions'])
        ttk.Checkbutton(main_options, text="🔒 Показувати права доступу", variable=self.permissions_var).pack(anchor='w',
                                                                                                             **padding)

        self.group_by_type_var = tk.BooleanVar(value=self.config_obj.config['group_by_type'])
        ttk.Checkbutton(main_options, text="🗂️ Групувати файли за типом", variable=self.group_by_type_var).pack(
            anchor='w', **padding)

        # Виключення
        exclusions_frame = ttk.LabelFrame(settings_frame, text="🚫 Виключення")
        exclusions_frame.pack(fill='x', **padding)

        ttk.Label(exclusions_frame, text="Ігнорувати папки (через кому):").pack(anchor='w', **padding)
        ttk.Entry(exclusions_frame, textvariable=self.excluded_var, width=60).pack(fill='x', **padding)

        ttk.Label(exclusions_frame, text="Ігнорувати розширення файлів (через кому):").pack(anchor='w', **padding)
        ttk.Entry(exclusions_frame, textvariable=self.excluded_ext_var, width=60).pack(fill='x', **padding)

        # Формат виводу
        format_frame = ttk.LabelFrame(settings_frame, text="📋 Формат виводу")
        format_frame.pack(fill='x', **padding)

        self.format_var = tk.StringVar(value=self.config_obj.config['output_format'])
        ttk.Radiobutton(format_frame, text="🌳 Дерево", variable=self.format_var, value='tree').pack(anchor='w',
                                                                                                    **padding)
        ttk.Radiobutton(format_frame, text="📊 JSON", variable=self.format_var, value='json').pack(anchor='w', **padding)
        ttk.Radiobutton(format_frame, text="📈 CSV", variable=self.format_var, value='csv').pack(anchor='w', **padding)

        # Кнопки дій
        buttons_frame = ttk.Frame(settings_frame)
        buttons_frame.pack(fill='x', pady=10)

        ttk.Button(buttons_frame, text="🔍 Сканувати", command=self.run_scan).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="💾 Зберегти налаштування", command=self.save_settings).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="🔄 Скинути налаштування", command=self.reset_settings).pack(side='left', padx=5)

        # Статистика
        self.stats_label = ttk.Label(settings_frame, text="📊 Статистика з'явиться тут після сканування.")
        self.stats_label.pack(pady=(10, 5))

    def create_results_tab(self):
        """Створює вкладку з результатами"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="📋 Результати")

        # Фрейм для пошуку
        search_frame = ttk.Frame(results_frame)
        search_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(search_frame, text="🔍 Пошук:").pack(side='left', padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_results)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side='left', padx=(0, 5))

        ttk.Button(search_frame, text="🗂️ Відкрити папку", command=self.open_selected_folder).pack(side='right', padx=5)
        ttk.Button(search_frame, text="📄 Відкрити файл", command=self.open_selected_file).pack(side='right', padx=5)

        # Текстове поле з прокруткою для результатів
        self.results_text = scrolledtext.ScrolledText(results_frame, height=25, font=("Consolas", 10))
        self.results_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Контекстне меню для результатів
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="📋 Копіювати шлях", command=self.copy_path)
        self.context_menu.add_command(label="📂 Відкрити в провіднику", command=self.open_in_explorer_context)
        self.context_menu.add_command(label="📄 Відкрити файл", command=self.open_file_context)

        self.results_text.bind("<Button-3>", self.show_context_menu)

    def create_analytics_tab(self):
        """Створює вкладку з аналітикою"""
        analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(analytics_frame, text="📊 Аналітика")

        # Фрейм для кнопок аналітики
        analytics_buttons = ttk.Frame(analytics_frame)
        analytics_buttons.pack(fill='x', padx=5, pady=5)

        ttk.Button(analytics_buttons, text="📈 Топ найбільших файлів", command=self.show_largest_files).pack(side='left',
                                                                                                            padx=5)
        ttk.Button(analytics_buttons, text="🗂️ Типи файлів", command=self.show_file_types).pack(side='left', padx=5)
        ttk.Button(analytics_buttons, text="📅 Останні зміни", command=self.show_recent_files).pack(side='left', padx=5)

        # Текстове поле для аналітики
        self.analytics_text = scrolledtext.ScrolledText(analytics_frame, height=25, font=("Consolas", 10))
        self.analytics_text.pack(fill='both', expand=True, padx=5, pady=5)

    def save_settings(self):
        """Зберігає поточні налаштування"""
        self.update_config()
        self.config_obj.save_config()
        messagebox.showinfo("Збережено", "Налаштування успішно збережено!")

    def reset_settings(self):
        """Скидає налаштування до значень за замовчуванням"""
        self.config_obj.config = TreeConfig().config
        self.update_gui_from_config()
        messagebox.showinfo("Скинуто", "Налаштування скинуто до значень за замовчуванням!")

    def update_gui_from_config(self):
        """Оновлює GUI на основі поточної конфігурації"""
        self.path_var.set(self.config_obj.config.get('last_path', SCRIPT_DIR))
        self.excluded_var.set(",".join(self.config_obj.config['excluded_folders']))
        self.excluded_ext_var.set(",".join(self.config_obj.config['excluded_extensions']))
        self.depth_spin.delete(0, tk.END)
        self.depth_spin.insert(0, str(self.config_obj.config['max_depth']))

        # Оновлюємо чекбокси
        self.hidden_var.set(self.config_obj.config['show_hidden'])
        self.files_var.set(self.config_obj.config['show_files'])
        self.icons_var.set(self.config_obj.config['file_icons'])
        self.sizes_var.set(self.config_obj.config['show_sizes'])
        self.dates_var.set(self.config_obj.config['show_dates'])
        self.permissions_var.set(self.config_obj.config['show_permissions'])
        self.group_by_type_var.set(self.config_obj.config['group_by_type'])
        self.format_var.set(self.config_obj.config['output_format'])

    def update_config(self):
        """Оновлює конфігурацію з GUI"""
        self.config_obj.config.update({
            'max_depth': int(self.depth_spin.get()),
            'show_hidden': self.hidden_var.get(),
            'show_files': self.files_var.get(),
            'file_icons': self.icons_var.get(),
            'show_sizes': self.sizes_var.get(),
            'show_dates': self.dates_var.get(),
            'show_permissions': self.permissions_var.get(),
            'group_by_type': self.group_by_type_var.get(),
            'last_path': self.path_var.get(),
            'excluded_folders': [x.strip().lower() for x in self.excluded_var.get().split(',') if x.strip()],
            'excluded_extensions': [x.strip().lower() for x in self.excluded_ext_var.get().split(',') if x.strip()],
            'output_format': self.format_var.get(),
        })

    def open_in_explorer(self):
        """Відкриває поточну папку в провіднику"""
        path = self.path_var.get()
        if os.path.isdir(path):
            self.open_path_in_system(path)

    def open_selected_folder(self):
        """Відкриває вибрану в результатах папку"""
        current_line = self.get_current_line()
        if current_line:
            path = self.extract_path_from_line(current_line)
            if path and os.path.isdir(path):
                self.open_path_in_system(path)

    def open_selected_file(self):
        """Відкриває вибраний файл"""
        current_line = self.get_current_line()
        if current_line:
            path = self.extract_path_from_line(current_line)
            if path and os.path.isfile(path):
                self.open_path_in_system(path)

    @staticmethod
    def open_path_in_system(path):
        """Відкриває шлях у системному провіднику або програмі за замовчуванням"""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося відкрити: {e}")

    def get_current_line(self):
        """Отримує поточний рядок з текстового поля"""
        try:
            current_pos = self.results_text.index(tk.INSERT)
            line_start = self.results_text.index(f"{current_pos} linestart")
            line_end = self.results_text.index(f"{current_pos} lineend")
            return self.results_text.get(line_start, line_end)
        except:
            return None

    def extract_path_from_line(self, line):
        """Витягує шлях з рядка результатів"""
        # Простий спосіб: шукаємо в словнику file_paths
        for stored_path, display_name in self.file_paths.items():
            if display_name in line:
                return stored_path
        return None

    def show_context_menu(self, event):
        """Показує контекстне меню"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_path(self):
        """Копіює шлях до буфера обміну"""
        current_line = self.get_current_line()
        if current_line:
            path = self.extract_path_from_line(current_line)
            if path:
                self.clipboard_clear()
                self.clipboard_append(path)
                messagebox.showinfo("Скопійовано", f"Шлях скопійовано:\n{path}")

    def open_in_explorer_context(self):
        """Відкриває в провіднику через контекстне меню"""
        self.open_selected_folder()

    def open_file_context(self):
        """Відкриває файл через контекстне меню"""
        self.open_selected_file()

    def filter_results(self, *args):
        """Фільтрує результати за пошуковим запитом"""
        if not hasattr(self, 'original_results'):
            return

        search_term = self.search_var.get().lower()
        if not search_term:
            self.results_text.delete('1.0', tk.END)
            self.results_text.insert('1.0', self.original_results)
            return

        filtered_lines = []
        for line in self.original_results.split('\n'):
            if search_term in line.lower():
                filtered_lines.append(line)

        self.results_text.delete('1.0', tk.END)
        self.results_text.insert('1.0', '\n'.join(filtered_lines))

    def run_scan(self):
        """Запускає сканування"""
        path = self.path_var.get()
        if not os.path.isdir(path):
            messagebox.showerror("Помилка", "Вкажіть існуючу папку")
            return

        self.update_config()

        # Очищуємо попередні результати
        self.file_paths.clear()

        try:
            # Прогрес-бар
            progress_window = tk.Toplevel(self)
            progress_window.title("Сканування...")
            progress_window.geometry("400x100")
            progress_window.transient(self)
            progress_window.grab_set()

            progress_label = ttk.Label(progress_window, text="Сканування структури папок...")
            progress_label.pack(pady=10)

            progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
            progress_bar.pack(fill='x', padx=20, pady=10)
            progress_bar.start()

            self.update()

            # Виконуємо сканування
            self.scan_results = self.perform_detailed_scan(path)

            # Генеруємо вивід
            if self.config_obj.config['output_format'] == 'json':
                output_content = self.generate_json_output()
            elif self.config_obj.config['output_format'] == 'csv':
                output_content = self.generate_csv_output()
            else:
                output_content = self.generate_tree_output()

            # Зберігаємо оригінальні результати для фільтрації
            self.original_results = output_content

            # Відображаємо результати
            self.results_text.delete('1.0', tk.END)
            self.results_text.insert('1.0', output_content)

            # Переключаємося на вкладку результатів
            self.notebook.select(1)

            # Оновлюємо статистику
            self.update_statistics()

            # Зберігаємо у файл
            self.save_results_to_file(output_content)

            progress_window.destroy()

        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            messagebox.showerror("Помилка", f"Помилка під час сканування: {e}")

    def perform_detailed_scan(self, root_path):
        """Виконує детальне сканування з збиранням метаданих"""
        results = {
            'root_path': root_path,
            'scan_time': datetime.datetime.now().isoformat(),
            'structure': [],
            'statistics': {
                'total_folders': 0,
                'total_files': 0,
                'total_size': 0,
                'file_types': {},
                'largest_files': [],
                'recent_files': []
            }
        }

        self._scan_directory_recursive(root_path, results, '', 0)
        self._calculate_statistics(results)

        return results

    def _scan_directory_recursive(self, dir_path, results, prefix, depth):
        """Рекурсивно сканує директорію"""
        if self.config_obj.config['max_depth'] > 0 and depth >= self.config_obj.config['max_depth']:
            return

        try:
            entries = os.listdir(dir_path)
        except OSError as e:
            error_item = {
                'name': f"[Помилка доступу: {e.strerror}]",
                'path': dir_path,
                'type': 'error',
                'prefix': prefix,
                'depth': depth
            }
            results['structure'].append(error_item)
            return

        items_to_process = []
        excluded_lower = self.config_obj.config['excluded_folders']
        excluded_ext = self.config_obj.config['excluded_extensions']

        for entry_name in entries:
            entry_path = os.path.join(dir_path, entry_name)

            try:
                entry_stat = os.lstat(entry_path)
                is_dir = stat.S_ISDIR(entry_stat.st_mode)
                is_link = stat.S_ISLNK(entry_stat.st_mode)

                # Перевірки виключень
                if not self.config_obj.config['show_hidden'] and is_hidden(entry_path):
                    continue
                if not is_dir and not self.config_obj.config['show_files']:
                    continue
                if not is_dir:
                    ext = os.path.splitext(entry_name)[1].lower()
                    if ext in excluded_ext:
                        continue

                # Збираємо метадані
                file_info = {
                    'name': entry_name,
                    'path': entry_path,
                    'type': 'directory' if is_dir else 'file',
                    'is_link': is_link,
                    'size': entry_stat.st_size if not is_dir else 0,
                    'modified': datetime.datetime.fromtimestamp(entry_stat.st_mtime),
                    'permissions': oct(entry_stat.st_mode)[-3:] if hasattr(entry_stat, 'st_mode') else '---',
                    'prefix': prefix,
                    'depth': depth
                }

                if not is_dir:
                    file_info['category'] = FileTypeAnalyzer.get_file_category(entry_path)
                    file_info['extension'] = os.path.splitext(entry_name)[1].lower()

                items_to_process.append(file_info)

            except OSError:
                continue

        # Сортуємо: спочатку папки, потім файли
        items_to_process.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))

        # Додаємо до результатів
        for item in items_to_process:
            results['structure'].append(item)

            # Зберігаємо шлях для швидкого пошуку
            self.file_paths[item['path']] = item['name']

            # Оновлюємо статистику
            if item['type'] == 'directory':
                results['statistics']['total_folders'] += 1
            else:
                results['statistics']['total_files'] += 1
                results['statistics']['total_size'] += item['size']

                # Додаємо до списку найбільших файлів
                results['statistics']['largest_files'].append({
                    'path': item['path'],
                    'size': item['size'],
                    'name': item['name']
                })

                # Додаємо до останніх файлів
                results['statistics']['recent_files'].append({
                    'path': item['path'],
                    'modified': item['modified'],
                    'name': item['name']
                })

            # Рекурсивно обробляємо папки
            if item['type'] == 'directory' and item['name'].lower() not in excluded_lower:
                count = len([x for x in items_to_process if x['type'] == item['type']])
                current_index = [x for x in items_to_process if x['type'] == item['type']].index(item)
                is_last = (current_index == count - 1)

                next_prefix = item['prefix'] + ('    ' if is_last else '│   ')
                self._scan_directory_recursive(item['path'], results, next_prefix, depth + 1)

    def _calculate_statistics(self, results):
        """Обчислює додаткову статистику"""
        # Сортуємо найбільші файли
        results['statistics']['largest_files'].sort(key=lambda x: x['size'], reverse=True)
        results['statistics']['largest_files'] = results['statistics']['largest_files'][:50]  # Топ 50

        # Сортуємо останні файли
        results['statistics']['recent_files'].sort(key=lambda x: x['modified'], reverse=True)
        results['statistics']['recent_files'] = results['statistics']['recent_files'][:50]  # Топ 50

        # Підраховуємо типи файлів
        file_types = {}
        for item in results['structure']:
            if item['type'] == 'file':
                category = item.get('category', 'other')
                if category not in file_types:
                    file_types[category] = {'count': 0, 'size': 0}
                file_types[category]['count'] += 1
                file_types[category]['size'] += item['size']

        results['statistics']['file_types'] = file_types

    def generate_tree_output(self):
        """Генерує вивід у форматі дерева"""
        if not self.scan_results:
            return "Немає результатів сканування"

        lines = []
        lines.append(f"📂 Структура папки: {self.scan_results['root_path']}")
        lines.append(f"🕒 Час сканування: {self.scan_results['scan_time']}")
        lines.append("")

        current_prefix = ""
        items_by_depth = {}

        # Групуємо елементи за глибиною та префіксом
        for item in self.scan_results['structure']:
            depth = item['depth']
            if depth not in items_by_depth:
                items_by_depth[depth] = []
            items_by_depth[depth].append(item)

        # Обробляємо по рівнях
        for depth in sorted(items_by_depth.keys()):
            for item in items_by_depth[depth]:
                line = self._format_tree_line(item)
                lines.append(line)

        return '\n'.join(lines)

    def _format_tree_line(self, item):
        """Форматує рядок для дерева"""
        # Базовий префікс
        line = item['prefix']

        # Коннектор (останній елемент або ні)
        siblings = [x for x in self.scan_results['structure']
                    if x['depth'] == item['depth'] and x['prefix'] == item['prefix']]
        is_last = siblings[-1] == item if siblings else True
        connector = '└── ' if is_last else '├── '

        line += connector

        # Іконка
        if self.config_obj.config['file_icons']:
            if item['type'] == 'directory':
                line += "📁 "
            else:
                line += FileTypeAnalyzer.get_file_icon(item['path']) + " "

        # Ім'я
        line += item['name']

        # Додаткова інформація для файлів
        if item['type'] == 'file':
            details = []

            if self.config_obj.config['show_sizes']:
                details.append(f"({human_readable_size(item['size'])})")

            if self.config_obj.config['show_dates']:
                details.append(f"[{item['modified'].strftime('%Y-%m-%d %H:%M')}]")

            if self.config_obj.config['show_permissions']:
                details.append(f"<{item['permissions']}>")

            if details:
                line += " " + " ".join(details)

        return line

    def generate_json_output(self):
        """Генерує вивід у форматі JSON"""
        if not self.scan_results:
            return "Немає результатів сканування"

        # Створюємо копію з серіалізованими датами
        json_data = json.loads(json.dumps(self.scan_results, default=str, ensure_ascii=False))
        return json.dumps(json_data, indent=2, ensure_ascii=False)

    def generate_csv_output(self):
        """Генерує вивід у форматі CSV"""
        if not self.scan_results:
            return "Немає результатів сканування"

        lines = []
        lines.append("Тип,Ім'я,Шлях,Розмір (байти),Розмір (читабельний),Дата модифікації,Права доступу,Категорія")

        for item in self.scan_results['structure']:
            if item['type'] == 'error':
                continue

            row = [
                item['type'],
                f'"{item["name"]}"',  # Беремо в лапки на випадок ком у назві
                f'"{item["path"]}"',
                str(item.get('size', 0)),
                f'"{human_readable_size(item.get("size", 0))}"',
                item.get('modified', '').strftime('%Y-%m-%d %H:%M:%S') if item.get('modified') else '',
                item.get('permissions', ''),
                item.get('category', '')
            ]
            lines.append(','.join(row))

        return '\n'.join(lines)

    def update_statistics(self):
        """Оновлює відображення статистики"""
        if not self.scan_results:
            return

        stats = self.scan_results['statistics']

        self.stats_label.config(
            text=f"📊 Папок: {stats['total_folders']} | "
                 f"Файлів: {stats['total_files']} | "
                 f"Загальний розмір: {human_readable_size(stats['total_size'])}")

    def save_results_to_file(self, content):
        """Зберігає результати у файл"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        format_ext = {
            'tree': 'txt',
            'json': 'json',
            'csv': 'csv'
        }

        ext = format_ext.get(self.config_obj.config['output_format'], 'txt')
        output_path = os.path.join(SCRIPT_DIR, f"scan_results_{timestamp}.{ext}")

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Збережено", f"Результати збережено у:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Помилка збереження", f"Не вдалося зберегти файл:\n{e}")

    def export_json(self):
        """Експортує результати у JSON"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(self.scan_results, f, indent=2, ensure_ascii=False, default=str)
                messagebox.showinfo("Експорт", f"Дані експортовано у JSON:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Помилка експорту: {e}")

    def export_csv(self):
        """Експортує результати у CSV"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if filepath:
            try:
                csv_content = self.generate_csv_output()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(csv_content)
                messagebox.showinfo("Експорт", f"Дані експортовано у CSV:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Помилка експорту: {e}")

    def export_html(self):
        """Експортує результати у HTML з інтерактивною навігацією"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )

        if filepath:
            try:
                html_content = self.generate_html_output()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                messagebox.showinfo("Експорт", f"Інтерактивний HTML створено:\n{filepath}")

                # Пропонуємо відкрити в браузері
                if messagebox.askyesno("Відкрити", "Відкрити HTML файл у браузері?"):
                    webbrowser.open(f"file://{os.path.abspath(filepath)}")
            except Exception as e:
                messagebox.showerror("Помилка", f"Помилка експорту: {e}")

    def generate_html_output(self):
        """Генерує інтерактивний HTML з JavaScript навігацією"""
        html_template = '''<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Структура папки: {root_path}</title>
    <style>
        body {{
            font-family: 'Consolas', 'Monaco', monospace;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 2px solid #eee;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .search-box {{
            margin: 15px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .search-box input {{
            width: 300px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .tree-item {{
            margin: 2px 0;
            padding: 3px;
            border-radius: 3px;
            cursor: pointer;
            transition: background-color 0.2s;
        }}
        .tree-item:hover {{
            background-color: #e3f2fd;
        }}
        .tree-item.selected {{
            background-color: #bbdefb;
        }}
        .file-item {{ color: #2e7d32; }}
        .folder-item {{ color: #1565c0; font-weight: bold; }}
        .error-item {{ color: #d32f2f; }}
        .file-details {{
            font-size: 0.9em;
            color: #666;
            margin-left: 10px;
        }}
        .statistics {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
        .path-breadcrumb {{
            background: #e3f2fd;
            padding: 8px;
            border-radius: 4px;
            margin: 10px 0;
            font-family: monospace;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📂 Структура папки</h1>
            <div class="path-breadcrumb">
                <strong>Шлях:</strong> {root_path}
            </div>
            <div><strong>🕒 Час сканування:</strong> {scan_time}</div>
        </div>

        <div class="search-box">
            🔍 <input type="text" id="searchInput" placeholder="Пошук файлів та папок..." onkeyup="filterItems()">
            <button onclick="clearSearch()">Очистити</button>
        </div>

        <div class="statistics">
            <h3>📊 Статистика</h3>
            <p><strong>📁 Папок:</strong> {total_folders}</p>
            <p><strong>📄 Файлів:</strong> {total_files}</p>
            <p><strong>💾 Загальний розмір:</strong> {total_size}</p>
        </div>

        <div id="treeContent">
            {tree_content}
        </div>
    </div>

    <script>
        const allItems = document.querySelectorAll('.tree-item');

        function filterItems() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();

            allItems.forEach(item => {{
                const text = item.textContent.toLowerCase();
                if (searchTerm === '' || text.includes(searchTerm)) {{
                    item.style.display = 'block';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}

        function clearSearch() {{
            document.getElementById('searchInput').value = '';
            filterItems();
        }}

        // Обробка кліків для виділення
        allItems.forEach(item => {{
            item.addEventListener('click', function() {{
                allItems.forEach(i => i.classList.remove('selected'));
                this.classList.add('selected');
            }});
        }});

        // Копіювання шляху при подвійному кліку
        allItems.forEach(item => {{
            item.addEventListener('dblclick', function() {{
                const pathElement = this.getAttribute('data-path');
                if (pathElement) {{
                    navigator.clipboard.writeText(pathElement).then(() => {{
                        alert('Шлях скопійовано: ' + pathElement);
                    }});
                }}
            }});
        }});
    </script>
</body>
</html>'''

        # Генеруємо HTML контент дерева
        tree_lines = []
        for item in self.scan_results['structure']:
            css_class = f"{item['type']}-item"

            # Формуємо рядок з деталями
            details = []
            if item['type'] == 'file':
                if self.config_obj.config['show_sizes']:
                    details.append(f"({human_readable_size(item['size'])})")
                if self.config_obj.config['show_dates']:
                    details.append(f"[{item['modified'].strftime('%Y-%m-%d %H:%M')}]")

            detail_str = " ".join(details)

            # Іконка
            icon = ""
            if self.config_obj.config['file_icons']:
                icon = FileTypeAnalyzer.get_file_icon(item['path'], item['type'] == 'directory')

            tree_line = f'''<div class="tree-item {css_class}" data-path="{item['path']}">
                {item['prefix']}{'└── ' if item.get('is_last', False) else '├── '}{icon} {item['name']}
                <span class="file-details">{detail_str}</span>
            </div>'''

            tree_lines.append(tree_line)

        stats = self.scan_results['statistics']

        return html_template.format(
            root_path=self.scan_results['root_path'],
            scan_time=self.scan_results['scan_time'],
            total_folders=stats['total_folders'],
            total_files=stats['total_files'],
            total_size=human_readable_size(stats['total_size']),
            tree_content='\n'.join(tree_lines)
        )

    def find_duplicates(self):
        """Знаходить дублікати файлів"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        self.analytics_text.delete('1.0', tk.END)
        self.analytics_text.insert('1.0', "🔍 Пошук дублікатів файлів...\n\n")
        self.update()

        # Групуємо файли за розміром та іменем
        files_by_size = {}
        files_by_name = {}

        for item in self.scan_results['structure']:
            if item['type'] == 'file':
                size = item['size']
                name = item['name'].lower()

                if size not in files_by_size:
                    files_by_size[size] = []
                files_by_size[size].append(item)

                if name not in files_by_name:
                    files_by_name[name] = []
                files_by_name[name].append(item)

        # Знаходимо дублікати за розміром
        duplicates_text = "🔍 ДУБЛІКАТИ ЗА РОЗМІРОМ:\n" + "=" * 50 + "\n\n"
        size_duplicates_found = False

        for size, files in files_by_size.items():
            if len(files) > 1 and size > 0:  # Ігноруємо порожні файли
                size_duplicates_found = True
                duplicates_text += f"📏 Розмір: {human_readable_size(size)} ({len(files)} файлів)\n"
                for file_item in files:
                    duplicates_text += f"   📄 {file_item['path']}\n"
                duplicates_text += "\n"

        if not size_duplicates_found:
            duplicates_text += "✅ Дублікатів за розміром не знайдено.\n\n"

        # Знаходимо дублікати за іменем
        duplicates_text += "\n🔍 ДУБЛІКАТИ ЗА ІМЕНЕМ:\n" + "=" * 50 + "\n\n"
        name_duplicates_found = False

        for name, files in files_by_name.items():
            if len(files) > 1:
                name_duplicates_found = True
                duplicates_text += f"📛 Ім'я: {name} ({len(files)} файлів)\n"
                for file_item in files:
                    duplicates_text += f"   📄 {file_item['path']} ({human_readable_size(file_item['size'])})\n"
                duplicates_text += "\n"

        if not name_duplicates_found:
            duplicates_text += "✅ Дублікатів за іменем не знайдено.\n"

        self.analytics_text.delete('1.0', tk.END)
        self.analytics_text.insert('1.0', duplicates_text)
        self.notebook.select(2)  # Переключаємося на вкладку аналітики

    def analyze_file_sizes(self):
        """Аналізує розподіл розмірів файлів"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        stats = self.scan_results['statistics']

        analysis_text = "📊 АНАЛІЗ РОЗМІРІВ ФАЙЛІВ\n" + "=" * 50 + "\n\n"

        # Топ найбільших файлів
        analysis_text += "🔝 ТОП-20 НАЙБІЛЬШИХ ФАЙЛІВ:\n" + "-" * 30 + "\n"
        for i, file_info in enumerate(stats['largest_files'][:20], 1):
            analysis_text += f"{i:2d}. {human_readable_size(file_info['size']):>10} - {file_info['path']}\n"

        # Розподіл за розмірами
        analysis_text += f"\n📏 РОЗПОДІЛ ЗА РОЗМІРАМИ:\n" + "-" * 30 + "\n"

        size_ranges = {
            'Дуже малі (< 1 КБ)': (0, 1024),
            'Малі (1 КБ - 1 МБ)': (1024, 1024 * 1024),
            'Середні (1 МБ - 100 МБ)': (1024 * 1024, 100 * 1024 * 1024),
            'Великі (100 МБ - 1 ГБ)': (100 * 1024 * 1024, 1024 * 1024 * 1024),
            'Дуже великі (> 1 ГБ)': (1024 * 1024 * 1024, float('inf'))
        }

        for range_name, (min_size, max_size) in size_ranges.items():
            count = sum(1 for item in self.scan_results['structure']
                        if item['type'] == 'file' and min_size <= item['size'] < max_size)
            total_size = sum(item['size'] for item in self.scan_results['structure']
                             if item['type'] == 'file' and min_size <= item['size'] < max_size)
            analysis_text += f"{range_name:20} : {count:6d} файлів ({human_readable_size(total_size)})\n"

        self.analytics_text.delete('1.0', tk.END)
        self.analytics_text.insert('1.0', analysis_text)
        self.notebook.select(2)

    def file_type_statistics(self):
        """Показує статистику типів файлів"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        stats_text = "📊 СТАТИСТИКА ТИПІВ ФАЙЛІВ\n" + "=" * 50 + "\n\n"

        file_types = self.scan_results['statistics']['file_types']

        # Сортуємо за кількістю файлів
        sorted_types = sorted(file_types.items(), key=lambda x: x[1]['count'], reverse=True)

        stats_text += f"{'Категорія':15} {'Файлів':>8} {'Розмір':>12} {'Середній розмір':>15}\n"
        stats_text += "-" * 55 + "\n"

        for category, data in sorted_types:
            avg_size = data['size'] / data['count'] if data['count'] > 0 else 0
            icon = {
                'code': '💻', 'image': '🖼️', 'video': '🎬', 'audio': '🎵',
                'document': '📄', 'archive': '📦', 'data': '📊', 'other': '❓'
            }.get(category, '❓')

            stats_text += f"{icon} {category:12} {data['count']:>8} {human_readable_size(data['size']):>12} {human_readable_size(avg_size):>15}\n"

        # Додаткова інформація
        total_files = sum(data['count'] for data in file_types.values())
        total_size = sum(data['size'] for data in file_types.values())

        stats_text += "\n" + "=" * 50 + "\n"
        stats_text += f"📄 Загалом файлів: {total_files}\n"
        stats_text += f"💾 Загальний розмір: {human_readable_size(total_size)}\n"

        if total_files > 0:
            stats_text += f"📊 Середній розмір файлу: {human_readable_size(total_size / total_files)}\n"

        self.analytics_text.delete('1.0', tk.END)
        self.analytics_text.insert('1.0', stats_text)
        self.notebook.select(2)

    def show_largest_files(self):
        """Показує найбільші файли"""
        self.analyze_file_sizes()

    def show_file_types(self):
        """Показує статистику типів файлів"""
        self.file_type_statistics()

    def show_recent_files(self):
        """Показує останньо змінені файли"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        recent_text = "📅 ОСТАННІ ЗМІНИ ФАЙЛІВ\n" + "=" * 50 + "\n\n"
        recent_text += "🔝 ТОП-30 ОСТАННЬО ЗМІНЕНИХ ФАЙЛІВ:\n" + "-" * 35 + "\n"

        for i, file_info in enumerate(self.scan_results['statistics']['recent_files'][:30], 1):
            date_str = file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')
            recent_text += f"{i:2d}. {date_str} - {file_info['path']}\n"

        self.analytics_text.delete('1.0', tk.END)
        self.analytics_text.insert('1.0', recent_text)
        self.notebook.select(2)


def human_readable_size(size_bytes):
    """Конвертує розмір у байтах у читабельний формат"""
    if size_bytes is None or size_bytes < 0:
        return "Н/Д"
    if size_bytes == 0:
        return "0 Б"

    units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {units[i]}" if size_bytes % 1 != 0 else f"{int(size_bytes)} {units[i]}"


def colorize(item_text, is_dir, full_item_name=None):
    """Додає кольори до тексту для консольного виводу"""
    if is_dir:
        return Fore.BLUE + item_text + Style.RESET_ALL
    else:
        check_name = full_item_name if full_item_name else item_text
        category = FileTypeAnalyzer.get_file_category(check_name)

        colors = {
            'code': Fore.YELLOW,
            'image': Fore.MAGENTA,
            'video': Fore.RED,
            'audio': Fore.CYAN,
            'document': Fore.GREEN,
            'archive': Fore.LIGHTBLUE_EX,
            'data': Fore.LIGHTGREEN_EX
        }

        color = colors.get(category, Fore.WHITE)
        return color + item_text + Style.RESET_ALL


def is_hidden(filepath):
    """Перевіряє чи є файл/папка прихованою"""
    try:
        if os.name == 'posix':
            return os.path.basename(filepath).startswith('.')
        elif os.name == 'nt':
            attrs = os.stat(filepath).st_file_attributes
            return attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM)
    except OSError:
        return False
    return False


def calculate_total_size(root_path):
    """
    Розраховує повний розмір папки та її вмісту, рекурсивно.
    Ігнорує помилки доступу до окремих файлів.
    """
    total_size = 0
    try:
        for entry in os.scandir(root_path):
            try:
                if entry.is_dir(follow_symlinks=False):
                    total_size += calculate_total_size(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    total_size += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    except OSError:
        return 0

    return total_size


class QuickAccessPanel:
    """Панель швидкого доступу до популярних папок"""

    def __init__(self, parent_app):
        self.parent_app = parent_app

    def get_common_folders(self):
        """Повертає список популярних папок для швидкого доступу"""
        common_folders = []

        # Домашня папка
        home_dir = os.path.expanduser("~")
        if os.path.exists(home_dir):
            common_folders.append(("🏠 Домашня папка", home_dir))

        # Робочий стіл
        desktop_paths = [
            os.path.join(home_dir, "Desktop"),
            os.path.join(home_dir, "Робочий стол"),
            os.path.join(home_dir, "Рабочий стол")
        ]
        for desktop_path in desktop_paths:
            if os.path.exists(desktop_path):
                common_folders.append(("🖥️ Робочий стіл", desktop_path))
                break

        # Документи
        documents_paths = [
            os.path.join(home_dir, "Documents"),
            os.path.join(home_dir, "Документи"),
            os.path.join(home_dir, "Документы")
        ]
        for doc_path in documents_paths:
            if os.path.exists(doc_path):
                common_folders.append(("📄 Документи", doc_path))
                break

        # Завантаження
        downloads_paths = [
            os.path.join(home_dir, "Downloads"),
            os.path.join(home_dir, "Завантаження"),
            os.path.join(home_dir, "Загрузки")
        ]
        for download_path in downloads_paths:
            if os.path.exists(download_path):
                common_folders.append(("⬇️ Завантаження", download_path))
                break

        # Програми (тільки для Windows)
        if os.name == 'nt':
            program_paths = [
                "C:\\Program Files",
                "C:\\Program Files (x86)"
            ]
            for prog_path in program_paths:
                if os.path.exists(prog_path):
                    common_folders.append((f"⚙️ {os.path.basename(prog_path)}", prog_path))

        # Поточна директорія скрипта
        common_folders.append(("📁 Папка програми", SCRIPT_DIR))

        return common_folders


class AdvancedFilterDialog:
    """Розширене вікно для налаштування фільтрів"""

    def __init__(self, parent, current_config):
        self.parent = parent
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🔍 Розширені фільтри")
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Змінні для фільтрів
        self.min_size = tk.StringVar(value="0")
        self.max_size = tk.StringVar(value="")
        self.date_from = tk.StringVar()
        self.date_to = tk.StringVar()
        self.name_pattern = tk.StringVar()
        self.include_extensions = tk.StringVar()
        self.exclude_extensions = tk.StringVar(value=",".join(current_config['excluded_extensions']))

        self.create_filter_widgets()

        # Центруємо вікно
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"500x600+{x}+{y}")

    def create_filter_widgets(self):
        """Створює віджети для налаштування фільтрів"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Фільтри за розміром
        size_frame = ttk.LabelFrame(main_frame, text="📏 Фільтри за розміром")
        size_frame.pack(fill='x', pady=5)

        ttk.Label(size_frame, text="Мінімальний розмір (байти):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(size_frame, textvariable=self.min_size, width=20).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(size_frame, text="Максимальний розмір (байти):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(size_frame, textvariable=self.max_size, width=20).grid(row=1, column=1, padx=5, pady=5)

        # Підказки для розміру
        hint_frame = ttk.Frame(size_frame)
        hint_frame.grid(row=2, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        ttk.Label(hint_frame, text="💡 Підказка: 1 КБ = 1024, 1 МБ = 1048576, 1 ГБ = 1073741824",
                  font=('TkDefaultFont', 8)).pack()

        # Швидкі кнопки для розмірів
        quick_size_frame = ttk.Frame(size_frame)
        quick_size_frame.grid(row=3, column=0, columnspan=2, pady=5)

        ttk.Button(quick_size_frame, text="> 1 МБ",
                   command=lambda: self.min_size.set("1048576")).pack(side='left', padx=2)
        ttk.Button(quick_size_frame, text="> 10 МБ",
                   command=lambda: self.min_size.set("10485760")).pack(side='left', padx=2)
        ttk.Button(quick_size_frame, text="> 100 МБ",
                   command=lambda: self.min_size.set("104857600")).pack(side='left', padx=2)

        # Фільтри за датою
        date_frame = ttk.LabelFrame(main_frame, text="📅 Фільтри за датою модифікації")
        date_frame.pack(fill='x', pady=5)

        ttk.Label(date_frame, text="Від дати (YYYY-MM-DD):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(date_frame, textvariable=self.date_from, width=20).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(date_frame, text="До дати (YYYY-MM-DD):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(date_frame, textvariable=self.date_to, width=20).grid(row=1, column=1, padx=5, pady=5)

        # Швидкі кнопки для дат
        quick_date_frame = ttk.Frame(date_frame)
        quick_date_frame.grid(row=2, column=0, columnspan=2, pady=5)

        today = datetime.datetime.now()
        week_ago = today - datetime.timedelta(days=7)
        month_ago = today - datetime.timedelta(days=30)

        ttk.Button(quick_date_frame, text="Останній тиждень",
                   command=lambda: self.date_from.set(week_ago.strftime("%Y-%m-%d"))).pack(side='left', padx=2)
        ttk.Button(quick_date_frame, text="Останній місяць",
                   command=lambda: self.date_from.set(month_ago.strftime("%Y-%m-%d"))).pack(side='left', padx=2)

        # Фільтри за іменем
        name_frame = ttk.LabelFrame(main_frame, text="📝 Фільтри за іменем")
        name_frame.pack(fill='x', pady=5)

        ttk.Label(name_frame, text="Шаблон імені (* = будь-які символи):").grid(row=0, column=0, sticky='w', padx=5,
                                                                                pady=5)
        ttk.Entry(name_frame, textvariable=self.name_pattern, width=30).grid(row=0, column=1, padx=5, pady=5)

        hint_name = ttk.Label(name_frame, text="💡 Приклади: *.txt, backup*, *config*",
                              font=('TkDefaultFont', 8))
        hint_name.grid(row=1, column=0, columnspan=2, sticky='w', padx=5)

        # Фільтри за розширеннями
        ext_frame = ttk.LabelFrame(main_frame, text="📎 Фільтри за розширеннями")
        ext_frame.pack(fill='x', pady=5)

        ttk.Label(ext_frame, text="Включити тільки (через кому):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(ext_frame, textvariable=self.include_extensions, width=30).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(ext_frame, text="Виключити (через кому):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        ttk.Entry(ext_frame, textvariable=self.exclude_extensions, width=30).grid(row=1, column=1, padx=5, pady=5)

        # Швидкі набори розширень
        quick_ext_frame = ttk.Frame(ext_frame)
        quick_ext_frame.grid(row=2, column=0, columnspan=2, pady=5)

        ttk.Button(quick_ext_frame, text="Зображення",
                   command=lambda: self.include_extensions.set(".jpg,.jpeg,.png,.gif,.bmp,.svg")).pack(side='left',
                                                                                                       padx=2)
        ttk.Button(quick_ext_frame, text="Документи",
                   command=lambda: self.include_extensions.set(".pdf,.doc,.docx,.txt,.md,.rtf")).pack(side='left',
                                                                                                      padx=2)
        ttk.Button(quick_ext_frame, text="Код",
                   command=lambda: self.include_extensions.set(".py,.js,.html,.css,.cpp,.java")).pack(side='left',
                                                                                                      padx=2)

        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=10)

        ttk.Button(button_frame, text="✅ Застосувати", command=self.apply_filters).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🔄 Скинути", command=self.reset_filters).pack(side='left', padx=5)
        ttk.Button(button_frame, text="❌ Скасувати", command=self.cancel).pack(side='right', padx=5)

    def apply_filters(self):
        """Застосовує налаштовані фільтри"""
        try:
            filters = {
                'min_size': int(self.min_size.get() or 0),
                'max_size': int(self.max_size.get()) if self.max_size.get() else None,
                'date_from': datetime.datetime.strptime(self.date_from.get(),
                                                        "%Y-%m-%d") if self.date_from.get() else None,
                'date_to': datetime.datetime.strptime(self.date_to.get(), "%Y-%m-%d") if self.date_to.get() else None,
                'name_pattern': self.name_pattern.get() if self.name_pattern.get() else None,
                'include_extensions': [ext.strip().lower() for ext in self.include_extensions.get().split(',') if
                                       ext.strip()],
                'exclude_extensions': [ext.strip().lower() for ext in self.exclude_extensions.get().split(',') if
                                       ext.strip()]
            }
            self.result = filters
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Помилка", f"Некоректні дані у фільтрах: {e}")

    def reset_filters(self):
        """Скидає всі фільтри"""
        self.min_size.set("0")
        self.max_size.set("")
        self.date_from.set("")
        self.date_to.set("")
        self.name_pattern.set("")
        self.include_extensions.set("")
        self.exclude_extensions.set("")

    def cancel(self):
        """Скасовує діалог"""
        self.dialog.destroy()


# Додаємо розширену функціональність до основного класу App
class EnhancedApp(App):
    """Розширена версія програми з додатковими можливостями"""

    def __init__(self, config):
        super().__init__(config)
        self.current_filters = None
        self.add_quick_access_panel()
        self.add_advanced_features()

    def add_quick_access_panel(self):
        """Додає панель швидкого доступу"""
        quick_panel = ttk.LabelFrame(self.notebook.winfo_children()[0], text="⚡ Швидкий доступ")
        quick_panel.pack(fill='x', padx=5, pady=5)

        self.quick_access = QuickAccessPanel(self)

        # Створюємо кнопки для популярних папок
        button_frame = ttk.Frame(quick_panel)
        button_frame.pack(fill='x', padx=5, pady=5)

        common_folders = self.quick_access.get_common_folders()
        for i, (name, path) in enumerate(common_folders):
            if i % 3 == 0 and i > 0:
                button_frame = ttk.Frame(quick_panel)
                button_frame.pack(fill='x', padx=5, pady=2)

            ttk.Button(button_frame, text=name,
                       command=lambda p=path: self.path_var.set(p)).pack(side='left', padx=2, pady=2)

    def add_advanced_features(self):
        """Додає розширені функції"""
        # Додаємо кнопку розширених фільтрів у налаштування
        settings_frame = self.notebook.winfo_children()[0]
        advanced_frame = ttk.Frame(settings_frame)
        advanced_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(advanced_frame, text="🔍 Розширені фільтри",
                   command=self.open_advanced_filters).pack(side='left', padx=5)
        ttk.Button(advanced_frame, text="📊 Порівняти папки",
                   command=self.compare_folders).pack(side='left', padx=5)
        ttk.Button(advanced_frame, text="🔄 Створити звіт",
                   command=self.generate_report).pack(side='left', padx=5)

    def open_advanced_filters(self):
        """Відкриває діалог розширених фільтрів"""
        dialog = AdvancedFilterDialog(self, self.config_obj.config)
        self.wait_window(dialog.dialog)

        if dialog.result:
            self.current_filters = dialog.result
            messagebox.showinfo("Фільтри", "Розширені фільтри застосовано! Запустіть сканування для використання.")

    def compare_folders(self):
        """Порівнює дві папки"""
        folder1 = filedialog.askdirectory(title="Оберіть першу папку для порівняння")
        if not folder1:
            return

        folder2 = filedialog.askdirectory(title="Оберіть другу папку для порівняння")
        if not folder2:
            return

        # Виконуємо порівняння
        self.perform_folder_comparison(folder1, folder2)

    def perform_folder_comparison(self, folder1, folder2):
        """Виконує порівняння двох папок"""
        comparison_text = f"📊 ПОРІВНЯННЯ ПАПОК\n{'=' * 50}\n\n"
        comparison_text += f"📁 Папка 1: {folder1}\n"
        comparison_text += f"📁 Папка 2: {folder2}\n\n"

        try:
            # Отримуємо списки файлів з обох папок
            files1 = set()
            files2 = set()

            for root, dirs, files in os.walk(folder1):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), folder1)
                    files1.add(rel_path)

            for root, dirs, files in os.walk(folder2):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), folder2)
                    files2.add(rel_path)

            # Знаходимо відмінності
            only_in_1 = files1 - files2
            only_in_2 = files2 - files1
            common_files = files1 & files2

            comparison_text += f"📊 Статистика:\n"
            comparison_text += f"   Файлів тільки в папці 1: {len(only_in_1)}\n"
            comparison_text += f"   Файлів тільки в папці 2: {len(only_in_2)}\n"
            comparison_text += f"   Спільних файлів: {len(common_files)}\n\n"

            if only_in_1:
                comparison_text += f"📁 Файли тільки в папці 1 ({len(only_in_1)}):\n{'-' * 30}\n"
                for file in sorted(list(only_in_1)[:50]):  # Показуємо перші 50
                    comparison_text += f"   {file}\n"
                if len(only_in_1) > 50:
                    comparison_text += f"   ... та ще {len(only_in_1) - 50} файлів\n"
                comparison_text += "\n"

            if only_in_2:
                comparison_text += f"📁 Файли тільки в папці 2 ({len(only_in_2)}):\n{'-' * 30}\n"
                for file in sorted(list(only_in_2)[:50]):  # Показуємо перші 50
                    comparison_text += f"   {file}\n"
                if len(only_in_2) > 50:
                    comparison_text += f"   ... та ще {len(only_in_2) - 50} файлів\n"
                comparison_text += "\n"

        except Exception as e:
            comparison_text += f"❌ Помилка під час порівняння: {e}\n"

        # Відображаємо результат
        self.analytics_text.delete('1.0', tk.END)
        self.analytics_text.insert('1.0', comparison_text)
        self.notebook.select(2)

    def generate_report(self):
        """Генерує детальний звіт"""
        if not self.scan_results:
            messagebox.showwarning("Попередження", "Спочатку виконайте сканування")
            return

        # Створюємо детальний звіт
        report = self.create_detailed_report()

        # Зберігаємо звіт
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(SCRIPT_DIR, f"detailed_report_{timestamp}.txt")

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)

            messagebox.showinfo("Звіт створено", f"Детальний звіт збережено:\n{report_path}")

            # Пропонуємо відкрити звіт
            if messagebox.askyesno("Відкрити звіт", "Відкрити звіт для перегляду?"):
                self.open_path_in_system(report_path)

        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося створити звіт: {e}")

    def create_detailed_report(self):
        """Створює детальний звіт про сканування"""
        stats = self.scan_results['statistics']

        report = f"""
🔍 ДЕТАЛЬНИЙ ЗВІТ СКАНУВАННЯ ПАПКИ
{'=' * 60}

📊 ЗАГАЛЬНА ІНФОРМАЦІЯ:
{'=' * 30}
🎯 Цільова папка: {self.scan_results['root_path']}
🕒 Час сканування: {self.scan_results['scan_time']}
📁 Загальна кількість папок: {stats['total_folders']}
📄 Загальна кількість файлів: {stats['total_files']}
💾 Загальний розмір: {human_readable_size(stats['total_size'])}

⚙️ ПАРАМЕТРИ СКАНУВАННЯ:
{'=' * 30}
🔍 Максимальна глибина: {self.config_obj.config['max_depth'] or 'Без обмежень'}
👁️ Показувати приховані: {'Так' if self.config_obj.config['show_hidden'] else 'Ні'}
📄 Показувати файли: {'Так' if self.config_obj.config['show_files'] else 'Ні'}
🎨 Показувати іконки: {'Так' if self.config_obj.config['file_icons'] else 'Ні'}
🚫 Виключені папки: {', '.join(self.config_obj.config['excluded_folders']) or 'Немає'}
🚫 Виключені розширення: {', '.join(self.config_obj.config['excluded_extensions']) or 'Немає'}

📊 СТАТИСТИКА ТИПІВ ФАЙЛІВ:
{'=' * 30}
"""

        # Додаємо статистику типів файлів
        for category, data in sorted(stats['file_types'].items(), key=lambda x: x[1]['count'], reverse=True):
            percentage = (data['count'] / stats['total_files'] * 100) if stats['total_files'] > 0 else 0
            report += f"📁 {category.upper():12} : {data['count']:6} файлів ({percentage:5.1f}%) - {human_readable_size(data['size'])}\n"

        # Додаємо топ найбільших файлів
        report += f"\n🔝 ТОП-20 НАЙБІЛЬШИХ ФАЙЛІВ:\n{'=' * 30}\n"
        for i, file_info in enumerate(stats['largest_files'][:20], 1):
            report += f"{i:2d}. {human_readable_size(file_info['size']):>10} - {file_info['path']}\n"

        # Додаємо останні файли
        report += f"\n📅 ОСТАННІ 20 ЗМІНЕНИХ ФАЙЛІВ:\n{'=' * 30}\n"
        for i, file_info in enumerate(stats['recent_files'][:20], 1):
            date_str = file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')
            report += f"{i:2d}. {date_str} - {file_info['path']}\n"

        return report


if __name__ == "__main__":
    config = TreeConfig()
    app = EnhancedApp(config)
    app.mainloop()