import os
import tempfile
import threading
import numpy as np

import sounddevice as sd
import soundfile as sf

import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ІМПОРТИ З ТВOЄЇ ПРОГРАМИ
from Uni_prog import (
    AppConfig,
    WhisperModelManager,
    TTSService
)

# ========= ІНІЦІАЛІЗАЦІЯ =========

BOT_TOKEN = "7018949729:AAHmKmZ2fS28L_Az6kpcryMLUPiCXvqpg6c"

config = AppConfig()

whisper_manager = WhisperModelManager(
    config.get_expanded_path('app.models_dir')
)

tts_service = TTSService(config)

print("⏳ Завантажую Whisper модель...")
whisper_model = whisper_manager.load_model(
    model_size=config.get('stt.model_size', 'large-v3'),
    device="cuda" if config.get('app.use_cuda') else "cpu"
)
print("✅ Whisper готовий")

# ========= STT =========

def transcribe_audio(file_path: str) -> str:
    segments, _ = whisper_model.transcribe(
        file_path,
        beam_size=config.get('stt.beam_size', 5),
        language=config.get('stt.language', 'uk'),
        vad_filter=True
    )
    return " ".join(segment.text for segment in segments)

# ========= HANDLERS =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎤 Надішли voice — отримаєш текст\n"
        "📝 Надішли текст — отримаєш голос"
    )

def play_wav(path: str):
    data, samplerate = sf.read(path, dtype="float32")
    sd.play(data, samplerate)
    sd.wait()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text("🔊 Генерую голос...")

    wav_path = await asyncio.to_thread(
        tts_service.synthesize_to_wav,
        text,
        "uk"
    )

    with open(wav_path, "rb") as audio:
        await update.message.reply_audio(
            audio=audio,
            title="TTS"
        )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as f:
        file = await context.bot.get_file(voice.file_id)
        await file.download_to_drive(f.name)
        audio_path = f.name

    await update.message.reply_text("⏳ Розпізнаю...")

    loop = asyncio.get_running_loop()

    def stt_job(loop):
        try:
            text = transcribe_audio(audio_path)
            asyncio.run_coroutine_threadsafe(
                update.message.reply_text(f"📝 {text}"),
                loop
            )
        finally:
            os.unlink(audio_path)

    threading.Thread(
        target=stt_job,
        args=(loop,),
        daemon=True
    ).start()


# ========= MAIN =========

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("🤖 Telegram бот запущений")
    app.run_polling()

if __name__ == "__main__":
    main()
