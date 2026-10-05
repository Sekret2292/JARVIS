"""
JARVIS ↔ ComfyUI — генерация изображений через API.
Работает с ComfyUI на http://127.0.0.1:8188
"""

import json
import time
import uuid
import urllib.request
import urllib.parse
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
GENERATED_DIR = Path(r"D:\JARVIS_DATA\generated")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# Модель по умолчанию
DEFAULT_CHECKPOINT = "sd_xl_base_1.0.safetensors"


def _post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _build_workflow(prompt, negative, steps=25, cfg=7.0, width=1024, height=1024, seed=None):
    """Собирает workflow для SDXL."""
    if seed is None:
        seed = int(time.time() * 1000) % (2**32)

    # Уникальный ID для нод
    return {
        "3": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "4": {
            "inputs": {"ckpt_name": DEFAULT_CHECKPOINT},
            "class_type": "CheckpointLoaderSimple",
        },
        "5": {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "6": {
            "inputs": {"text": prompt, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "7": {
            "inputs": {"text": negative, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "8": {
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            "class_type": "VAEDecode",
        },
        "9": {
            "inputs": {"filename_prefix": "jarvis", "images": ["8", 0]},
            "class_type": "SaveImage",
        },
    }


def generate_image(prompt_ru, negative="ugly, blurry, bad quality", timeout=120):
    """
    Генерирует изображение через ComfyUI.
    Возвращает путь к PNG или None.
    """
    # Переводим русский промпт в английский (простая эвристика)
    prompt_en = _translate_prompt(prompt_ru)

    workflow = _build_workflow(prompt_en, negative)

    # Отправляем workflow
    client_id = str(uuid.uuid4())
    try:
        resp = _post(f"{COMFYUI_URL}/prompt", {
            "prompt": workflow,
            "client_id": client_id,
        })
    except Exception as e:
        print(f"[comfy] ошибка отправки: {e}", flush=True)
        return None

    prompt_id = resp.get("prompt_id")
    if not prompt_id:
        print(f"[comfy] нет prompt_id в ответе: {resp}", flush=True)
        return None

    print(f"[comfy] задание отправлено, prompt_id={prompt_id}", flush=True)

    # Ждём выполнения
    start = time.time()
    while time.time() - start < timeout:
        try:
            history = _get(f"{COMFYUI_URL}/history/{prompt_id}")
        except Exception as e:
            print(f"[comfy] ошибка запроса истории: {e}", flush=True)
            time.sleep(2)
            continue

        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            for node_id, node_data in outputs.items():
                images = node_data.get("images", [])
                if images:
                    img = images[0]
                    filename = img.get("filename")
                    subfolder = img.get("subfolder", "")
                    img_type = img.get("type", "output")
                    return _download_image(filename, subfolder, img_type)

        time.sleep(2)

    print(f"[comfy] таймаут ({timeout} сек)", flush=True)
    return None


def _download_image(filename, subfolder, img_type):
    """Скачивает готовую картинку из ComfyUI."""
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": img_type,
    })
    url = f"{COMFYUI_URL}/view?{params}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception as e:
        print(f"[comfy] ошибка скачивания: {e}", flush=True)
        return None

    # Сохраняем в D:\JARVIS_DATA\generated\
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = GENERATED_DIR / f"jarvis_{ts}_{filename}"
    out_path.write_bytes(data)
    print(f"[comfy] сохранено: {out_path}", flush=True)
    return str(out_path)


def _translate_prompt(prompt_ru):
    """Простой перевод ключевых слов рус→англ."""
    # Известные соответствия
    dict_ru_en = {
        "кот": "cat", "кошка": "cat", "кошки": "cat", "кота": "cat",
        "собака": "dog", "собаки": "dog", "пёс": "dog",
        "космос": "space, cosmic, stars, nebula",
        "космонавт": "astronaut",
        "звёзды": "stars, galaxy",
        "планета": "planet",
        "робот": "robot, futuristic",
        "дракон": "dragon",
        "замок": "castle",
        "лес": "forest, trees",
        "море": "sea, ocean, waves",
        "горы": "mountains",
        "закат": "sunset",
        "рассвет": "sunrise",
        "город": "city",
        "девушка": "girl, woman",
        "парень": "young man",
        "воин": "warrior",
        "магия": "magic, magical",
        "фэнтези": "fantasy",
        "реалистичный": "realistic, photorealistic",
        "красивый": "beautiful, stunning",
        "детальный": "detailed, intricate",
        "яркий": "bright, vibrant",
        "тёмный": "dark, moody",
        "ночь": "night, moonlight",
        "день": "day, sunlight",
        "дождь": "rain",
        "снег": "snow, winter",
        "цветы": "flowers",
        "вода": "water",
        "огонь": "fire, flames",
        "небо": "sky",
        "облака": "clouds",
        "в космосе": "in space",
        "в лесу": "in the forest",
        "в городе": "in the city",
        "на море": "on the sea",
        "на горе": "on the mountain",
    }

    result = prompt_ru.lower()
    for ru, en in dict_ru_en.items():
        result = result.replace(ru, en)

    # Остаток на русском — оставляем, SDXL немного понимает
    # Плюс добавляем quality-теги
    result = result.strip()
    if result:
        result += ", high quality, best quality, detailed"
    return result


# Ручной тест
if __name__ == "__main__":
    print("Тест comfyui_bridge...")
    print("Генерирую 'кота в космосе'...")
    result = generate_image("кот в космосе, звёзды, галактика")
    if result:
        print(f"\n✅ ГОТОВО: {result}")
    else:
        print("\n❌ Не удалось сгенерировать")