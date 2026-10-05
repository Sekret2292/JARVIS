import json
import urllib.request
from brain import JarvisBrain

b = JarvisBrain()
print("Модель:", b.model)
print("Промпт:", len(b.system_prompt), "символов")
print("Сообщений в контексте:", len(b.messages))
print()

# Прямой вызов
reply = b.ask("Привет! Ответь одной строкой.")
print("Тип ответа:", type(reply))
print("Длина ответа:", len(reply) if reply else 0)
print("Ответ:", repr(reply))
print()
print("Сообщений после запроса:", len(b.messages))
for i, msg in enumerate(b.messages):
    role = msg["role"]
    content = msg["content"][:80].replace("\n", " ")
    print(f"  [{i}] {role}: {content}...")
