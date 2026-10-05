"""
JARVIS Telegram Users — имена друзей + история.
Сохраняет в D:\JARVIS_DATA\telegram\
"""

import json
import time
from pathlib import Path

# ============ CONFIG ============
TELEGRAM_DIR = Path(r"D:\JARVIS_DATA\telegram")
TELEGRAM_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = TELEGRAM_DIR / "users.json"
HISTORY_DIR = TELEGRAM_DIR / "history"
HISTORY_DIR.mkdir(exist_ok=True)

# Админ (твой chat_id — узнаешь позже, впиши сюда)
ADMIN_CHAT_ID = None  # Например: 123456789


# ============ ПОЛЬЗОВАТЕЛИ ============
def load_users():
    """Загружает всех пользователей."""
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users):
    """Сохраняет пользователей."""
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def register_user(chat_id, username, first_name):
    """Регистрирует пользователя (если новый)."""
    users = load_users()
    chat_id_str = str(chat_id)
    
    if chat_id_str not in users:
        users[chat_id_str] = {
            "chat_id": chat_id,
            "username": username or "",
            "first_name": first_name or "",
            "real_name": "",  # Имя, которое введёт пользователь
            "registered": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S"),
            "message_count": 0,
            "is_blocked": False,
        }
        save_users(users)
        return True, "new"
    
    # Обновляем last_seen
    users[chat_id_str]["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
    users[chat_id_str]["message_count"] = users[chat_id_str].get("message_count", 0) + 1
    save_users(users)
    return False, "existing"


def get_user(chat_id):
    """Получает данные пользователя."""
    users = load_users()
    return users.get(str(chat_id))


def set_user_name(chat_id, real_name):
    """Устанавливает имя пользователя."""
    users = load_users()
    chat_id_str = str(chat_id)
    
    if chat_id_str in users:
        users[chat_id_str]["real_name"] = real_name
        save_users(users)
        return True
    return False


def get_user_name(chat_id):
    """Возвращает отображаемое имя."""
    user = get_user(chat_id)
    if not user:
        return "Неизвестный"
    
    # Приоритет: real_name > first_name > username > chat_id
    if user.get("real_name"):
        return user["real_name"]
    if user.get("first_name"):
        return user["first_name"]
    if user.get("username"):
        return f"@{user['username']}"
    return f"User{chat_id}"


def is_admin(chat_id):
    """Проверяет, админ ли это."""
    if ADMIN_CHAT_ID is None:
        return False
    return str(chat_id) == str(ADMIN_CHAT_ID)


def block_user(chat_id, blocked=True):
    """Блокирует/разблокирует пользователя."""
    users = load_users()
    chat_id_str = str(chat_id)
    
    if chat_id_str in users:
        users[chat_id_str]["is_blocked"] = blocked
        save_users(users)
        return True
    return False


def is_blocked(chat_id):
    """Проверяет, заблокирован ли."""
    user = get_user(chat_id)
    if not user:
        return False
    return user.get("is_blocked", False)


# ============ ИСТОРИЯ ============
def get_history_file(chat_id):
    """Путь к файлу истории пользователя."""
    return HISTORY_DIR / f"{chat_id}.json"


def load_history(chat_id):
    """Загружает историю диалога."""
    path = get_history_file(chat_id)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(chat_id, messages):
    """Сохраняет историю диалога."""
    path = get_history_file(chat_id)
    try:
        # Ограничиваем 50 последними сообщениями
        if len(messages) > 50:
            messages = messages[-50:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def add_to_history(chat_id, role, content):
    """Добавляет сообщение в историю."""
    history = load_history(chat_id)
    history.append({
        "role": role,
        "content": content,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_history(chat_id, history)


def clear_history(chat_id):
    """Очищает историю."""
    path = get_history_file(chat_id)
    if path.exists():
        try:
            path.unlink()
            return True
        except Exception:
            return False
    return True


# ============ СТАТИСТИКА ============
def get_stats():
    """Общая статистика бота."""
    users = load_users()
    total_users = len(users)
    total_messages = sum(u.get("message_count", 0) for u in users.values())
    blocked = sum(1 for u in users.values() if u.get("is_blocked", False))
    
    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "blocked_users": blocked,
    }


def get_all_users_list():
    """Список всех пользователей."""
    users = load_users()
    result = []
    for chat_id, data in users.items():
        result.append({
            "chat_id": chat_id,
            "name": get_user_name(chat_id),
            "username": data.get("username", ""),
            "messages": data.get("message_count", 0),
            "last_seen": data.get("last_seen", ""),
            "blocked": data.get("is_blocked", False),
        })
    # Сортируем по количеству сообщений
    result.sort(key=lambda x: x["messages"], reverse=True)
    return result