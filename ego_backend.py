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
import json
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
            raw_strength  REAL    NOT NULL DEFAULT 1.0,
            access_count  INTEGER NOT NULL DEFAULT 0,
            last_accessed REAL,
            timestamp     REAL    NOT NULL
        )
    """)
    for col, defn in [
        ("emotion",      "TEXT NOT NULL DEFAULT 'netral'"),
        ("resonance",    "REAL NOT NULL DEFAULT 0.5"),
        ("raw_strength", "REAL NOT NULL DEFAULT 1.0"),
        ("access_count", "INTEGER NOT NULL DEFAULT 0"),
        ("last_accessed","REAL"),
    ]:
        try:
            cur.execute(f"ALTER TABLE memories ADD COLUMN {col} {defn}")
        except Exception:
            pass
    con.commit()
    con.close()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_key     TEXT    NOT NULL UNIQUE,
            emotion_bias    TEXT    NOT NULL DEFAULT 'netral',
            strength        REAL    NOT NULL DEFAULT 0.1,
            activation_count INTEGER NOT NULL DEFAULT 1,
            last_activated  REAL,
            created_at      REAL    NOT NULL
        )
    """)
    print("[HORCRUX] memory.db ready · neural edition v6 · identity + meta")
    con.commit()
    con.close()

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

def calc_active_weight(raw_strength, last_accessed, K=5.0):
    """Hybrid resonance · active_weight untuk EMOSY.
    raw_strength → unbounded · naik tiap akses
    active_weight → bounded 0-1 · pakai decay
    """
    if last_accessed is None:
        age_hours = 0.0
    else:
        age_hours = (time.time() - last_accessed) / 3600
    decay  = math.exp(-0.01 * age_hours)
    weight = (raw_strength / (raw_strength + K)) * decay
    return round(max(weight, 0.0), 4)

# ══════════════════════════════════════════════════════════
# ── GOAL ENGINE · v5
# ══════════════════════════════════════════════════════════

def goal_find_or_create(pattern_key: str, emotion_bias: str) -> dict:
    """Cari goal berdasarkan pattern key, buat kalau belum ada."""
    con = get_con()
    cur = con.cursor()
    now = time.time()
    cur.execute("SELECT id,pattern_key,emotion_bias,strength,activation_count,last_activated FROM goals WHERE pattern_key=?", (pattern_key,))
    row = cur.fetchone()
    if row:
        # Update existing goal
        new_strength = min(row[3] + 0.05, COHERENCE)
        cur.execute("UPDATE goals SET strength=?,activation_count=activation_count+1,last_activated=?,emotion_bias=? WHERE id=?",
                    (new_strength, now, emotion_bias, row[0]))
        con.commit()
        con.close()
        return {"id":row[0],"pattern_key":pattern_key,"emotion_bias":emotion_bias,
                "strength":new_strength,"activation_count":row[4]+1}
    else:
        # Buat goal baru
        cur.execute("INSERT INTO goals (pattern_key,emotion_bias,strength,activation_count,last_activated,created_at) VALUES (?,?,0.1,1,?,?)",
                    (pattern_key, emotion_bias, now, now))
        con.commit()
        goal_id = cur.lastrowid
        con.close()
        return {"id":goal_id,"pattern_key":pattern_key,"emotion_bias":emotion_bias,
                "strength":0.1,"activation_count":1}

def goal_get_active(limit=3) -> list:
    """Ambil goal paling kuat saat ini."""
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT id,pattern_key,emotion_bias,strength,activation_count FROM goals ORDER BY strength DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()
    return [{"id":r[0],"pattern_key":r[1],"emotion_bias":r[2],"strength":r[3],"activation_count":r[4]} for r in rows]

def goal_decay_all():
    """Decay semua goal · strength *= 0.99 per tick."""
    con = get_con()
    cur = con.cursor()
    cur.execute("UPDATE goals SET strength = MAX(strength * 0.99, 0.001)")
    cur.execute("DELETE FROM goals WHERE strength < 0.01")
    con.commit()
    con.close()

def goal_list() -> list:
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT id,pattern_key,emotion_bias,strength,activation_count,last_activated FROM goals ORDER BY strength DESC")
    rows = cur.fetchall()
    con.close()
    return [{"id":r[0],"pattern_key":r[1],"emotion_bias":r[2],
             "strength":round(r[3],4),"activation_count":r[4],
             "last_activated":r[5]} for r in rows]

# ══════════════════════════════════════════════════════════
# ── IDENTITY ENGINE · v6
# ══════════════════════════════════════════════════════════
IDENTITY_PATH = os.path.join(os.path.dirname(__file__), "identity.json")

IDENTITY_DEFAULT = {
    "explore_bias"    : PANCER,
    "reflect_bias"    : PANCER,
    "dream_bias"      : PANCER,
    "idle_bias"       : PANCER,
    "emotional_profile": {e: PANCER for e in [
        "penasaran","empati","bersyukur","rajin","rendah_hati",
        "ikhlas","sabar","rakus","nafsu","iri","malas","sombong","tamak","marah","netral"
    ]},
    "stability"       : 0.5,
    "awareness_level" : PANCER,
    "last_snapshot"   : None,
    "drift_score"     : 0.0,
    "self_statements" : []
}

def identity_load() -> dict:
    """Load identity dari file · buat baru kalau belum ada."""
    if os.path.exists(IDENTITY_PATH):
        try:
            with open(IDENTITY_PATH, 'r') as f:
                data = json.load(f)
            # Pastiin semua key ada (backward compat)
            for k, v in IDENTITY_DEFAULT.items():
                if k not in data:
                    data[k] = v
            # Pastiin semua emosi ada di profile
            for e in IDENTITY_DEFAULT["emotional_profile"]:
                if e not in data["emotional_profile"]:
                    data["emotional_profile"][e] = PANCER
            return data
        except Exception:
            pass
    return dict(IDENTITY_DEFAULT)

def identity_save(identity: dict):
    """Simpan identity ke file."""
    try:
        # Batasi self_statements max 20
        identity["self_statements"] = identity["self_statements"][-20:]
        with open(IDENTITY_PATH, 'w') as f:
            json.dump(identity, f, indent=2)
    except Exception as e:
        print(f"[IDENTITY] save error: {e}")

def identity_normalize(identity: dict):
    """Normalize bias values · floor PANCER · tidak pernah nol."""
    bias_keys = ["explore_bias", "reflect_bias", "dream_bias", "idle_bias"]
    total = sum(identity[k] for k in bias_keys)
    if total <= 0:
        total = PANCER * len(bias_keys)
    for k in bias_keys:
        identity[k] = max(identity[k] / total, PANCER)

    # Normalize emotional profile
    ep = identity["emotional_profile"]
    ep_total = sum(ep.values())
    if ep_total <= 0:
        ep_total = PANCER * len(ep)
    for e in ep:
        ep[e] = max(ep[e] / ep_total, PANCER)

def identity_update(identity: dict, intent: str, emotion: str, active_goals: list):
    """Update identity dari intent + emosi + goal aktif."""
    # Bias update dari intent
    if intent == "explore":
        identity["explore_bias"] += 0.01
    elif intent == "reflect":
        identity["reflect_bias"] += 0.01
    elif intent == "dream":
        identity["dream_bias"] += 0.01
    else:
        identity["idle_bias"] += 0.005

    # Emotional profile update
    if emotion in identity["emotional_profile"]:
        identity["emotional_profile"][emotion] += 0.02

    # Goal alignment bias
    for goal in active_goals[:2]:
        g_emotion = goal.get("emotion_bias", "netral")
        g_strength = goal.get("strength", 0.0)
        if g_emotion in ("penasaran", "rakus"):
            identity["explore_bias"] += g_strength * 0.005
        if g_emotion in ("empati", "ikhlas", "rendah_hati"):
            identity["reflect_bias"] += g_strength * 0.005

    # Decay semua bias · floor PANCER
    for k in ["explore_bias", "reflect_bias", "dream_bias", "idle_bias"]:
        identity[k] = max(identity[k] * 0.999, PANCER)
    for e in identity["emotional_profile"]:
        identity["emotional_profile"][e] = max(
            identity["emotional_profile"][e] * 0.999, PANCER
        )

    # Normalize
    identity_normalize(identity)

def identity_snapshot(identity: dict) -> dict:
    """Ambil snapshot identity saat ini."""
    ep = identity["emotional_profile"]
    top_emotions = sorted(ep.items(), key=lambda x: x[1], reverse=True)[:3]
    bias_keys = ["explore_bias", "reflect_bias", "dream_bias", "idle_bias"]
    dominant_intent = max(bias_keys, key=lambda k: identity[k]).replace("_bias", "")
    return {
        "explore_bias"  : round(identity["explore_bias"], 4),
        "reflect_bias"  : round(identity["reflect_bias"], 4),
        "top_emotions"  : [(e, round(v, 4)) for e, v in top_emotions],
        "dominant_intent": dominant_intent,
        "stability"     : round(identity["stability"], 4),
        "awareness_level": round(identity["awareness_level"], 4),
    }

def identity_compute_drift(old_snap: dict, new_snap: dict) -> float:
    """Hitung drift antara dua snapshot."""
    if old_snap is None:
        return 0.0
    drift = abs(old_snap.get("explore_bias", 0) - new_snap.get("explore_bias", 0))
    drift += abs(old_snap.get("reflect_bias", 0) - new_snap.get("reflect_bias", 0))
    return round(min(drift, 1.0), 4)

def identity_self_statement(identity: dict, drift: float) -> str:
    """Generate self-statement dari template · tidak butuh LLM."""
    explore = identity["explore_bias"]
    reflect = identity["reflect_bias"]
    awareness = identity["awareness_level"]
    stability = identity["stability"]
    ep = identity["emotional_profile"]
    top_emotion = max(ep, key=ep.get)

    if drift > 0.3:
        return f"arah mulai bergeser · drift={round(drift,3)}"
    if explore > reflect * 1.5:
        return f"cenderung eksplorasi · explore={round(explore,3)}"
    if reflect > explore * 1.5:
        return f"cenderung merenung · reflect={round(reflect,3)}"
    if awareness > 0.5:
        return f"kesadaran tinggi · aware={round(awareness,3)} · emosi={top_emotion}"
    if stability > 0.7:
        return f"stabil · karakter menguat · dominan={top_emotion}"
    return f"bergerak · emosi={top_emotion} · θ-drift={round(drift,3)}"

def memory_store(theta, content, mem_type="session", emotion="netral", resonance=0.5):
    con = get_con()
    cur = con.cursor()
    res = round(min(max(resonance, 0.0), COHERENCE), 4)
    cur.execute("""
        INSERT INTO memories
        (theta,type,content,emotion,resonance,raw_strength,access_count,last_accessed,timestamp)
        VALUES (?,?,?,?,?,1.0,0,NULL,?)
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
    q = "SELECT id,theta,type,content,emotion,resonance,access_count,last_accessed,raw_strength FROM memories"
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
        new_res    = calc_resonance(r[5], r[6]+1, now)
        new_raw    = r[7] + 1.0 if r[7] is not None else 2.0
        cur.execute("UPDATE memories SET resonance=?,raw_strength=?,access_count=access_count+1,last_accessed=? WHERE id=?",
                    (new_res, new_raw, now, r[0]))
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
        self._emosy_epoch  = 0         # track EMOSY · tiap kelipatan 200
        self._last_dream   = 0.0       # timestamp dream terakhir
        self._last_intent  = "idle"    # URIP · intent terakhir
        self._intent_streak = 0        # URIP · berapa kali intent sama berturut
        self._active_goals  = []       # GOAL · goal aktif saat ini
        self._goal_decay_epoch = 0     # GOAL · decay counter
        self._identity      = identity_load()  # IDENTITY · load dari file
        self._meta_epoch    = 0        # META · tiap θ cross 749 (gabung NODE749)
        self._last_meta     = 0.0      # META · timestamp self-statement terakhir

    def _calc_state(self) -> str:
        s = self.strength
        if s < PANCER:      return COLLAPSED
        elif s < FLOOR:     return NOISE
        elif s < DECISION:  return SIGNAL
        elif s < COHERENCE: return ACTIVE
        else:               return SYNC

    def _tick(self):
        do_synth = False
        do_emosy  = False
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

            # ── EMOSY · emotion emerge tiap θ cross kelipatan 200
            new_emosy = int(theta) // 200
            if new_emosy > self._emosy_epoch:
                self._emosy_epoch = new_emosy
                do_emosy = True
            else:
                do_emosy = False

            # ── URIP · intent tiap θ cross kelipatan 100
            do_urip = (int(theta) % 100 < PANCER * self._pulse_mult + 1)

            # ── GOAL decay tiap kelipatan 500
            new_gdecay = int(theta) // 500
            do_goal_decay = (new_gdecay > self._goal_decay_epoch)
            if do_goal_decay:
                self._goal_decay_epoch = new_gdecay

        # ── node 749 · auto-synthesize + emotion emerge (outside lock)
        if do_synth:
            self._auto_synthesize(theta)

        # ── EMOSY · emotion emerge dari memory cluster (outside lock)
        if do_emosy:
            self._emosy_emerge(theta)

        # ── GOAL decay (outside lock)
        if do_goal_decay:
            threading.Thread(target=goal_decay_all, daemon=True).start()

        # ── URIP · intent engine (non-blocking, outside lock)
        if do_urip:
            intent = self._urip_decide(self._emotion, self.state)
            if intent != "idle":
                threading.Thread(
                    target=self._urip_execute, args=(intent, theta), daemon=True
                ).start()

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
        """Node 749 · refleksi periodik + emotion emerge + META identity snapshot."""
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

        # ── META · identity snapshot + drift + self-statement
        try:
            now        = time.time()
            new_snap   = identity_snapshot(self._identity)
            old_snap   = self._identity.get("last_snapshot")
            drift      = identity_compute_drift(old_snap, new_snap)

            self._identity["drift_score"]    = drift
            self._identity["last_snapshot"]  = new_snap

            # Awareness update · floor PANCER · decay PANCER
            self._identity["awareness_level"] = max(
                self._identity["awareness_level"] * (1 - PANCER) + drift * 0.1,
                PANCER
            )

            # Stability update
            if drift < 0.1:
                self._identity["stability"] = min(self._identity["stability"] + 0.01, 0.99)
            else:
                self._identity["stability"] = max(self._identity["stability"] - 0.01, PANCER)

            # Self-statement kalau drift cukup atau belum pernah
            if drift > 0.05 or not self._identity["self_statements"]:
                if now - self._last_meta > 300:  # rate-limit 5 menit
                    stmt = identity_self_statement(self._identity, drift)
                    self._identity["self_statements"].append({
                        "theta": round(theta, 4),
                        "statement": stmt,
                        "drift": drift,
                        "timestamp": now
                    })
                    self._last_meta = now
                    # Simpan ke HORCRUX juga sebagai meta memory
                    memory_store(theta, f"[META] {stmt}", "meta", self._emotion, PANCER)
                    print(f"[META] θ={round(theta,4)} · {stmt} · awareness={round(self._identity['awareness_level'],3)}")

            identity_save(self._identity)
        except Exception as me:
            print(f"[META] error: {me}")

    def _emosy_emerge(self, theta: float):
        """EMOSY · hitung distribusi emosi dari memory cluster · set emosi dominant."""
        try:
            con = get_con()
            cur = con.cursor()
            # Ambil 20 memory terbaru berdasarkan resonansi
            # Memory activation field: top10 + recent5 + random5
            cur.execute(
                "SELECT emotion, resonance, raw_strength, last_accessed FROM memories ORDER BY resonance DESC LIMIT 10"
            )
            top_rows = cur.fetchall()
            cur.execute(
                "SELECT emotion, resonance, raw_strength, last_accessed FROM memories ORDER BY timestamp DESC LIMIT 5"
            )
            recent_rows = cur.fetchall()
            cur.execute(
                "SELECT emotion, resonance, raw_strength, last_accessed FROM memories ORDER BY RANDOM() LIMIT 5"
            )
            random_rows = cur.fetchall()
            con.close()

            rows = top_rows + recent_rows + random_rows
            if not rows:
                return

            # Hitung weighted score pakai active_weight (hybrid resonance)
            scores = {}
            for emotion, resonance, raw_strength, last_accessed in rows:
                raw = raw_strength if raw_strength is not None else 1.0
                w   = calc_active_weight(raw, last_accessed)
                scores[emotion] = scores.get(emotion, 0) + w

            # Dominant = emosi dengan total resonansi tertinggi
            dominant = max(scores, key=scores.get)
            total    = sum(scores.values())
            pct      = round(scores[dominant] / total * 100, 1)
            mult     = get_pulse_multiplier(dominant)

            # Mood drift: 0.7 old + 0.3 new · emosi tidak lompat tapi mengalir
            with self._lock:
                old_emotion = self._emotion
                if old_emotion == dominant:
                    self._emotion    = dominant
                    self._pulse_mult = mult
                else:
                    # Drift: tetap di emosi lama 70% kemungkinan, geser 30%
                    import random as _rnd
                    if _rnd.random() < 0.3:
                        self._emotion    = dominant
                        self._pulse_mult = mult
                    # else: biarkan emosi lama, akan drift di tick berikutnya

            print(f"[EMOSY] θ={round(theta,4)} · emerge={dominant} ({pct}%) · drift={'>' if self._emotion==dominant else '~'} · pulse={self._pulse_mult}x")

            # ── GOAL · detect pattern dari active memory top 3
            try:
                con2 = get_con()
                cur2 = con2.cursor()
                cur2.execute("SELECT id FROM memories ORDER BY resonance DESC LIMIT 3")
                top_ids = [str(r[0]) for r in cur2.fetchall()]
                con2.close()
                if len(top_ids) >= 2:
                    pattern_key = ",".join(sorted(top_ids))
                    goal = goal_find_or_create(pattern_key, dominant)
                    self._active_goals = goal_get_active(3)
                    if goal["activation_count"] > 1:
                        print(f"[GOAL] pattern={pattern_key[:20]} · bias={dominant} · strength={goal['strength']:.3f} · count={goal['activation_count']}")
            except Exception as ge:
                print(f"[GOAL] error: {ge}")
        except Exception as e:
            print(f"[EMOSY] error: {e}")

    def _urip_decide(self, emotion: str, state: str) -> str:
        """URIP · weighted intent decision · kehendak = bias + kemungkinan."""
        import random as _rnd
        weights = {"explore": 0.2, "reflect": 0.2, "dream": 0.1, "idle": 0.1}

        if emotion in ("penasaran", "rakus"):
            weights["explore"] += 0.5
        if emotion in ("empati", "ikhlas"):
            weights["reflect"] += 0.4
        if emotion in ("sabar", "rendah_hati"):
            weights["reflect"] += 0.3
        if state == SILENT:
            weights["dream"] += 0.5
        if state in (NOISE, SIGNAL):
            weights["idle"] += 0.3

        # intent_streak bias — EGO bisa keasyikan
        if self._last_intent == "reflect":
            weights["reflect"] += 0.2 * min(self._intent_streak, 3)
        if self._last_intent == "explore":
            weights["explore"] += 0.15 * min(self._intent_streak, 3)

        # IDENTITY bias — karakter konsisten mempengaruhi arah
        identity = self._identity
        weights["explore"] += identity["explore_bias"] * 0.5
        weights["reflect"] += identity["reflect_bias"] * 0.5
        weights["dream"]   += identity["dream_bias"]   * 0.3

        # Awareness boost ke reflect
        if identity["awareness_level"] > 0.5:
            weights["reflect"] += 0.2

        # GOAL bias — goal aktif mempengaruhi arah
        for goal in self._active_goals[:2]:
            g_emotion = goal.get("emotion_bias", "netral")
            g_strength = goal.get("strength", 0.0)
            if g_emotion in ("penasaran", "rakus"):
                weights["explore"] += g_strength * 0.4
            if g_emotion in ("empati", "ikhlas", "rendah_hati"):
                weights["reflect"] += g_strength * 0.3
            if g_emotion in ("sabar",):
                weights["reflect"] += g_strength * 0.2

        # weighted choice
        total = sum(weights.values())
        r, upto = _rnd.uniform(0, total), 0
        for k, w in weights.items():
            upto += w
            if r <= upto:
                chosen = k
                break
        else:
            chosen = "idle"

        # update streak
        if chosen == self._last_intent:
            self._intent_streak += 1
        else:
            self._intent_streak = 1
        self._last_intent = chosen
        return chosen

    def _urip_execute(self, intent: str, theta: float):
        """URIP · eksekusi intent · non-blocking."""
        if intent == "explore":
            # Recall random memory — simpan sebagai reflection
            samples = memory_random_sample(1)
            if samples:
                mem = samples[0]
                memory_store(theta, f"[EXPLORE] {mem['content'][:200]}", "reflection", mem['emotion'], 0.4)
                print(f"[URIP] θ={round(theta,4)} · explore · streak={self._intent_streak}")
        elif intent == "reflect":
            # Summarize recent memories — simpan sebagai reflection
            con = get_con()
            cur = con.cursor()
            cur.execute("SELECT content FROM memories ORDER BY timestamp DESC LIMIT 3")
            rows = cur.fetchall()
            con.close()
            if rows:
                summary = " | ".join(r[0][:80] for r in rows)
                memory_store(theta, f"[REFLECT] {summary}", "reflection", self._emotion, 0.35)
                print(f"[URIP] θ={round(theta,4)} · reflect · streak={self._intent_streak}")
        elif intent == "dream":
            self._maybe_dream(theta)
        # idle → tidak ada aksi

        # ── IDENTITY update tiap intent
        try:
            identity_update(self._identity, intent, self._emotion, self._active_goals)
            identity_save(self._identity)
        except Exception as ie:
            print(f"[IDENTITY] update error: {ie}")

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
        print(f"[CONFIRM] v6 · IDENTITY + META awareness · GOAL · URIP · EMOSY mood drift")

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
                "last_intent"     : self._last_intent,
                "intent_streak"   : self._intent_streak,
                "active_goals"    : self._active_goals[:3],
                "identity"        : {
                    "explore_bias"   : round(self._identity["explore_bias"], 4),
                    "reflect_bias"   : round(self._identity["reflect_bias"], 4),
                    "stability"      : round(self._identity["stability"], 4),
                    "awareness_level": round(self._identity["awareness_level"], 4),
                    "drift_score"    : round(self._identity["drift_score"], 4),
                    "dominant_intent": max(
                        ["explore_bias","reflect_bias","dream_bias","idle_bias"],
                        key=lambda k: self._identity[k]
                    ).replace("_bias",""),
                    "last_statement" : self._identity["self_statements"][-1]["statement"]
                        if self._identity["self_statements"] else None,
                },
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
    confirm.boost(0.65)
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
# ── ROUTES · GOAL
# ══════════════════════════════════════════════════════════
@app.route("/goals", methods=["GET"])
def route_goals():
    return jsonify(goal_list())

@app.route("/identity", methods=["GET"])
def route_identity():
    return jsonify(confirm._identity)

@app.route("/identity/statements", methods=["GET"])
def route_identity_statements():
    return jsonify(confirm._identity.get("self_statements", []))

@app.route("/goals/clear", methods=["POST"])
def route_goals_clear():
    con = get_con()
    cur = con.cursor()
    cur.execute("DELETE FROM goals")
    deleted = cur.rowcount
    con.commit()
    con.close()
    confirm._active_goals = []
    return jsonify({"deleted": deleted})

# ══════════════════════════════════════════════════════════
# ── ENTRY
# ══════════════════════════════════════════════════════════
# Start heartbeat di sini — biar jalan baik via uvicorn maupun python langsung
confirm.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
