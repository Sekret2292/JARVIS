"""
JARVIS memory — SQLite база фактов.
Категории, теги, источник, важность, дата.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"D:\JARVIS_DATA\memory\jarvis_memory.db")


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создать таблицы, если их нет."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                category TEXT DEFAULT 'общее',
                tags TEXT DEFAULT '',
                source TEXT DEFAULT 'пользователь',
                importance INTEGER DEFAULT 5,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_text ON facts(text)
        """)
        conn.commit()


def add_fact(text, category="общее", tags="", source="пользователь", importance=5):
    """Добавить факт. Возвращает id или None, если дубликат."""
    if not text or not text.strip():
        return None
    text = text.strip()

    # Проверка дубликата
    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM facts WHERE LOWER(text) = LOWER(?)",
            (text,)
        ).fetchone()
        if existing:
            return None

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            """INSERT INTO facts (text, category, tags, source, importance, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (text, category, tags, source, importance, now, now)
        )
        conn.commit()
        return cur.lastrowid


def update_fact(fact_id, new_text=None, category=None, tags=None, importance=None):
    """Обновить факт."""
    fields = []
    values = []

    if new_text is not None:
        fields.append("text = ?")
        values.append(new_text)
    if category is not None:
        fields.append("category = ?")
        values.append(category)
    if tags is not None:
        fields.append("tags = ?")
        values.append(tags)
    if importance is not None:
        fields.append("importance = ?")
        values.append(importance)

    if not fields:
        return False

    fields.append("updated_at = ?")
    values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    values.append(fact_id)

    with _conn() as conn:
        conn.execute(f"UPDATE facts SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        return True


def remove_fact_by_text(substring):
    """Удалить факты, содержащие подстроку. Возвращает количество удалённых."""
    if not substring:
        return 0
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM facts WHERE LOWER(text) LIKE ?",
            (f"%{substring.lower()}%",)
        )
        conn.commit()
        return cur.rowcount


def get_all_facts(category=None, limit=100):
    """Получить все факты (или по категории)."""
    with _conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM facts WHERE category = ? ORDER BY importance DESC, created_at DESC LIMIT ?",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM facts ORDER BY importance DESC, created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def search_facts(query, limit=20):
    """Поиск по тексту / тегам / категории."""
    if not query:
        return []
    q = f"%{query.lower()}%"
    with _conn() as conn:
        rows = conn.execute(
            """SELECT * FROM facts
               WHERE LOWER(text) LIKE ?
                  OR LOWER(tags) LIKE ?
                  OR LOWER(category) LIKE ?
               ORDER BY importance DESC, updated_at DESC
               LIMIT ?""",
            (q, q, q, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_categories():
    """Все категории с количеством фактов."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM facts GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def clear_all():
    """Удалить все факты."""
    with _conn() as conn:
        conn.execute("DELETE FROM facts")
        conn.commit()


def count_facts():
    with _conn() as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM facts").fetchone()
        return row["cnt"] if row else 0


def format_facts_for_prompt(facts):
    """Форматирует факты для передачи в промпт."""
    if not facts:
        return ""
    lines = []
    for f in facts:
        cat = f.get("category", "общее")
        text = f.get("text", "")
        tags = f.get("tags", "")
        imp = f.get("importance", 5)
        line = f"- [{cat}] {text}"
        if tags:
            line += f" (теги: {tags})"
        if imp >= 8:
            line += " ★"
        lines.append(line)
    return "\n".join(lines)


# Автоинициализация при импорте
init_db()


if __name__ == "__main__":
    # Тест
    print("Тест memory_db.py")
    print(f"Всего фактов: {count_facts()}")

    fid = add_fact("Я люблю кофе", category="предпочтения", tags="еда,напитки", importance=6)
    print(f"Добавлен факт id={fid}")

    fid2 = add_fact("Работаю программистом", category="про меня", tags="работа", importance=8)
    print(f"Добавлен факт id={fid2}")

    print("\nВсе факты:")
    for f in get_all_facts():
        print(f"  #{f['id']} [{f['category']}] {f['text']} (важность {f['importance']})")

    print("\nПоиск 'кофе':")
    for f in search_facts("кофе"):
        print(f"  #{f['id']} {f['text']}")

    print(f"\nВсего: {count_facts()}")