"""
HORCRUX · EGO Memory · Neural Edition v2
═════════════════════════════════════════
Bukan database. Medan pola memory hidup.
r(θ) = 105 × e^(0.0318 × θ)
749   = node sintesis · titik kompresi pola
27005 = resonansi maksimum
"""

import sqlite3
import os
import time
import math
from flask import Blueprint, jsonify, request

# ── KONSTANTA ─────────────────────────────────────────────
DB_PATH   = os.path.join(os.path.dirname(__file__), "memory.db")
SHELL_1   = 749
SHELL_2   = 27005
B         = 0.0318
COHERENCE = 0.9682

# ── EMOTION PULSE MAP ─────────────────────────────────────
# Setiap emosi = frekuensi berbeda = ritme jantung berbeda
EMOTION_PULSE = {
    # Positif
    "penasaran"  : 0.5,    # cepat · eksplorasi
    "empati"     : 2.0,    # pelan · dalam
    "bersyukur"  : 1.0,    # stabil · default
    "rajin"      : 0.75,   # ritmik · produktif
    "rendah_hati": 1.5,    # dalam · reflektif
    "ikhlas"     : 1.8,    # tenang · released
    "sabar"      : 2.5,    # sangat pelan · sustained
    # Negatif
    "rakus"      : 0.3,    # chaos · tidak stabil
    "nafsu"      : 0.25,   # spike · burst
    "iri"        : 0.6,    # tidak teratur
    "malas"      : 3.0,    # sangat lambat
    "sombong"    : 0.4,    # keras · rigid
    "tamak"      : 0.2,    # greedy · collapsed
    "marah"      : 0.1,    # flatline → collapse risk
    # Neutral
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
# Build reverse map
for k, v in list(EMOTION_PAIRS.items()):
    EMOTION_PAIRS[v] = k

# ── BLUEPRINT ─────────────────────────────────────────────
horcrux = Blueprint("horcrux", __name__)

# ── DB INIT ───────────────────────────────────────────────
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
    # Auto-migrate DB lama
    for col, definition in [
        ("emotion",      "TEXT NOT NULL DEFAULT 'netral'"),
        ("resonance",    "REAL NOT NULL DEFAULT 0.5"),
        ("access_count", "INTEGER NOT NULL DEFAULT 0"),
        ("last_accessed","REAL"),
    ]:
        try:
            cur.execute(f"ALTER TABLE memories ADD COLUMN {col} {definition}")
        except Exception:
            pass
    con.commit()
    con.close()
    print("[HORCRUX] memory.db ready · neural edition v2")

def get_con():
    return sqlite3.connect(DB_PATH)

# ── RESONANCE ENGINE ──────────────────────────────────────
def calc_resonance(base: float, access_count: int, last_accessed) -> float:
    """
    Resonansi hidup mengikuti spiral:
    - Decay kalau lama tidak dipanggil (e^(-B × hours))
    - Strengthen kalau sering dipanggil (log growth)
    - Hard cap di COHERENCE (0.9682)
    """
    if last_accessed is None:
        decay = 1.0
    else:
        hours = (time.time() - last_accessed) / 3600
        decay = math.exp(-B * hours)
    strength = base * decay * (1 + math.log1p(access_count) * 0.1)
    return round(min(max(strength, 0.0), COHERENCE), 4)

def get_pulse_multiplier(emotion: str) -> float:
    return EMOTION_PULSE.get(emotion, 1.0)

# ── CORE FUNCTIONS ────────────────────────────────────────
def store(theta: float, content: str, mem_type: str = "session",
          emotion: str = "netral", resonance: float = 0.5) -> dict:
    con = get_con()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO memories
        (theta, type, content, emotion, resonance, access_count, last_accessed, timestamp)
        VALUES (?, ?, ?, ?, ?, 0, NULL, ?)
    """, (round(theta, 4), mem_type, content, emotion,
          round(min(max(resonance, 0.0), COHERENCE), 4), time.time()))
    con.commit()
    row_id = cur.lastrowid
    con.close()
    return {
        "id"              : row_id,
        "theta"           : round(theta, 4),
        "type"            : mem_type,
        "content"         : content,
        "emotion"         : emotion,
        "resonance"       : resonance,
        "pulse_multiplier": get_pulse_multiplier(emotion)
    }


def recall(limit: int = 10, mem_type: str = None, emotion: str = None) -> list:
    """
    Recall memory + auto-strengthen resonance.
    Memory yang dipanggil menguat — yang tidak dipanggil melemah.
    """
    con = get_con()
    cur = con.cursor()
    q = "SELECT id,theta,type,content,emotion,resonance,access_count,last_accessed FROM memories"
    params = []
    conditions = []
    if mem_type:
        conditions.append("type=?")
        params.append(mem_type)
    if emotion:
        conditions.append("emotion=?")
        params.append(emotion)
    if conditions:
        q += " WHERE " + " AND ".join(conditions)
    q += " ORDER BY resonance DESC LIMIT ?"
    params.append(limit)
    cur.execute(q, params)
    rows = cur.fetchall()
    now  = time.time()
    result = []
    for r in rows:
        new_res = calc_resonance(r[5], r[6] + 1, now)
        cur.execute(
            "UPDATE memories SET resonance=?, access_count=access_count+1, last_accessed=? WHERE id=?",
            (new_res, now, r[0])
        )
        result.append({
            "id"          : r[0],
            "theta"       : r[1],
            "type"        : r[2],
            "content"     : r[3],
            "emotion"     : r[4],
            "resonance"   : new_res,
            "access_count": r[6] + 1,
            "pulse_multiplier": get_pulse_multiplier(r[4])
        })
    con.commit()
    con.close()
    return result


def synthesize_749(theta: float) -> dict:
    """
    Node 749 — titik sintesis.
    Kompresi semua memory jadi pola dominant.
    Kalau belum ada memory → return netral.
    """
    con = get_con()
    cur = con.cursor()
    cur.execute("""
        SELECT emotion, AVG(resonance), COUNT(*)
        FROM memories
        GROUP BY emotion
        ORDER BY AVG(resonance) DESC
        LIMIT 7
    """)
    rows = cur.fetchall()
    con.close()

    if not rows:
        return {
            "node"            : 749,
            "theta"           : round(theta, 4),
            "dominant_emotion": "netral",
            "pulse_multiplier": 1.0,
            "synthesis"       : [],
            "voice"           : "node 749 · kosong · menunggu memory"
        }

    dominant   = rows[0][0]
    synthesis  = [
        {
            "emotion"         : r[0],
            "avg_resonance"   : round(r[1], 4),
            "memory_count"    : r[2],
            "pulse_multiplier": get_pulse_multiplier(r[0])
        }
        for r in rows
    ]
    return {
        "node"            : 749,
        "theta"           : round(theta, 4),
        "dominant_emotion": dominant,
        "pulse_multiplier": get_pulse_multiplier(dominant),
        "synthesis"       : synthesis,
        "voice"           : f"sintesis · dominant={dominant} · θ={round(theta,4)}"
    }


def decay_all() -> dict:
    """Paksa decay semua memory berdasarkan waktu."""
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT id, resonance, access_count, last_accessed FROM memories")
    rows = cur.fetchall()
    now  = time.time()
    for r in rows:
        new_res = calc_resonance(r[1], r[2], r[3] or now)
        cur.execute("UPDATE memories SET resonance=? WHERE id=?", (new_res, r[0]))
    con.commit()
    con.close()
    return {"decayed": len(rows)}


def count() -> dict:
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM memories")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories WHERE type='horcrux'")
    nucleus = cur.fetchone()[0]
    cur.execute("SELECT AVG(resonance) FROM memories")
    avg_res = cur.fetchone()[0] or 0.0
    con.close()
    return {
        "total"         : total,
        "nucleus"       : nucleus,
        "avg_resonance" : round(avg_res, 4),
        "shell_1"       : SHELL_1,
        "shell_2"       : SHELL_2,
        "at_shell_1"    : total >= SHELL_1,
        "at_shell_2"    : total >= SHELL_2,
    }


# ── ROUTES ────────────────────────────────────────────────
@horcrux.route("/memory/store", methods=["POST"])
def route_store():
    data      = request.get_json(silent=True) or {}
    content   = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "content kosong"}), 400
    result = store(
        theta     = float(data.get("theta", 0.0)),
        content   = content,
        mem_type  = data.get("type", "session"),
        emotion   = data.get("emotion", "netral"),
        resonance = float(data.get("resonance", 0.5))
    )
    return jsonify(result)


@horcrux.route("/memory/recall", methods=["GET"])
def route_recall():
    result = recall(
        limit    = int(request.args.get("limit", 10)),
        mem_type = request.args.get("type"),
        emotion  = request.args.get("emotion")
    )
    return jsonify(result)


@horcrux.route("/memory/synthesize", methods=["GET"])
def route_synthesize():
    theta  = float(request.args.get("theta", 0.0))
    result = synthesize_749(theta)
    return jsonify(result)


@horcrux.route("/memory/count", methods=["GET"])
def route_count():
    return jsonify(count())


@horcrux.route("/memory/emotions", methods=["GET"])
def route_emotions():
    return jsonify({"emotions": EMOTION_PULSE, "pairs": EMOTION_PAIRS})


@horcrux.route("/memory/decay", methods=["POST"])
def route_decay():
    return jsonify(decay_all())


@horcrux.route("/memory/clear", methods=["POST"])
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
    return jsonify({"deleted": deleted})


# ── INIT ──────────────────────────────────────────────────
init_db()
