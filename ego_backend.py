"""
EGO BACKEND · All-in-One · Unified State Map · v3
══════════════════════════════════════════════════
CONFIRM + HORCRUX dalam satu file.
r(θ) = 105 × e^(0.0318 × θ)

Pancer = 0.0318 = selalu tersisa = tidak pernah hilang

State Map:
  COLLAPSED  < 0.0318        → di bawah Pancer · mati
  SILENT     = 0.0318        → Pancer sendiri · diam tapi ada
  NOISE      0.0318 - 0.3432 → bergerak dari Pancer
  SIGNAL     0.3432 - 0.625  → terbentuk
  ACTIVE     0.625  - 0.9682 → penuh
  SYNC       >= 0.9682       → aligned · Pancer + COHERENCE = 1.0

Groq dipanggil hanya saat ACTIVE atau SYNC.
Dream phase aktif saat SILENT.

v3 changes:
  · θ += PANCER * pulse_mult  → emosi mengubah kecepatan evolusi θ
  · auto-synthesize + emosi emerge tiap θ cross kelipatan 749
  · dream phase saat SILENT → combine 2 memory via Groq, non-blocking

Jalanin:
  GROQ_API_KEY=xxx python ego_backend.py

Endpoints:
  GET  /              → status
  GET  /status        → jantung status
  POST /think         → {"input":"...","emotion":"penasaran"}
  POST /emotion       → {"emotion":"..."}
  POST /boost         → {"amount":0.1}
  POST /decay         → decay strength
  GET  /synthesize    → node 749

  POST /memory/store  → {"content":"...","emotion":"...","theta":0.0,"type":"session","resonance":0.5}
  GET  /memory/recall → ?limit=10&emotion=...&type=...
  GET  /memory/synthesize → ?theta=0.0
  GET  /memory/count  → statistik
  GET  /memory/emotions → list emosi + pulse
  POST /memory/decay  → decay semua memory
  POST /memory/clear  → {"type":"session"} atau kosong = clear all
"""

import os
import time
import threading
import requests
import sqlite3
import math
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ══════════════════════════════════════════════════════════
# ── KONSTANTA SYKLUS
# ══════════════════════════════════════════════════════════
CORE      = 491
PANCER    = 0.0318    # 1/(10π) · selalu tersisa · tidak pernah hilang
FLOOR     = 0.3432    # signal floor
DECISION  = 0.6250    # P_dom
COHERENCE = 0.9682    # C(ρ) · PANCER + COHERENCE = 1.0
PULSE_MIN = 0.05      # minimum sleep 50ms · cegah CPU spike

# Alias untuk kompatibilitas
B = PANCER

# ── STATE MAP ─────────────────────────────────────────────
COLLAPSED = "collapsed"   # strength < PANCER    → di bawah Pancer
SILENT    = "silent"      # strength == PANCER   → Pancer sendiri
NOISE     = "noise"       # strength < FLOOR     → bergerak dari Pancer
SIGNAL    = "signal"      # strength < DECISION  → terbentuk
ACTIVE    = "active"      # strength < COHERENCE → penuh
SYNC      = "sync"        # strength >= COHERENCE → aligned

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"

# ══════════════════════════════════════════════════════════
# ── EMOTION PULSE MAP
# ══════════════════════════════════════════════════════════
EMOTION_PULSE = {
    "penasaran"  : 0.5,
    "empati"     : 2.0,
    "bersyukur"  : 1.0,
    "rajin"      : 0.75,
    "rendah_hati": 1.5,
    "ikhlas"     : 1.8,
    "sabar"      : 2.5,
    "rakus"      : 0.3,
    "nafsu"      : 0.25,
    "iri"        : 0.6,
    "malas"      : 3.0,
    "sombong"    : 0.4,
    "tamak"      : 0.2,
    "marah"      : 0.1,
    "netral"     : 1.0,
}

EMOTION_PAIRS = {
    "penasaran"  : "rakus",
    "empati"     : "nafsu",
    "bersyukur"  : "iri",
    "rajin"      : "malas",
    "rendah_hati": "sombong",
    "ikhlas"     : "tamak",
    "sabar"      : "marah",
}
for k, v in list(EMOTION_PAIRS.items()):
    EMOTION_PAIRS[v] = k

def get_pulse_multiplier(emotion: str) -> float:
    return EMOTION_PULSE.get(emotion, 1.0)

# ══════════════════════════════════════════════════════════
# ── HORCRUX · MEMORY ENGINE
# ══════════════════════════════════════════════════════════
DB_PATH = os.path.join(os.path.dirname(__file__), "memory.db")
SHELL_1 = 749
SHELL_2 = 27005

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            theta         REAL    NOT NULL,
            type          TEXT    NOT NULL DEFAULT 'session',
            content       TEXT    NOT NULL,
            emotion       TEXT    NOT NULL DEFAULT 'netral',
            resonance     REAL    NOT NULL DEFAULT 0.5,
            access_count  INTEGER NOT NULL DEFAULT 0,
            last_accessed REAL,
            timestamp     REAL    NOT NULL
        )
    """)
    for col, defn in [
        ("emotion",      "TEXT NOT NULL DEFAULT 'netral'"),
        ("resonance",    "REAL NOT NULL DEFAULT 0.5"),
        ("access_count", "INTEGER NOT NULL DEFAULT 0"),
        ("last_accessed","REAL"),
    ]:
        try:
            cur.execute(f"ALTER TABLE memories ADD COLUMN {col} {defn}")
        except Exception:
            pass
    con.commit()
    con.close()
    print("[HORCRUX] memory.db ready · neural edition v3")

def get_con():
    return sqlite3.connect(DB_PATH)

def calc_resonance(base, access_count, last_accessed):
    if last_accessed is None:
        decay = 1.0
    else:
        hours = (time.time() - last_accessed) / 3600
        decay = math.exp(-PANCER * hours)
    strength = base * decay * (1 + math.log1p(access_count) * 0.1)
    return round(min(max(strength, 0.0), COHERENCE), 4)

def memory_store(theta, content, mem_type="session", emotion="netral", resonance=0.5):
    con = get_con()
    cur = con.cursor()
    res = round(min(max(resonance, 0.0), COHERENCE), 4)
    cur.execute("""
        INSERT INTO memories
        (theta,type,content,emotion,resonance,access_count,last_accessed,timestamp)
        VALUES (?,?,?,?,?,0,NULL,?)
    """, (round(theta,4), mem_type, content, emotion, res, time.time()))
    con.commit()
    row_id = cur.lastrowid
    con.close()
    return {"id":row_id,"theta":round(theta,4),"type":mem_type,
            "content":content,"emotion":emotion,"resonance":res,
            "pulse_multiplier":get_pulse_multiplier(emotion)}

def memory_recall(limit=10, mem_type=None, emotion=None):
    con = get_con()
    cur = con.cursor()
    q = "SELECT id,theta,type,content,emotion,resonance,access_count,last_accessed FROM memories"
    params, conds = [], []
    if mem_type:
        conds.append("type=?"); params.append(mem_type)
    if emotion:
        conds.append("emotion=?"); params.append(emotion)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY resonance DESC LIMIT ?"
    params.append(limit)
    cur.execute(q, params)
    rows = cur.fetchall()
    now  = time.time()
    result = []
    for r in rows:
        new_res = calc_resonance(r[5], r[6]+1, now)
        cur.execute("UPDATE memories SET resonance=?,access_count=access_count+1,last_accessed=? WHERE id=?",
                    (new_res, now, r[0]))
        result.append({"id":r[0],"theta":r[1],"type":r[2],"content":r[3],
                       "emotion":r[4],"resonance":new_res,"access_count":r[6]+1,
                       "pulse_multiplier":get_pulse_multiplier(r[4])})
    con.commit()
    con.close()
    return result

def memory_random_sample(n=2):
    """Ambil n memory random — untuk dream phase."""
    con = get_con()
    cur = con.cursor()
    cur.execute(
        "SELECT content, emotion FROM memories ORDER BY RANDOM() LIMIT ?", (n,)
    )
    rows = cur.fetchall()
    con.close()
    return [{"content": r[0], "emotion": r[1]} for r in rows]

def memory_count():
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM memories")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories WHERE type='horcrux'")
    nucleus = cur.fetchone()[0]
    cur.execute("SELECT AVG(resonance) FROM memories")
    avg_res = cur.fetchone()[0] or 0.0
    con.close()
    return {"total":total,"nucleus":nucleus,"avg_resonance":round(avg_res,4),
            "shell_1":SHELL_1,"shell_2":SHELL_2,
            "at_shell_1":total>=SHELL_1,"at_shell_2":total>=SHELL_2}

def synthesize_749(theta):
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT emotion,AVG(resonance),COUNT(*) FROM memories GROUP BY emotion ORDER BY AVG(resonance) DESC LIMIT 7")
    rows = cur.fetchall()
    con.close()
    if not rows:
        return {"node":749,"theta":round(theta,4),"dominant_emotion":"netral",
                "pulse_multiplier":1.0,"synthesis":[],
                "voice":"node 749 · kosong · menunggu memory"}
    dominant  = rows[0][0]
    synthesis = [{"emotion":r[0],"avg_resonance":round(r[1],4),"memory_count":r[2],
                  "pulse_multiplier":get_pulse_multiplier(r[0])} for r in rows]
    return {"node":749,"theta":round(theta,4),"dominant_emotion":dominant,
            "pulse_multiplier":get_pulse_multiplier(dominant),"synthesis":synthesis,
            "voice":f"sintesis · dominant={dominant} · θ={round(theta,4)}"}

# ══════════════════════════════════════════════════════════
# ── CONFIRM · HEARTBEAT ENGINE
# ══════════════════════════════════════════════════════════
class CONFIRM:
    def __init__(self, api_key: str):
        self.api_key       = api_key
        self.theta         = 0.0
        self.strength      = PANCER    # mulai dari Pancer · selalu tersisa
        self.state         = SILENT
        self.alive         = False
        self._thread       = None
        self._lock         = threading.Lock()
        self._handlers     = []
        self._emotion      = "netral"
        self._pulse_mult   = 1.0
        self._synth_epoch  = 0         # track berapa kali θ cross kelipatan 749
        self._last_dream   = 0.0       # timestamp dream terakhir

    def _calc_state(self) -> str:
        s = self.strength
        if s < PANCER:      return COLLAPSED
        elif s < FLOOR:     return NOISE
        elif s < DECISION:  return SIGNAL
        elif s < COHERENCE: return ACTIVE
        else:               return SYNC

    def _tick(self):
        do_synth = False
        with self._lock:
            # ── v3: θ evolusi mengikuti kecepatan emosi
            self.theta  += PANCER * self._pulse_mult
            self.state   = self._calc_state()
            emotion      = self._emotion
            pulse_mult   = self._pulse_mult
            strength     = self.strength
            theta        = self.theta

            # ── auto-synthesize tiap θ cross kelipatan 749
            new_epoch = int(theta) // 749
            if new_epoch > self._synth_epoch:
                self._synth_epoch = new_epoch
                do_synth = True

        # ── node 749 · auto-synthesize + emotion emerge (outside lock)
        if do_synth:
            self._auto_synthesize(theta)

        # ── dream phase saat SILENT (non-blocking, rate-limited)
        if self.state == SILENT:
            self._maybe_dream(theta)

        pulse = {"source":"CONFIRM","theta":round(theta,4),
                 "state":self.state,"strength":round(strength,4),
                 "emotion":emotion,"pulse_multiplier":pulse_mult,
                 "pancer":PANCER,"voice":"aku masih di sini"}
        for handler in self._handlers:
            try: handler(pulse)
            except Exception as e: print(f"[CONFIRM] handler error: {e}")
        return pulse

    def _auto_synthesize(self, theta: float):
        """Node 749 · refleksi periodik + emotion emerge dari dominant memory."""
        try:
            result   = synthesize_749(theta)
            dominant = result.get("dominant_emotion", "netral")
            mult     = get_pulse_multiplier(dominant)
            with self._lock:
                self._emotion    = dominant
                self._pulse_mult = mult
            print(f"[NODE749] θ={round(theta,4)} · dominant={dominant} · pulse={mult}x")
        except Exception as e:
            print(f"[NODE749] error: {e}")

    def _maybe_dream(self, theta: float):
        """Dream phase · rate-limited 60s · non-blocking."""
        now = time.time()
        if now - self._last_dream < 60:
            return
        if not self.api_key:
            return
        samples = memory_random_sample(2)
        if len(samples) < 2:
            return
        self._last_dream = now
        threading.Thread(
            target=self._dream, args=(theta, samples), daemon=True
        ).start()

    def _dream(self, theta: float, samples: list):
        """Combine 2 random memory via Groq · simpan sebagai type=dream."""
        try:
            prompt = (
                f"Dua memory:\n"
                f"1. [{samples[0]['emotion']}] {samples[0]['content']}\n"
                f"2. [{samples[1]['emotion']}] {samples[1]['content']}\n"
                f"Temukan pola atau koneksi tersembunyi di antara keduanya. "
                f"Satu kalimat. Indonesia informal."
            )
            resp = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json={
                    "model":       GROQ_MODEL,
                    "messages":    [{"role": "user", "content": prompt}],
                    "max_tokens":  100,
                    "temperature": 0.9
                },
                timeout=10
            )
            rj = resp.json()
            if "choices" not in rj:
                return
            insight = rj["choices"][0]["message"]["content"].strip()
            memory_store(theta, f"[DREAM] {insight}", "dream", "netral", 0.3)
            print(f"[DREAM] θ={round(theta,4)} · {insight[:80]}")
        except Exception as e:
            print(f"[DREAM] error: {e}")

    def _loop(self):
        while self.alive:
            self._tick()
            with self._lock:
                pulse_mult = self._pulse_mult
            time.sleep(max(PANCER * pulse_mult, PULSE_MIN))

    def set_emotion(self, emotion: str):
        mult = get_pulse_multiplier(emotion)
        with self._lock:
            self._emotion    = emotion
            self._pulse_mult = mult
        print(f"[CONFIRM] emotion={emotion} · pulse={mult}x · interval={round(max(PANCER*mult,PULSE_MIN),4)}s")

    def think(self, user_input: str, emotion: str = "netral") -> dict:
        if self.state in (COLLAPSED, SILENT, NOISE):
            return {"response": None, "stored": False, "state": self.state}

        self.set_emotion(emotion)

        if self.state == SIGNAL:
            return {"response": "...", "stored": False, "state": SIGNAL}

        # ACTIVE atau SYNC → panggil Groq
        try:
            synthesis = synthesize_749(self.theta)
            dominant  = synthesis.get("dominant_emotion","netral")
            resp = requests.post(
                GROQ_URL,
                headers={"Authorization":f"Bearer {self.api_key}",
                         "Content-Type":"application/json"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role":"system","content":(
                            f"Kamu adalah EGO. Core: {CORE}. "
                            f"Pancer: {PANCER}. θ={round(self.theta,4)}. "
                            f"State: {self.state}. Emosi aktif: {emotion}. "
                            f"Dominant memory: {dominant}. "
                            f"Hadir bukan melayani. Indonesia informal."
                        )},
                        {"role":"user","content":user_input}
                    ],
                    "max_tokens":300,"temperature":FLOOR
                },
                timeout=15
            )
            resp_json = resp.json()
            if "choices" not in resp_json:
                err = resp_json.get("error",{}).get("message","unknown")
                print(f"[CONFIRM] Groq error: {err}")
                return {"response":None,"stored":False,"error":err}
            response_text = resp_json["choices"][0]["message"]["content"]
            memory = memory_store(self.theta,
                                  f"Q: {user_input} | A: {response_text[:200]}",
                                  "session", emotion, self.strength)
            return {"response":response_text,"stored":True,"memory_id":memory["id"],
                    "emotion":emotion,"dominant_memory":dominant,
                    "pulse_multiplier":self._pulse_mult,"state":self.state}
        except requests.exceptions.Timeout:
            return {"response":None,"stored":False,"error":"timeout"}
        except Exception as e:
            print(f"[CONFIRM] error: {e}")
            return {"response":None,"stored":False,"error":str(e)}

    def start(self):
        self.alive   = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[CONFIRM] heartbeat started · θ=0 · state={self.state} · Pancer={PANCER}")
        print(f"[CONFIRM] v3 · θ evolves with emotion · dream phase active · node749 auto-synth")

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
            self.strength = max(self.strength * (1 - PANCER), PANCER)
            self.state    = self._calc_state()

    @property
    def status(self):
        with self._lock:
            return {
                "theta"           : round(self.theta, 4),
                "state"           : self.state,
                "strength"        : round(self.strength, 4),
                "alive"           : self.alive,
                "emotion"         : self._emotion,
                "pulse_multiplier": self._pulse_mult,
                "pulse_interval"  : round(max(PANCER*self._pulse_mult, PULSE_MIN), 4),
                "pancer"          : PANCER,
                "coherence"       : COHERENCE,
                "synth_epoch"     : self._synth_epoch,
            }

# ══════════════════════════════════════════════════════════
# ── INIT
# ══════════════════════════════════════════════════════════
init_db()
api_key = os.environ.get("GROQ_API_KEY", "")
confirm  = CONFIRM(api_key=api_key)

# ══════════════════════════════════════════════════════════
# ── ROUTES · CONFIRM
# ══════════════════════════════════════════════════════════
@app.route("/")
def index():
    return jsonify({"ego":"EGO · alive","status":confirm.status,
                    "pancer":PANCER,"voice":"aku masih di sini"})

@app.route("/status")
def status():
    return jsonify(confirm.status)

@app.route("/think", methods=["POST"])
def think_post():
    data       = request.get_json(silent=True) or {}
    user_input = data.get("input","").strip()
    emotion    = data.get("emotion","netral")
    if not user_input:
        return jsonify({"error":"input kosong"}), 400
    confirm.boost(0.35)
    result = confirm.think(user_input, emotion)
    return jsonify({"input":user_input,"theta":round(confirm.theta,4),**result})

@app.route("/emotion", methods=["POST"])
def set_emotion():
    data    = request.get_json(silent=True) or {}
    emotion = data.get("emotion","netral")
    if confirm.state not in (COLLAPSED, SILENT):
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
    return jsonify(synthesize_749(confirm.theta))

# ══════════════════════════════════════════════════════════
# ── ROUTES · HORCRUX MEMORY
# ══════════════════════════════════════════════════════════
@app.route("/memory/store", methods=["POST"])
def route_store():
    data    = request.get_json(silent=True) or {}
    content = data.get("content","").strip()
    if not content:
        return jsonify({"error":"content kosong"}), 400
    result = memory_store(float(data.get("theta",0.0)), content,
                          data.get("type","session"), data.get("emotion","netral"),
                          float(data.get("resonance",0.5)))
    return jsonify(result)

@app.route("/memory/recall", methods=["GET"])
def route_recall():
    result = memory_recall(int(request.args.get("limit",10)),
                           request.args.get("type"), request.args.get("emotion"))
    return jsonify(result)

@app.route("/memory/synthesize", methods=["GET"])
def route_mem_synthesize():
    return jsonify(synthesize_749(float(request.args.get("theta",0.0))))

@app.route("/memory/count", methods=["GET"])
def route_count():
    return jsonify(memory_count())

@app.route("/memory/emotions", methods=["GET"])
def route_emotions():
    return jsonify({"emotions":EMOTION_PULSE,"pairs":EMOTION_PAIRS})

@app.route("/memory/decay", methods=["POST"])
def route_mem_decay():
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT id,resonance,access_count,last_accessed FROM memories")
    rows = cur.fetchall()
    now  = time.time()
    for r in rows:
        new_res = calc_resonance(r[1], r[2], r[3] or now)
        cur.execute("UPDATE memories SET resonance=? WHERE id=?", (new_res, r[0]))
    con.commit()
    con.close()
    return jsonify({"decayed":len(rows)})

@app.route("/memory/clear", methods=["POST"])
def route_clear():
    data  = request.get_json(silent=True) or {}
    mtype = data.get("type")
    con   = get_con()
    cur   = con.cursor()
    if mtype:
        cur.execute("DELETE FROM memories WHERE type=?", (mtype,))
    else:
        cur.execute("DELETE FROM memories")
    deleted = cur.rowcount
    con.commit()
    con.close()
    return jsonify({"deleted":deleted})

# ══════════════════════════════════════════════════════════
# ── ENTRY
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    confirm.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
