import subprocess
import re
from pathlib import Path
from config import COMMAND_TIMEOUT

# Импорт SQLite-памяти
try:
    from memory_db import (
        add_fact, remove_fact_by_text, get_all_facts,
        search_facts, clear_all, count_facts,
        format_facts_for_prompt, update_fact,
    )
    MEM_DB_OK = True
except Exception as e:
    print(f"[tools] memory_db не загружен: {e}")
    MEM_DB_OK = False
    def add_fact(*a, **k): return None
    def remove_fact_by_text(s): return 0
    def get_all_facts(*a, **k): return []
    def search_facts(q, limit=20): return []
    def clear_all(): pass
    def count_facts(): return 0
    def format_facts_for_prompt(f): return ""
    def update_fact(*a, **k): return False


# ============ WEB SEARCH ============

def web_search(query, max_results=5):
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS
        except ImportError:
            return "[err] duckduckgo-search не установлен"

    try:
        results = []
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=max_results), 1):
                t = r.get("title", "").strip()
                b = r.get("body", "").strip()
                h = r.get("href", "").strip()
                results.append(f"{i}. {t}\n   {b}\n   Источник: {h}")
        if not results:
            return f"Ничего не найдено: {query}"
        return "\n\n".join(results)
    except Exception as e:
        return f"[err] поиск не удался: {e}"


def extract_web_search(text):
    if not text:
        return None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("WEB_SEARCH:"):
            q = s[len("WEB_SEARCH:"):].strip().strip('"').strip("'")
            if q:
                return q
    return None


def extract_look(text):
    if not text:
        return None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("LOOK:"):
            q = s[len("LOOK:"):].strip().strip('"').strip("'")
            return q or "Что на экране?"
    return None


def extract_screenshot(text):
    if not text:
        return None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("SCREENSHOT:"):
            name = s[len("SCREENSHOT:"):].strip().strip('"').strip("'")
            return name or ""
    return None


# ============ RUN ============

def extract_run_command(text):
    if not text:
        return None
    for line in text.split("\n"):
        if "RUN:" in line:
            idx = line.find("RUN:")
            cmd = line[idx + 4:].strip()
            if cmd:
                return cmd
    return None


def run_command(cmd):
    if not cmd:
        return "(empty)"
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=COMMAND_TIMEOUT,
            encoding="utf-8", errors="replace",
        )
        out = (r.stdout.strip() + "\n" + r.stderr.strip()).strip()
        return out or "(ok)"
    except Exception as e:
        return f"[ERROR] {e}"


def strip_run_command(text):
    if not text:
        return ""
    return "\n".join(ln for ln in text.split("\n") if "RUN:" not in ln).strip()


# ============ FILES ============

def file_read(path):
    try:
        p = Path(path)
        if not p.exists():
            return f"[err] файл не найден: {path}"
        return p.read_text(encoding="utf-8", errors="replace")[:1500]
    except Exception as e:
        return f"[err] {e}"


def file_write(path, content):
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"OK: записано {len(content)} символов в {path}"
    except Exception as e:
        return f"[err] {e}"


def file_append(path, content):
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(content + "\n")
        return f"OK: добавлено в {path}"
    except Exception as e:
        return f"[err] {e}"


def file_list(path):
    try:
        p = Path(path)
        if not p.exists():
            return f"[err] папка не найдена: {path}"
        items = list(p.iterdir())[:20]
        return "\n".join(("[D] " if i.is_dir() else "[F] ") + i.name for i in items) or "(пусто)"
    except Exception as e:
        return f"[err] {e}"


def extract_file_commands(text):
    cmds = []
    if not text:
        return cmds
    for line in text.split("\n"):
        s = line.strip()
        idx = s.find("FILE_READ:")
        if idx >= 0:
            p = s[idx + 10:].strip().strip('"').strip("'")
            if p:
                cmds.append(("read", p))
            continue
        idx = s.find("FILE_WRITE:")
        if idx >= 0:
            rest = s[idx + 11:].strip()
            if "|" in rest:
                parts = rest.split("|", 1)
                p = parts[0].strip().strip('"').strip("'")
                if p:
                    cmds.append(("write", p, parts[1].strip()))
            continue
        idx = s.find("FILE_APPEND:")
        if idx >= 0:
            rest = s[idx + 12:].strip()
            if "|" in rest:
                parts = rest.split("|", 1)
                p = parts[0].strip().strip('"').strip("'")
                if p:
                    cmds.append(("append", p, parts[1].strip()))
            continue
        idx = s.find("FILE_LIST:")
        if idx >= 0:
            p = s[idx + 10:].strip().strip('"').strip("'")
            if p:
                cmds.append(("list", p))
    return cmds


# ============ MEMORY (SQLite) ============

def memory_add(fact, category="общее", tags="", source="пользователь", importance=5):
    """Добавить факт в SQLite. Возвращает текстовый ответ."""
    if not MEM_DB_OK:
        return "[err] memory_db не загружен"
    fact = fact.strip()
    if not fact:
        return "Пустой факт"

    fid = add_fact(fact, category=category, tags=tags,
                   source=source, importance=importance)
    if fid is None:
        return "Уже знаю"
    return f"Запомнил: {fact}"


def memory_get_all():
    """Получить все факты в виде текста."""
    if not MEM_DB_OK:
        return "(память недоступна)"
    facts = get_all_facts(limit=100)
    if not facts:
        return "(память пуста)"
    return format_facts_for_prompt(facts)


def memory_remove(fact):
    """Удалить факты, содержащие подстроку."""
    if not MEM_DB_OK:
        return "[err] memory_db не загружен"
    n = remove_fact_by_text(fact)
    if n == 0:
        return "Не нашёл такой факт"
    return f"Забыл: {fact} (удалено: {n})"


def memory_clear():
    """Очистить всю память."""
    if not MEM_DB_OK:
        return "[err] memory_db не загружен"
    clear_all()
    return "Память очищена"


def memory_search(query, limit=20):
    """Поиск в памяти."""
    if not MEM_DB_OK:
        return []
    return search_facts(query, limit=limit)


def memory_count():
    if not MEM_DB_OK:
        return 0
    return count_facts()


def extract_memory_commands(text):
    """Ищет REMEMBER:, FORGET:, MEMORY_CLEAR, SEARCH_MEMORY: в ответе."""
    cmds = []
    if not text:
        return cmds
    for line in text.split("\n"):
        s = line.strip()
        idx = s.find("REMEMBER:")
        if idx >= 0:
            fact = s[idx + 9:].strip()
            if fact:
                cmds.append(("remember", fact))
            continue
        idx = s.find("FORGET:")
        if idx >= 0:
            fact = s[idx + 7:].strip()
            if fact:
                cmds.append(("forget", fact))
            continue
        idx = s.find("SEARCH_MEMORY:")
        if idx >= 0:
            q = s[idx + 14:].strip()
            if q:
                cmds.append(("search", q))
            continue
        if "MEMORY_CLEAR" in s:
            cmds.append(("clear",))
    return cmds


# ============ CLEAN ДЛЯ ОЗВУЧКИ ============

def clean_for_speech(text):
    if not text:
        return ""
    text = re.sub(r"\*\*|__|##|[*`#]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", text)
    lines = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s:
            continue
        if s.startswith(("RUN:", "FILE_", "REMEMBER:", "FORGET:", "MEMORY_CLEAR",
                         "WEB_SEARCH:", "LOOK:", "SCREENSHOT:", "SEARCH_MEMORY:",
                         "IMAGE:",
                         "[err]", "[ERROR", "[Brain error]", "[web_search]", "[web_fetch]",
                         "[UI]", ">>", "Wait,", "Okay,", "Let's", "Hmm,", "Actually,")):
            continue
        lines.append(s)
    return " ".join(lines).strip()