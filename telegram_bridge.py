"""
JARVIS Telegram Bridge v2.
Имена друзей + Админ-команды + История в файле.
"""

import asyncio
import logging
import sys
import time
import os
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Импорт JARVIS
sys.path.insert(0, r"D:\JARVIS")
from brain import JarvisBrain
from telegram_users import (
    register_user, set_user_name, get_user_name, is_admin, is_blocked,
    block_user, load_history, add_to_history, clear_history,
    get_stats, get_all_users_list, load_users,
)

try:
    from telegram_voice import process_voice_message
    VOICE_ENABLED = True
except Exception as e:
    VOICE_ENABLED = False
    print(f"[Bot] Voice недоступен: {e}")

# ============ CONFIG ============
BOT_TOKEN = "8654271893:AAEbr3fAFbFT276EhdThHQLh7R4ecYfSnAw"

# Логирование
LOG_DIR = Path(r"D:\JARVIS\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_DIR / "telegram_bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ============ BRAINS ============
user_brains = {}


def get_brain(chat_id):
    if chat_id not in user_brains:
        user_brains[chat_id] = JarvisBrain()
        # Загружаем историю
        history = load_history(chat_id)
        if history:
            for msg in history:
                if msg["role"] in ("user", "assistant"):
                    user_brains[chat_id].messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })
            logger.info(f"История загружена для {chat_id}: {len(history)} сообщений")
    return user_brains[chat_id]


# ============ КОМАНДЫ ============
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Регистрируем
    register_user(chat_id, user.username, user.first_name)
    
    welcome = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я — JARVIS, локальный AI-ассистент.\n\n"
        f"📝 Просто напиши мне:\n"
        f"• Привет\n"
        f"• Погода в Москве\n"
        f"• Курс доллара\n"
        f"• Сколько времени\n\n"
        f"📝 Или отправь голосовое 🎤\n\n"
        f"Команды:\n"
        f"/help — справка\n"
        f"/name Имя — задать своё имя\n"
        f"/clear — очистить историю\n"
        f"/status — статус\n"
    )
    await update.message.reply_text(welcome)
    logger.info(f"/start от {user.first_name} ({chat_id})")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 JARVIS — команды:\n\n"
        "📝 Пиши текстом или отправляй 🎤 голосовое.\n\n"
        "Команды:\n"
        "/start — начать\n"
        "/help — справка\n"
        "/name Имя — задать имя (например /name Вася)\n"
        "/clear — очистить историю\n"
        "/status — статус\n"
    )
    await update.message.reply_text(help_text)


async def cmd_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка имени: /name Вася"""
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text(
            "📝 Использование: /name Вася\n"
            "Или: /name Иван Петров"
        )
        return
    
    real_name = " ".join(context.args).strip()
    
    if len(real_name) > 50:
        await update.message.reply_text("⚠️ Слишком длинное имя.")
        return
    
    if set_user_name(chat_id, real_name):
        await update.message.reply_text(f"✅ Отлично! Теперь я зову тебя {real_name}.")
        logger.info(f"Пользователь {chat_id} установил имя: {real_name}")
    else:
        await update.message.reply_text("⚠️ Ошибка. Попробуй /start.")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if chat_id in user_brains:
        user_brains[chat_id].reset()
    
    clear_history(chat_id)
    await update.message.reply_text("🧹 История очищена.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = get_user_name(chat_id)
    history = load_history(chat_id)
    
    status = (
        f"📊 Статус:\n\n"
        f"• Имя: {user_name}\n"
        f"• Chat ID: {chat_id}\n"
        f"• Модель: qwen3.5:9b\n"
        f"• Сообщений в истории: {len(history)}\n"
        f"• Пользователей: {len(load_users())}\n"
        f"• Голос: {'✅' if VOICE_ENABLED else '❌'}\n"
    )
    await update.message.reply_text(status)


# ============ АДМИН-КОМАНДЫ ============
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список админ-команд."""
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    text = (
        "👑 Админ-команды:\n\n"
        "/admin_users — список пользователей\n"
        "/admin_stats — статистика\n"
        "/admin_block <chat_id> — заблокировать\n"
        "/admin_unblock <chat_id> — разблокировать\n"
        "/admin_clear <chat_id> — очистить историю\n"
        "/admin_broadcast <text> — рассылка\n"
    )
    await update.message.reply_text(text)


async def cmd_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    users = get_all_users_list()
    
    if not users:
        await update.message.reply_text("📭 Нет пользователей.")
        return
    
    lines = ["👥 Пользователи:\n"]
    for u in users[:20]:  # Первые 20
        block = "🚫" if u["blocked"] else "✅"
        lines.append(
            f"{block} {u['name']}\n"
            f"   ID: {u['chat_id']}\n"
            f"   Сообщений: {u['messages']}\n"
            f"   Был: {u['last_seen']}\n"
        )
    
    await update.message.reply_text("\n".join(lines))


async def cmd_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    stats = get_stats()
    text = (
        f"📊 Статистика бота:\n\n"
        f"• Пользователей: {stats['total_users']}\n"
        f"• Сообщений всего: {stats['total_messages']}\n"
        f"• Заблокировано: {stats['blocked_users']}\n"
        f"• Активных сессий: {len(user_brains)}\n"
    )
    await update.message.reply_text(text)


async def cmd_admin_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /admin_block <chat_id>")
        return
    
    target_id = context.args[0]
    if block_user(target_id, True):
        await update.message.reply_text(f"🚫 Заблокирован: {target_id}")
    else:
        await update.message.reply_text(f"⚠️ Не найден: {target_id}")


async def cmd_admin_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if not is_admin(chat_id):
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    if not context.args:
        await update.message.reply_text("Использование: /admin_unblock <chat_id>")
        return
    
    target_id = context.args[0]
    if block_user(target_id, False):
        await update.message.reply_text(f"✅ Разблокирован: {target_id}")
    else:
        await update.message.reply_text(f"⚠️ Не найден: {target_id}")


# ============ ОБРАБОТКА ТЕКСТА ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    
    if not text:
        return
    
    # Проверка блокировки
    if is_blocked(chat_id):
        await update.message.reply_text("🚫 Вы заблокированы.")
        return
    
    # Регистрация
    register_user(chat_id, user.username, user.first_name)
    
    user_name = get_user_name(chat_id)
    logger.info(f"📝 {user_name} ({chat_id}): {text}")
    
    await update.message.chat.send_action("typing")
    
    try:
        brain = get_brain(chat_id)
        
        # Сохраняем в историю
        add_to_history(chat_id, "user", text)
        
        loop = asyncio.get_event_loop()
        t0 = time.time()
        reply = await loop.run_in_executor(None, brain.ask, text)
        elapsed = time.time() - t0
        
        if not reply:
            reply = "(пустой ответ)"
        
        # Сохраняем ответ
        add_to_history(chat_id, "assistant", reply)
        
        # Отправка
        if len(reply) > 4000:
            parts = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(reply)
        
        logger.info(f"✅ Ответ ({elapsed:.1f}s)")
    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(f"⚠️ Ошибка: {e}")


# ============ ОБРАБОТКА ГОЛОСА ============
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if is_blocked(chat_id):
        await update.message.reply_text("🚫 Вы заблокированы.")
        return
    
    if not VOICE_ENABLED:
        await update.message.reply_text("🎤 Голосовой модуль недоступен.")
        return
    
    register_user(chat_id, user.username, user.first_name)
    user_name = get_user_name(chat_id)
    
    logger.info(f"🎤 {user_name} ({chat_id}) — голосовое")
    await update.message.chat.send_action("record_voice")
    
    try:
        voice_file = await update.message.voice.get_file()
        ogg_path = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg").name
        await voice_file.download_to_drive(ogg_path)
        
        brain = get_brain(chat_id)
        loop = asyncio.get_event_loop()
        t0 = time.time()
        result = await loop.run_in_executor(None, process_voice_message, ogg_path, brain)
        elapsed = time.time() - t0
        
        try:
            os.unlink(ogg_path)
        except OSError:
            pass
        
        recognized = result.get("recognized", "")
        reply = result.get("reply", "")
        reply_ogg = result.get("reply_ogg")
        
        if not recognized:
            await update.message.reply_text("🎤 Не разобрал. Попробуй ещё раз.")
            return
        
        await update.message.reply_text(f"🎤 Ты сказал: {recognized}")
        
        if reply:
            add_to_history(chat_id, "user", recognized)
            add_to_history(chat_id, "assistant", reply)
            
            if len(reply) > 4000:
                parts = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
                for part in parts:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(reply)
            
            if reply_ogg and os.path.exists(reply_ogg):
                with open(reply_ogg, "rb") as f:
                    await update.message.reply_voice(voice=f)
                try:
                    os.unlink(reply_ogg)
                except OSError:
                    pass
        
        logger.info(f"✅ Голосовой ответ ({elapsed:.1f}s)")
    
    except Exception as e:
        logger.error(f"Ошибка голоса: {e}")
        await update.message.reply_text(f"⚠️ Ошибка: {e}")


# ============ ЗАПУСК ============
def main():
    logger.info("=" * 60)
    logger.info("JARVIS Telegram Bot v2 запускается...")
    logger.info("Бот: @Sekatikati_bot")
    logger.info("Функции: имена, админ-команды, история")
    logger.info("=" * 60)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Основные команды
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("name", cmd_name))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("status", cmd_status))
    
    # Админ-команды
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("admin_users", cmd_admin_users))
    app.add_handler(CommandHandler("admin_stats", cmd_admin_stats))
    app.add_handler(CommandHandler("admin_block", cmd_admin_block))
    app.add_handler(CommandHandler("admin_unblock", cmd_admin_unblock))
    
    # Сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")