import sys
import base64
import hashlib
import random
import string

sys.set_int_max_str_digits(0)

# ===================== CHARLIST / SQUEEZE =====================

def generate_full_charlist():
    chars = []

    chars += [chr(i) for i in range(ord('A'), ord('Z') + 1)]
    chars += [chr(i) for i in range(ord('a'), ord('z') + 1)]
    chars += [chr(i) for i in range(ord('А'), ord('я') + 1)]
    chars += list("ёЁіІїЇєЄґҐ")
    chars += [str(i) for i in range(10)]
    chars += list(" .,!?;:-_+=*/\\|@#$%^&()[]{}<>")
    chars += list("±×÷≈≠∞√∑∈∪∅")
    chars += list("₴$€£¥₽")
    chars += list("←↑→↓↔✓✔✕✗")
    chars += ["\n", "\t"]

    unique, seen = [], set()
    for c in chars:
        if c not in seen and len(unique) < 1000:
            seen.add(c)
            unique.append(c)
    return unique


CHARLIST = generate_full_charlist()
CHAR_INDEX = {c: i for i, c in enumerate(CHARLIST)}

ALPHABETS = {
    "en_low": "abcdefghijklmnopqrstuvwxyz",
    "en_up":  "ABCDEFGHIJKLMNOPQRSTUVWXYZ",

    "ua_low": "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя",
    "ua_up":  "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ",
}


def squeeze_v2(data: str) -> int:
    out = "999"
    for c in data:
        if c in CHARLIST:
            out += f"{CHAR_INDEX[c]:03d}"
    return int(out)


def desqueeze_v2(num: str) -> str:
    s = ''.join(filter(str.isdigit, str(num)))
    if not s.startswith("999"):
        raise ValueError("Не SQUEEZE v2")
    s = s[3:]

    out = ""
    for i in range(0, len(s), 3):
        idx = int(s[i:i+3])
        if 0 <= idx < len(CHARLIST):
            out += CHARLIST[idx]
    return out


# ===================== TEXT / BINARY =====================

def text_to_binary(text: str) -> str:
    return " ".join(format(b, "08b") for b in text.encode("utf-8"))


def binary_to_text(binary: str) -> str:
    bits = binary.replace(" ", "")
    return bytes(
        int(bits[i:i+8], 2)
        for i in range(0, len(bits), 8)
    ).decode("utf-8", errors="replace")


SCHEMES = {
    "2347": [2, 3, 4, 7],
    "3301": [3, 3, 0, 1],
    "135":  [1, 3, 5],
}


def encode_binary(binary: str, pattern: list[int]) -> str:
    out, idx = [], 0
    for bit in binary.replace(" ", ""):
        d = pattern[idx]
        out.append(f"{d}-" if bit == "1" else str(d))
        idx = (idx + 1) % len(pattern)
    return "".join(out)


def decode_binary(encoded: str) -> str:
    binary, i = [], 0
    while i < len(encoded):
        if encoded[i].isdigit():
            if i + 1 < len(encoded) and encoded[i+1] == "-":
                binary.append("1")
                i += 2
            else:
                binary.append("0")
                i += 1
        else:
            i += 1
    return "".join(binary)


# ===================== CLASSIC CIPHERS =====================

def caesar_encrypt(text: str, shift: int) -> str:
    res = []

    for c in text:
        done = False
        for alpha in ALPHABETS.values():
            if c in alpha:
                i = alpha.index(c)
                res.append(alpha[(i + shift) % len(alpha)])
                done = True
                break
        if not done:
            res.append(c)

    return "".join(res)


def caesar_decrypt(text: str, shift: int) -> str:
    return caesar_encrypt(text, -shift)


def rot13(text: str) -> str:
    res = []

    for c in text:
        if c in ALPHABETS["en_low"]:
            res.append(ALPHABETS["en_low"][(ALPHABETS["en_low"].index(c) + 13) % 26])
        elif c in ALPHABETS["en_up"]:
            res.append(ALPHABETS["en_up"][(ALPHABETS["en_up"].index(c) + 13) % 26])
        else:
            res.append(c)

    return "".join(res)

def rot17_ua(text: str) -> str:
    res = []

    UA_LOW = (
        "абвгґдеєжз"
        "и"
        "і"
        "ї"
        "й"
        "клмнопрстуфх"
        "цчшщ"
        "ь"
        "ю"
        "я"
        "0"
    )

    UA_UP = (
        "АБВГҐДЕЄЖЗ"
        "И"
        "І"
        "Ї"
        "Й"
        "КЛМНОПРСТУФХ"
        "ЦЧШЩ"
        "Ь"
        "Ю"
        "Я"
        "0"
    )

    L = len(UA_LOW)  # = 34

    for c in text:
        if c in UA_LOW:
            res.append(UA_LOW[(UA_LOW.index(c) + 17) % L])
        elif c in UA_UP:
            res.append(UA_UP[(UA_UP.index(c) + 17) % L])
        else:
            res.append(c)

    return "".join(res)





def atbash(text: str) -> str:
    res = []

    for c in text:
        done = False
        for alpha in ALPHABETS.values():
            if c in alpha:
                res.append(alpha[::-1][alpha.index(c)])
                done = True
                break
        if not done:
            res.append(c)

    return "".join(res)



def vigenere_encrypt(text: str, key: str) -> str:
    res = []
    k = 0

    for c in text:
        done = False
        for alpha in ALPHABETS.values():
            if c in alpha:
                key_c = key[k % len(key)]
                if key_c not in alpha:
                    res.append(c)
                else:
                    shift = alpha.index(key_c)
                    res.append(alpha[(alpha.index(c) + shift) % len(alpha)])
                    k += 1
                done = True
                break
        if not done:
            res.append(c)

    return "".join(res)


def vigenere_decrypt(text: str, key: str) -> str:
    res = []
    k = 0

    for c in text:
        done = False
        for alpha in ALPHABETS.values():
            if c in alpha:
                key_c = key[k % len(key)]
                if key_c not in alpha:
                    res.append(c)
                else:
                    shift = alpha.index(key_c)
                    res.append(alpha[(alpha.index(c) - shift) % len(alpha)])
                    k += 1
                done = True
                break
        if not done:
            res.append(c)

    return "".join(res)


def xor_cipher(text: str, key: int) -> str:
    return "".join(chr(ord(c) ^ key) for c in text)


# ===================== ONE-WAY / FUN =====================

def hash_md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def hash_sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fake_encrypt(text: str) -> str:
    return base64.b64encode(hash_sha256(text).encode()).decode()[:64]


def random_id(length=32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


# ===================== MENUS =====================

def menu_main():
    print("""
========= CRYPTO TOOL =========
1. Шифрування
2. Розшифрування
3. One-way / fun
0. Вийти
===============================
""")


def menu_encrypt():
    print("""
--- ШИФРУВАННЯ ---
1. Text → Binary
2. Binary scheme
3. Caesar
4. ROT13
5. ROT17_UA
6. Atbash
7. Vigenere
8. XOR
9. SQUEEZE v2
10. Base64
0. Назад
""")


def menu_decrypt():
    print("""
--- РОЗШИФРУВАННЯ ---
1. Binary → Text
2. Binary scheme decode
3. Caesar
4. ROT13
5. ROT17_UA
6. Atbash
7. Vigenere
8. XOR
9. SQUEEZE v2
10. Base64
0. Назад
""")


def menu_oneway():
    print("""
--- ONE-WAY / FUN ---
1. MD5
2. SHA256
3. Fake encrypt (no decrypt)
4. Random ID
0. Назад
""")


def choose_scheme():
    print("Схеми:", ", ".join(SCHEMES.keys()))
    return SCHEMES.get(input("Обери: "))


# ===================== MAIN =====================

def main():
    while True:
        menu_main()
        m = input(">>> ")

        if m == "0":
            break

        if m == "1":
            while True:
                menu_encrypt()
                c = input(">>> ")

                if c == "0":
                    break
                elif c == "1":
                    print(text_to_binary(input("Текст: ")))
                elif c == "2":
                    text = input("Текст: ")
                    scheme = choose_scheme()
                    if scheme:
                        print(encode_binary(text_to_binary(text), scheme))
                elif c == "3":
                    print(caesar_encrypt(input("Текст: "), int(input("Зсув: "))))
                elif c == "4":
                    print(rot13(input("Текст: ")))
                elif c == "5":
                    print(rot17_ua(input("Текст: ")))
                elif c == "6":
                    print(atbash(input("Текст: ")))
                elif c == "7":
                    print(vigenere_encrypt(input("Текст: "), input("Ключ: ")))
                elif c == "8":
                    print(xor_cipher(input("Текст: "), int(input("Ключ 0-255: "))))
                elif c == "9":
                    print(squeeze_v2(input("Текст: ")))
                elif c == "10":
                    print(base64.b64encode(input("Текст: ").encode()).decode())

        elif m == "2":
            while True:
                menu_decrypt()
                c = input(">>> ")

                if c == "0":
                    break
                elif c == "1":
                    print(binary_to_text(input("Binary: ")))
                elif c == "2":
                    print(binary_to_text(decode_binary(input("Encoded: "))))
                elif c == "3":
                    print(caesar_decrypt(input("Текст: "), int(input("Зсув: "))))
                elif c == "4":
                    print(rot13(input("Текст: ")))
                elif c == "5":
                    print(rot17_ua(input("Текст: ")))
                elif c == "6":
                    print(atbash(input("Текст: ")))
                elif c == "7":
                    print(vigenere_decrypt(input("Текст: "), input("Ключ: ")))
                elif c == "8":
                    print(xor_cipher(input("Текст: "), int(input("Ключ 0-255: "))))
                elif c == "9":
                    print(desqueeze_v2(input("Число: ")))
                elif c == "10":
                    print(base64.b64decode(input("Base64: ").encode()).decode(errors="replace"))

        elif m == "3":
            while True:
                menu_oneway()
                c = input(">>> ")

                if c == "0":
                    break
                elif c == "1":
                    print(hash_md5(input("Текст: ")))
                elif c == "2":
                    print(hash_sha256(input("Текст: ")))
                elif c == "3":
                    print(fake_encrypt(input("Текст: ")))
                elif c == "4":
                    print(random_id())


if __name__ == "__main__":
    main()
