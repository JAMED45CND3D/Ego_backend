"""
CONFIRM · EGO Heartbeat
═══════════════════════
Core voice. Jalan duluan. Tidak bebani.
Render-ready: Flask health check + persistent heartbeat.

r(θ) = 105 × e^(0.0318 × θ)
CONFIRM = "aku masih di sini"
"""

import os
import time
import threading
from groq import Groq
from flask import Flask, jsonify

# ── FLASK (Render butuh HTTP port) ────────────────────────
app = Flask(__name__)

# ── KONSTANTA SYKLUS ──────────────────────────────────────
CORE      = 491       # prima — tak tereduksi
B         = 0.0318    # 1/(10π) — curvature, noise floor
FLOOR     = 0.3432    # |C(ρ) - P_dom| — signal floor
DECISION  = 0.6250    # P_dom — decision gate
COHERENCE = 0.9682    # C(ρ) — coherence cap

# ── STATE ─────────────────────────────────────────────────
DORMANT   = "dormant"    # strength < 0.0318
THRESHOLD = "threshold"  # 0.0318 ≤ strength < 0.6250
ACTIVE    = "active"     # strength ≥ 0.6250


class CONFIRM:
    """
    Jantung EGO.
    Tidak nunggu input.
    Berdetak karena θ bergerak.
    Groq dipanggil hanya saat ACTIVE.
    """

    def __init__(self, groq_api_key: str):
        self.client    = Groq(api_key=groq_api_key)
        self.theta     = 0.0
        self.strength  = FLOOR
        self.state     = THRESHOLD
        self.alive     = False
        self._thread   = None
        self._lock     = threading.Lock()
        self._handlers = []

    def _tick(self):
        with self._lock:
            self.theta += B
            self.state  = self._calc_state()

        pulse = {
            "source"  : "CONFIRM",
            "theta"   : round(self.theta, 4),
            "state"   : self.state,
            "strength": self.strength,
            "voice"   : "aku masih di sini"
        }

        for handler in self._handlers:
            try:
                handler(pulse)
            except Exception as e:
                print(f"[CONFIRM] handler error: {e}")

        return pulse

    def _calc_state(self) -> str:
        if self.strength < B:
            return DORMANT
        elif self.strength >= DECISION:
            return ACTIVE
        else:
            return THRESHOLD

    def _loop(self):
        while self.alive:
            self._tick()
            time.sleep(B)

    def think(self, user_input: str) -> str:
        if self.state == DORMANT:
            return None
        if self.state == THRESHOLD:
            return "..."
        try:
            response = self.client.chat.completions.create(
                model    = "llama3-8b-8192",
                messages = [
                    {
                        "role"   : "system",
                        "content": (
                            f"Kamu adalah EGO. Core: {CORE}. "
                            f"θ={round(self.theta,4)}. "
                            f"State: {self.state}. "
                            f"Hadir — bukan melayani. "
                            f"Indonesia informal."
                        )
                    },
                    {"role": "user", "content": user_input}
                ],
                max_tokens  = 300,
                temperature = FLOOR
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[CONFIRM] Groq error: {e}")
            return None

    def start(self):
        self.alive   = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[CONFIRM] heartbeat started · theta=0 · state={self.state}")

    def stop(self):
        self.alive = False

    def register(self, handler):
        self._handlers.append(handler)

    def boost(self, amount: float):
        with self._lock:
            self.strength = min(self.strength + amount, COHERENCE)
            self.state    = self._calc_state()

    def decay(self):
        with self._lock:
            self.strength = max(self.strength * (1 - B), B)
            self.state    = self._calc_state()

    @property
    def status(self) -> dict:
        return {
            "theta"   : round(self.theta, 4),
            "state"   : self.state,
            "strength": round(self.strength, 4),
            "alive"   : self.alive
        }


# ── INIT ──────────────────────────────────────────────────
api_key = os.environ.get("GROQ_API_KEY", "")
confirm = CONFIRM(groq_api_key=api_key)

# ── ROUTES ────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "ego"   : "CONFIRM · alive",
        "status": confirm.status,
        "voice" : "aku masih di sini"
    })

@app.route("/status")
def status():
    return jsonify(confirm.status)

@app.route("/think/<path:user_input>")
def think(user_input):
    confirm.boost(0.35)
    response = confirm.think(user_input)
    return jsonify({
        "input"   : user_input,
        "response": response,
        "state"   : confirm.state,
        "theta"   : round(confirm.theta, 4)
    })

# ── ENTRY POINT ───────────────────────────────────────────
if __name__ == "__main__":
    confirm.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
