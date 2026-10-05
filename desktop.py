"""
JARVIS desktop — скриншоты экрана + отправка в vision-модель.
"""

import base64
import json
import urllib.request
from pathlib import Path
from datetime import datetime

from config import OLLAMA_URL, MODEL, REQUEST_TIMEOUT

SCREENSHOTS_DIR = Path(r"D:\JARVIS_DATA\screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def take_screenshot(out_path=None):
    """Делает скриншот всего экрана. Возвращает путь к PNG."""
    try:
        import mss
    except ImportError:
        return None

    if out_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = SCREENSHOTS_DIR / f"screen_{ts}.png"
    else:
        out_path = Path(out_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with mss.mss() as sct:
            # Монитор 1 (или все — если несколько)
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            # Сохраняем через PIL
            from PIL import Image
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            img.save(str(out_path))
        return str(out_path)
    except Exception as e:
        print(f"[desktop] screenshot error: {e}", flush=True)
        return None


def describe_screen(question="Что на экране?"):
    """Делает скриншот → отправляет в vision-модель → возвращает описание."""
    img_path = take_screenshot()
    if not img_path:
        return "[err] не удалось сделать скриншот"

    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return f"[err] не удалось прочитать скриншот: {e}"

    # Отправляем в Ollama /api/chat с images
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": question,
                "images": [img_b64],
            }
        ],
        "stream": False,
        "think": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            reply = data.get("message", {}).get("content", "").strip()
            return reply or "(модель не ответила)"
    except Exception as e:
        return f"[err] vision: {e}"


# Ручной тест
if __name__ == "__main__":
    print("Делаю скриншот...")
    p = take_screenshot()
    print(f"Скриншот сохранён: {p}")

    print("\nСпрашиваю модель, что на экране...")
    desc = describe_screen("Что ты видишь на этом экране? Опиши кратко (2-3 предложения).")
    print(f"\nОтвет: {desc}")