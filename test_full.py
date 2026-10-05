from brain import JarvisBrain
import json

b = JarvisBrain()
b.messages.append({"role": "user", "content": "кто ты"})

print("Количество сообщений:", len(b.messages))
print()
for i, msg in enumerate(b.messages):
    role = msg["role"]
    content = msg["content"]
    print(f"[{i}] role={role}, len={len(content)}, first50={repr(content[:50])}")
print()

# Что отправляется
payload = json.dumps({
    "model": b.model,
    "messages": b.messages,
    "stream": False,
    "options": {"num_predict": 200}
}).encode("utf-8")
print("Payload размер:", len(payload), "байт")
print()

# Прямой запрос с этими же данными
import urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode("utf-8"))
print("RESPONSE message:", repr(data.get("message", {})))
