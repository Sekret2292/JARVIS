"""
JARVIS HTTP Server — мост между ПК и мобильным приложением.
Слушает порт 5000, принимает POST /ask, возвращает JSON с ответом от brain.
"""
import sys
import json
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, r"D:\JARVIS")

try:
    from brain import JarvisBrain
    print("[Server] brain module loaded")
except Exception as e:
    print(f"[Server] brain import failed: {e}")
    JarvisBrain = None


# ============================================================
# Инициализация мозга (один раз при старте)
# ============================================================
BRAIN = None
if JarvisBrain is not None:
    try:
        BRAIN = JarvisBrain()
        print(f"[Server] Brain initialised. Model: {getattr(BRAIN, 'model', '?')}")
    except Exception as e:
        print(f"[Server] Brain init failed: {e}")


# ============================================================
# HTTP Handler
# ============================================================
class JarvisHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Показываем только действительно важные логи
        print(f"[HTTP] {self.address_string()} - {fmt % args}")

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {
                "status": "ok",
                "brain": BRAIN is not None,
                "model": getattr(BRAIN, "model", None) if BRAIN else None,
            })
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/ask":
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw or "{}")
            text = (data.get("text") or "").strip()
            if not text:
                self._send_json(400, {"error": "empty text"})
                return

            print(f"[Ask] {text[:120]}")

            if BRAIN is None:
                self._send_json(503, {"error": "brain not available"})
                return

            t0 = time.time()
            reply = BRAIN.ask(text)
            elapsed = time.time() - t0
            print(f"[Reply] {elapsed:.1f}s - {str(reply)[:120]}")

            self._send_json(200, {
                "reply": reply or "",
                "elapsed": round(elapsed, 2),
            })

        except Exception as e:
            print(f"[Error] {e}")
            traceback.print_exc()
            self._send_json(500, {"error": str(e)})


# ============================================================
# Запуск
# ============================================================
def main():
    host = "0.0.0.0"
    port = 5000
    server = HTTPServer((host, port), JarvisHandler)
    print(f"[Server] JARVIS HTTP server listening on http://{host}:{port}")
    print(f"[Server] On local network:  http://192.168.1.72:{port}")
    print(f"[Server] Health check:      http://192.168.1.72:{port}/health")
    print("[Server] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()