from pathlib import Path

prompt = Path(r"D:\JARVIS\prompts\system.md").read_text(encoding="utf-8")
paths = Path(r"D:\JARVIS\prompts\paths.md").read_text(encoding="utf-8")

print(f"system.md: {len(prompt)} символов")
print(f"paths.md:  {len(paths)} символов")
print(f"ИТОГО:     {len(prompt) + len(paths)} символов")
