import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

WINDOW_WIDTH = 500
WINDOW_HEIGHT = 500

def to_pixel_art(img, pixel_size=16, num_colors=16):
    # Обчислюємо новий розмір для стискання
    new_width = max(1, img.width // pixel_size)
    new_height = max(1, img.height // pixel_size)

    # Стискаємо зображення
    pixel_art = img.resize((new_width, new_height), resample=Image.Resampling.BOX)

    # Квантизація кольорів
    pixel_art = pixel_art.convert('P', palette=Image.ADAPTIVE, colors=num_colors)
    return pixel_art


def resize_for_display(img):
    # Масштабуємо для GUI, зберігаючи пропорції
    w_ratio = WINDOW_WIDTH / img.width
    h_ratio = WINDOW_HEIGHT / img.height
    ratio = min(w_ratio, h_ratio)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    return img.resize(new_size, Image.Resampling.LANCZOS)

def open_image():
    global original_img, displayed_img
    path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
    if path:
        original_img = Image.open(path)
        img_for_display = resize_for_display(original_img)
        update_preview(img_for_display)

def update_preview(img):
    global displayed_img
    displayed_img = ImageTk.PhotoImage(img)
    preview_label.config(image=displayed_img)

def apply_pixel_art():
    if original_img:
        try:
            pixel_size = max(1, int(pixel_size_entry.get()))
            num_colors = min(256, max(1, int(num_colors_entry.get())))  # обмежуємо від 1 до 256
        except ValueError:
            print("Помилка: введіть коректні числа")
            return

        pixel_img = to_pixel_art(original_img, pixel_size, num_colors)
        img_for_display = resize_for_display(pixel_img)
        update_preview(img_for_display)


def save_image():
    if original_img:
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files","*.png")])
        if path:
            pixel_img = to_pixel_art(original_img, int(pixel_size_entry.get()), int(num_colors_entry.get()))
            pixel_img.save(path)
            print(f"Збережено: {path}")

# ---- GUI ----
root = tk.Tk()
root.title("Pixel Art Converter")
root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT + 150}")
root.resizable(False, False)

open_btn = tk.Button(root, text="Відкрити зображення", command=open_image)
open_btn.pack(pady=5)

pixel_size_label = tk.Label(root, text="Розмір пікселя")
pixel_size_label.pack(pady=2)
pixel_size_entry = tk.Entry(root)
pixel_size_entry.insert(0, "16")
pixel_size_entry.pack(pady=2)

num_colors_label = tk.Label(root, text="Кількість кольорів")
num_colors_label.pack(pady=2)
num_colors_entry = tk.Entry(root)
num_colors_entry.insert(0, "16")
num_colors_entry.pack(pady=2)

apply_btn = tk.Button(root, text="Застосувати Pixel Art", command=apply_pixel_art)
apply_btn.pack(pady=5)

save_btn = tk.Button(root, text="Зберегти зображення", command=save_image)
save_btn.pack(pady=5)

preview_label = tk.Label(root)
preview_label.pack(pady=10, expand=True)

original_img = None
displayed_img = None

root.mainloop()