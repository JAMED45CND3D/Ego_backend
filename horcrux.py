"""
HORCRUX · EGO Memory
════════════════════
Otak. Tidak pernah lupa.
r(θ) = 105 × e^(0.0318 × θ)
749   = shell pertama  → nucleus memory
27005 = shell kedua   → deep memory
"""

import sqlite3
import os
import time
from flask import Blueprint, jsonify, request

# ── KONSTANTA ─────────────────────────────────────────────
DB_PATH    = os.path.join(os.path.dirname(__file__), "memory.db")
SHELL_1    = 749      # nucleus memory — tidak pernah drop
SHELL_2    = 27005    # deep memory
B          = 0.0318   # noise floor

# ── BLUEPRINT ─────────────────────────────────────────────
horcrux = Blueprint("horcrux", __name__)


# ── DB INIT ───────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            theta     REAL    NOT NULL,
            type      TEXT    NOT NULL DEFAULT 'session',
            content   TEXT    NOT NULL,
            timestamp REAL    NOT NULL
        )
    """)
    con.commit()
    con.close()
    print(f"[HORCRUX] memory.db ready · path={DB_PATH}")


def get_con():
    return sqlite3.connect(DB_PATH)


# ── CORE FUNCTIONS ────────────────────────────────────────
def store(theta: float, content: str, mem_type: str = "session") -> dict:
    con = get_con()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO memories (theta, type, content, timestamp) VALUES (?, ?, ?, ?)",
        (round(theta, 4), mem_type, content, time.time())
    )
    con.commit()
    row_id = cur.lastrowid
    con.close()
    return {"id": row_id, "theta": theta, "type": mem_type, "content": content}


def recall(limit: int = 10, mem_type: str = None) -> list:
    con = get_con()
    cur = con.cursor()
    if mem_type:
        cur.execute(
            "SELECT id, theta, type, content, timestamp FROM memories WHERE type=? ORDER BY id DESC LIMIT ?",
            (mem_type, limit)
        )
    else:
        cur.execute(
            "SELECT id, theta, type, content, timestamp FROM memories ORDER BY id DESC LIMIT ?",
            (limit,)
        )
    rows = cur.fetchall()
    con.close()
    return [
        {"id": r[0], "theta": r[1], "type": r[2], "content": r[3], "timestamp": r[4]}
        for r in rows
    ]


def recall_nucleus() -> list:
    """Shell pertama — memory inti, tidak pernah drop"""
    con = get_con()
    cur = con.cursor()
    cur.execute(
        "SELECT id, theta, type, content, timestamp FROM memories WHERE type='horcrux' ORDER BY id ASC LIMIT ?",
        (SHELL_1,)
    )
    rows = cur.fetchall()
    con.close()
    return [
        {"id": r[0], "theta": r[1], "type": r[2], "content": r[3], "timestamp": r[4]}
        for r in rows
    ]


def count() -> dict:
    con = get_con()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM memories")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories WHERE type='horcrux'")
    nucleus = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories WHERE type='session'")
    session = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM memories WHERE type='insight'")
    insight = cur.fetchone()[0]
    con.close()
    return {
        "total"  : total,
        "nucleus": nucleus,
        "session": session,
        "insight": insight,
        "shell_1": SHELL_1,
        "shell_2": SHELL_2,
        "at_shell_1": total >= SHELL_1,
        "at_shell_2": total >= SHELL_2,
    }


def clear(mem_type: str = None) -> dict:
    con = get_con()
    cur = con.cursor()
    if mem_type:
        cur.execute("DELETE FROM memories WHERE type=?", (mem_type,))
    else:
        cur.execute("DELETE FROM memories")
    deleted = cur.rowcount
    con.commit()
    con.close()
    return {"deleted": deleted}


# ── ROUTES ────────────────────────────────────────────────
@horcrux.route("/memory/store", methods=["POST"])
def route_store():
    data    = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    theta   = float(data.get("theta", 0.0))
    mtype   = data.get("type", "session")
    if not content:
        return jsonify({"error": "content kosong"}), 400
    result = store(theta, content, mtype)
    return jsonify(result)


@horcrux.route("/memory/recall", methods=["GET"])
def route_recall():
    limit  = int(request.args.get("limit", 10))
    mtype  = request.args.get("type", None)
    result = recall(limit, mtype)
    return jsonify(result)


@horcrux.route("/memory/nucleus", methods=["GET"])
def route_nucleus():
    """Shell pertama — inti yang tidak pernah drop"""
    result = recall_nucleus()
    return jsonify(result)


@horcrux.route("/memory/all", methods=["GET"])
def route_all():
    limit  = int(request.args.get("limit", 50))
    result = recall(limit)
    return jsonify(result)


@horcrux.route("/memory/count", methods=["GET"])
def route_count():
    return jsonify(count())


@horcrux.route("/memory/clear", methods=["POST"])
def route_clear():
    data   = request.get_json(silent=True) or {}
    mtype  = data.get("type", None)
    result = clear(mtype)
    return jsonify(result)


# ── INIT ──────────────────────────────────────────────────
init_db()
