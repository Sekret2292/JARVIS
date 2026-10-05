import sounddevice as sd
import numpy as np

device = 1
print(f"Записываю 5 секунд с device={device}...")
print("Говори громко: ПРИВЕТ ДЖАРВИС")
d = sd.rec(int(5*44100), samplerate=44100, channels=1, device=device)
sd.wait()
level = float(np.max(np.abs(d)))
print(f"Уровень: {level:.4f}")
if level > 0.1:
    print("OK: микрофон слышит")
elif level > 0.01:
    print("Тихо, но слышит")
else:
    print("Не слышит - проверь микрофон")
