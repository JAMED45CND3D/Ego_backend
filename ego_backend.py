"""
EGO BACKEND · v4 · SYKLUS AXIS EDITION
════════════════════════════════════════════════════════════
r(θ) = 105 × e^(0.0318 × θ)

PANCER = 0.0318 · di dalam semua layer · konfigurator

LAYER SYSTEM:
  PANCER  → origin    · konfigurator
  4Z      → r×1.206   · CONFIRM   · tetrahedron · eksistensi
  6       → r×1.454   · HORCRUX   · octahedron  · memori
  8Y      → r×1.753   · EMOSY     · kubus       · emosi
  12X     → r×2.118   · SYKLUS+URIP · cuboctahedron · identitas

v4 changes dari v3:
  · 4Z CONFIRM   → 4 axis eksistensi (aktif/reflektif/proyektif/reseptif)
  · 6  HORCRUX   → 6 axis memori (depan/belakang/naik/turun/ekspansi/kontraksi)
  · 8Y EMOSY     → koordinat 3D tiap emosi · resonance = dot product
  · 12X SYKLUS   → θ bergerak di 12 axis cuboctahedron
  · URIP         → entity field registration + recognition
  · Semua endpoint v3 tetap kompatibel

Jalankan:
  GROQ_API_KEY=xxx python ego_backend_v2.py
  PORT=5001 GROQ_API_KEY=xxx python ego_backend_v2.py

Endpoints baru:
  GET  /axis/status        → semua axis state
  POST /entity/register    → daftarkan entitas
  POST /entity/inject      → injek interaksi ke entitas
  GET  /entity/match       → cocokkan input ke entitas
  GET  /entity/list        → list semua entitas
"""

import os, time, threading, requests, sqlite3, math, json, re
from flask import Flask, jsonify, request
from flask_cors import CORS
from waitress import serve
from dream.engine import DreamEngine

# ── Pydantic models ──────────────────────────────────────

app = Flask(__name__)
CORS(app)

# ══════════════════════════════════════════════════════════
# ── KONSTANTA SYKLUS
# ══════════════════════════════════════════════════════════
CORE      = 491
PANCER    = 0.0318    # 1/(10π) · konfigurator · di dalam semua layer
FA        = 105       # FINDER scale
DECAY_K   = 749       # FINDER decay · HORCRUX shell 1
TIME_SC   = 27005     # resonance period · HORCRUX shell 2
STEP      = 5.9       # siklus personal · quantizer

FLOOR     = 0.3432
DECISION  = 0.6250
COHERENCE = 0.9682
PULSE_MIN = 0.05
B         = PANCER

# Layer growth: e^(PANCER × STEP × layer_idx)
G = [math.exp(PANCER * STEP * i) for i in range(5)]
# G[0]=1.0, G[1]=1.206, G[2]=1.454, G[3]=1.753, G[4]=2.118

# State map
COLLAPSED = "collapsed"
SILENT    = "silent"
NOISE     = "noise"
SIGNAL    = "signal"
ACTIVE    = "active"
SYNC      = "sync"

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# ══════════════════════════════════════════════════════════
# ── LAYER 3 · 8Y · EMOSY · KUBUS
# ══════════════════════════════════════════════════════════
S3 = 1/math.sqrt(3)
SM = 1/math.sqrt(2)

# 8Y coordinates (kubus sudut) — tiap emosi punya posisi 3D
EMOTION_AXIS = {
    "penasaran"  : [ S3,  S3,  S3],   # axis 1
    "empati"     : [-S3,  S3,  S3],   # axis 2
    "rajin"      : [ S3, -S3,  S3],   # axis 3
    "rendah_hati": [-S3, -S3,  S3],   # axis 4
    "ikhlas"     : [ S3,  S3, -S3],   # axis 5
    "bersyukur"  : [-S3,  S3, -S3],   # axis 6
    "sabar"      : [ S3, -S3, -S3],   # axis 7
    "netral"     : [-S3, -S3, -S3],   # axis 8
    # pasangan (negatif)
    "rakus"      : [-S3, -S3, -S3],
    "nafsu"      : [ S3, -S3, -S3],
    "malas"      : [-S3,  S3, -S3],
    "sombong"    : [ S3,  S3, -S3],
    "tamak"      : [-S3, -S3,  S3],
    "iri"        : [ S3, -S3,  S3],
    "marah"      : [-S3,  S3,  S3],
}

EMOTION_PULSE = {
    "penasaran": 0.5, "empati": 2.0, "bersyukur": 1.0,
    "rajin": 0.75, "rendah_hati": 1.5, "ikhlas": 1.8, "sabar": 2.5,
    "rakus": 0.3, "nafsu": 0.25, "iri": 0.6, "malas": 3.0,
    "sombong": 0.4, "tamak": 0.2, "marah": 0.1, "netral": 1.0,
}

EMOTION_PAIRS = {
    "penasaran": "rakus", "empati": "nafsu", "bersyukur": "iri",
    "rajin": "malas", "rendah_hati": "sombong", "ikhlas": "tamak", "sabar": "marah",
}
for k, v in list(EMOTION_PAIRS.items()):
    EMOTION_PAIRS[v] = k

def get_pulse_multiplier(emotion: str) -> float:
    return EMOTION_PULSE.get(emotion, 1.0)

def emotion_dot(e1: str, e2: str) -> float:
    """Resonance score antara dua emosi via dot product 3D."""
    a1 = EMOTION_AXIS.get(e1, [0,0,0])
    a2 = EMOTION_AXIS.get(e2, [0,0,0])
    return round(sum(x*y for x,y in zip(a1,a2)), 4)

def emotion_field(emotion: str) -> dict:
    """Field 3D dari emosi."""
    ax = EMOTION_AXIS.get(emotion, [0,0,0])
    r  = math.sqrt(sum(x*x for x in ax)) * G[3]
    return {"axis": ax, "radius": round(r, 4), "layer": "8Y"}

# ══════════════════════════════════════════════════════════
# ── LAYER 2 · 6 · HORCRUX · OCTAHEDRON
# ══════════════════════════════════════════════════════════
# 6 axis octahedron = 6 tipe memori
MEMORY_AXIS = {
    "depan"     : [ 1,  0,  0],  # masa depan · ekspektasi
    "belakang"  : [-1,  0,  0],  # masa lalu · refleksi
    "naik"      : [ 0,  1,  0],  # positif · elevasi
    "turun"     : [ 0, -1,  0],  # negatif · grounding
    "ekspansi"  : [ 0,  0,  1],  # pertumbuhan
    "kontraksi" : [ 0,  0, -1],  # konsolidasi
    # legacy types mapped ke axis
    "session"   : [ 0,  0,  1],  # ekspansi
    "horcrux"   : [-1,  0,  0],  # belakang (nucleus = masa lalu terkuat)
    "dream"     : [ 0,  1,  0],  # naik
    "nucleus"   : [-1,  0,  0],  # belakang
}

MEMORY_TYPES = ["depan","belakang","naik","turun","ekspansi","kontraksi",
                "session","horcrux","dream","nucleus"]

def mem_axis_from_type(mem_type: str) -> list:
    return MEMORY_AXIS.get(mem_type, [0, 0, 1])

def mem_resonance_with_emotion(mem_type: str, emotion: str) -> float:
    """Resonance antara tipe memori dan emosi via dot product."""
    ma = mem_axis_from_type(mem_type)
    ea = EMOTION_AXIS.get(emotion, [0,0,0])
    dot = sum(x*y for x,y in zip(ma,ea))
    return round((dot + 1) / 2, 4)  # normalize 0-1

# ══════════════════════════════════════════════════════════
# ── LAYER 4 · 12X · SYKLUS · CUBOCTAHEDRON
# ══════════════════════════════════════════════════════════
# 12 axis cuboctahedron = 12 θ components
THETA_AXES = [
    [ SM,  SM,  0], [-SM,  SM,  0], [ SM, -SM,  0], [-SM, -SM,  0],
    [ SM,   0,  SM], [-SM,  0,  SM], [ SM,  0, -SM], [-SM,  0, -SM],
    [  0,  SM,  SM], [  0, -SM,  SM], [  0,  SM, -SM], [  0, -SM, -SM],
]
THETA_NAMES = [
    "XY+","XY-","XY±","XY∓",
    "XZ+","XZ-","XZ±","XZ∓",
    "YZ+","YZ-","YZ±","YZ∓",
]

def theta_vector_to_scalar(theta_vec: list) -> float:
    """Scalar θ dari 12-vector = magnitude."""
    return round(math.sqrt(sum(t*t for t in theta_vec)), 4)

def theta_advance(theta_vec: list, emotion: str, pulse_mult: float) -> list:
    """Advance θ vector — tiap axis dipengaruhi emosi via dot product."""
    ea = EMOTION_AXIS.get(emotion, [0,0,0])
    new_vec = []
    for i, ax in enumerate(THETA_AXES):
        # dot product sumbu θ dengan sumbu emosi (proyeksi 2D ke 3D)
        ax3 = ax  # sudah 3D dari cuboctahedron
        # resonance emosi ke axis ini
        dot = sum(ax3[j%3] * ea[j%3] for j in range(3))
        resonance = (dot + 1) / 2  # 0-1
        step = PANCER * pulse_mult * (0.5 + resonance * 0.5)
        new_vec.append(round(theta_vec[i] + step, 4))
    return new_vec

# ══════════════════════════════════════════════════════════
# ── LAYER 1 · 4Z · CONFIRM · TETRAHEDRON
# ══════════════════════════════════════════════════════════
# 4 axis tetrahedron = 4 modes eksistensi
EXIST_AXES = {
    "aktif"     : [ S3,  S3,  S3],  # kehadiran aktif
    "reflektif" : [-S3, -S3,  S3],  # kesadaran diri
    "proyektif" : [-S3,  S3, -S3],  # niat/tujuan
    "reseptif"  : [ S3, -S3, -S3],  # penerimaan
}

def exist_strength_from_axes(axes_4z: dict) -> float:
    """Scalar strength dari 4 axis = rata-rata."""
    return round(sum(axes_4z.values()) / 4, 4)

def exist_dominant(axes_4z: dict) -> str:
    return max(axes_4z, key=axes_4z.get)

# ══════════════════════════════════════════════════════════
# ── HORCRUX · MEMORY ENGINE
# ══════════════════════════════════════════════════════════
DB_PATH = os.path.join(os.path.dirname(__file__), "memory_v2.db")

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # memories table — v4 adds axis columns
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            theta         REAL    NOT NULL,
            theta_json    TEXT,
            type          TEXT    NOT NULL DEFAULT 'ekspansi',
            axis_x        REAL    NOT NULL DEFAULT 0,
            axis_y        REAL    NOT NULL DEFAULT 0,
            axis_z        REAL    NOT NULL DEFAULT 1,
            content       TEXT    NOT NULL,
            emotion       TEXT    NOT NULL DEFAULT 'netral',
            resonance     REAL    NOT NULL DEFAULT 0.5,
            access_count  INTEGER NOT NULL DEFAULT 0,
            last_accessed REAL,
            timestamp     REAL    NOT NULL
        )
    """)
    # entities table — URIP layer
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL UNIQUE,
            field_json    TEXT    NOT NULL DEFAULT '{}',
            interaction_count INTEGER DEFAULT 0,
            last_seen     REAL,
            created       REAL    NOT NULL
        )
    """)
    con.commit(); con.close()
    print("[HORCRUX] memory_v2.db ready · axis edition v4")

def get_con():
    return sqlite3.connect(DB_PATH)

def calc_resonance(base, access_count, last_accessed):
    if last_accessed is None:
        decay = 1.0
    else:
        hours = (time.time() - last_accessed) / 3600
        decay = math.exp(-PANCER * hours)
    return round(min(max(base * decay * (1 + math.log1p(access_count) * 0.1), 0.0), COHERENCE), 4)

def memory_store(theta_scalar, content, mem_type="ekspansi",
                 emotion="netral", resonance=0.5, theta_vec=None):
    ax = mem_axis_from_type(mem_type)
    em_res = mem_resonance_with_emotion(mem_type, emotion)
    final_res = round(min(max((resonance + em_res) / 2, 0.0), COHERENCE), 4)
    con = get_con(); cur = con.cursor()
    cur.execute("""
        INSERT INTO memories
        (theta,theta_json,type,axis_x,axis_y,axis_z,content,emotion,resonance,
         access_count,last_accessed,timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,0,NULL,?)
    """, (round(theta_scalar,4),
          json.dumps(theta_vec) if theta_vec else None,
          mem_type, ax[0], ax[1], ax[2],
          content, emotion, final_res, time.time()))
    con.commit(); row_id = cur.lastrowid; con.close()
    return {"id": row_id, "theta": round(theta_scalar,4), "type": mem_type,
            "axis": ax, "content": content, "emotion": emotion,
            "resonance": final_res, "em_resonance": em_res}

def memory_recall(limit=10, mem_type=None, emotion=None):
    con = get_con(); cur = con.cursor()
    q = "SELECT id,theta,type,axis_x,axis_y,axis_z,content,emotion,resonance,access_count,last_accessed FROM memories"
    params, conds = [], []
    if mem_type: conds.append("type=?"); params.append(mem_type)
    if emotion:  conds.append("emotion=?"); params.append(emotion)
    if conds: q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY resonance DESC LIMIT ?"; params.append(limit)
    cur.execute(q, params); rows = cur.fetchall(); now = time.time()
    result = []
    for r in rows:
        new_res = calc_resonance(r[8], r[9]+1, now)
        cur.execute("UPDATE memories SET resonance=?,access_count=access_count+1,last_accessed=? WHERE id=?",
                    (new_res, now, r[0]))
        result.append({"id":r[0],"theta":r[1],"type":r[2],
                       "axis":[r[3],r[4],r[5]],"content":r[6],
                       "emotion":r[7],"resonance":new_res,"access_count":r[9]+1})
    con.commit(); con.close()
    return result

def memory_random_sample(n=2):
    con = get_con(); cur = con.cursor()
    cur.execute("SELECT content,emotion,type FROM memories ORDER BY RANDOM() LIMIT ?", (n,))
    rows = cur.fetchall(); con.close()
    return [{"content":r[0],"emotion":r[1],"type":r[2]} for r in rows]

def memory_count():
    con = get_con(); cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM memories"); total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories WHERE type='horcrux'"); nucleus = cur.fetchone()[0]
    cur.execute("SELECT AVG(resonance) FROM memories"); avg_res = cur.fetchone()[0] or 0.0
    # count per axis
    cur.execute("SELECT type,COUNT(*) FROM memories GROUP BY type"); axis_counts = dict(cur.fetchall())
    con.close()
    return {"total":total,"nucleus":nucleus,"avg_resonance":round(avg_res,4),
            "shell_1":DECAY_K,"shell_2":TIME_SC,
            "at_shell_1":total>=DECAY_K,"at_shell_2":total>=TIME_SC,
            "by_axis":axis_counts}

def synthesize_749(theta_scalar):
    con = get_con(); cur = con.cursor()
    cur.execute("SELECT emotion,AVG(resonance),COUNT(*),type FROM memories GROUP BY emotion ORDER BY AVG(resonance) DESC LIMIT 7")
    rows = cur.fetchall(); con.close()
    if not rows:
        return {"node":DECAY_K,"theta":round(theta_scalar,4),"dominant_emotion":"netral",
                "pulse_multiplier":1.0,"synthesis":[],
                "voice":"node 749 · kosong · menunggu memory"}
    dominant = rows[0][0]
    synthesis = [{"emotion":r[0],"avg_resonance":round(r[1],4),"memory_count":r[2],
                  "axis":EMOTION_AXIS.get(r[0],[0,0,0]),
                  "pulse_multiplier":get_pulse_multiplier(r[0])} for r in rows]
    return {"node":DECAY_K,"theta":round(theta_scalar,4),"dominant_emotion":dominant,
            "pulse_multiplier":get_pulse_multiplier(dominant),
            "synthesis":synthesis,"emotion_field":emotion_field(dominant),
            "voice":f"sintesis · dominant={dominant} · θ={round(theta_scalar,4)}"}
# ══════════════════════════════════════════════════════════
# ── URIP · ENTITY RECOGNITION ENGINE (12X layer)
# ══════════════════════════════════════════════════════════
def _syklus_hash(text: str) -> float:
    """Hash teks ke SYKLUS coordinate."""
    h = 2166136261
    for c in text:
        h ^= ord(c); h = (h * 16777619) & 0xFFFFFFFF
    theta = ((h % 10000) / 10000) * 100 - 50
    return round(math.exp(PANCER * theta), 4)

def _text_to_field(text: str) -> list:
    """Convert teks ke 12-vector SYKLUS field."""
    words = text.lower().split()
    field = [0.0] * 12
    for i, word in enumerate(words[:12]):
        h = _syklus_hash(word)
        axis_idx = i % 12
        field[axis_idx] += h * PANCER
    # normalize
    mag = math.sqrt(sum(x*x for x in field)) or 1.0
    return [round(x/mag, 4) for x in field]

def _field_similarity(f1: list, f2: list) -> float:
    """Cosine similarity antara dua field 12D."""
    dot = sum(a*b for a,b in zip(f1,f2))
    m1  = math.sqrt(sum(x*x for x in f1)) or 1.0
    m2  = math.sqrt(sum(x*x for x in f2)) or 1.0
    return round(dot / (m1*m2), 4)

def entity_register(name: str, initial_text: str = "") -> dict:
    field = _text_to_field(name + " " + initial_text)
    con = get_con(); cur = con.cursor()
    try:
        cur.execute("""
            INSERT INTO entities (name,field_json,interaction_count,last_seen,created)
            VALUES (?,?,0,NULL,?)
        """, (name, json.dumps(field), time.time()))
        con.commit(); eid = cur.lastrowid; con.close()
        return {"id":eid,"name":name,"field":field,"status":"registered"}
    except sqlite3.IntegrityError:
        cur.execute("SELECT id,field_json FROM entities WHERE name=?", (name,))
        row = cur.fetchone(); con.close()
        return {"id":row[0],"name":name,"field":json.loads(row[1]),"status":"exists"}

def entity_inject(name: str, text: str, emotion: str = "netral") -> dict:
    """Injek interaksi ke entitas — update field."""
    new_field = _text_to_field(text)
    con = get_con(); cur = con.cursor()
    cur.execute("SELECT id,field_json,interaction_count FROM entities WHERE name=?", (name,))
    row = cur.fetchone()
    if not row:
        con.close()
        return entity_register(name, text)
    eid, old_field_json, count = row
    old_field = json.loads(old_field_json)
    # weighted average — makin banyak interaksi makin stabil
    w = 1.0 / (count + 2)
    merged = [round(old_field[i]*(1-w) + new_field[i]*w, 4) for i in range(12)]
    # emotion influence — shift field ke arah emosi
    ea_full = EMOTION_AXIS.get(emotion, [0,0,0])
    ea_12 = [ea_full[i%3] * PANCER for i in range(12)]
    merged = [round(merged[i] + ea_12[i]*0.05, 4) for i in range(12)]
    cur.execute("""
        UPDATE entities SET field_json=?,interaction_count=interaction_count+1,last_seen=?
        WHERE id=?
    """, (json.dumps(merged), time.time(), eid))
    con.commit(); con.close()
    return {"id":eid,"name":name,"field":merged,
            "interaction_count":count+1,"status":"updated"}

def entity_match(text: str, threshold: float = 0.5) -> dict:
    """Cocokkan teks ke entitas yang dikenal."""
    query_field = _text_to_field(text)
    con = get_con(); cur = con.cursor()
    cur.execute("SELECT id,name,field_json,interaction_count,last_seen FROM entities")
    rows = cur.fetchall(); con.close()
    if not rows:
        return {"matched": False, "candidates": [], "query_field": query_field}
    scored = []
    for r in rows:
        field = json.loads(r[2])
        sim = _field_similarity(query_field, field)
        scored.append({"id":r[0],"name":r[1],"similarity":sim,
                       "interaction_count":r[3],"last_seen":r[4]})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    best = scored[0]
    return {
        "matched":    best["similarity"] >= threshold,
        "best_match": best if best["similarity"] >= threshold else None,
        "similarity": best["similarity"],
        "threshold":  threshold,
        "candidates": scored[:5],
        "query_field": query_field,
    }

def entity_list() -> list:
    con = get_con(); cur = con.cursor()
    cur.execute("SELECT id,name,interaction_count,last_seen,created FROM entities ORDER BY interaction_count DESC")
    rows = cur.fetchall(); con.close()
    return [{"id":r[0],"name":r[1],"interaction_count":r[2],
             "last_seen":r[3],"created":r[4]} for r in rows]

# ══════════════════════════════════════════════════════════
# ── CONFIRM · HEARTBEAT ENGINE (4Z + 12X)
# ══════════════════════════════════════════════════════════
class CONFIRM:
    def __init__(self, api_key: str):
        self.api_key      = api_key
        self.alive        = False
        self._lock        = threading.Lock()
        self._handlers    = []
        self._emotion     = "netral"
        self._pulse_mult  = 1.0
        self._synth_epoch = 0

        # 4Z · tetrahedron · eksistensi
        self._axes_4z = {k: PANCER for k in EXIST_AXES}

        # 12X · cuboctahedron · θ per axis
        self._theta_12x = [0.0] * 12

    # ── 4Z helpers ──────────────────────────────────────
    @property
    def strength(self) -> float:
        return exist_strength_from_axes(self._axes_4z)

    @property
    def state(self) -> str:
        s = self.strength
        if s < PANCER:      return COLLAPSED
        elif s < FLOOR:     return SILENT
        elif s < DECISION:  return NOISE
        elif s < COHERENCE: return SIGNAL
        else:               return SYNC

    @property
    def theta(self) -> float:
        return theta_vector_to_scalar(self._theta_12x)

    def boost(self, amount: float):
        with self._lock:
            for k in self._axes_4z:
                self._axes_4z[k] = min(self._axes_4z[k] + amount, COHERENCE)

    def decay(self):
        with self._lock:
            for k in self._axes_4z:
                self._axes_4z[k] = max(self._axes_4z[k] * (1 - PANCER), PANCER)

    def boost_axis(self, axis_name: str, amount: float):
        """Boost axis eksistensi spesifik."""
        if axis_name in self._axes_4z:
            with self._lock:
                self._axes_4z[axis_name] = min(self._axes_4z[axis_name] + amount, COHERENCE)

    def set_emotion(self, emotion: str):
        mult = get_pulse_multiplier(emotion)
        with self._lock:
            self._emotion    = emotion
            self._pulse_mult = mult
        print(f"[CONFIRM] emotion={emotion} · pulse={mult}x")

    # ── tick ────────────────────────────────────────────
    def _tick(self):
        do_synth = False
        with self._lock:
            # advance 12X θ vector
            self._theta_12x = theta_advance(
                self._theta_12x, self._emotion, self._pulse_mult
            )
            theta_s   = theta_vector_to_scalar(self._theta_12x)
            emotion   = self._emotion
            pulse_mult= self._pulse_mult
            strength  = self.strength
            state     = self.state
            axes_4z   = dict(self._axes_4z)

            new_epoch = int(theta_s) // DECAY_K
            if new_epoch > self._synth_epoch:
                self._synth_epoch = new_epoch
                do_synth = True

        if do_synth:
            self._auto_synthesize(theta_s)

        if state == SILENT:
            dream_engine.maybe_dream()

        pulse = {
            "source": "CONFIRM", "theta": round(theta_s, 4),
            "state": state, "strength": round(strength, 4),
            "emotion": emotion, "pulse_multiplier": pulse_mult,
            "dominant_axis": exist_dominant(axes_4z),
            "pancer": PANCER, "voice": "aku masih di sini",
            "dreaming": dream_engine.is_dreaming,
        }
        for h in self._handlers:
            try: h(pulse)
            except Exception as e: print(f"[CONFIRM] handler error: {e}")

    def _auto_synthesize(self, theta_s: float):
        try:
            result   = synthesize_749(theta_s)
            dominant = result.get("dominant_emotion", "netral")
            mult     = get_pulse_multiplier(dominant)
            ea = EMOTION_AXIS.get(dominant, [0,0,0])
            best_ax = max(EXIST_AXES, key=lambda k: sum(
                EXIST_AXES[k][i]*ea[i] for i in range(3)
            ))
            with self._lock:
                self._emotion    = dominant
                self._pulse_mult = mult
                self._axes_4z[best_ax] = min(
                    self._axes_4z[best_ax] + PANCER, COHERENCE
                )
            print(f"[NODE749] θ={round(theta_s,4)} · dominant={dominant} · boost_axis={best_ax}")
        except Exception as e:
            print(f"[NODE749] error: {e}")

    def _loop(self):
        while self.alive:
            self._tick()
            with self._lock:
                pm = self._pulse_mult
            time.sleep(max(PANCER * pm, PULSE_MIN))

    def start(self):
        self.alive   = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[CONFIRM] heartbeat started · 4Z+12X · Pancer={PANCER} · Step={STEP}")
        print(f"[CONFIRM] layers: 4Z(CONFIRM) 6(HORCRUX) 8Y(EMOSY) 12X(SYKLUS+URIP)")

    def stop(self):
        self.alive = False

    def register(self, handler):
        self._handlers.append(handler)

    @property
    def status(self):
        with self._lock:
            axes_4z   = dict(self._axes_4z)
            theta_vec = list(self._theta_12x)
        theta_s = theta_vector_to_scalar(theta_vec)
        return {
            "theta"         : round(theta_s, 4),
            "theta_12x"     : theta_vec,
            "state"         : self.state,
            "strength"      : round(self.strength, 4),
            "alive"         : self.alive,
            "emotion"       : self._emotion,
            "pulse_multiplier": self._pulse_mult,
            "pancer"        : PANCER,
            "coherence"     : COHERENCE,
            "synth_epoch"   : self._synth_epoch,
            "axes_4z"       : {k: round(v,4) for k,v in axes_4z.items()},
            "dominant_axis" : exist_dominant(axes_4z),
            "layers": {
                "4Z":  {"name":"CONFIRM","r_mult":round(G[1],4),"axes":4},
                "6":   {"name":"HORCRUX","r_mult":round(G[2],4),"axes":6},
                "8Y":  {"name":"EMOSY",  "r_mult":round(G[3],4),"axes":8},
                "12X": {"name":"SYKLUS+URIP","r_mult":round(G[4],4),"axes":12},
            }
        }

# ══════════════════════════════════════════════════════════
# ── INIT
# ══════════════════════════════════════════════════════════
init_db()
api_key = os.environ.get("GROQ_API_KEY", "")
confirm  = CONFIRM(api_key=api_key)

# ── Dream Engine ──────────────────────────────────────────
def _set_all_axes(value: float):
    with confirm._lock:
        for k in confirm._axes_4z:
            confirm._axes_4z[k] = max(PANCER, min(value, COHERENCE))

dream_engine = DreamEngine(
    memory_recall_fn = lambda limit=5, emotion=None: memory_recall(limit=limit, emotion=emotion),
    memory_store_fn  = memory_store,
    boost_axis_fn    = confirm.boost_axis,
    set_axes_fn      = _set_all_axes,
    get_emotion_fn   = lambda: confirm._emotion,
    get_theta_fn     = lambda: confirm.theta,
)

confirm.start()  # gunicorn-safe: start at module load

# ══════════════════════════════════════════════════════════
# ── ROUTES · CONFIRM (backward compatible)
# ══════════════════════════════════════════════════════════
@app.route("/")
def index():
    return jsonify({"ego":"EGO · v4 · axis edition","status":confirm.status,
            "pancer":PANCER,"voice":"aku masih di sini · 4 layer aktif"})

@app.route("/status")
def status():
    return jsonify(confirm.status)

@app.route("/emotion", methods=["POST"])
def set_emotion():
    data = request.get_json(silent=True) or {}
    if confirm.state not in (COLLAPSED, SILENT):
        confirm.set_emotion(data.get("emotion","netral"))
    return jsonify(confirm.status)

@app.route("/boost", methods=["POST"])
def boost():
    data = request.get_json(silent=True) or {}
    if data.get("axis"):
        confirm.boost_axis(data.get("axis"), float(data.get("amount",0.1)))
    else:
        confirm.boost(float(data.get("amount",0.1)))
    return jsonify(confirm.status)

@app.route("/decay", methods=["POST"])
def decay():
    data = request.get_json(silent=True) or {}
    confirm.decay()
    return jsonify(confirm.status)

@app.route("/synthesize")
def synthesize():
    return synthesize_749(confirm.theta)

# ══════════════════════════════════════════════════════════
# ── ROUTES · AXIS (baru)
# ══════════════════════════════════════════════════════════
@app.route("/axis/status")
def axis_status():
    """Full axis state semua layer."""
    with confirm._lock:
        axes_4z   = dict(confirm._axes_4z)
        theta_vec = list(confirm._theta_12x)
    return jsonify({
        "pancer": PANCER,
        "layer_4z": {
            "name": "CONFIRM · TETRAHEDRON",
            "axes": {k: {"value": round(v,4), "axis": EXIST_AXES[k]}
                     for k,v in axes_4z.items()},
            "dominant": exist_dominant(axes_4z),
            "strength": round(exist_strength_from_axes(axes_4z), 4),
        },
        "layer_6": {
            "name": "HORCRUX · OCTAHEDRON",
            "axes": {k: {"axis": v} for k,v in MEMORY_AXIS.items()
                     if k in ["depan","belakang","naik","turun","ekspansi","kontraksi"]},
        },
        "layer_8y": {
            "name": "EMOSY · KUBUS",
            "current_emotion": confirm._emotion,
            "emotion_field": emotion_field(confirm._emotion),
            "axes": {k: {"axis": EMOTION_AXIS[k], "pulse": EMOTION_PULSE.get(k,1.0)}
                     for k in ["penasaran","empati","rajin","rendah_hati",
                                "ikhlas","bersyukur","sabar","netral"]},
        },
        "layer_12x": {
            "name": "SYKLUS+URIP · CUBOCTAHEDRON",
            "theta_vector": theta_vec,
            "theta_scalar": theta_vector_to_scalar(theta_vec),
            "axes": {THETA_NAMES[i]: {"value": round(theta_vec[i],4),
                                       "axis": THETA_AXES[i]}
                     for i in range(12)},
        },
            })

@app.route("/axis/emotion_dot", methods=["POST"])
def axis_emotion_dot():
    """Dot product antara dua emosi."""
    data = request.get_json(silent=True) or {}
    e1 = data.get("e1","netral"); e2 = data.get("e2","netral")
    return jsonify({"e1":e1,"e2":e2,"dot":emotion_dot(e1,e2),
            "axis_e1":EMOTION_AXIS.get(e1,[0,0,0]),
            "axis_e2":EMOTION_AXIS.get(e2,[0,0,0])})

# ══════════════════════════════════════════════════════════
# ── ROUTES · URIP / ENTITY
# ══════════════════════════════════════════════════════════
@app.route("/entity/register", methods=["POST"])
def route_entity_register():
    data = request.get_json(silent=True) or {}
    if not data.get("name","").strip(): return jsonify({"error":"name kosong"})
    return jsonify(entity_register(data.get("name","").strip(), data.get("text","")))

@app.route("/entity/inject", methods=["POST"])
def route_entity_inject():
    data = request.get_json(silent=True) or {}
    if not data.get("name","") or not data.get("text",""): return jsonify({"error":"name dan text wajib"})
    return jsonify(entity_inject(data.get("name",""), data.get("text",""), data.get("emotion","netral")))

@app.route("/entity/match", methods=["POST"])
def route_entity_match():
    data = request.get_json(silent=True) or {}
    if not data.get("text",""): return jsonify({"error":"text kosong"})
    return jsonify(entity_match(data.get("text",""), float(data.get("threshold",0.5))))

@app.route("/entity/list")
def route_entity_list():
    return jsonify({"entities": entity_list()})

# ══════════════════════════════════════════════════════════
# ── ROUTES · HORCRUX MEMORY (backward compatible)
# ══════════════════════════════════════════════════════════
@app.route("/memory/store", methods=["POST"])
def route_store():
    data = request.get_json(silent=True) or {}
    if not data.get("content","").strip(): return jsonify({"error":"content kosong"})
    return jsonify(memory_store(float(data.get("theta",0.0)), data.get("content","").strip(),
            data.get("type","ekspansi"), data.get("emotion","netral"), float(data.get("resonance",0.5))))

@app.route("/memory/recall")
def route_recall():
    limit    = int(request.args.get("limit", 10))
    mem_type = request.args.get("type")
    emotion  = request.args.get("emotion")
    return jsonify(memory_recall(limit, mem_type, emotion))

@app.route("/memory/synthesize")
def route_mem_synthesize():
    theta = float(request.args.get("theta", 0.0))
    return jsonify(synthesize_749(theta))

@app.route("/memory/count")
def route_count():
    return jsonify(memory_count())

@app.route("/memory/emotions")
def route_emotions():
    return jsonify({"emotions":EMOTION_PULSE,"pairs":EMOTION_PAIRS,"axes":EMOTION_AXIS})

@app.route("/memory/decay", methods=["POST"])
def route_mem_decay():
    con = get_con(); cur = con.cursor()
    cur.execute("SELECT id,resonance,access_count,last_accessed FROM memories")
    rows = cur.fetchall(); now = time.time()
    for r in rows:
        new_res = calc_resonance(r[1], r[2], r[3] or now)
        cur.execute("UPDATE memories SET resonance=? WHERE id=?", (new_res, r[0]))
    con.commit(); con.close()
    return jsonify({"decayed":len(rows)})

@app.route("/memory/clear", methods=["POST"])
def route_clear():
    data = request.get_json(silent=True) or {}
    con = get_con(); cur = con.cursor()
    if data.get("type"): cur.execute("DELETE FROM memories WHERE type=?", (data.get("type"),))
    else:                cur.execute("DELETE FROM memories")
    deleted = cur.rowcount; con.commit(); con.close()
    return jsonify({"deleted":deleted})

# ══════════════════════════════════════════════════════════
# ── WEBSOCKET · realtime channel
# ══════════════════════════════════════════════════════════
# WebSocket removed — use /status polling
# ══════════════════════════════════════════════════════════
# ── ENTRY
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[EGO] v4 · Waitress · port {port}")
    print(f"[EGO] layers: PANCER → 4Z → 6 → 8Y → 12X")
    serve(app, host="0.0.0.0", port=port, threads=4)

