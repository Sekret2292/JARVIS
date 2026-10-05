"""
Voice module для JARVIS UI.
Записывает с микрофона, распознаёт через Whisper.
"""

import os
import sys
import time
import queue
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel

# Импорт конфига
sys.path.insert(0, r"D:\JARVIS")
from config import (
    WHISPER_MODEL_SIZE, WHISPER_LANGUAGE, WHISPER_DEVICE, WHISPER_COMPUTE,
    MIC_DEVICE, SAMPLE_RATE, CHANNELS,
    SILENCE_THRESHOLD, SILENCE_DURATION, MAX_RECORD_SECONDS
)

# Инициализация Whisper (один раз)
print("[voice_ui] Загрузка Whisper...", flush=True)
whisper = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
print("[voice_ui] Whisper готов.", flush=True)


def record_until_silence():
    """Записывает с микрофона до тишины."""
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata.copy())

    frames = []
    silence_start = None
    start = time.time()
    heard = False

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=callback,
        device=MIC_DEVICE
    ):
        while True:
            try:
                data = q.get(timeout=0.5)
            except queue.Empty:
                if time.time() - start > MAX_RECORD_SECONDS:
                    break
                continue

            frames.append(data)
            rms = float(np.sqrt(np.mean(data ** 2)))

            if rms > SILENCE_THRESHOLD:
                heard = True
                silence_start = None
            else:
                if heard:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > SILENCE_DURATION:
                        break

            if time.time() - start > MAX_RECORD_SECONDS:
                break

    if not frames or not heard:
        return None

    audio = np.concatenate(frames, axis=0)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, SAMPLE_RATE)
    return tmp.name


def transcribe(wav_path):
    """Распознаёт речь."""
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


def listen():
    """Запись + распознавание. Возвращает текст или None."""
    wav = record_until_silence()
    if not wav:
        return None
    
    try:
        text = transcribe(wav)
    finally:
        try:
            os.unlink(wav)
        except OSError:
            pass
    
    return text if text else None

def listen_with_level(ui):
    """Записывает с обновлением уровня громкости в UI.
    Параметр ui — объект JarvisUI для set_audio_level."""
    q = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(indata.copy())

    frames = []
    silence_start = None
    start = time.time()
    heard = False

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=callback,
        device=MIC_DEVICE
    ):
        while True:
            try:
                data = q.get(timeout=0.5)
            except queue.Empty:
                if time.time() - start > MAX_RECORD_SECONDS:
                    break
                continue

            frames.append(data)
            rms = float(np.sqrt(np.mean(data ** 2)))
            
            # Обновляем уровень в UI
            if ui:
                ui.audio_level = min(1.0, rms * 10)

            if rms > SILENCE_THRESHOLD:
                heard = True
                silence_start = None
            else:
                if heard:
                    if silence_start is None:
                        silence_start = time.time()
                    elif time.time() - silence_start > SILENCE_DURATION:
                        break

            if time.time() - start > MAX_RECORD_SECONDS:
                break

    if not frames or not heard:
        return None

    audio = np.concatenate(frames, axis=0)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    sf.write(tmp.name, audio, SAMPLE_RATE)
    return transcribe(tmp.name)