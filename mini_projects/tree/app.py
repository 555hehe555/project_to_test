import os
import stat
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from colorama import init, Fore, Style

init(autoreset=True)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class TreeConfig:
    def __init__(self):
        self.config = {
            'excluded_folders': [".git", "__pycache__", "venv", ".idea", "домашня"],
            'max_depth': 0,
            'show_files': True,
            'show_hidden': True,
            'file_icons': True,
            'last_path': SCRIPT_DIR,
        }


# Визначаємо SCRIPT_DIR коректно для .exe
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class App(tk.Tk):
    def __init__(self, config):
        super().__init__()
        self.title("Сканування структури папок")
        self.config_obj = config
        # Встановлюємо початковий шлях як SCRIPT_DIR
        self.path_var = tk.StringVar(value=SCRIPT_DIR)
        self.excluded_var = tk.StringVar(value=",".join(self.config_obj.config['excluded_folders']))
        self.create_widgets()

    def choose_directory(self):
        # Відкриваємо діалог з початковою папкою SCRIPT_DIR
        path = filedialog.askdirectory(initialdir=SCRIPT_DIR)
        if path:
            self.path_var.set(path)

    def create_widgets(self):
        padding = {'padx': 5, 'pady': 5}

        frame = ttk.LabelFrame(self, text="Цільова папка")
        frame.pack(fill='x', **padding)
        ttk.Entry(frame, textvariable=self.path_var, width=50).pack(side='left', fill='x', expand=True, **padding)
        ttk.Button(frame, text="Обрати...", command=self.choose_directory).pack(side='left', **padding)

        options = ttk.LabelFrame(self, text="Налаштування")
        options.pack(fill='x', **padding)

        self.depth_spin = ttk.Spinbox(options, from_=0, to=100, width=5)
        self.depth_spin.insert(0, str(self.config_obj.config['max_depth']))
        ttk.Label(options, text="Максимальна глибина (0 = без обмеження):").grid(row=0, column=0, sticky='w', **padding)
        self.depth_spin.grid(row=0, column=1, **padding)

        self.hidden_var = tk.BooleanVar(value=self.config_obj.config['show_hidden'])
        ttk.Checkbutton(options, text="Показувати приховані", variable=self.hidden_var).grid(row=1, column=0,
                                                                                             columnspan=2, sticky='w',
                                                                                             **padding)

        self.files_var = tk.BooleanVar(value=self.config_obj.config['show_files'])
        ttk.Checkbutton(options, text="Показувати файли", variable=self.files_var).grid(row=2, column=0, columnspan=2,
                                                                                        sticky='w', **padding)

        self.icons_var = tk.BooleanVar(value=self.config_obj.config['file_icons'])
        ttk.Checkbutton(options, text="Показувати іконки", variable=self.icons_var).grid(row=3, column=0, columnspan=2,
                                                                                         sticky='w', **padding)

        ttk.Label(options, text="Ігнорувати (через кому):").grid(row=4, column=0, sticky='w', **padding)
        ttk.Entry(options, textvariable=self.excluded_var, width=40).grid(row=4, column=1, sticky='w', **padding)

        ttk.Button(self, text="Сканувати", command=self.run_scan).pack(pady=10)

        self.stats_label = ttk.Label(self, text="📊 Статистика зʼявиться тут.")
        self.stats_label.pack(pady=(0, 10))

    def run_scan(self):
        path = self.path_var.get()
        if not os.path.isdir(path):
            messagebox.showerror("Помилка", "Вкажіть існуючу папку")
            return

        excluded_raw = [x.strip().lower() for x in self.excluded_var.get().split(',') if x.strip()]

        self.config_obj.config.update({
            'max_depth': int(self.depth_spin.get()),
            'show_hidden': self.hidden_var.get(),
            'show_files': self.files_var.get(),
            'file_icons': self.icons_var.get(),
            'last_path': path,
            'excluded_folders': excluded_raw,
        })

        # 1. Генеруємо дерево для ВІДОБРАЖЕННЯ і рахуємо ВІДОБРАЖЕНІ папки/файли
        # Передаємо лише об'єкт конфігурації
        output_lines, display_stats = generate_tree(path, self.config_obj)

        # 2. Розраховуємо ПОВНИЙ розмір папки окремо
        total_size = calculate_total_size(path)

        # 3. Формуємо фінальну статистику
        final_stats = {
            'folders': display_stats.get('folders', 0),  # Кількість з generate_tree
            'files': display_stats.get('files', 0),  # Кількість з generate_tree
            'size': total_size  # Повний розмір з calculate_total_size
        }

        # Виводимо дерево в консоль з розфарбуванням
        print(f"\n📂 Структура папки: {os.path.abspath(path)}")
        for line in output_lines:
            is_dir_indicator = "📁" in line or "⛔" in line or "🚫" in line
            is_file_indicator = "📄" in line
            if is_dir_indicator:
                print(colorize(line, True))
            elif is_file_indicator:
                print(colorize(line, False, line))
            else:
                print(line)

        # Оновлюємо лейбл статистики в GUI
        self.stats_label.config(
            text=f"📊 Папок (відобр.): {final_stats['folders']} | "
                 f"Файлів (відобр.): {final_stats['files']} | "
                 f"Загальний розмір: {human_readable_size(final_stats['size'])}")

        # Зберігаємо результат у файл
        output_path = os.path.join(SCRIPT_DIR, "structure.txt")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"📂 Структура папки: {os.path.abspath(path)}\n")
                f.write(f"⚙️ Глибина: {self.config_obj.config['max_depth'] or 'без обмежень'} | "
                        f"Файли: {'так' if self.config_obj.config['show_files'] else 'ні'} | "
                        f"Приховані: {'так' if self.config_obj.config['show_hidden'] else 'ні'} | "
                        f"Ігноровано для відображення: {', '.join(self.config_obj.config['excluded_folders']) or 'немає'}\n\n")
                f.write('\n'.join(output_lines))
                f.write(f"\n\n📊 Статистика:\n"
                        f"  📁 Папок (відображено): {final_stats['folders']}\n"  # Уточнення
                        f"  📄 Файлів (відображено): {final_stats['files']}\n"  # Уточнення
                        f"  💾 Загальний розмір: {human_readable_size(final_stats['size'])}\n")  # Повний розмір
            messagebox.showinfo("Готово", f"Результати збережено в:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Помилка збереження", f"Не вдалося зберегти файл:\n{e}")


def human_readable_size(size_bytes):
    if size_bytes is None or size_bytes < 0:  # Додаємо перевірку на None або негативне значення
        return "Н/Д"
    if size_bytes == 0:
        return "0 Б"
    units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024.0
        i += 1
    # Використовуємо f-string для форматування
    return f"{size_bytes:.1f} {units[i]}" if size_bytes % 1 != 0 else f"{int(size_bytes)} {units[i]}"


def colorize(item_text, is_dir, full_item_name=None):
    if is_dir:
        return Fore.BLUE + item_text + Style.RESET_ALL
    else:
        check_name = full_item_name if full_item_name else item_text
        if check_name.endswith(".py"):
            return Fore.YELLOW + item_text + Style.RESET_ALL
        else:
            return Fore.GREEN + item_text + Style.RESET_ALL


def is_hidden(filepath):
    try:
        if os.name == 'posix':
            return os.path.basename(filepath).startswith('.')
        elif os.name == 'nt':
            attrs = os.stat(filepath).st_file_attributes
            # Перевіряємо наявність атрибутів HIDDEN або SYSTEM
            return attrs & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM)
    except OSError:
        return False
    return False


# --- Функція generate_tree тепер НЕ РАХУЄ РОЗМІР ---
def generate_tree(root_path, config_obj, prefix='', depth=0, stats=None):
    """
    Генерує дерево файлів та папок для ВІДОБРАЖЕННЯ та рахує КІЛЬКІСТЬ
    відображених елементів. НЕ РАХУЄ загальний розмір.
    """
    # Ініціалізуємо статистику ЛИШЕ для кількості
    if stats is None:
        stats = {'folders': 0, 'files': 0}  # Розмір тут не рахуємо!

    if config_obj.config['max_depth'] > 0 and depth >= config_obj.config['max_depth']:
        return [], stats

    output_lines = []
    excluded_lower = config_obj.config['excluded_folders']

    try:
        entries = os.listdir(root_path)
    except OSError as e:
        error_line = prefix + f"⛔ [Помилка доступу: {e.strerror}]"
        output_lines.append(error_line)
        return output_lines, stats

    items_to_process = []
    for entry_name in entries:
        entry_path = os.path.join(root_path, entry_name)
        try:
            # Використовуємо lstat щоб не йти за символічними посиланнями для визначення типу
            entry_stat = os.lstat(entry_path)
            is_dir = stat.S_ISDIR(entry_stat.st_mode)
            is_link = stat.S_ISLNK(entry_stat.st_mode)

            # Якщо це символічне посилання на директорію, вважаємо її директорією для відображення
            # Але повний шлях нам потрібен для рекурсії
            if is_link:
                try:
                    # Спробуємо отримати реальний шлях
                    real_path = os.path.realpath(entry_path)
                    if os.path.isdir(real_path):
                        is_dir = True  # Якщо посилання вказує на директорію
                except OSError:
                    pass  # Залишаємо is_dir=False якщо посилання недійсне

            if not config_obj.config['show_hidden'] and is_hidden(
                    entry_path):  # Перевірка прихованості оригінального шляху
                continue
            if not is_dir and not config_obj.config['show_files']:
                continue

            items_to_process.append({
                'name': entry_name,
                'path': entry_path,  # Використовуємо оригінальний шлях для подальшої обробки
                'is_dir': is_dir
                # Розмір тут більше не потрібен
            })
        except OSError:
            continue

    items_to_process.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))

    count = len(items_to_process)
    for i, item in enumerate(items_to_process):
        is_last = (i == count - 1)
        connector = '└── ' if is_last else '├── '
        current_prefix = prefix + connector
        next_level_prefix = prefix + ('    ' if is_last else '│   ')

        if item['is_dir']:
            folder_name = item['name']
            folder_path = item['path']
            icon = "📁 " if config_obj.config['file_icons'] else ""
            folder_line = current_prefix + icon + folder_name
            output_lines.append(folder_line)
            stats['folders'] += 1  # Рахуємо папку (для відображення)

            if folder_name.lower() in excluded_lower:
                ignore_line = next_level_prefix + "🚫 Вміст приховано користувачем"
                output_lines.append(ignore_line)
            else:
                # Рекурсія лише для неігнорованих папок
                sub_lines, stats = generate_tree(folder_path, config_obj, next_level_prefix, depth + 1, stats)
                output_lines.extend(sub_lines)
        else:  # Це файл або посилання, яке не є директорією
            file_name = item['name']
            icon = "📄 " if config_obj.config['file_icons'] else ""
            file_line = current_prefix + icon + file_name
            output_lines.append(file_line)
            stats['files'] += 1  # Рахуємо файл (для відображення)
            # Розмір файлу тут не додаємо!

    return output_lines, stats


# --- Повертаємо окрему функцію для РОЗРАХУНКУ ПОВНОГО РОЗМІРУ ---
def calculate_total_size(root_path):
    """
    Розраховує повний розмір папки та її вмісту, рекурсивно.
    Ігнорує помилки доступу до окремих файлів.
    """
    total_size = 0
    try:
        # Використовуємо os.scandir для потенційно кращої продуктивності
        for entry in os.scandir(root_path):
            try:
                if entry.is_dir(follow_symlinks=False):
                    # Рекурсивно викликаємо для підпапок
                    total_size += calculate_total_size(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    # Додаємо розмір файлу
                    total_size += entry.stat(follow_symlinks=False).st_size
            except OSError:
                # Ігноруємо помилки доступу до окремих елементів (файли, папки)
                # Це може бути через права доступу або якщо файл зник
                # print(f"Warning: Cannot access '{entry.path}', skipping size calculation.")
                continue  # Переходимо до наступного елемента
    except OSError as e:
        # Помилка доступу до самої root_path папки
        return 0  # Повертаємо -1 або інший індикатор помилки

    return total_size


if __name__ == "__main__":
    config = TreeConfig()
    app = App(config)
    app.mainloop()
