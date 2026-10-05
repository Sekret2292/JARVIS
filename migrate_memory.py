"""
Одноразовая миграция: facts.txt → SQLite
"""

import re
from pathlib import Path

from memory_db import add_fact, get_all_facts, count_facts

OLD_FILE = Path(r"D:\JARVIS_DATA\memory\facts.txt")


def guess_category(text):
    """Определяет категорию по тексту."""
    t = text.lower()
    if any(w in t for w in ["зовут", "имя", "меня зовут"]):
        return "про меня"
    if any(w in t for w in ["живёт", "живу", "живёшь", "город", "костром", "москв"]):
        return "про меня"
    if any(w in t for w in ["работа", "программист", "инженер", "профессия"]):
        return "про меня"
    if any(w in t for w in ["любл", "нравитс", "предпочт", "хочу"]):
        return "предпочтения"
    if any(w in t for w in ["знаю", "научился", "изучил", "факт"]):
        return "знания"
    return "общее"


def guess_importance(text):
    """Важность 1-10."""
    t = text.lower()
    # Имя, город, работа — важное
    if any(w in t for w in ["зовут", "живёт", "работа", "программист"]):
        return 8
    # Предпочтения — средне
    if any(w in t for w in ["любл", "нравитс"]):
        return 6
    return 5


def main():
    print("Миграция facts.txt → SQLite")
    print(f"Файл: {OLD_FILE}")

    if not OLD_FILE.exists():
        print("Файл не найден — ничего не делаем")
        return

    print(f"\nДо миграции в БД: {count_facts()} фактов")

    content = OLD_FILE.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in content.split("\n") if ln.strip()]

    added = 0
    skipped = 0

    for line in lines:
        # Убираем "- " в начале
        if line.startswith("- "):
            line = line[2:].strip()

        # Убираем перенос строки, если есть
        line = re.sub(r"\s+", " ", line).strip()

        if not line:
            continue

        category = guess_category(line)
        importance = guess_importance(line)
        tags = ""

        fid = add_fact(line, category=category, tags=tags,
                       source="миграция", importance=importance)

        if fid:
            print(f"  ✅ [{category}] {line}")
            added += 1
        else:
            print(f"  ⏭ уже есть: {line}")
            skipped += 1

    print(f"\nДобавлено: {added}")
    print(f"Пропущено (дубликаты): {skipped}")
    print(f"Всего в БД: {count_facts()}")

    # Показываем итог
    print("\n=== ВСЕ ФАКТЫ ===")
    for f in get_all_facts():
        print(f"  #{f['id']} [{f['category']}] {f['text']} (важность {f['importance']})")

    # Переименовываем старый файл, чтобы больше не использовался
    backup = OLD_FILE.with_suffix(".txt.old")
    OLD_FILE.rename(backup)
    print(f"\n✅ Старый файл переименован в: {backup}")


if __name__ == "__main__":
    main()