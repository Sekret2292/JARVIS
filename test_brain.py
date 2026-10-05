from brain import JarvisBrain

b = JarvisBrain()
print("Модель:", b.model)
print("Промпт загружен:", len(b.system_prompt), "символов")
print()
reply = b.ask("Привет! Ответь одной строкой — как тебя зовут?")
print("JARVIS:", reply)
