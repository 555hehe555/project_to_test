import tkinter as tk
from tkinter import ttk, messagebox
from PIL import ImageGrab, ImageTk, Image
import pytesseract
import pyperclip
import threading
import keyboard
import time
from translatepy import Translator

pytesseract.pytesseract.tesseract_cmd = r"D:\\Games\\tesseract_ocr\\tesseract.exe"

LANG_OPTIONS = {
    "Українська": "ukr",
    "Англійська": "eng",
    "Українська + Англійська": "ukr+eng"
}


class ScreenOCR:
    def __init__(self):
        self.start_x = self.start_y = self.end_x = self.end_y = 0
        self.rect_id = None
        self.overlay = None
        self.running = False
        self.overlay_window = None

        self.root = tk.Tk()
        self.root.withdraw()
        threading.Thread(target=self.listen_for_hotkey, daemon=True).start()
        self.root.mainloop()

    def listen_for_hotkey(self):
        while True:
            if keyboard.is_pressed('ctrl+shift+z'):
                if not self.running:
                    self.running = True
                    self.toggle_overlay()
                    self.running = False
            time.sleep(0.1)

    def toggle_overlay(self):
        if self.overlay_window is None:
            self.overlay_window = tk.Toplevel()
            self.overlay_window.attributes("-fullscreen", True)
            self.overlay_window.attributes("-alpha", 0.3)
            self.overlay_window.attributes("-topmost", True)
            self.overlay_window.configure(bg="black")

            self.canvas = tk.Canvas(self.overlay_window, cursor="cross", highlightthickness=0, bd=0, bg="black")
            self.canvas.pack(fill=tk.BOTH, expand=True)
            self.canvas.bind("<ButtonPress-1>", self.on_start)
            self.canvas.bind("<B1-Motion>", self.on_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_release)

            # Додавання Escape для закриття вікна
            self.overlay_window.bind("<Escape>", self.on_escape)
        else:
            self.overlay_window.deiconify()

    def on_escape(self, event):
        """Функція для закриття вікна при натисканні Escape"""
        self.overlay_window.withdraw()

    def on_start(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=3, fill=""
        )

    def on_drag(self, event):
        cur_x, cur_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        self.end_x, self.end_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.overlay_window.withdraw()
        self.process_selection()

    def process_selection(self):
        x1, y1 = int(min(self.start_x, self.end_x)), int(min(self.start_y, self.end_y))
        x2, y2 = int(max(self.start_x, self.end_x)), int(max(self.start_y, self.end_y))
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        OCRWindow(img, self)


class OCRWindow:
    def __init__(self, image, screen_ocr):
        self.image = image
        self.screen_ocr = screen_ocr
        self.root = tk.Toplevel()
        self.root.title("Розпізнавання тексту + Переклад")

        self.language_var = tk.StringVar(value="Українська + Англійська")

        main_frame = ttk.Frame(self.root)
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Ліва частина: OCR
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lang_label = ttk.Label(left_frame, text="Мова розпізнавання:")
        lang_label.pack(anchor="w")

        lang_combo = ttk.Combobox(left_frame, textvariable=self.language_var,
                                  values=list(LANG_OPTIONS.keys()), state="readonly")
        lang_combo.pack(fill="x")
        lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        self.text = tk.Text(left_frame, wrap="word", height=15)
        self.text.pack(fill="both", expand=True, pady=5)

        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill="x")

        copy_btn = ttk.Button(button_frame, text="📋 Копіювати", command=self.copy_text)
        copy_btn.pack(side="left")

        rerun_btn = ttk.Button(button_frame, text="🔁 Повторити розпізнавання", command=self.rerun_ocr)
        rerun_btn.pack(side="right")

        # Права частина: Перекладач
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        self.translate_direction = tk.StringVar(value="Англійська → Українська")
        direction_combo = ttk.Combobox(
            right_frame, textvariable=self.translate_direction,
            values=["Англійська → Українська", "Українська → Англійська"],
            state="readonly"
        )
        direction_combo.pack(fill="x")

        self.input_translate = tk.Text(right_frame, height=5, wrap="word")
        self.input_translate.pack(fill="both", expand=True, pady=(5, 2))

        translate_btn = ttk.Button(right_frame, text="🌐 Перекласти", command=self.translate_text)
        translate_btn.pack(pady=2)

        self.output_translate = tk.Text(right_frame, height=5, wrap="word", state="disabled")
        self.output_translate.pack(fill="both", expand=True, pady=(2, 5))

        copy_tr_btn = ttk.Button(right_frame, text="📋 Скопіювати переклад", command=self.copy_translation)
        copy_tr_btn.pack()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.run_ocr()

    def on_close(self):
        self.root.withdraw()

    def rerun_ocr(self):
        self.on_close()
        self.screen_ocr.toggle_overlay()

    def run_ocr(self):
        lang_code = LANG_OPTIONS[self.language_var.get()]
        threading.Thread(target=self._ocr_thread, args=(lang_code,), daemon=True).start()

    def _ocr_thread(self, lang):
        text = pytesseract.image_to_string(self.image, lang=lang)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)

    def copy_text(self):
        content = self.text.get("1.0", "end").strip()
        pyperclip.copy(content)
        messagebox.showinfo("Готово", "Текст скопійовано!")

    def copy_translation(self):
        content = self.output_translate.get("1.0", "end").strip()
        if content:
            pyperclip.copy(content)
            messagebox.showinfo("Готово", "Переклад скопійовано!")

    def on_language_change(self, event):
        self.run_ocr()

    def translate_text(self):
        direction = self.translate_direction.get()
        text_to_translate = self.input_translate.get("1.0", "end").strip()

        if not text_to_translate:
            messagebox.showwarning("Порожнє поле", "Введіть текст для перекладу.")
            return

        direction = self.translate_direction.get()
        if direction == "Англійська → Українська":
            src, dest = "en", "uk"
        else:
            src, dest = "uk", "en"

        try:
            translator = Translator()
            result = translator.translate(text_to_translate, destination_language=dest)
            self.output_translate.config(state="normal")
            self.output_translate.delete("1.0", "end")
            self.output_translate.insert("1.0", result.result)
            self.output_translate.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Помилка перекладу", str(e))



if __name__ == "__main__":
    screen_ocr = ScreenOCR()
