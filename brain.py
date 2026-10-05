"""
JARVIS brain — общение с Ollama.
Память из SQLite автоматически добавляется в системный промпт.
"""

import json
import re
import urllib.request

from config import (
    OLLAMA_URL, MODEL, SYSTEM_PROMPT_FILE,
    NUM_PREDICT, REQUEST_TIMEOUT
)

# Импорт памяти
try:
    from tools import memory_get_all, memory_count
    MEM_OK = True
except Exception as e:
    print(f"[Brain] память недоступна: {e}", flush=True)
    MEM_OK = False
    def memory_get_all(): return "(память недоступна)"
    def memory_count(): return 0


class JarvisBrain:
    def __init__(self, model=None):
        self.model = model or MODEL
        self.system_prompt = self._load_system_prompt()
        self.messages = []
        self.reset()

    def _load_system_prompt(self):
        """Загружает system.md + факты из SQLite."""
        # 1. Основной промпт
        try:
            base = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[Brain] Промпт не загружен: {e}", flush=True)
            base = "Ты — JARVIS. Отвечай коротко и по делу."

        # 2. Факты из SQLite
        if MEM_OK:
            try:
                n = memory_count()
                if n > 0:
                    facts = memory_get_all()
                    if facts and facts != "(память пуста)":
                        base += (
                            f"\n\n## ПАМЯТЬ О ПОЛЬЗОВАТЕЛЕ (факты из базы, {n} шт.)\n\n"
                            f"Используй эти факты в ответах. Не переспрашивай то, что уже знаешь.\n\n"
                            f"{facts}\n"
                        )
                        print(f"[Brain] Загружено {n} фактов из памяти", flush=True)
            except Exception as e:
                print(f"[Brain] Ошибка загрузки памяти: {e}", flush=True)

        return base

    def reload_memory(self):
        """Перезагружает память (после REMEMBER/FORGET)."""
        self.system_prompt = self._load_system_prompt()
        self.messages[0] = {"role": "system", "content": self.system_prompt}

    def reset(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _strip_thinking(self, text):
        if not text:
            return text
        lines = text.split("\n")
        clean = []
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            if s.startswith("*") and s.endswith("*") and not s.startswith("**"):
                continue
            if re.match(r"^\*[^*].*[^*]\*$", s):
                continue
            if s.startswith(("Wait,", "Okay,", "Let's", "Hmm,", "Actually,", "Self-Correction")):
                continue
            if s in ("...", "..", "."):
                continue
            if s.startswith("*") and not s.startswith("**"):
                continue
            clean.append(ln)
        result = "\n".join(clean).strip()
        result = result.replace("**", "").replace("##", "").replace("`", "")
        result = re.sub(r"\*+", "", result)
        return result.strip()

    def ask(self, user_message):
        msg = user_message.rstrip() + " /no_think"
        self.messages.append({"role": "user", "content": msg})

        payload = json.dumps({
            "model": self.model,
            "messages": self.messages,
            "stream": False,
            "think": False,
            "options": {"num_predict": NUM_PREDICT}
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
                reply = data["message"]["content"]
                reply = self._strip_thinking(reply)
                self.messages.append({"role": "assistant", "content": reply})
                return reply
        except Exception as e:
            import traceback
            print(f"[Brain] ERROR: {e}", flush=True)
            traceback.print_exc()
            return f"[Brain error] {e}"

    def ask_raw(self):
        payload = json.dumps({
            "model": self.model,
            "messages": self.messages,
            "stream": False,
            "think": False,
            "options": {"num_predict": NUM_PREDICT}
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
                return self._strip_thinking(data["message"]["content"])
        except Exception as e:
            import traceback
            print(f"[Brain] ERROR: {e}", flush=True)
            traceback.print_exc()
            return ""

    def add_command_result(self, result):
        self.messages.append({
            "role": "user",
            "content": f"[Результат команды]\n{result[:500]}\n\nПродолжи. /no_think"
        })