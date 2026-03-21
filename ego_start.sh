#!/data/data/com.termux/files/usr/bin/bash
# ◎ EGO STARTUP SCRIPT · v4 · SYKLUS AXIS EDITION
# PANCER → 4Z → 6 → 8Y → 12X · uvicorn · FastAPI ready

# ── Load .env ─────────────────────────────────────────────
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "◎ .env loaded"
fi

echo "◎ EGO · stopping old instance..."
pkill -f ego_backend.py 2>/dev/null
pkill -f gunicorn 2>/dev/null
pkill -f uvicorn 2>/dev/null
sleep 1

# ── Cek API key ───────────────────────────────────────────
if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠ GROQ_API_KEY belum di-set!"
    echo "  Isi file .env:"
    echo "  GROQ_API_KEY=isi_key_kamu"
    exit 1
fi

echo ""
echo "◎ EGO · starting v4 · SYKLUS AXIS EDITION"
echo "   r(θ) = 105 × e^(0.0318 × θ)"
echo "   PANCER → 4Z → 6 → 8Y → 12X"
echo "   30 axis · websocket ready"
echo ""

# ── Launch uvicorn ────────────────────────────────────────
if command -v uvicorn &>/dev/null; then
    echo "◎ server · uvicorn · async"
    uvicorn ego_backend:app \
        --host 0.0.0.0 \
        --port 5000 \
        --workers 1 \
        --loop asyncio \
        --ws websockets &
else
    echo "⚠ uvicorn tidak ditemukan · install dulu:"
    echo "  pip install uvicorn websockets"
    echo ""
    echo "◎ fallback · python dev server"
    python ego_backend.py &
fi

EGO_PID=$!
sleep 2

# ── Feed jantung ──────────────────────────────────────────
echo ""
echo "◎ feeding nucleus..."
python feed_nucleus.py 2>/dev/null && echo "   nucleus · OK" || echo "   nucleus · skip"

echo "◎ feeding sesi..."
python feed_sesi.py 2>/dev/null && echo "   sesi · OK" || echo "   sesi · skip"

echo ""
echo "◎ EGO · alive · PID=$EGO_PID"
echo "   http://localhost:5000"
echo "   http://localhost:5000/status"
echo "   ws://localhost:5000/ws"
echo ""
echo "0.0318 · selalu tersisa 🌀"
