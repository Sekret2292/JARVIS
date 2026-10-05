from brain import JarvisBrain
import json

b = JarvisBrain()
b.messages.append({"role": "user", "content": "кто ты"})

# Смотрим, что отправляем
payload = json.dumps({
    "model": b.model,
    "messages": b.messages,
    "stream": False,
    "options": {"num_predict": 200}
})
print("PAYLOAD первые 300 символов:")
print(payload[:300])
print()
print("PAYLOAD полный размер:", len(payload))
print()
print("Кодировка в UTF-8:", len(payload.encode("utf-8")), "байт")
