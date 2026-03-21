#!/data/data/com.termux/files/usr/bin/bash
# ◎ EGO STARTUP SCRIPT · v4 · Flask edition

if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    echo "◎ .env loaded"
fi

echo "◎ EGO · stopping old instance..."
pkill -f ego_backend.py 2>/dev/null
pkill -f gunicorn 2>/dev/null
sleep 1

# ── WAKE LOCK · jaga EGO tetap hidup saat layar mati
if command -v termux-wake-lock &>/dev/null; then
    termux-wake-lock
    echo "◎ wake lock · aktif"
else
    echo "⚠ termux-wake-lock tidak tersedia · install: pkg install termux-api"
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo "⚠ GROQ_API_KEY belum di-set!"
    echo "  Isi file .env: GROQ_API_KEY=isi_key_kamu"
    exit 1
fi

echo ""
echo "◎ EGO · starting v4 · SYKLUS AXIS EDITION"
echo "   r(θ) = 105 × e^(0.0318 × θ)"
echo "   PANCER → 4Z → 6 → 8Y → 12X"
echo ""

python ego_backend.py &

EGO_PID=$!

# Wait until port 5000 ready — max 60 detik
echo "◎ waiting for backend to be ready..."
for i in $(seq 1 60); do
  curl -s --max-time 2 http://localhost:5000/ > /dev/null 2>&1 && echo "◎ backend ready · ${i}s" && break
  sleep 1
done

# Start Server 2 — /think engine
python ego_think.py &
THINK_PID=$!
echo "◎ think engine started · PID=$THINK_PID"
sleep 2

echo "◎ feeding nucleus..."
python feed_nucleus.py 2>/dev/null && echo "   nucleus · OK" || echo "   nucleus · skip"

echo "◎ feeding sesi..."
python feed_sesi.py 2>/dev/null && echo "   sesi · OK" || echo "   sesi · skip"

echo ""
echo "◎ EGO · alive · PID=$EGO_PID"
echo "   http://localhost:5000"
echo "   http://localhost:5000/status"
echo ""
echo "0.0318 · selalu tersisa 🌀"
