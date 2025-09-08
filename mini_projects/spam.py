import asyncio
import keyboard as kb
import winsound

# ──────────────── ГОЛОВНІ ЗМІННІ ──────────────── #
SPAM_TEXT = "test text"  # Що писати
SPAM_DELAY = 0.05  # Затримка між повідомленнями (секунди)
ENABLE_BEEPS = True  # True = з біпами, False = без них

BEEP_SHORT = (2000, 5)  # Частота, тривалість (мс) перед кожним повідомленням
BEEP_START = (2000, 1000)  # Початковий біп
BEEP_READY = (3000, 200)  # Після затримки
BEEP_STOP1 = (1000, 300)  # Кінець — 1
BEEP_STOP2 = (3000, 500)  # Кінець — 2
# ──────────────────────────────────────────────── #

stop_flag = False


async def async_beep(frequency, duration_ms):
    if ENABLE_BEEPS:
        await asyncio.to_thread(winsound.Beep, frequency, duration_ms)


async def monitor_keys():
    global stop_flag
    while not stop_flag:
        if kb.is_pressed('ctrl+shift+q'):
            print("⛔ Зупинка по Ctrl+Shift+Q")
            stop_flag = True
        await asyncio.sleep(0.1)


async def spam(text, delay):
    while not stop_flag:
        await async_beep(*BEEP_SHORT)
        kb.write(text)
        kb.send('enter')
        await asyncio.sleep(delay)

    # Завершальні біпи
    await async_beep(*BEEP_STOP1)
    await asyncio.sleep(0.3)
    await async_beep(*BEEP_STOP2)


async def main():
    print("▶️ Починаємо за 3 секунди. Натисни Ctrl+Shift+Q для зупинки.")
    await async_beep(*BEEP_START)
    await asyncio.sleep(3)
    await async_beep(*BEEP_READY)

    await asyncio.gather(
        monitor_keys(),
        spam(SPAM_TEXT, SPAM_DELAY)
    )


if __name__ == "__main__":
    asyncio.run(main())
