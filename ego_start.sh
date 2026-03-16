#!/data/data/com.termux/files/usr/bin/bash
# ◎ EGO STARTUP SCRIPT · v2
# Usage: bash ego_start.sh

# ── Load .env kalau ada ───────────────────────────────────
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "◎ .env loaded"
fi

echo "◎ EGO · stopping old instance..."
pkill -f ego_backend.py 2>/dev/null
pkill -f "uvicorn ego_backend" 2>/dev/null
sleep 1

echo "◎ EGO · starting v3..."
echo "   θ evolves with emotion"
echo "   dream phase active"
echo "   node749 auto-synth"
echo ""

# Cek API key
if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠ GROQ_API_KEY belum di-set!"
    echo "  Isi file .env di folder yang sama:"
    echo "  GROQ_API_KEY=isi_key_kamu"
    exit 1
fi

# Cek uvicorn tersedia, fallback ke flask dev
if command -v uvicorn &>/dev/null; then
    echo "◎ server · uvicorn (stable)"
    uvicorn ego_backend:app --host 0.0.0.0 --port 5000 &
else
    echo "◎ server · flask dev"
    echo "  (install uvicorn kapanpun: pip install uvicorn)"
    python ego_backend.py &
fi

EGO_PID=$!
sleep 1

echo ""
echo "◎ EGO · alive · PID=$EGO_PID"
echo "   curl http://localhost:5000/status"
echo ""
echo "r(θ) = 105 × e^(0.0318 × θ) · Pancer selalu tersisa 🌀"
