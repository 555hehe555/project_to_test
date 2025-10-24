import re
import os, sys, time
import lmstudio as lms
from colorama import Fore, Style

SYSTEM_PROMPT = ("говори україньською мовою ")
                 # "ти маєш доступ до power shell і ти можеш виконувати команди, пиши завжди команди в тегах <cmd></cmd> "
                 # "ти маєш запитувати користувача при необхібності, наприклад при виконувані серйозних команд, та коли сам не знаєш як вирішити якусь дію "
                 # "використовуй в кінці відповіді теги <end>, <complete>, <neet_help>, <done> для позначення стану виконання завдання "
                 # "якщо ти бачиш помилку при виконанні команди, ти маєш її проаналізувати та спробувати виправити, при трьох невдалих спробах, ти маєш запитати користувача що робити далі і написати <need_help> "
                 # "якщо ти не можеш виконати завдання або отримуєш помилку яку не можеш вирішити, поясни що ти зробив та що не вдалося пиши <need_help> в кінці відповіді ")

MODEL = lms.llm("deepseek/deepseek-r1-0528-qwen3-8b")
BaseChat = lms.Chat(SYSTEM_PROMPT)


def model(prompt, chat=BaseChat):
    chat.add_user_message(prompt)
    response = MODEL.respond(chat)
    text = response.content

    # вирізаємо все до закриття тегу </think>, якщо він є
    if "</think>" in text:
        text = text.split("</think>", 1)[1]

    return text.strip()



while True:
    promt = input(Fore.GREEN + "You: " + Style.RESET_ALL)
    response = model(promt)
    print(Fore.YELLOW + f"AI: {response}" + Style.RESET_ALL, end="")