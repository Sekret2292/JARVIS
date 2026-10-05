"""
JARVIS main — простой текстовый чат.
"""

import sys
import time
from pathlib import Path

from brain import JarvisBrain
from tools import extract_run_command, run_command, strip_run_command

LOG_FILE = Path(r"D:\JARVIS\logs\jarvis.log")


def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def process(brain, user_input):
    """Простая обработка: спрашиваем, проверяем RUN, отвечаем."""

    brain.reset()
    brain.messages.append({"role": "user", "content": user_input})

    for iteration in range(5):
        log(f"[loop {iteration+1}] Отправка в модель...")
        t0 = time.time()

        reply = brain.ask_raw()  # Метод, который мы добавим в brain.py
        elapsed = time.time() - t0

        if not reply:
            log(f"[model {elapsed:.1f}s] ПУСТОЙ ОТВЕТ")
            return

        log(f"[model {elapsed:.1f}s] {reply[:200]}")

        brain.messages.append({"role": "assistant", "content": reply})

        cmd = extract_run_command(reply)
        if cmd:
            log(f"[exec] {cmd}")
            result = run_command(cmd)
            log(f"[result] {result[:200]}")
            brain.messages.append({
                "role": "user",
                "content": f"[Результат команды]\n{result[:200]}\n\nОтветь коротко."
            })
            continue

        clean = strip_run_command(reply)
        if clean:
            print(f"\nJARVIS> {clean}\n", flush=True)
        return


def main():
    print("=" * 60)
    print("JARVIS — текстовый чат")
    print("Команды: 'quit' / 'exit' / 'выход' | 'clear' / 'сброс'")
    print("=" * 60)

    brain = JarvisBrain()
    log(f"Модель: {brain.model}")
    log(f"Промпт: {len(brain.system_prompt)} символов")
    print("=" * 60)

    while True:
        try:
            user_input = input("Вы> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "выход", "q"):
            log("До встречи!")
            break

        if user_input.lower() in ("clear", "сброс"):
            brain.reset()
            log("История сброшена.")
            continue

        process(brain, user_input)
        print("-" * 60)


if __name__ == "__main__":
    main()