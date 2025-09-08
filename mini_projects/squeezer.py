import tkinter as tk
import sys
from tkinter import messagebox, scrolledtext

sys.set_int_max_str_digits(0)


# Повний список символів
def generate_full_charlist():
    char_list = []

    # Латиниця (базові літери + розширення)
    char_list += [chr(i) for i in range(ord('A'), ord('Z') + 1)]
    char_list += [chr(i) for i in range(ord('a'), ord('z') + 1)]
    char_list += list("áéíóúñüøçßðþæåäöâêîôûàèìòùãõ")

    # Кирилиця (основні літери + специфічні)
    char_list += [chr(i) for i in range(ord('А'), ord('я') + 1)]
    char_list += list("ёЁіІїЇєЄґҐ")

    # Цифри та системи числення
    char_list += [str(i) for i in range(10)]
    char_list += list("²³¹¼½¾⅓⅔⅛⅜⅝")

    # Пунктуація та розділові знаки
    char_list += list(" .,!?;:-–—…_+=*/\\|@#$%^&()[]{}<>«»„“”‘’'\"`~")

    # Математичні символи
    char_list += list("±×÷≈≠≡≤≥∞√∫∂∆∑∏∈∉∩∪∅∁∀∃∄∴∵")

    # Валюти
    char_list += list("₴$€£¥₽¢₤₦₨৲৳௹﷼")

    # Стрілки та маркери
    char_list += list("←↑→↓↔↕↨⇐⇑⇒⇓⇔⇴↻↺↯↶↷✓✔✕✗✘☑☒☐●○◯◉◎◌◍◦▪▫▭▮▯")

    # Технічні символи
    char_list += list("⌂⌘⌥⌃⇧⌨⌫⌦⌧⌚⏰⏳⌛⌨️🖱️💻📱📦🛠️⚙️🔧")

    # Емодзі та піктограми
    char_list += list("""😀😃😄😁😆😅🤣😂🙂🙃😉😊😇🥰😍🤩😘😗☺️😚😙😋😛😜🤪😝🤑🤗🤭🤫🤔🤐🤨😐😑😶😶‍🌫️😏😒🙄😬😮‍💨🤥🫨🙂‍↔️🙂‍↕️😌😔😪🤤😴😷🤒🤕🤢🤮🤧🥵🥶🥴😵😵‍💫🤯🤠🥳🥸😎🤓🧐😕🫤😟🙁☹️😮😯😲😳🥺🥹😦😧😨😰😥😢😭😱😖😣😞😓😩😫🥱😤😡😠🤬😈👿💀☠️💩🤡👹👺👻👽👾🤖😺😸😹😻😼😽🙀😿😾🙈👌🤏✌️🤞🤟🤘🤙👈👉👆🖕👇☝️👍👎✊👊🤛🤜👏🙌👐🤲🤝🙏✍️💅🤳💪👶💘💝💖💗💓💞💕💟❣️💔❤️‍🔥❤️‍🩹❤️🧡💛💚💙💜🤎🖤🤍💻👨‍💻👩‍💻🧑🌍🌎🌏🌐🗺️🗾🧭🏔️⛰️🌋🗻🏕️🏖️🏜️🏝️🏞️🔥💧
👓📱📲☎️📞📟📠🔋🪫🔌💻🖥️🖨️⌨️🖱️🖲️💽💾💿📀🧮🎥
🏧🚮🚰♿🚹🚺🚻🚼🚾🛂🛃🛄🛅🗣
☺︎☹︎☠︎❣︎❤︎☘︎⛸︎♠︎♥︎♦︎♣︎♟︎⛷︎⛰︎⛩︎♨︎⛴︎✈︎☀︎⏱︎⏲︎☁︎⛈︎☂︎⛱︎❄︎☃︎☄︎⛑︎☎︎⌨︎✏︎✒︎✉︎✂︎⛏︎⚒︎⚔︎⚙︎⚖︎⛓︎⚗︎⚰︎⚱︎⚠︎☢︎☣︎⬆︎↗︎➡︎↘︎⬇︎↙︎⬅︎↖︎↕︎↔︎↩︎↪︎⤴︎⤵︎⚛︎✡︎☸︎☯︎✝︎☦︎☪︎☮︎▶︎⏭︎⏯︎◀︎⏮︎⏸︎⏹︎⏺︎⏏︎♀︎♂︎⚧︎✖︎♾︎‼︎⁉︎⚕︎♻︎⚜︎☑︎✔︎〽︎✳︎✴︎❇︎©︎®︎™︎🅰︎🅱︎ℹ︎Ⓜ︎🅾︎🅿︎🈂︎🈷︎㊗︎㊙︎◼︎◻︎▪︎▫︎""")

    # Спеціальні символи
    char_list += list("¶§©®™°µ№℗℠℡☎☏✆✉☢☣☮☯⚕⚖⚔✈☠☄❄⛄♨")

    # Додаткові символи (заповнення до 1000)
    # Брайль (U+2800-U+28FF)
    char_list += [chr(0x2800 + i) for i in range(256)]
    # Геометричні фігури (U+25A0-U+25FF)
    char_list += [chr(0x25A0 + i) for i in range(96)]
    # Додаткові ідеограми (U+1F300-U+1F5FF)
    char_list += [chr(0x1F300 + i) for i in range(768) if len(char_list) < 1000]

    # Видалення дублікатів зі збереженням порядку
    unique_chars = []
    seen = set()
    for char in char_list:
        if char not in seen and len(unique_chars) < 1000:
            seen.add(char)
            unique_chars.append(char)

    return unique_chars


list_of_chars = generate_full_charlist()
print(list_of_chars)


# Стиснення з пропуском невідомих символів
def squeeze_v2(in_data):
    if not isinstance(in_data, str):
        in_data = str(in_data)
    out_data = "999"
    for char in in_data:
        try:
            index = list_of_chars.index(char)
            out_data += f"{index:03d}"
        except ValueError:
            # Пропустити символ, якого немає в списку
            continue
    return int(out_data) if out_data != "999" else 0


# Розпакування з очищенням вводу і обробкою сміття
def desqueeze_v2(in_number):
    try:
        in_data = str(in_number)
        # Прибрати всі нечислові символи
        in_data = ''.join(filter(str.isdigit, in_data))
        if not in_data.startswith("999"):
            raise ValueError("Дані не містять правильний заголовок '999'")
        in_data = in_data[3:]
        out_data = ""
        for i in range(0, len(in_data), 3):
            part = in_data[i:i + 3]
            if len(part) != 3:
                continue  # пропустити неповний блок
            index = int(part)
            if 0 <= index < len(list_of_chars):
                out_data += list_of_chars[index]
            else:
                continue  # пропустити некоректний індекс
        return out_data
    except Exception as e:
        raise ValueError("Помилка при розшифруванні: " + str(e))



# GUI
def build_gui():
    window = tk.Tk()
    window.title("🔐 MiniCoder v2 (squeeze / encode)")
    window.geometry("400x450")
    window.configure(bg="#f0f0f0")

    # ===== Текстове поле вводу =====
    tk.Label(window, text="не стиснутий", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(pady=(10, 2))
    input_text = scrolledtext.ScrolledText(window, height=6, font=("Consolas", 12))
    input_text.pack(fill="x", padx=20)

    # ===== Поле для введення послідовності V2-2-2... =====
    tk.Label(window, text="скільки раз зжати/розжати:", bg="#f0f0f0").pack()
    seq_entry = tk.Entry(window)
    seq_entry.insert(0, "1")
    seq_entry.pack(pady=5)

    # ===== Поле результату =====
    tk.Label(window, text="стиснутий", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(pady=(10, 2))
    result_text = scrolledtext.ScrolledText(window, height=8, font=("Consolas", 12))
    result_text.pack(fill="x", padx=20)

    # ===== Функції кнопок =====
    def compress_action():
        text = input_text.get("1.0", tk.END).strip()
        try:
            sequence = int(seq_entry.get())
        except:
            messagebox.showerror("Введіть число")

        try:
            result = text
            for step in range(sequence):
                result = squeeze_v2(result)
            result_text.delete("1.0", tk.END)
            result_text.insert(tk.END, str(result))
        except Exception as e:
            messagebox.showerror("❌ Помилка", str(e))

    def decompress_action():
        text = result_text.get("1.0", tk.END).strip()
        try:
            sequence = int(seq_entry.get())
        except:
            messagebox.showerror("Введіть число")

        try:
            result = text
            for step in range(sequence):
                result = desqueeze_v2(result)
            input_text.delete("1.0", tk.END)
            input_text.insert(tk.END, result)
        except Exception as e:
            messagebox.showerror("❌ Помилка", str(e))

    # ===== Кнопки =====
    btn_frame = tk.Frame(window, bg="#f0f0f0")
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text="🔒 Стиснути", command=compress_action, width=20).pack(side="left", padx=10)
    tk.Button(btn_frame, text="🔓 Розпакувати", command=decompress_action, width=20).pack(side="left", padx=10)

    # ===== Запуск =====
    window.mainloop()


# 🏁 Старт GUI
if __name__ == "__main__":
    build_gui()
