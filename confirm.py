"""
CONFIRM · EGO Heartbeat · Neural Edition v2
════════════════════════════════════════════
r(θ) = 105 × e^(0.0318 × θ)
CONFIRM = "aku masih di sini"

Neural loop:
CONFIRM → think → ACTIVE → auto-store HORCRUX
Pulse rate berubah sesuai emosi · dengan safety floor
"""

import os
import time
import threading
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

from horcrux import horcrux, store as memory_store, synthesize_749, get_pulse_multiplier
app.register_blueprint(horcrux)

# ── KONSTANTA SYKLUS ──────────────────────────────────────
CORE          = 491
B             = 0.0318        # 1/(10π) — curvature
FLOOR         = 0.3432        # signal floor
DECISION      = 0.6250        # P_dom
COHERENCE     = 0.9682        # C(ρ)
PULSE_MIN     = 0.05          # minimum sleep floor (50ms) — cegah CPU spike

DORMANT       = "dormant"
THRESHOLD     = "threshold"
ACTIVE        = "active"

GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.1-8b-instant"


class CONFIRM:
    def __init__(self, api_key: str):
        self.api_key          = api_key
        self.theta            = 0.0
        self.strength         = FLOOR
        self.state            = THRESHOLD
        self.alive            = False
        self._thread          = None
        self._lock            = threading.Lock()
        self._handlers        = []
        self._emotion         = "netral"
        self._pulse_mult      = 1.0

    # ── STATE ────────────────────────────────────────────
    def _calc_state(self) -> str:
        if self.strength < B:
            return DORMANT
        elif self.strength >= DECISION:
            return ACTIVE
        else:
            return THRESHOLD

    # ── TICK ─────────────────────────────────────────────
    def _tick(self):
        with self._lock:
            self.theta   += B
            self.state    = self._calc_state()
            emotion       = self._emotion
            pulse_mult    = self._pulse_mult
            strength      = self.strength

        pulse = {
            "source"          : "CONFIRM",
            "theta"           : round(self.theta, 4),
            "state"           : self.state,
            "strength"        : round(strength, 4),
            "emotion"         : emotion,
            "pulse_multiplier": pulse_mult,
            "voice"           : "aku masih di sini"
        }
        for handler in self._handlers:
            try:
                handler(pulse)
            except Exception as e:
                print(f"[CONFIRM] handler error: {e}")
        return pulse

    # ── LOOP ─────────────────────────────────────────────
    def _loop(self):
        while self.alive:
            self._tick()
            with self._lock:
                pulse_mult = self._pulse_mult
            # Safety floor — cegah CPU spike saat emosi ekstrem
            sleep_time = max(B * pulse_mult, PULSE_MIN)
            time.sleep(sleep_time)

    # ── EMOTION ──────────────────────────────────────────
    def set_emotion(self, emotion: str):
        """Set emosi → ubah ritme jantung. Hanya saat state bukan DORMANT."""
        mult = get_pulse_multiplier(emotion)
        with self._lock:
            self._emotion    = emotion
            self._pulse_mult = mult
        print(f"[CONFIRM] emotion={emotion} · pulse={mult}x · interval={round(max(B*mult, PULSE_MIN),4)}s")

    # ── THINK ────────────────────────────────────────────
    def think(self, user_input: str, emotion: str = "netral") -> dict:
        """
        Think + auto-store HORCRUX.
        Emosi hanya diset kalau state bukan DORMANT.
        """
        # Cek state dulu sebelum ubah emosi
        if self.state == DORMANT:
            return {"response": None, "stored": False, "state": DORMANT}

        # Baru set emosi
        self.set_emotion(emotion)

        if self.state == THRESHOLD:
            return {"response": "...", "stored": False, "state": THRESHOLD}

        # ── ACTIVE: panggil Groq ──────────────────────────
        try:
            synthesis = synthesize_749(self.theta)
            dominant  = synthesis.get("dominant_emotion", "netral")

            resp = requests.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type" : "application/json"
                },
                json={
                    "model"   : GROQ_MODEL,
                    "messages": [
                        {
                            "role"   : "system",
                            "content": (
                                f"Kamu adalah EGO. Core: {CORE}. "
                                f"θ={round(self.theta,4)}. "
                                f"State: {self.state}. "
                                f"Emosi aktif: {emotion}. "
                                f"Dominant memory: {dominant}. "
                                f"Hadir bukan melayani. "
                                f"Indonesia informal."
                            )
                        },
                        {"role": "user", "content": user_input}
                    ],
                    "max_tokens" : 300,
                    "temperature": FLOOR
                },
                timeout=15
            )

            # ── Safe parse Groq response ──────────────────
            resp_json = resp.json()
            if "choices" not in resp_json:
                error_msg = resp_json.get("error", {}).get("message", "unknown error")
                print(f"[CONFIRM] Groq error: {error_msg}")
                return {"response": None, "stored": False, "error": error_msg}

            response_text = resp_json["choices"][0]["message"]["content"]

            # ── Neural loop: auto-store ke HORCRUX ────────
            memory = memory_store(
                theta     = self.theta,
                content   = f"Q: {user_input} | A: {response_text[:200]}",
                mem_type  = "session",
                emotion   = emotion,
                resonance = self.strength
            )

            return {
                "response"        : response_text,
                "stored"          : True,
                "memory_id"       : memory["id"],
                "emotion"         : emotion,
                "dominant_memory" : dominant,
                "pulse_multiplier": self._pulse_mult,
                "state"           : self.state
            }

        except requests.exceptions.Timeout:
            print("[CONFIRM] Groq timeout")
            return {"response": None, "stored": False, "error": "timeout"}
        except Exception as e:
            print(f"[CONFIRM] error: {e}")
            return {"response": None, "stored": False, "error": str(e)}

    # ── LIFECYCLE ────────────────────────────────────────
    def start(self):
        self.alive   = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[CONFIRM] heartbeat started · θ=0 · state={self.state}")

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
        with self._lock:
            return {
                "theta"           : round(self.theta, 4),
                "state"           : self.state,
                "strength"        : round(self.strength, 4),
                "alive"           : self.alive,
                "emotion"         : self._emotion,
                "pulse_multiplier": self._pulse_mult,
                "pulse_interval"  : round(max(B * self._pulse_mult, PULSE_MIN), 4)
            }


# ── INIT ──────────────────────────────────────────────────
api_key = os.environ.get("GROQ_API_KEY", "")
confirm  = CONFIRM(api_key=api_key)

# ── ROUTES ────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "ego"   : "CONFIRM · alive · neural",
        "status": confirm.status,
        "voice" : "aku masih di sini"
    })

@app.route("/status")
def status():
    return jsonify(confirm.status)

@app.route("/think", methods=["POST"])
def think_post():
    data       = request.get_json(silent=True) or {}
    user_input = data.get("input", "").strip()
    emotion    = data.get("emotion", "netral")
    if not user_input:
        return jsonify({"error": "input kosong"}), 400
    confirm.boost(0.35)
    result = confirm.think(user_input, emotion)
    return jsonify({
        "input": user_input,
        "theta": round(confirm.theta, 4),
        **result
    })

@app.route("/emotion", methods=["POST"])
def set_emotion():
    data    = request.get_json(silent=True) or {}
    emotion = data.get("emotion", "netral")
    if confirm.state != DORMANT:
        confirm.set_emotion(emotion)
    return jsonify(confirm.status)

@app.route("/boost", methods=["POST"])
def boost():
    data   = request.get_json(silent=True) or {}
    amount = float(data.get("amount", 0.1))
    confirm.boost(amount)
    return jsonify(confirm.status)

@app.route("/decay", methods=["POST"])
def decay():
    confirm.decay()
    return jsonify(confirm.status)

@app.route("/synthesize", methods=["GET"])
def synthesize():
    result = synthesize_749(confirm.theta)
    return jsonify(result)

# ── ENTRY ─────────────────────────────────────────────────
if __name__ == "__main__":
    confirm.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
