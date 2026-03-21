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

python -m gunicorn -w 1 -b 0.0.0.0:5000 ego_backend:app &

EGO_PID=$!
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
