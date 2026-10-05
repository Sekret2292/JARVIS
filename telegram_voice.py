"""
JARVIS Telegram Voice — приём и отправка голосовых.
Использует: Whisper (STT) + Piper (TTS).
"""

import os
import sys
import time
import tempfile
import subprocess
import logging
from pathlib import Path

sys.path.insert(0, r"D:\JARVIS")

from faster_whisper import WhisperModel
from pydub import AudioSegment

# ============ CONFIG ============
PIPER_MODEL = r"D:\JARVIS_DATA\voices\ru_RU-dmitri-medium.onnx"
WHISPER_MODEL = "large-v3"
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE = "float16"
WHISPER_LANGUAGE = "ru"
SAMPLE_RATE = 48000  # для OGG голосовых Telegram

LOG_DIR = Path(r"D:\JARVIS\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("voice")

# Инициализация Whisper
logger.info("Загрузка Whisper...")
whisper = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
logger.info("Whisper готов.")


def ogg_to_wav(ogg_path):
    """Конвертирует OGG в WAV 16000 Hz."""
    try:
        audio = AudioSegment.from_ogg(ogg_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        wav_path = ogg_path.replace(".ogg", ".wav")
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        logger.error(f"OGG->WAV ошибка: {e}")
        return None


def transcribe(wav_path):
    """Распознаёт речь через Whisper."""
    try:
        segments, _ = whisper.transcribe(
            wav_path,
            language=WHISPER_LANGUAGE,
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
                threshold=0.5,
            ),
            condition_on_previous_text=False,
            initial_prompt=(
                "Джарвис, заметки, файл, папка, открой, создай, покажи, "
                "погода, курс, время, гугл, ютуб, википедия, кострома, москва"
            ),
        )
        return "".join(seg.text for seg in segments).strip()
    except Exception as e:
        logger.error(f"Whisper ошибка: {e}")
        return ""


def tts_to_ogg(text):
    """Генерирует OGG-голосовое из текста через Piper."""
    try:
        # Piper → WAV
        wav_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
        cmd = [
            sys.executable, "-m", "piper",
            "-m", PIPER_MODEL,
            "-f", wav_out,
            "--",
            text[:500],  # Ограничение на длину
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        
        # WAV → OGG (Opus) для Telegram
        ogg_out = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg").name
        
        # Конвертация через ffmpeg для максимального качества
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", wav_out,
            "-c:a", "libopus",
            "-b:a", "48k",
            "-ar", "48000",
            "-ac", "1",
            ogg_out
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=60)
        except (FileNotFoundError, subprocess.CalledProcessError):
            # Fallback через pydub
            audio = AudioSegment.from_wav(wav_out)
            audio = audio.set_frame_rate(48000).set_channels(1)
            audio.export(ogg_out, format="ogg", codec="libopus", bitrate="48k")
        
        # Чистим WAV
        try:
            os.unlink(wav_out)
        except OSError:
            pass
        
        return ogg_out if os.path.exists(ogg_out) else None
    except Exception as e:
        logger.error(f"TTS ошибка: {e}")
        return None


def process_voice_message(ogg_path, brain):
    """Полный цикл: OGG → текст → ответ → OGG."""
    result = {
        "recognized": "",
        "reply": "",
        "reply_ogg": None,
    }
    
    # 1. OGG → WAV
    wav_path = ogg_to_wav(ogg_path)
    if not wav_path:
        return result
    
    # 2. Распознавание
    text = transcribe(wav_path)
    try:
        os.unlink(wav_path)
    except OSError:
        pass
    
    if not text:
        return result
    
    result["recognized"] = text
    logger.info(f"Распознано: {text}")
    
    # 3. Ответ от brain
    reply = brain.ask(text)
    result["reply"] = reply
    logger.info(f"Ответ: {reply[:100]}")
    
    if not reply:
        return result
    
    # 4. TTS — генерируем OGG
    reply_ogg = tts_to_ogg(reply)
    result["reply_ogg"] = reply_ogg
    
    return result