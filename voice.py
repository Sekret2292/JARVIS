"""
JARVIS voice — TTS через Piper.
Обрезка по предложениям, чистка от логов и ошибок.
"""

import os
import sys
import re
import subprocess
import tempfile
from pathlib import Path

from config import PIPER_MODEL, LOG_FILE


def log(msg):
    timestamp = __import__("time").strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def clean_for_speech(text: str) -> str:
    """Убирает markdown, служебные строки, ошибки, мусор."""
    if not text:
        return ""

    # 1. Убираем служебные строки целиком
    lines = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s:
            continue
        # Технические логи, ошибки, команды — не озвучиваем
        if s.startswith((
            "RUN:", "FILE_READ:", "FILE_WRITE:", "FILE_APPEND:", "FILE_LIST:",
            "REMEMBER:", "FORGET:", "MEMORY_CLEAR", "WEB_SEARCH:",
            "[err]", "[ERROR", "[Brain error]", "[web_search]", "[web_fetch]",
            "[UI]", ">>", "Wait,", "Okay,", "Let's", "Hmm,", "Actually,",
            "📋", "📖", "📌", "🎒", "💡", "⏰", "🌐",
        )):
            continue
        lines.append(s)
    text = " ".join(lines)

    # 2. Убираем markdown
    text = re.sub(r"\*\*|__|##|[*`#]", "", text)

    # 3. Убираем эмодзи
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", text)

    # 4. Убираем лишние пробелы
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _truncate_by_sentence(text: str, max_chars: int = 400) -> str:
    """Обрезает текст по границе предложения, не разрывая числа."""
    if len(text) <= max_chars:
        return text

    # Ищем последнюю точку/!/?/… до max_chars
    cut = text[:max_chars]
    last_punct = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"), cut.rfind("…"))
    if last_punct > max_chars * 0.5:  # если нашли в пределах половины
        return cut[:last_punct + 1].strip()

    # Иначе — по последнему пробелу (чтобы не рвать слово)
    last_space = cut.rfind(" ")
    if last_space > 0:
        return cut[:last_space].strip() + "…"

    return cut.strip()


def speak(text: str):
    """Озвучивает текст через Piper."""
    if not text:
        return

    clean = clean_for_speech(text)
    if not clean:
        return

    # Обрезаем по границе предложения
    clean = _truncate_by_sentence(clean, max_chars=400)

    wav_out = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name

    try:
        cmd = [
            sys.executable, "-m", "piper",
            "-m", PIPER_MODEL,
            "-f", wav_out,
            "--", clean,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        # Воспроизведение
        import soundfile as sf
        import sounddevice as sd
        data, sr = sf.read(wav_out)
        sd.play(data, sr)
        sd.wait()
    except Exception as e:
        log(f"speak error: {e}")
    finally:
        try:
            os.unlink(wav_out)
        except OSError:
            pass