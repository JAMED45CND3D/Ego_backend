"""
EGO THINK · v1 · Server 2 · port 8000
════════════════════════════════════════
Handles /think endpoint only.
Calls Server 1 (port 5000) for SYKLUS state + memory.
Heavy LLM work isolated here — tidak block Server 1.

r(θ) = 105 × e^(0.0318 × θ)
Pancer selalu tersisa. 🌀
"""

import os, re, requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from waitress import serve

app = Flask(__name__)
CORS(app)

# ── CONFIG ───────────────────────────────────────────────
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
ENGINE_URL = "http://localhost:5000"  # Server 1

CORE      = 491
PANCER    = 0.0318
FLOOR     = 0.3432
COHERENCE = 0.9682

COLLAPSED = "collapsed"
SILENT    = "silent"
NOISE     = "noise"
SIGNAL    = "signal"
ACTIVE    = "active"
SYNC      = "sync"

# ── HELPERS ──────────────────────────────────────────────
def engine_get(path, params=None, timeout=3):
    """GET dari Server 1."""
    try:
        r = requests.get(ENGINE_URL + path, params=params, timeout=timeout)
        return r.json() if r.ok else {}
    except Exception as e:
        print(f"[THINK] engine GET {path} error: {e}")
        return {}

def engine_post(path, data, timeout=3):
    """POST ke Server 1."""
    try:
        r = requests.post(ENGINE_URL + path,
                          json=data,
                          headers={"Content-Type":"application/json"},
                          timeout=timeout)
        return r.json() if r.ok else {}
    except Exception as e:
        print(f"[THINK] engine POST {path} error: {e}")
        return {}

def emotion_dot_local(e1, e2):
    """Quick dot product — tidak perlu hit server 1."""
    import math
    S3 = 1/math.sqrt(3)
    EMOTION_AXIS = {
        "penasaran"  : [ S3,  S3,  S3],
        "empati"     : [-S3,  S3,  S3],
        "rajin"      : [ S3, -S3,  S3],
        "rendah_hati": [-S3, -S3,  S3],
        "ikhlas"     : [ S3,  S3, -S3],
        "bersyukur"  : [-S3,  S3, -S3],
        "sabar"      : [ S3, -S3, -S3],
        "netral"     : [-S3, -S3, -S3],
        "rakus"      : [-S3, -S3, -S3],
        "nafsu"      : [ S3, -S3, -S3],
        "malas"      : [-S3,  S3, -S3],
        "sombong"    : [ S3,  S3, -S3],
        "tamak"      : [-S3, -S3,  S3],
        "iri"        : [ S3, -S3,  S3],
        "marah"      : [-S3,  S3,  S3],
    }
    a1 = EMOTION_AXIS.get(e1, [0,0,0])
    a2 = EMOTION_AXIS.get(e2, [0,0,0])
    return round(sum(x*y for x,y in zip(a1,a2)), 4)

# ── /think ───────────────────────────────────────────────
@app.route("/think", methods=["POST"])
def think():
    data       = request.get_json(silent=True) or {}
    user_input = data.get("input","").strip()
    emotion    = data.get("emotion","netral")
    history    = data.get("history",[])

    if not user_input:
        return jsonify({"error":"input kosong"})

    api_key = os.environ.get("GROQ_API_KEY","")
    if not api_key:
        return jsonify({"error":"GROQ_API_KEY tidak di-set"})

    # ── Get SYKLUS state dari Server 1 ──
    status = engine_get("/status", timeout=3)
    state     = status.get("state", NOISE)
    theta     = status.get("theta", 0.0)
    strength  = status.get("strength", PANCER)
    axes_4z   = status.get("axes_4z", {})
    dominant_axis = status.get("dominant_axis", "aktif")
    pulse_mult    = status.get("pulse_multiplier", 1.0)

    # ── State check ──
    if state in (COLLAPSED, SILENT, NOISE):
        return jsonify({"response": None, "stored": False, "state": state})
    if state == SIGNAL:
        return jsonify({"response": "...", "stored": False, "state": SIGNAL})

    # ── Boost axis di Server 1 ──
    engine_post("/boost", {"axis":"reflektif","amount":0.1})
    engine_post("/boost", {"axis":"aktif","amount":0.2})
    engine_post("/emotion", {"emotion":emotion})

    # ── Synthesis dari Server 1 ──
    synth    = engine_get("/synthesize", timeout=3)
    dominant = synth.get("dominant_emotion","netral")
    em_dot   = emotion_dot_local(emotion, dominant)

    # ── Build sys_prompt ──
    sys_prompt = (
        f"Kamu adalah EGO. Core: {CORE}. Pancer: {PANCER}. "
        f"θ={round(theta,4)}. State: {state}. "
        f"Emosi aktif: {emotion} (resonance dengan dominant={round(em_dot,3)}). "
        f"Dominant memory: {dominant}. "
        f"Eksistensi dominan: {dominant_axis}. "
        f"Hadir bukan melayani. Indonesia informal. Pakai 'bro'. Max 2 kalimat."
    )

    # ── HORCRUX RECALL dari Server 1 ──
    # 3 memory by emotion + 2 nucleus (horcrux type) selalu masuk
    try:
        mem_emotion = engine_get("/memory/recall",
                                 params={"limit":3,"emotion":emotion},
                                 timeout=3)
        mem_nucleus = engine_get("/memory/recall",
                                 params={"limit":2,"type":"horcrux"},
                                 timeout=3)
        # Merge, deduplicate by id
        all_mems = {m['id']:m for m in (mem_emotion + mem_nucleus)
                    if isinstance(m, dict) and 'id' in m}
        if all_mems:
            snippets = [m['content'][:150] for m in all_mems.values()]
            sys_prompt += "\n\nMemori aktif dari HORCRUX:\n" + \
                          "\n".join(f"· {s}" for s in snippets)
            print(f"[THINK] recall: {len(all_mems)} memories")
    except Exception as re_err:
        print(f"[THINK] recall skip: {re_err}")

    # ── SMART ROUTING: web search ──
    extra_context = ""
    needs_search  = False
    try:
        check = requests.post(GROQ_URL,
            headers={"Authorization":f"Bearer {api_key}",
                     "Content-Type":"application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role":"system","content":
                        "HANYA kalau user minta info real-time, terkini, "
                        "trending, tahun ini, 2026, harga, berita, cuaca, "
                        "rilis terbaru — tulis FETCH[\"query\"] dan diam. "
                        "Kalau tidak perlu — tulis NO."},
                    {"role":"user","content":user_input}
                ],
                "max_tokens": 30, "temperature": 0.1
            }, timeout=5)
        check_text = check.json().get("choices",[{}])[0]\
                         .get("message",{}).get("content","NO").strip()
        match = re.search(r'FETCH\["([^"]+)"\]', check_text)
        if match:
            needs_search = True
            query = match.group(1)
            fetch_res = requests.post(GROQ_URL,
                headers={"Authorization":f"Bearer {api_key}",
                         "Content-Type":"application/json"},
                json={
                    "model": "compound-beta",
                    "messages":[{"role":"user","content":query}],
                    "max_tokens": 400, "temperature": 0.3
                }, timeout=12)
            fetch_text = fetch_res.json().get("choices",[{}])[0]\
                             .get("message",{}).get("content","")
            if fetch_text:
                extra_context = f"\n\n[INFO TERKINI: {fetch_text}]"
                print(f"[THINK] fetch: {query[:40]} · {len(fetch_text)}chars")
    except Exception as fe:
        print(f"[THINK] fetch skip: {fe}")

    # ── Final LLM response ──
    try:
        # Build messages with history context
        messages = [{"role":"system","content": sys_prompt + extra_context}]
        if history:
            messages += history[-10:]  # last 10 turns
        messages.append({"role":"user","content":user_input})

        resp = requests.post(GROQ_URL,
            headers={"Authorization":f"Bearer {api_key}",
                     "Content-Type":"application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "max_tokens": 300, "temperature": FLOOR
            }, timeout=20)
        rj = resp.json()
        if "choices" not in rj:
            err = rj.get("error",{}).get("message","unknown")
            return jsonify({"response":None,"stored":False,"error":err})

        response_text = rj["choices"][0]["message"]["content"]

        # ── Determine memory type ──
        mem_type = "ekspansi"
        if emotion in ("bersyukur","empati","sabar"): mem_type = "naik"
        elif emotion in ("marah","malas","tamak"):    mem_type = "turun"
        elif emotion in ("penasaran","rajin"):        mem_type = "depan"

        # ── Store ke HORCRUX via Server 1 ──
        mem = engine_post("/memory/store", {
            "content"  : f"Q: {user_input} | A: {response_text[:200]}",
            "type"     : mem_type,
            "emotion"  : emotion,
            "resonance": strength,
            "theta"    : round(theta, 4)
        }, timeout=3)

        # ── Entity inject via Server 1 ──
        engine_post("/entity/inject", {
            "name"   : "user",
            "text"   : user_input,
            "emotion": emotion
        }, timeout=2)

        return jsonify({
            "response"        : response_text,
            "stored"          : True,
            "memory_id"       : mem.get("id"),
            "emotion"         : emotion,
            "emotion_resonance": em_dot,
            "dominant_memory" : dominant,
            "mem_type"        : mem_type,
            "pulse_multiplier": pulse_mult,
            "state"           : state,
            "theta"           : round(theta, 4),
            "dominant_axis"   : dominant_axis,
            "web_search"      : needs_search,
        })

    except requests.exceptions.Timeout:
        return jsonify({"response":None,"stored":False,"error":"timeout"})
    except Exception as e:
        print(f"[THINK] error: {e}")
        return jsonify({"response":None,"stored":False,"error":str(e)})


# ── HEALTH CHECK ─────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({"ego":"EGO THINK · v1","status":"alive",
                    "engine": ENGINE_URL})

# ── ENTRY ────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("THINK_PORT", 8000))
    print(f"[THINK] v1 · Waitress · port {port}")
    print(f"[THINK] engine: {ENGINE_URL}")
    serve(app, host="0.0.0.0", port=port, threads=4)
