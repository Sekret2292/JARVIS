from brain import JarvisBrain
import json

b = JarvisBrain()
b.messages.append({"role": "user", "content": "кто ты"})

# Ручной запрос — показываем ВСЁ
import urllib.request
payload = json.dumps({
    "model": b.model,
    "messages": b.messages,
    "stream": False,
    "options": {"num_predict": 2000}
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=120) as resp:
    data = json.loads(resp.read().decode("utf-8"))

print("=== КЛЮЧИ ОТВЕТА ===")
print(list(data.keys()))
print()
print("=== message ===")
msg = data.get("message", {})
print("message keys:", list(msg.keys()))
print()
print("=== content (длина) ===")
print(repr(msg.get("content", "NO CONTENT"))[:500])
print()
print("=== thinking (длина) ===")
thinking = msg.get("thinking", "")
print("Длина thinking:", len(thinking))
print("Последние 500 символов:")
print(thinking[-500:])
