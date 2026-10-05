import json
import urllib.request
from brain import JarvisBrain

b = JarvisBrain()
print("Промпт:", repr(b.system_prompt[:200]))
print()

# Прямой запрос
payload = json.dumps({
    "model": "qwen3.5:9b",
    "messages": b.messages + [{"role": "user", "content": "кто ты"}],
    "stream": False,
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode("utf-8"))
print("Полный ответ:")
print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
