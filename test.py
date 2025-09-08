import os
import subprocess

input_dir = r"C:\Users\Asus\Desktop\my_music"
output_dir = r"C:\Users\Asus\Desktop\out"
os.makedirs(output_dir, exist_ok=True)

# тут ти заповниш відповідності
rename_map = {
    "Aloboi Dies Irae (Just Raw).mp3": "aloboi - Dies Irae.mp3",
    "Aloboi Give Me More (Just Rawer).mp3": "aloboi - Give Me More.mp3",
    "Aloboi It's Ok (Just Raw).mp3": "aloboi - It's Ok.mp3",
    "aloboi Locrian Dominant.mp3": "aloboi - Locrian Dominant.mp3",
    "Aloboi Paranoid (Just Raw Instrumental) (1).mp3": "aloboi - Paranoid.mp3",
    "Aloboi_All_Raw_Tracks.mp3": "aloboi - All Raw Tracks.mp3",
    "DBH - 1-01. Hostage.mp3": "Detroit Soundtrack - Hostage.mp3",
    "DBH - 1-02. Your Choice.mp3": "Detroit Soundtrack - Your Choice.mp3",
    "DBH - 1-03. Connor and Hank.mp3": "Detroit Soundtrack - Connor and Hank.mp3",
    "DBH - 1-04. The Interrogation.mp3": "Detroit Soundtrack - The Interrogation.mp3",
    "DBH - 1-05. Deviant.mp3": "Detroit Soundtrack - Deviant.mp3",
    "DBH - 1-06. Investigation.mp3": "Detroit Soundtrack - Investigation.mp3",
    "DBH - 1-08. As I See Them.mp3": "Detroit Soundtrack - As I See Them.mp3",
    "DBH - 1-20. Will You Trust Me.mp3": "Detroit Soundtrack - Will You Trust Me.mp3",
    "jockii druce - бути довбойобом.mp3": "Жадан і Собаки - бути довбойобом.mp3",
    "Jockii Druce Вони Все Знають.mp3": "Jockii Druce - Вони Все Знають.mp3",
    "Jockii Druce пайка стайл.mp3": "Jockii Druce - пайка стайл.mp3",
    "Malyarevsky Гей Гу, Гей Га!.mp3": "Malyarevsky - Гей Гу, Гей Га!.mp3",
    "Nik Ammar - Diskovery.mp3": "Nik Ammar - Diskovery.mp3",
    "Riffmaster - тихо прийшов, тихо пішов.mp3": "Riffmaster - тихо прийшов, тихо пішов.mp3",
    "SadSvit - Прощавай (mp3dim.com).mp3": "SadSvit - Прощавай.mp3",
    "Sadsvit Силуети.mp3": "SadSvit - Силуети.mp3",
    "sadsvit-касета(meloua.com).mp3": "SadSvit - касета.mp3",
    "sadsvit-молодість-(meloua.com).mp3": "SadSvit - молодість.mp3",
    "sadsvit-небо (meloua.com).mp3": "SadSvit - небо.mp3",
    "sadsvit-ніч (meloua.com).mp3": "SadSvit - ніч.mp3",
    "sadsvit-персонажі (meloua.com).mp3": "SadSvit - Персонажі.mp3",
    "sadsvit-полум'Я(meloua.com).mp3": "SadSvit - полумя.mp3",
    "sharax - tokyovania.mp3": "sharax - tokyovania.mp3",
    "Sonyachna - ZVIR.mp3": "Sonyachna - ZVIR.mp3",
    "Toby_Fox_-_ASGORE_64962836.mp3": "Toby Fox - ASGORE.mp3",
    "Toby_Fox_-_Battle_Against_A_True_Hero_64962864.mp3": "Toby Fox - Battle Against A True Hero.mp3",
    "Toby_Fox_-_Dating_Tense_64962769.mp3": "Toby Fox - Dating Tense.mp3",
    "Toby_Fox_-_Ghouliday_64962787.mp3": "Toby Fox - Ghouliday.mp3",
    "Toby_Fox_-_Hopes_And_Dreams_64962849.mp3": "Toby Fox - Hopes And Dreams.mp3",
    "Toby_Fox_-_Last_Goodbye_64962860.mp3": "Toby Fox - Last Goodbye.mp3",
    "Toby_Fox_-_Oh_My_64962821.mp3": "Toby Fox - Oh My.mp3",
    "Toby_Fox_-_Run_64962777.mp3": "Toby Fox - Run.mp3",
    "Toby_Fox_-_SAVE_The_World_64962851.mp3": "Toby Fox - SAVE The World.mp3",
    "Toby_Fox_-_Spear_of_Justice_64962793.mp3": "Toby Fox - Spear of Justice.mp3",
    "Toby_Fox_-_Uwa_So_Holiday_64962759.mp3": "Toby Fox - Uwa So Holiday.mp3",
    "Toby_Fox_-_Your_Best_Nightmare_64962838.mp3": "Toby Fox - Your Best Nightmare.mp3",
    "Анастимоза - проси пробачення.mp3": "Анастимоза - Проси пробачення.mp3",
    "Власне Виробницьтво - марічка.mp3": "Власне Виробницьтво - марічка.mp3",
    "віктор винник я з України.mp3": "Віктор Винник - Я з України.mp3",
    "Жадан і Собаки - .mp3": "Жадан і Собаки - Антидепресанти.mp3",
    "Жадан і Собаки - автозак.mp3": "Жадан і Собаки - Автозак.mp3",
    "Жадан і Собаки - бухло.mp3": "Жадан і Собаки - Бухло.mp3",
    "Жадан і Собаки - Виживи.mp3": "Жадан і Собаки - Виживи.mp3",
    "Жадан і Собаки - Забухав.mp3": "Жадан і Собаки - Забухав.mp3",
    "Жадан і Собаки - Закладчик.mp3": "Жадан і Собаки - Закладчик.mp3",
    "Жадан і Собаки - Кобзон.mp3": "Жадан і Собаки - Кобзон.mp3",
    "Жадан і Собаки - Мадонна.mp3": "Жадан і Собаки - Мадонна.mp3",
    "Жадан і Собаки - Натаха.mp3": "Жадан і Собаки - Натаха.mp3",
    "Жадан і Собаки - Переваги.mp3": "Жадан і Собаки - Переваги.mp3",
    "Жадан і Собаки - Перекличка.mp3": "Жадан і Собаки - Перекличка.mp3",
    "Жадан і Собаки - Радіо «Промінь».mp3": "Жадан і Собаки - Радіо Промінь.mp3",
    "Жадан і Собаки - Троєщина.mp3": "Жадан і Собаки - Троєщина.mp3",
    "Жадан і Собаки - Чужий.mp3": "Жадан і Собаки - Чужий.mp3",
    "Жадан і Собаки – Мальви (Офіційне відео) - Жадан і Собаки.mp3": "Жадан і Собаки - Мальви.mp3",
    "льоха.mp3": "Україньська воєна - льоха.mp3",
    "Ляпис Трубецкой - Воїни Світла.mp3": "Ляпис Трубецкой - Воїни Світла.mp3",
    "Марш нової армії.mp3": "Україньська воєна - Марш нової армії.mp3",
    "МУР - Приходь у KТM!.mp3": "МУР - Приходь у KТM!.mp3",
    "Нежеголь - Украина.mp3": "Нежеголь - Украина.mp3",
    "Скрябiн - Герой.mp3": "Скрябін - Герой.mp3",
    "скрябін не треба.mp3": "Скрябін - не треба.mp3",
    "СТРУКТУРА ЩАСТЯ - Ліпший день.mp3": "СТРУКТУРА ЩАСТЯ - Ліпший день.mp3",
    "СТРУКТУРА ЩАСТЯ - Сидативи (mp3dim.com).mp3": "СТРУКТУРА ЩАСТЯ - Сидативи.mp3",
    "СТРУКТУРА ЩАСТЯ - СУМ  ГНВ (mp3dim.com).mp3": "СТРУКТУРА ЩАСТЯ - СУМ ГНВ.mp3",
    "хейтспіч - це не сильно радикально (відео) - хейтспіч.mp3": "ХейтСпіч - це не сильно радикально.mp3",
    "ХейтСпіч - Я вб'ю всіх богів.mp3": "ХейтСпіч - Я вб'ю всіх богів.mp3",
    "чорними хмарами.mp3": "Україньська воєна - чорними хмарами.mp3",
}

def ensure_mp3(src, dst):
    # все проганяємо через ffmpeg, щоб був справжній mp3
    subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-codec:a", "libmp3lame", "-q:a", "2", dst
    ], check=True)

for fname in os.listdir(input_dir):
    src = os.path.join(input_dir, fname)
    if not os.path.isfile(src):
        continue

    # нова назва або залишаємо ту ж саму
    new_name = rename_map.get(fname, fname)
    dst = os.path.join(output_dir, new_name)

    try:
        ensure_mp3(src, dst)
        print(f"✔ {fname} → {new_name}")
    except Exception as e:
        print(f"✖ {fname}: {e}")
