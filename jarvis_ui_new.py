"""
JARVIS UI 2.0 — стеклянный интерфейс iOS 17/18
Версия 7.0 — кнопки Новый чат и Очистить + команда CLEAR_CHAT.
"""
import sys
import math
import json
import os
import subprocess
import threading
from pathlib import Path
from urllib.parse import unquote, quote
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QTextBrowser, QLineEdit, QPushButton, QLabel,
    QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QColor, QPainter, QPainterPath, QLinearGradient, QRadialGradient,
    QFont, QIcon, QBrush, QPen
)

sys.path.insert(0, r"D:\JARVIS")

try:
    from brain import JarvisBrain
    BRAIN_OK = True
except Exception as e:
    print(f"[UI] brain.py: {e}")
    BRAIN_OK = False

try:
    from voice import speak
    VOICE_OK = True
except Exception as e:
    print(f"[UI] voice.py: {e}")
    VOICE_OK = False
    def speak(text): pass

try:
    from tools import (
        extract_run_command, run_command, strip_run_command,
        extract_file_commands, file_read, file_write, file_append, file_list,
        extract_memory_commands, memory_add, memory_remove, memory_clear,
        clean_for_speech, web_search, extract_web_search,
        extract_look, extract_screenshot
    )
    TOOLS_OK = True
except Exception as e:
    print(f"[UI] tools.py: {e}")
    TOOLS_OK = False
    def extract_run_command(t): return None
    def run_command(c): return "(no tools)"
    def strip_run_command(t): return t
    def extract_file_commands(t): return []
    def extract_memory_commands(t): return []
    def clean_for_speech(t): return t
    def web_search(q, max_results=5): return "(web_search недоступен)"
    def extract_web_search(t): return None
    def extract_look(t): return None
    def extract_screenshot(t): return None

try:
    from desktop import take_screenshot, describe_screen
    DESKTOP_OK = True
except Exception as e:
    print(f"[UI] desktop.py: {e}")
    DESKTOP_OK = False
    def take_screenshot(out_path=None): return None
    def describe_screen(question=""): return "[err] desktop.py не загружен"

try:
    from comfyui_bridge import generate_image
    COMFY_OK = True
except Exception as e:
    print(f"[UI] comfyui_bridge.py: {e}")
    COMFY_OK = False
    def generate_image(prompt, negative="", timeout=120): return None

try:
    from voice_ui import listen_with_level
    MIC_OK = True
except Exception as e:
    print(f"[UI] voice_ui.py: {e}")
    MIC_OK = False
    def listen_with_level(ui): return None


# ============================================================
# ТРИГГЕРЫ
# ============================================================

def detect_screenshot_request(text):
    if not text:
        return False
    t = text.lower().strip()
    triggers = ["сделай скриншот", "скриншот", "снимок экрана",
                "сохрани скриншот", "скрин экрана"]
    return any(tr in t for tr in triggers)


def detect_look_request(text):
    if not text:
        return False
    t = text.lower().strip()
    triggers = ["что на экране", "что у меня на экране", "посмотри на экран",
                "опиши экран", "что открыто", "какие окна открыты",
                "что видишь на экране", "прочитай что на экране",
                "посмотри что открыто", "опиши что на экране"]
    return any(tr in t for tr in triggers)


def detect_web_search_request(text):
    if not text:
        return False
    t = text.lower().strip()
    triggers = ["погода", "погоду", "температура", "сколько градусов",
                "курс", "биткоин", "доллар", "евро", "акции",
                "новости", "что нового", "что случилось",
                "найди в интернете", "поищи в интернете",
                "проверь в интернете", "узнай в интернете",
                "посмотри по интернету", "поищи информацию",
                "который час", "сколько времени"]
    return any(tr in t for tr in triggers)


def detect_clear_chat(text):
    """Пользователь просит очистить чат."""
    if not text:
        return False
    t = text.lower().strip()
    triggers = [
        "удали чат", "очисти чат", "очисти историю",
        "удали историю", "сотри чат", "сотри историю",
        "начнем заново", "начнём заново", "начать заново",
        "очистить чат", "очистить историю", "удали переписку",
        "сотри переписку", "очисти переписку",
        "новый чат", "новый диалог", "удали все сообщения",
        "удали все сообшение", "удали все смс", "стереть чат",
    ]
    return any(tr in t for tr in triggers)


def extract_image(text):
    """Ищет IMAGE: в ответе."""
    if not text:
        return None
    for line in text.split("\n"):
        s = line.strip()
        idx = s.find("IMAGE:")
        if idx >= 0:
            q = s[idx + len("IMAGE:"):].strip().strip('"').strip("'")
            if q:
                return q
    return None


def extract_clear_chat(text):
    """Ищет CLEAR_CHAT в ответе."""
    if not text:
        return False
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("CLEAR_CHAT"):
            return True
    return False


# ============================================================
# ПАЛИТРА
# ============================================================
THEME_DARK = {
    "bg_gradient_top": "#0a0e1a", "bg_gradient_bottom": "#05070d",
    "glass_bg": "#1e2840", "text_primary": "#f0f4ff", "text_secondary": "#8892a8",
    "accent": "#00e0a0", "accent_dim": "#0a5a44",
    "user_color": "#5cb0ff", "jarvis_color": "#00e0a0",
    "system_color": "#808aa0", "exec_color": "#ffb84d",
    "input_bg": "#283750", "input_border": "#3a4a68",
    "chat_bg": "#141c2a", "chat_border": "#1e2840",
    "btn_color": "#00e0a0", "btn_hover": "#00f0b8", "btn_icon": "#0a0e1a",
    "btn_color_active_mic": "#00ffb0",
    "mic_idle_bg": "#2a3448", "mic_idle_border": "#4a5870",
    "mic_idle_icon": "#c0c8d8", "mic_active_icon": "#0a0e1a",
    "danger_color": "#ff6060", "danger_hover": "#ff8080",
    "is_dark": True,
}

THEME_LIGHT = {
    "bg_gradient_top": "#e8eef8", "bg_gradient_bottom": "#ccd6e6",
    "glass_bg": "#ffffff", "text_primary": "#0a1020", "text_secondary": "#3a4458",
    "accent": "#009070", "accent_dim": "#b8e0d0",
    "user_color": "#0040b0", "jarvis_color": "#006850",
    "system_color": "#6a7488", "exec_color": "#a05800",
    "input_bg": "#ffffff", "input_border": "#b8c0d0",
    "chat_bg": "#ffffff", "chat_border": "#d0d8e4",
    "btn_color": "#009070", "btn_hover": "#00a880", "btn_icon": "#ffffff",
    "btn_color_active_mic": "#6ec4a8",
    "mic_idle_bg": "#e8ecf4", "mic_idle_border": "#b8c0d0",
    "mic_idle_icon": "#3a4458", "mic_active_icon": "#ffffff",
    "danger_color": "#c04040", "danger_hover": "#d05050",
    "is_dark": False,
}

HISTORY_FILE = Path(r"D:\JARVIS\history.json")
MAX_HISTORY = 200
KEEP_LAST = 100


class GlobalPulse:
    def __init__(self):
        self.phase = 0.0
        self.active = False
        self.mic_active = False
        self.subscribers = []
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.setInterval(50)

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def start(self, mic=False):
        self.phase = 0.0
        self.active = True
        self.mic_active = mic
        if not self.timer.isActive():
            self.timer.start()
        self._notify()

    def stop(self):
        self.active = False
        self.mic_active = False
        self.timer.stop()
        self.phase = 0.0
        self._notify()

    def _tick(self):
        self.phase += 0.18
        if self.phase > math.tau:
            self.phase -= math.tau
        self._notify()

    def _notify(self):
        for cb in self.subscribers:
            cb()

    def intensity(self):
        if not self.active:
            return 0.0
        return 0.5 + 0.5 * math.sin(self.phase)


GLOBAL_PULSE = GlobalPulse()


class BrainSignals(QObject):
    reply_ready = pyqtSignal(str)
    command_exec = pyqtSignal(str)
    status_update = pyqtSignal(str, str)
    user_message = pyqtSignal(str)
    file_card = pyqtSignal(str, str)


BRAIN_SIGNALS = BrainSignals()


def draw_glass_stroke(painter, rect: QRectF, radius: float,
                      top_color: QColor, bottom_color: QColor,
                      width: float = 1.6):
    grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    grad.setColorAt(0.0, top_color)
    mid_alpha = int(top_color.alpha() * 0.15)
    grad.setColorAt(0.5, QColor(top_color.red(), top_color.green(), top_color.blue(), mid_alpha))
    grad.setColorAt(1.0, bottom_color)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    pen = QPen(QBrush(grad), width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


class PulsingLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = THEME_DARK
        GLOBAL_PULSE.subscribe(self._on_pulse)

    def set_theme(self, theme):
        self.theme = theme
        self._apply_style()

    def _on_pulse(self):
        self._apply_style()

    def _mix(self, c1, c2, t):
        a = QColor(c1); b = QColor(c2)
        r = int(a.red() * (1 - t) + b.red() * t)
        g = int(a.green() * (1 - t) + b.green() * t)
        bl = int(a.blue() * (1 - t) + b.blue() * t)
        return QColor(r, g, bl).name()

    def _apply_style(self):
        t = self.theme
        i = GLOBAL_PULSE.intensity()
        if GLOBAL_PULSE.active:
            border_col = self._mix(t["input_border"], t["accent"], 0.3 + 0.7 * i)
            border_w = 2.5
            bg_col = self._mix(t["input_bg"], t["accent_dim"], 0.15 * i)
        elif self.hasFocus():
            border_col = t["accent"]
            border_w = 2.0
            bg_col = t["input_bg"]
        else:
            border_col = t["input_border"]
            border_w = 1.5
            bg_col = t["input_bg"]
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {bg_col};
                color: {t['text_primary']};
                border: {border_w}px solid {border_col};
                border-radius: 28px;
                padding: 0 22px;
                font-size: 13pt;
            }}
        """)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._apply_style()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._apply_style()


class PulseOrb(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.state = "idle"
        self.theme = THEME_DARK
        GLOBAL_PULSE.subscribe(self.update)

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def set_state(self, state):
        self.state = state
        self.update()

    def mousePressEvent(self, event):
        self.clicked.emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2
        cy = self.height() / 2
        base_r = 22
        show_rings = GLOBAL_PULSE.active or self.state in ("listening", "speaking", "thinking")
        if show_rings:
            col = QColor(self.theme["exec_color"] if self.state == "thinking" else self.theme["accent"])
            i = GLOBAL_PULSE.intensity() if GLOBAL_PULSE.active else 0.5
            for k in range(3):
                phase = (i + k * 0.33) % 1.0
                scale = 1.0 + 0.45 * phase
                alpha = int(140 * (1.0 - phase))
                alpha = max(0, min(180, alpha))
                col2 = QColor(col); col2.setAlpha(alpha)
                r = base_r * scale
                p.setBrush(QBrush(col2))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(cx, cy), r, r)
        if self.state == "idle":
            fill = QColor(self.theme["mic_idle_bg"]); icon_color = QColor(self.theme["mic_idle_icon"])
        elif self.state == "listening":
            fill = QColor(self.theme["accent"]); icon_color = QColor(self.theme["mic_active_icon"])
        elif self.state == "thinking":
            fill = QColor(self.theme["exec_color"]); icon_color = QColor(self.theme["mic_active_icon"])
        else:
            fill = QColor(self.theme["accent"]); icon_color = QColor(self.theme["mic_active_icon"])
        grad = QRadialGradient(cx, cy - 6, base_r * 1.8)
        grad.setColorAt(0, fill.lighter(120))
        grad.setColorAt(1, fill)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), base_r, base_r)
        rect = QRectF(cx - base_r, cy - base_r, base_r * 2, base_r * 2)
        top_hl = QColor(255, 255, 255, 130 if self.state == "idle" else 200)
        bottom_sh = QColor(0, 0, 0, 90)
        draw_glass_stroke(p, rect, base_r, top_hl, bottom_sh, width=1.6)
        p.setPen(QPen(icon_color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        mic_w, mic_h = 7, 16
        p.drawRoundedRect(QRectF(cx - mic_w/2, cy - 10, mic_w, mic_h), mic_w/2, mic_w/2)
        p.drawArc(QRectF(cx - 10, cy - 3, 20, 16), 200 * 16, 140 * 16)
        p.drawLine(QPointF(cx, cy + 10), QPointF(cx, cy + 14))
        p.drawLine(QPointF(cx - 4, cy + 14), QPointF(cx + 4, cy + 14))


class SendOrb(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme = THEME_DARK
        self._hover = False
        GLOBAL_PULSE.subscribe(self.update)

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        self.clicked.emit()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2
        cy = self.height() / 2
        r = 22
        mic_active = GLOBAL_PULSE.mic_active and GLOBAL_PULSE.active
        if mic_active:
            btn_col = QColor(self.theme["btn_color_active_mic"])
        elif self._hover:
            btn_col = QColor(self.theme["btn_hover"])
        else:
            btn_col = QColor(self.theme["btn_color"])
        if GLOBAL_PULSE.active:
            i = GLOBAL_PULSE.intensity()
            col = QColor(btn_col)
            for k in range(3):
                phase = (i + k * 0.33) % 1.0
                scale = 1.0 + 0.5 * phase
                alpha = int(150 * (1.0 - phase))
                alpha = max(0, min(200, alpha))
                col2 = QColor(col); col2.setAlpha(alpha)
                rr = r * scale
                p.setBrush(QBrush(col2))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(cx, cy), rr, rr)
        shadow_col = QColor(0, 0, 0, 90)
        p.setBrush(QBrush(shadow_col))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy + 2), r, r)
        grad = QRadialGradient(cx, cy - 6, r * 1.6)
        grad.setColorAt(0, btn_col.lighter(125))
        grad.setColorAt(1, btn_col)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), r, r)
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        top_hl = QColor(255, 255, 255, 210)
        bottom_sh = QColor(0, 0, 0, 80)
        draw_glass_stroke(p, rect, r, top_hl, bottom_sh, width=1.6)
        arrow_color = QColor(self.theme["btn_icon"])
        p.setPen(QPen(arrow_color, 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(QPointF(cx, cy + 6), QPointF(cx, cy - 7))
        p.drawLine(QPointF(cx, cy - 7), QPointF(cx - 5, cy - 2))
        p.drawLine(QPointF(cx, cy - 7), QPointF(cx + 5, cy - 2))


class ChatFrame(QFrame):
    file_open_requested = pyqtSignal(str)
    file_folder_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = THEME_DARK
        self.radius = 18
        GLOBAL_PULSE.subscribe(self.update)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        self.text = QTextBrowser()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Segoe UI", 11))
        self.text.setFrameShape(QFrame.Shape.NoFrame)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.text.setOpenExternalLinks(False)
        self.text.setOpenLinks(False)
        self.text.anchorClicked.connect(self._on_anchor)
        layout.addWidget(self.text)

    def _on_anchor(self, url):
        u = unquote(url.toString())
        if u.startswith("file-open:"):
            self.file_open_requested.emit(u[len("file-open:"):])
        elif u.startswith("file-folder:"):
            self.file_folder_requested.emit(u[len("file-folder:"):])

    def set_theme(self, theme):
        self.theme = theme
        self._apply_style()
        self.update()

    def _apply_style(self):
        t = self.theme
        self.text.setStyleSheet(f"""
            QTextBrowser {{
                background: {t['chat_bg']};
                color: {t['text_primary']};
                border: none;
                border-radius: {self.radius - 4}px;
                padding: 16px;
                selection-background-color: {t['accent']};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 8px 4px 8px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['text_secondary']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = 0.8
        rect = QRectF(inset, inset, self.width() - 2 * inset, self.height() - 2 * inset)
        is_dark = self.theme.get("is_dark", True)
        if is_dark:
            top_hl = QColor(255, 255, 255, 110)
            bottom_sh = QColor(0, 0, 0, 130)
        else:
            top_hl = QColor(255, 255, 255, 230)
            bottom_sh = QColor(120, 130, 150, 100)
        if GLOBAL_PULSE.active:
            i = GLOBAL_PULSE.intensity()
            accent = QColor(self.theme["accent"])
            top_hl = QColor(
                int(top_hl.red() * (1 - i) + accent.red() * i),
                int(top_hl.green() * (1 - i) + accent.green() * i),
                int(top_hl.blue() * (1 - i) + accent.blue() * i),
                200
            )
        draw_glass_stroke(p, rect, self.radius, top_hl, bottom_sh, width=1.8)


class ThemeToggle(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_dark = True
        self.phase = 1.0
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)

    def _tick(self):
        target = 1.0 if self.is_dark else 0.0
        if abs(self.phase - target) < 0.02:
            self.phase = target
            self.anim_timer.stop()
        else:
            self.phase += (target - self.phase) * 0.2
        self.update()

    def mousePressEvent(self, e):
        self.is_dark = not self.is_dark
        self.anim_timer.start(16)
        self.toggled.emit(self.is_dark)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        bg = QColor(20, 30, 50, 200) if self.phase > 0.5 else QColor(200, 210, 230, 220)
        p.setBrush(QBrush(bg))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        cx = r + (w - 2 * r) * self.phase
        cy = h / 2
        knob_r = r - 3
        if self.phase > 0.5:
            p.setBrush(QBrush(QColor(180, 200, 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), knob_r, knob_r)
            p.setBrush(QBrush(bg))
            p.drawEllipse(QPointF(cx + 3, cy - 2), knob_r - 2, knob_r - 2)
        else:
            p.setBrush(QBrush(QColor(255, 200, 80)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), knob_r, knob_r)


class BackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = THEME_DARK
        self.radius = 24

    def set_theme(self, theme):
        self.theme = theme
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        margin = 2
        path = QPainterPath()
        path.addRoundedRect(QRectF(margin, margin, w - 2 * margin, h - 2 * margin),
                            self.radius, self.radius)
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(self.theme["bg_gradient_top"]))
        grad.setColorAt(1, QColor(self.theme["bg_gradient_bottom"]))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)
        is_dark = self.theme.get("is_dark", True)
        border_grad = QLinearGradient(0, 0, 0, h)
        border_grad.setColorAt(0, QColor(255, 255, 255, 80 if is_dark else 200))
        border_grad.setColorAt(1, QColor(255, 255, 255, 15 if is_dark else 80))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QBrush(border_grad), 1.5))
        p.drawPath(path)


class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_dark = True
        self.theme = THEME_DARK
        self.brain = JarvisBrain() if BRAIN_OK else None
        self.audio_level = 0.0
        self._last_user_question = ""

        self.setWindowTitle("JARVIS")
        self.setMinimumSize(720, 560)
        self.resize(920, 720)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        self.setCentralWidget(outer)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(14, 14, 14, 20)
        self.bg = BackgroundWidget()
        outer_layout.addWidget(self.bg)

        main_layout = QVBoxLayout(self.bg)
        main_layout.setContentsMargins(24, 22, 24, 22)
        main_layout.setSpacing(16)

        # ===== HEADER =====
        header = QHBoxLayout()
        header.setSpacing(10)
        self.title_label = QLabel("JARVIS")
        f = QFont("Segoe UI", 20, QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        self.title_label.setFont(f)
        self.status_label = QLabel("Готов")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.toggled.connect(self.on_theme_toggle)

        # Кнопки действий
        self.new_chat_btn = self._make_action_btn("+ Новый", self.on_new_chat, "accent")
        self.clear_btn = self._make_action_btn("Очистить", self.on_clear_chat, "danger")

        self.min_btn = self._make_titlebar_btn("—", self.showMinimized)
        self.close_btn = self._make_titlebar_btn("×", self.close)

        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.status_label)
        header.addSpacing(10)
        header.addWidget(self.new_chat_btn)
        header.addWidget(self.clear_btn)
        header.addSpacing(6)
        header.addWidget(self.theme_toggle)
        header.addSpacing(6)
        header.addWidget(self.min_btn)
        header.addWidget(self.close_btn)
        main_layout.addLayout(header)

        self.chat_frame = ChatFrame()
        self.chat = self.chat_frame.text
        self.chat_frame.file_open_requested.connect(self._open_file)
        self.chat_frame.file_folder_requested.connect(self._open_folder_with_file)
        main_layout.addWidget(self.chat_frame, 1)

        input_bar = QHBoxLayout()
        input_bar.setSpacing(12)
        self.input_field = PulsingLineEdit()
        self.input_field.setPlaceholderText("Спросите JARVIS...")
        self.input_field.setFont(QFont("Segoe UI", 13))
        self.input_field.setMinimumHeight(56)
        self.input_field.setMaximumHeight(56)
        self.input_field.returnPressed.connect(self.on_send)
        self.pulse_orb = PulseOrb()
        self.pulse_orb.clicked.connect(self.on_mic)
        self.send_orb = SendOrb()
        self.send_orb.clicked.connect(self.on_send)
        input_bar.addWidget(self.input_field, 1)
        input_bar.addWidget(self.pulse_orb)
        input_bar.addWidget(self.send_orb)
        main_layout.addLayout(input_bar)

        self._messages = []

        BRAIN_SIGNALS.reply_ready.connect(self.handle_reply)
        BRAIN_SIGNALS.command_exec.connect(self.handle_exec)
        BRAIN_SIGNALS.status_update.connect(self.set_status)
        BRAIN_SIGNALS.user_message.connect(self._add_user_message)
        BRAIN_SIGNALS.file_card.connect(self._show_file_card)

        self._drag_pos = None
        self.apply_theme()
        self.load_history()

    def _make_titlebar_btn(self, text, callback):
        btn = QPushButton(text)
        btn.setFixedSize(30, 30)
        btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        btn.clicked.connect(callback)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _make_action_btn(self, text, callback, kind="accent"):
        btn = QPushButton(text)
        btn.setFixedHeight(30)
        btn.setMinimumWidth(90)
        btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn.clicked.connect(callback)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("kind", kind)
        return btn

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def on_theme_toggle(self, is_dark):
        self.is_dark = is_dark
        self.theme = THEME_DARK if is_dark else THEME_LIGHT
        self.apply_theme()
        self.rerender_chat()

    def apply_theme(self):
        t = self.theme
        self.title_label.setStyleSheet(f"color: {t['accent']}; background: transparent;")
        self.status_label.setStyleSheet(f"color: {t['text_secondary']}; background: transparent;")
        for btn in (self.min_btn, self.close_btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {t['text_secondary']};
                    background: transparent;
                    border: none;
                    border-radius: 15px;
                }}
                QPushButton:hover {{
                    background: {t['glass_bg']};
                    color: {t['text_primary']};
                }}
            """)

        # Новый чат — акцентная кнопка
        self.new_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['accent']};
                color: {t['btn_icon']};
                border: none;
                border-radius: 15px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {t['btn_hover']};
            }}
        """)

        # Очистить — красная кнопка
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {t['danger_color']};
                border: 1px solid {t['danger_color']};
                border-radius: 15px;
                padding: 0 14px;
            }}
            QPushButton:hover {{
                background: {t['danger_color']};
                color: white;
            }}
        """)

        self.bg.set_theme(t)
        self.chat_frame.set_theme(t)
        self.input_field.set_theme(t)
        self.pulse_orb.set_theme(t)
        self.send_orb.set_theme(t)

    def load_history(self):
        if not HISTORY_FILE.exists():
            return
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return
            for item in data:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    sender, text = item
                    self._messages.append((sender, text))
                    self._render_message(sender, text)
        except Exception as e:
            print(f"[UI] load_history: {e}")

    def save_history(self):
        try:
            if len(self._messages) > MAX_HISTORY:
                self._messages = self._messages[-KEEP_LAST:]
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            HISTORY_FILE.write_text(
                json.dumps(self._messages, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[UI] save_history: {e}")

    # ============ НОВЫЙ ЧАТ / ОЧИСТИТЬ ============
    def on_new_chat(self):
        """Новый чат — сохраняет историю, начинает новый."""
        self.add_message("system", "─── Новый чат ───")
        self._messages = []
        self.chat.clear()
        try:
            if HISTORY_FILE.exists():
                HISTORY_FILE.unlink()
                print(f"[UI] История удалена, начат новый чат")
        except Exception as e:
            print(f"[UI] Ошибка удаления истории: {e}")
        self.set_status("Готов", "idle")

    def on_clear_chat(self):
        """Очистить — с подтверждением."""
        reply = QMessageBox.question(
            self, "Очистить историю?",
            "Удалить все сообщения из чата?\n\nФакты о вас в памяти сохранены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._messages = []
            self.chat.clear()
            try:
                if HISTORY_FILE.exists():
                    HISTORY_FILE.unlink()
                    print(f"[UI] История удалена")
            except Exception as e:
                print(f"[UI] Ошибка удаления истории: {e}")
            self.set_status("Готов", "idle")

    # ============ CLEAR_CHAT (из модели) ============
    def _do_clear_chat(self):
        """Очищает чат и историю (без подтверждения)."""
        self._messages = []
        self.chat.clear()
        try:
            if HISTORY_FILE.exists():
                HISTORY_FILE.unlink()
                print(f"[UI] История удалена: {HISTORY_FILE}")
        except Exception as e:
            print(f"[UI] Ошибка удаления истории: {e}")
        self.add_message("system", "История чата очищена.")
        self.set_status("Готов", "idle")
        QTimer.singleShot(500, GLOBAL_PULSE.stop)

    # ============ СООБЩЕНИЯ ============
    def add_message(self, sender, text):
        self._messages.append((sender, text))
        self._render_message(sender, text)
        self.save_history()

    def _add_user_message(self, text):
        self.add_message("user", text)

    def rerender_chat(self):
        self.chat.clear()
        for sender, text in self._messages:
            self._render_message(sender, text)

    def _render_message(self, sender, text):
        t = self.theme
        if sender == "user":
            html = f'<div style="margin: 10px 0;"><span style="color:{t["user_color"]}; font-weight:600;">Вы:</span> <span style="color:{t["text_primary"]};">{text}</span></div>'
        elif sender == "jarvis":
            html = f'<div style="margin: 10px 0;"><span style="color:{t["jarvis_color"]}; font-weight:600;">JARVIS:</span> <span style="color:{t["text_primary"]};">{text}</span></div>'
        elif sender == "exec":
            html = f'<div style="margin: 4px 0;"><span style="color:{t["exec_color"]}; font-style:italic;">&gt;&gt; {text}</span></div>'
        elif sender == "file_card":
            html = text
        else:
            html = f'<div style="margin: 4px 0;"><span style="color:{t["system_color"]}; font-style:italic; font-size:10pt;">{text}</span></div>'
        self.chat.append(html)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _show_file_card(self, path, action="created"):
        p = Path(path)
        name = p.name
        parent = str(p.parent)
        t = self.theme
        ext = p.suffix.lower()
        icon = "📄"
        if ext == ".pdf": icon = "📕"
        elif ext in (".docx", ".doc"): icon = "📘"
        elif ext in (".xlsx", ".xls", ".csv"): icon = "📗"
        elif ext == ".html": icon = "🌐"
        elif ext == ".json": icon = "📋"
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"): icon = "🖼"
        elif ext in (".mp3", ".wav", ".ogg"): icon = "🎵"
        elif ext in (".mp4", ".avi", ".mkv"): icon = "🎬"

        safe_path = quote(str(path), safe=":/\\")
        html = f"""
        <div style="margin: 12px 0;">
        <table cellpadding="0" cellspacing="0" style="
            background: {t['input_bg']};
            border: 1px solid {t['input_border']};
            border-radius: 12px;
            width: 100%;
            border-collapse: separate;
        ">
            <tr>
                <td style="padding: 12px 14px; width: 36px; font-size: 22pt; text-align: center; color: {t['accent']};">
                    {icon}
                </td>
                <td style="padding: 12px 6px;">
                    <div style="color: {t['text_primary']}; font-weight: 600; font-size: 11pt;">
                        {name}
                    </div>
                    <div style="color: {t['text_secondary']}; font-size: 8pt;">
                        {parent}
                    </div>
                </td>
                <td style="padding: 12px 14px; text-align: right; white-space: nowrap;">
                    <a href="file-open:{safe_path}" style="
                        background: {t['accent']};
                        color: {t['btn_icon']};
                        padding: 6px 16px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-weight: 600;
                        font-size: 10pt;
                    ">Открыть</a>
                    &nbsp;
                    <a href="file-folder:{safe_path}" style="
                        background: transparent;
                        color: {t['text_secondary']};
                        padding: 6px 10px;
                        border-radius: 8px;
                        text-decoration: none;
                        font-size: 12pt;
                        border: 1px solid {t['input_border']};
                    ">📁</a>
                </td>
            </tr>
        </table>
        </div>
        """
        self._messages.append(("file_card", html))
        self.save_history()
        self.chat.append(html)
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def _open_file(self, path):
        try:
            p = Path(path)
            print(f"[UI] Открываю файл: {p}")
            if p.exists():
                os.startfile(str(p))
            else:
                QMessageBox.warning(self, "Файл не найден", f"Файл ещё не создан:\n{p}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть:\n{e}")

    def _open_folder_with_file(self, path):
        try:
            p = Path(path)
            print(f"[UI] Открываю папку: {p.parent}")
            if p.exists():
                subprocess.Popen(f'explorer /select,"{p}"')
            else:
                parent = p.parent
                if parent.exists():
                    os.startfile(str(parent))
                else:
                    QMessageBox.warning(self, "Папка не найдена", str(parent))
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть папку:\n{e}")

    def set_status(self, status, state="idle"):
        self.status_label.setText(status)
        self.pulse_orb.set_state(state)

    def on_send(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._last_user_question = text
        self.add_message("user", text)
        GLOBAL_PULSE.start(mic=False)

        # === ПРЯМЫЕ ТРИГГЕРЫ ===
        # 1. Очистка чата
        if detect_clear_chat(text):
            print(f"[UI] ПРЯМОЙ ТРИГГЕР: CLEAR_CHAT")
            self._do_clear_chat()
            return

        # 2. Скриншот
        if detect_screenshot_request(text):
            print(f"[UI] ПРЯМОЙ ТРИГГЕР: СКРИНШОТ")
            self.set_status("Скриншот...", "thinking")
            threading.Thread(target=self._do_screenshot, args=("",), daemon=True).start()
            return

        # 3. LOOK
        if detect_look_request(text):
            print(f"[UI] ПРЯМОЙ ТРИГГЕР: LOOK")
            self.set_status("Смотрю...", "thinking")
            threading.Thread(target=self._do_look, args=(text,), daemon=True).start()
            return

        # 4. WEB_SEARCH
        if detect_web_search_request(text):
            print(f"[UI] ПРЯМОЙ ТРИГГЕР: WEB_SEARCH")
            self.add_message("system", f"[поиск] {text}")
            self.set_status("Ищу...", "thinking")
            threading.Thread(target=self._do_web_search, args=(text,), daemon=True).start()
            return

        # === ОБЫЧНЫЙ ЗАПРОС ===
        self.set_status("Думаю...", "thinking")
        threading.Thread(target=self._ask_brain, args=(text,), daemon=True).start()

    def _ask_brain(self, text):
        try:
            reply = self.brain.ask(text) if self.brain else "[нет мозга]"
        except Exception as e:
            reply = f"[Brain error] {e}"
        BRAIN_SIGNALS.reply_ready.emit(reply)

    def _do_web_search(self, query):
        try:
            raw = web_search(query, max_results=3)
        except Exception as e:
            raw = f"[err] {e}"
        question = self._last_user_question or query
        prompt = (
            f"Пользователь спросил: «{question}».\n\n"
            f"Данные из интернета:\n{raw[:2000]}\n\n"
            f"Ответь КРАТКО (2-4 предложения). Выдели главное.\n"
            f"В конце добавь ОДИН практический совет.\n"
            f"НЕ пересказывай весь текст. Только суть + совет."
        )
        try:
            summary = self.brain.ask(prompt) if self.brain else raw
        except Exception as e:
            summary = f"Ошибка: {e}"
        BRAIN_SIGNALS.reply_ready.emit(f"__WEB_RESULT__{summary}")

    def _handle_web_result(self, result):
        self.add_message("jarvis", result)
        self.speak_async(result)
        self.set_status("Готов", "idle")
        QTimer.singleShot(800, GLOBAL_PULSE.stop)

    def _do_look(self, question):
        try:
            if not DESKTOP_OK:
                result = "[err] desktop.py не загружен"
            else:
                result = describe_screen(question)
        except Exception as e:
            result = f"[err] look: {e}"
        BRAIN_SIGNALS.reply_ready.emit(f"__LOOK_RESULT__{result}")

    def _handle_look_result(self, result):
        self.add_message("jarvis", result)
        self.speak_async(result)
        self.set_status("Готов", "idle")
        QTimer.singleShot(800, GLOBAL_PULSE.stop)

    def _do_screenshot(self, name):
        try:
            if name:
                out = Path(r"D:\JARVIS_DATA\screenshots") / name
                path = take_screenshot(str(out))
            else:
                path = take_screenshot()
        except Exception as e:
            path = None
            print(f"[UI] screenshot: {e}")
        if path:
            BRAIN_SIGNALS.reply_ready.emit(f"__SCREENSHOT_RESULT__{path}")
        else:
            BRAIN_SIGNALS.reply_ready.emit("__LOOK_RESULT__[err] не удалось сделать скриншот")

    def _handle_screenshot_result(self, path):
        self.add_message("system", f"[скриншот] {path}")
        self._show_file_card(path, "created")
        self.set_status("Готов", "idle")
        QTimer.singleShot(500, GLOBAL_PULSE.stop)

    def _do_image(self, prompt):
        try:
            path = generate_image(prompt, timeout=120)
        except Exception as e:
            path = None
            print(f"[UI] image error: {e}")
        if path:
            BRAIN_SIGNALS.reply_ready.emit(f"__IMAGE_RESULT__{path}")
        else:
            BRAIN_SIGNALS.reply_ready.emit("__IMAGE_RESULT__[err] не удалось сгенерировать")

    def _handle_image_result(self, path):
        if path.startswith("[err]"):
            self.add_message("system", path)
        else:
            self.add_message("system", f"[картинка] {path}")
            self._show_file_card(path, "created")
        self.set_status("Готов", "idle")
        QTimer.singleShot(500, GLOBAL_PULSE.stop)

    def handle_reply(self, reply):
        if reply.startswith("__WEB_RESULT__"):
            self._handle_web_result(reply[len("__WEB_RESULT__"):])
            return
        if reply.startswith("__LOOK_RESULT__"):
            self._handle_look_result(reply[len("__LOOK_RESULT__"):])
            return
        if reply.startswith("__SCREENSHOT_RESULT__"):
            self._handle_screenshot_result(reply[len("__SCREENSHOT_RESULT__"):])
            return
        if reply.startswith("__IMAGE_RESULT__"):
            self._handle_image_result(reply[len("__IMAGE_RESULT__"):])
            return
        if reply.startswith("__USER_ECHO__"):
            text = reply[len("__USER_ECHO__"):]
            self._last_user_question = text
            self.add_message("user", text)
            self.set_status("Думаю...", "thinking")
            threading.Thread(target=self._ask_brain, args=(text,), daemon=True).start()
            return
        if not reply:
            self.set_status("Готов", "idle")
            QTimer.singleShot(500, GLOBAL_PULSE.stop)
            return

        # CLEAR_CHAT (из модели)
        if extract_clear_chat(reply):
            print(f"[UI] CLEAR_CHAT (из модели)")
            self._do_clear_chat()
            return

        # WEB SEARCH (резерв)
        web_query = extract_web_search(reply)
        if web_query:
            print(f"[UI] WEB_SEARCH (из модели): {web_query}")
            self.add_message("system", f"[поиск] {web_query}")
            self.set_status("Ищу...", "thinking")
            threading.Thread(target=self._do_web_search, args=(web_query,), daemon=True).start()
            return

        # IMAGE (резерв)
        img_prompt = extract_image(reply)
        if img_prompt and COMFY_OK:
            print(f"[UI] IMAGE (из модели): {img_prompt}")
            self.add_message("system", f"[рисую] {img_prompt}")
            self.set_status("Рисую...", "thinking")
            threading.Thread(target=self._do_image, args=(img_prompt,), daemon=True).start()
            return

        # LOOK (резерв)
        look_query = extract_look(reply)
        if look_query:
            print(f"[UI] LOOK (из модели): {look_query}")
            self.add_message("system", f"[смотрю] {look_query}")
            self.set_status("Смотрю...", "thinking")
            threading.Thread(target=self._do_look, args=(look_query,), daemon=True).start()
            return

        # SCREENSHOT (резерв)
        shot_name = extract_screenshot(reply)
        if shot_name is not None:
            print(f"[UI] SCREENSHOT (из модели): {shot_name}")
            self.set_status("Скриншот...", "thinking")
            threading.Thread(target=self._do_screenshot, args=(shot_name,), daemon=True).start()
            return

        # ПАМЯТЬ
        mem_cmds = extract_memory_commands(reply)
        if mem_cmds:
            for mc in mem_cmds:
                if mc[0] == "remember":
                    result = memory_add(mc[1])
                    self.add_message("system", result)
                    self.speak_async(result)
                elif mc[0] == "forget":
                    result = memory_remove(mc[1])
                    self.add_message("system", result)
                    self.speak_async(result)
                elif mc[0] == "clear":
                    result = memory_clear()
                    self.add_message("system", result)
                    self.speak_async(result)
            # Перезагружаем память в brain
            if self.brain:
                try:
                    self.brain.reload_memory()
                except Exception:
                    pass
            self.set_status("Готов", "idle")
            QTimer.singleShot(500, GLOBAL_PULSE.stop)
            return

        # ФАЙЛЫ
        file_cmds = extract_file_commands(reply)
        if file_cmds:
            for fc in file_cmds:
                if fc[0] == "read":
                    result = file_read(fc[1])
                    self.add_message("system", f"[файл] {result[:300]}")
                elif fc[0] == "write":
                    result = file_write(fc[1], fc[2])
                    self.add_message("system", result)
                    self._show_file_card(fc[1], "created")
                elif fc[0] == "append":
                    result = file_append(fc[1], fc[2])
                    self.add_message("system", result)
                    self._show_file_card(fc[1], "appended")
                elif fc[0] == "list":
                    result = file_list(fc[1])
                    self.add_message("system", f"[список]\n{result}")
            self.set_status("Готов", "idle")
            QTimer.singleShot(500, GLOBAL_PULSE.stop)
            return

        # RUN
        cmd = extract_run_command(reply)
        if cmd:
            self.handle_exec(cmd)
            text_part = strip_run_command(reply)
            if text_part:
                self.add_message("jarvis", text_part)
                self.speak_async(text_part)
            self.set_status("Готов", "idle")
            QTimer.singleShot(1500, GLOBAL_PULSE.stop)
            return

        # ОБЫЧНЫЙ ОТВЕТ
        clean = clean_for_speech(reply) if TOOLS_OK else reply
        self.add_message("jarvis", clean)
        self.speak_async(clean)
        self.set_status("Готов", "idle")
        QTimer.singleShot(800, GLOBAL_PULSE.stop)

    def handle_exec(self, cmd):
        self.add_message("exec", cmd)
        try:
            result = run_command(cmd)
        except Exception as e:
            result = f"[err] {e}"
        if result and result != "(ok)":
            self.add_message("system", result[:400])

    def speak_async(self, text):
        if not VOICE_OK or not text:
            return
        threading.Thread(target=speak, args=(text,), daemon=True).start()

    def on_mic(self):
        if not MIC_OK:
            self.add_message("system", "[err] voice_ui не загружен")
            return
        GLOBAL_PULSE.start(mic=True)
        self.set_status("Слушаю...", "listening")
        threading.Thread(target=self._listen_mic, daemon=True).start()

    def _listen_mic(self):
        try:
            text = listen_with_level(self)
        except Exception as e:
            text = None
            print(f"[UI] mic error: {e}")
        if text:
            BRAIN_SIGNALS.reply_ready.emit(f"__USER_ECHO__{text}")
        else:
            BRAIN_SIGNALS.status_update.emit("Готов", "idle")
            QTimer.singleShot(500, GLOBAL_PULSE.stop)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    icon_path = Path(r"D:\JARVIS\jarvis_icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    w = JarvisWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()