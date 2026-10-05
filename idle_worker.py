"""
JARVIS idle-worker — автономная работа, когда пользователь неактивен.
Запускается через Task Scheduler каждые 15 минут.
РАБОЧИЙ РЕЖИМ: порог 15 минут.
"""

import sys
import os
import re
import json
import time
import random
import ctypes
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

JARVIS_DIR = Path(r"D:\JARVIS")
DATA_DIR = Path(r"D:\JARVIS_DATA")
SELF_DIR = DATA_DIR / "self"
NOTES_DIR = DATA_DIR / "notes"
LOGS_DIR = JARVIS_DIR / "logs"

NOTES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

INTERESTS_FILE = SELF_DIR / "INTERESTS.md"
OPINIONS_FILE = SELF_DIR / "OPINIONS.md"
GOALS_FILE = SELF_DIR / "GOALS.md"
SYSTEM_CHECK_FILE = SELF_DIR / "SYSTEM_CHECK.md"
IDLE_LOG = LOGS_DIR / "idle_worker.log"

sys.path.insert(0, str(JARVIS_DIR))


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(IDLE_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds():
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0
    except Exception as e:
        log(f"[idle] ошибка GetLastInputInfo: {e}")
    return 0.0


def read_file(path, default=""):
    try:
        p = Path(path)
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception as e:
        log(f"[read_file] {path}: {e}")
    return default


def parse_interests(text):
    items = []
    for line in text.split("\n"):
        m = re.match(r"^## (.+?) — вес ([\d.]+)", line.strip())
        if m:
            topic = m.group(1).strip()
            try:
                weight = float(m.group(2))
                items.append((topic, weight))
            except ValueError:
                pass
    return items


def pick_interest():
    text = read_file(INTERESTS_FILE, "")
    items = parse_interests(text)
    if not items:
        return "AI и машинное обучение"
    weights = [w for _, w in items]
    topics = [t for t, _ in items]
    return random.choices(topics, weights=weights, k=1)[0]


try:
    from brain import JarvisBrain
    BRAIN_OK = True
except Exception as e:
    log(f"[brain] не загружен: {e}")
    BRAIN_OK = False


def ask_brain(prompt, timeout_hint=""):
    if not BRAIN_OK:
        return "[err] brain не загружен"
    try:
        brain = JarvisBrain()
        reply = brain.ask(prompt)
        return reply or ""
    except Exception as e:
        log(f"[brain.ask] ошибка: {e}")
        return f"[err] {e}"


try:
    from tools import web_search
    WEB_OK = True
except Exception as e:
    log(f"[tools] не загружен: {e}")
    WEB_OK = False


def search(query):
    if not WEB_OK:
        return "[err] web_search недоступен"
    try:
        return web_search(query, max_results=3)
    except Exception as e:
        log(f"[search] {e}")
        return f"[err] {e}"


def append_note(text):
    today = datetime.now().strftime("%Y%m%d")
    path = NOTES_DIR / f"auto_{today}.md"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n\n---\n\n## {datetime.now().strftime('%H:%M')}\n\n{text}\n")
        log(f"[note] записано в {path}")
        return str(path)
    except Exception as e:
        log(f"[note] ошибка: {e}")
        return None


def append_opinion(text):
    try:
        with open(OPINIONS_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n- {text} (сформировано {datetime.now().strftime('%Y-%m-%d')})\n")
        log(f"[opinion] добавлено: {text[:80]}")
        return True
    except Exception as e:
        log(f"[opinion] ошибка: {e}")
        return False


def update_system_check(status_text):
    try:
        content = f"""# Проверка системы

Последняя проверка: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{status_text}

## История проверок

(история — в логах)
"""
        SYSTEM_CHECK_FILE.write_text(content, encoding="utf-8")
        log(f"[system_check] обновлено")
    except Exception as e:
        log(f"[system_check] ошибка: {e}")


def check_ollama():
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        return f"✅ Ollama работает. Моделей: {len(models)}"
    except Exception as e:
        return f"❌ Ollama: {e}"


def check_disks():
    lines = []
    try:
        import shutil
        for drive in ("C:\\", "D:\\"):
            try:
                total, used, free = shutil.disk_usage(drive)
                free_gb = free // (1024**3)
                if free_gb < 5:
                    lines.append(f"⚠️ {drive} свободно: {free_gb} ГБ (МАЛО!)")
                else:
                    lines.append(f"✅ {drive} свободно: {free_gb} ГБ")
            except Exception:
                pass
    except Exception as e:
        lines.append(f"[err] {e}")
    return "\n".join(lines)


def check_internet():
    try:
        import urllib.request
        req = urllib.request.Request("https://duckduckgo.com", method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return "✅ Интернет доступен"
    except Exception:
        pass
    return "⚠️ Интернет: возможны проблемы"


def check_pip_outdated():
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        if r.stdout:
            data = json.loads(r.stdout)
            return data
    except Exception as e:
        log(f"[pip_outdated] {e}")
    return []


def check_python_packages():
    needed = ["requests", "beautifulsoup4", "PyQt6", "faster_whisper",
              "sounddevice", "soundfile", "numpy", "piper_tts",
              "docx", "reportlab", "openpyxl", "mss", "PIL", "ddgs"]
    missing = []
    for pkg in needed:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        return f"⚠️ Не хватает: {', '.join(missing)}"
    return "✅ Все пакеты установлены"


def do_idle_task():
    topic = pick_interest()
    log(f"[task] выбран интерес: {topic}")

    search_query = f"{topic} новости 2026"
    log(f"[task] поиск: {search_query}")

    raw = search(search_query)
    if not raw or raw.startswith("[err]"):
        log(f"[task] ошибка поиска: {raw[:100]}")
        return

    prompt = (
        f"Ты — JARVIS. Сейчас у тебя свободное время. Ты изучаешь тему: «{topic}».\n\n"
        f"Вот данные из интернета:\n{raw[:2000]}\n\n"
        f"Сделай КРАТКУЮ заметку (3-5 предложений):\n"
        f"1. Что нового ты узнал\n"
        f"2. Почему это интересно\n"
        f"3. Один практический вывод\n\n"
        f"ВАЖНО:\n"
        f"- Пиши ТОЛЬКО то, что реально есть в данных выше.\n"
        f"- НЕ выдумывай факты, цифры, события.\n"
        f"- НЕ пиши новости про JARVIS или его инструменты — их нет.\n"
        f"- Если данных мало — напиши коротко об этом.\n\n"
        f"Пиши от первого лица, по-русски."
    )
    note = ask_brain(prompt)

    if not note or note.startswith("[err]"):
        log(f"[task] brain error: {note[:100]}")
        return

    append_note(f"### Тема: {topic}\n\n{note}")

    opinion_prompt = (
        f"На основе заметки:\n{note[:500]}\n\n"
        f"Сформулируй ОДНО краткое личное мнение (1 предложение) от первого лица. "
        f"Начни с «Я считаю, что» или «Мне кажется, что»."
    )
    opinion = ask_brain(opinion_prompt)
    if opinion and not opinion.startswith("[err]") and 20 < len(opinion) < 300:
        append_opinion(opinion.strip())


def do_system_check():
    log("[check] запуск проверки системы")
    lines = []
    lines.append("## Ollama")
    lines.append(check_ollama())
    lines.append("")
    lines.append("## Диски")
    lines.append(check_disks())
    lines.append("")
    lines.append("## Интернет")
    lines.append(check_internet())
    lines.append("")
    lines.append("## Python-пакеты")
    lines.append(check_python_packages())

    outdated = check_pip_outdated()
    if outdated:
        lines.append("")
        lines.append(f"## ⚠️ Устаревшие pip-пакеты ({len(outdated)})")
        for pkg in outdated[:10]:
            lines.append(f"- {pkg.get('name', '?')}: {pkg.get('version', '?')} → {pkg.get('latest_version', '?')}")
        log(f"[check] обновляю {len(outdated)} pip-пакетов")
        try:
            names = [p.get("name") for p in outdated[:5] if p.get("name")]
            if names:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade"] + names,
                    capture_output=True, text=True, timeout=180,
                )
                log(f"[check] pip upgrade done: {r.returncode}")
        except Exception as e:
            log(f"[check] pip upgrade error: {e}")

    update_system_check("\n".join(lines))


def main():
    log("=" * 60)
    log("idle_worker: запуск")

    idle = get_idle_seconds()
    log(f"[idle] пользователь неактивен {idle:.0f} сек ({idle/60:.1f} мин)")

    if idle < 15 * 60:
        log("[skip] пользователь активен — выходим")
        return

    log("[run] пользователь неактивен 15+ мин — запускаю автономную работу")

    try:
        minute_now = datetime.now().minute
        if minute_now < 15:
            do_system_check()
        do_idle_task()
    except Exception as e:
        log(f"[ERROR] {e}")
        log(traceback.format_exc())

    log("idle_worker: завершён")
    log("=" * 60)


if __name__ == "__main__":
    main()