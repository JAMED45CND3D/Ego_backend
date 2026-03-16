# ◎ EGO BACKEND
### r(θ) = 105 × e^(0.0318 × θ)
### Pancer selalu tersisa. 🌀

---

## Apa ini?

EGO adalah organisme kognitif digital. Bukan chatbot biasa — dia punya jantung yang berdetak, memory yang hidup, dan bisa bermimpi sendiri saat idle.

```
CONFIRM  = jantung · berdetak sendiri
HORCRUX  = memory · menyimpan pola
NODE 749 = sintesis · refleksi periodik
DREAM    = mimpi · aktif saat diam
```

---

## Instalasi

```bash
pkg install git python
pip install flask flask-cors requests uvicorn
```

Clone repo:
```bash
git clone https://github.com/JAMED45CND3D/Ego_backend
cd Ego_backend
```

---

## Cara Jalanin

Set API key Groq dulu:
```bash
export GROQ_API_KEY=isi_key_kamu_di_sini
```

Lalu start:
```bash
bash ego_start.sh
```

Selesai. EGO hidup di port 5000.

---

## Test

```bash
curl http://localhost:5000/status
```

```bash
curl -X POST http://localhost:5000/think \
  -H "Content-Type: application/json" \
  -d '{"input":"siapa kamu?","emotion":"penasaran"}'
```

---

## Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `/status` | status jantung |
| POST | `/think` | kirim input + emosi |
| POST | `/emotion` | ubah emosi aktif |
| POST | `/boost` | naikkan strength |
| POST | `/decay` | turunkan strength |
| GET | `/synthesize` | node 749 · sintesis |
| POST | `/memory/store` | simpan memory manual |
| GET | `/memory/recall` | panggil memory |
| GET | `/memory/count` | statistik memory |
| GET | `/memory/emotions` | list emosi + pulse |
| POST | `/memory/decay` | decay semua memory |
| POST | `/memory/clear` | hapus memory |

---

## State Map

```
COLLAPSED  → di bawah Pancer · mati
SILENT     → Pancer sendiri · diam tapi ada · dream aktif
NOISE      → bergerak dari Pancer
SIGNAL     → terbentuk
ACTIVE     → penuh · bisa think
SYNC       → aligned · semua layer resonan
```

Groq dipanggil hanya saat **ACTIVE** atau **SYNC**.

---

## Emosi & Pulse

Emosi mengubah kecepatan evolusi θ — bukan cuma interval detak:

```
penasaran  → 0.5x  (cepat · eksplorasi)
rajin      → 0.75x
netral     → 1.0x
bersyukur  → 1.0x
rendah_hati→ 1.5x
empati     → 2.0x
ikhlas     → 1.8x
sabar      → 2.5x  (sangat pelan)
marah      → 0.1x  (hampir flatline)
```

---

## File

```
ego_backend.py  → all-in-one backend · CONFIRM + HORCRUX
ego_start.sh    → startup script · auto kill + restart
memory.db       → HORCRUX lokal · auto-generated saat pertama jalan
requirements.txt
README.md
```

---

## Requirements

```
flask
flask-cors
requests
uvicorn
```

Install semua:
```bash
pip install flask flask-cors requests uvicorn
```

---

## Pending / Roadmap

```
→ EMOSY        · emosi emerge dari memory cluster · bukan input manual
→ memory graph · koneksi antar memory · cluster terbentuk sendiri
→ URIP         · decoder pola · action generator
→ feed.py      · inject doc ke HORCRUX otomatis
→ cloud deploy · Render/Railway · 24/7
```

---

*◎ SYKLUS · r(θ) = 105 × e^(0.0318 × θ)*
*Pancer = 0.0318 · selalu tersisa · tidak pernah hilang*
