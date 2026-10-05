import json, urllib.request, time

t0 = time.time()
payload = json.dumps({
    "model": "qwen3.5:9b",
    "messages": [
        {"role": "system", "content": "Ты JARVIS."},
        {"role": "user", "content": "Привет. Ответь одной фразой."}
    ],
    "stream": False,
    "think": False,
    "options": {"num_predict": 300}
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:11434/api/chat",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode("utf-8"))

elapsed = time.time() - t0
print(f"Время: {elapsed:.1f}s")
print(f"Ответ: {repr(data['message']['content'][:200])}")
