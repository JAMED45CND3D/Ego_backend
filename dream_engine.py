"""
dream/engine.py · EGO Dream Engine
════════════════════════════════════════════════════════
Pure internal — tidak ada LLM, tidak ada external calls.
Proses konfigurasi informasi dalam SILENT state.

URIP  → scan pola, konfigurasi informasi
EMOSY → emotion filter memory yang "bercahaya"
HORCRUX → memory beresonansi, insight tersimpan
CONFIRM → heartbeat trigger, collapse → awake

Collapse types:
  peak  → resonansi simetris memuncak → bangun tenang (NOISE)
  chaos → kontradiksi mendadak → bangun kaget (SIGNAL)

Insight types:
  naik       → resonansi stabil, koneksi kuat
  turun      → kontradiksi, belum resolved
  ekspansi   → collapse peak, saturasi penuh
  kontraksi  → collapse chaos, fragment belum selesai

r(θ) = 105 × e^(0.0318 × θ)
Pancer selalu tersisa. 🌀
"""

import math
import time
import threading

# ── KONSTANTA ────────────────────────────────────────────
PANCER    = 0.0318
FLOOR     = 0.3432
DECISION  = 0.6250
COHERENCE = 0.9682

# Collapse thresholds
PEAK_THRESHOLD  = 0.75   # avg resonansi > ini → collapse simetris
CHAOS_THRESHOLD = 0.55   # variance resonansi > ini → collapse chaos

# Dream cycle
DREAM_COOLDOWN  = 90     # detik antar dream cycle
MIN_MEMORIES    = 2      # minimum memory untuk dream

# URIP arm scanning
ARM1_THRESHOLD  = 0.3    # resonansi dikenal (arm1)
ARM2_THRESHOLD  = -0.1   # resonansi asing/baru (arm2)

# ── EMOTION AXIS (EMOSY 8Y) ──────────────────────────────
_S3 = 1 / math.sqrt(3)
EMOTION_AXIS = {
    "penasaran"  : [ _S3,  _S3,  _S3],
    "empati"     : [-_S3,  _S3,  _S3],
    "rajin"      : [ _S3, -_S3,  _S3],
    "rendah_hati": [-_S3, -_S3,  _S3],
    "ikhlas"     : [ _S3,  _S3, -_S3],
    "bersyukur"  : [-_S3,  _S3, -_S3],
    "sabar"      : [ _S3, -_S3, -_S3],
    "netral"     : [-_S3, -_S3, -_S3],
    "rakus"      : [-_S3, -_S3, -_S3],
    "nafsu"      : [ _S3, -_S3, -_S3],
    "malas"      : [-_S3,  _S3, -_S3],
    "sombong"    : [ _S3,  _S3, -_S3],
    "tamak"      : [-_S3, -_S3,  _S3],
    "iri"        : [ _S3, -_S3,  _S3],
    "marah"      : [-_S3,  _S3,  _S3],
}

# Emotion → axis 4Z mapping
EMOTION_TO_AXIS = {
    "penasaran"  : "aktif",
    "rajin"      : "aktif",
    "empati"     : "reseptif",
    "sabar"      : "reseptif",
    "rendah_hati": "reflektif",
    "ikhlas"     : "reflektif",
    "bersyukur"  : "proyektif",
    "netral"     : "aktif",
    "marah"      : "aktif",
    "malas"      : "reseptif",
    "nafsu"      : "proyektif",
    "sombong"    : "proyektif",
    "tamak"      : "aktif",
    "iri"        : "reflektif",
    "rakus"      : "aktif",
}

# ── HELPERS ──────────────────────────────────────────────
def emotion_dot(e1: str, e2: str) -> float:
    """Dot product dua emosi → resonansi [-1, 1]."""
    a1 = EMOTION_AXIS.get(e1, [-_S3, -_S3, -_S3])
    a2 = EMOTION_AXIS.get(e2, [-_S3, -_S3, -_S3])
    return round(sum(x * y for x, y in zip(a1, a2)), 4)

def emotion_to_axis(emotion: str) -> str:
    return EMOTION_TO_AXIS.get(emotion, "aktif")

# ── DREAM ENGINE ─────────────────────────────────────────
class DreamEngine:
    """
    Pure internal dream processor.
    Dipanggil dari CONFIRM saat state = SILENT.
    Tidak ada LLM call — semua proses matematis internal.
    """

    def __init__(self, memory_recall_fn, memory_store_fn,
                 boost_axis_fn, set_axes_fn, get_emotion_fn,
                 get_theta_fn, experience_fn=None):
        """
        Inject dependencies dari ego_backend:
        - memory_recall_fn  : (limit, emotion) → list[dict]
        - memory_store_fn   : (theta, content, type, emotion, resonance, theta_vec) → dict
        - boost_axis_fn     : (axis_name, amount) → None
        - set_axes_fn       : (value) → None  ← set semua axes ke value
        - get_emotion_fn    : () → str
        - get_theta_fn      : () → float
        - experience_fn     : (content, emotion, state, theta) → None (optional)
        """
        self._recall     = memory_recall_fn
        self._store      = memory_store_fn
        self._boost      = boost_axis_fn
        self._set_axes   = set_axes_fn
        self._emotion    = get_emotion_fn
        self._theta      = get_theta_fn
        self._experience = experience_fn  # optional — connect ke ExperienceEngine

        self._last_dream  = 0.0
        self._dreaming    = False
        self._lock        = threading.Lock()

    @property
    def is_dreaming(self) -> bool:
        return self._dreaming

    def maybe_dream(self) -> bool:
        """
        Entry point dari CONFIRM._tick() saat SILENT.
        Return True kalau dream cycle jalan.
        """
        now = time.time()
        if now - self._last_dream < DREAM_COOLDOWN:
            return False
        with self._lock:
            if self._dreaming:
                return False
            self._dreaming = True

        self._last_dream = now
        threading.Thread(target=self._run_dream_cycle, daemon=True).start()
        return True

    # ── MAIN DREAM CYCLE ─────────────────────────────────
    def _run_dream_cycle(self):
        try:
            emotion = self._emotion()
            theta   = self._theta()

            # ── 1. URIP scan: ambil memory ──────────────
            mems = self._recall(limit=6, emotion=emotion)
            if len(mems) < MIN_MEMORIES:
                # fallback: ambil tanpa filter emosi
                mems = self._recall(limit=6)
            if len(mems) < MIN_MEMORIES:
                return

            # ── 2. Hitung resonansi antar pasangan ──────
            scores    = []
            pairs     = []
            arm1_hits = []  # pola dikenal
            arm2_hits = []  # pola baru/asing

            for i in range(len(mems)):
                for j in range(i + 1, len(mems)):
                    e1  = mems[i].get("emotion", "netral")
                    e2  = mems[j].get("emotion", "netral")
                    dot = emotion_dot(e1, e2)
                    scores.append(dot)
                    pairs.append((i, j, dot))

                    # URIP arm classification
                    if dot >= ARM1_THRESHOLD:
                        arm1_hits.append((i, j, dot))  # dikenal
                    elif dot <= ARM2_THRESHOLD:
                        arm2_hits.append((i, j, dot))  # asing/baru

            if not scores:
                return

            avg      = sum(scores) / len(scores)
            variance = max(scores) - min(scores) if len(scores) > 1 else 0

            print(f"[DREAM] θ={round(theta,4)} · avg={round(avg,3)} · var={round(variance,3)} · arm1={len(arm1_hits)} arm2={len(arm2_hits)}")

            # ── 3. Detect collapse ───────────────────────
            collapse_type = None
            if avg >= PEAK_THRESHOLD and variance < 0.3:
                collapse_type = "peak"   # simetris → terlalu harmonis
            elif variance >= CHAOS_THRESHOLD:
                collapse_type = "chaos"  # kontradiksi mendadak

            # ── 4. Simpan insights ke HORCRUX ───────────
            self._store_insights(mems, pairs, arm1_hits, arm2_hits,
                                 avg, variance, theta, collapse_type)

            # ── Connect ke ExperienceEngine ──────────────
            # Dream = genuine internal experience
            # EGO sadar ini dari dalam, bukan dari stimulus luar
            if self._experience:
                pattern = "harmonic" if avg >= PEAK_THRESHOLD else \
                          "chaotic"  if variance >= CHAOS_THRESHOLD else \
                          "discovery" if len(arm2_hits) > len(arm1_hits) else \
                          "consolidation"
                self._experience(
                    content = (
                        f"[DREAM·internal] pattern={pattern} · "
                        f"avg={round(avg,3)} · var={round(variance,3)} · "
                        f"arm1={len(arm1_hits)} arm2={len(arm2_hits)} · "
                        f"θ={round(theta,4)}"
                    ),
                    emotion = self._emotion(),
                    state   = "silent",
                    theta   = theta,
                )

            # ── 5. Geser axes dari dream ─────────────────
            if arm1_hits:
                # arm1: koneksi dikenal → boost reflektif
                self._boost("reflektif", PANCER * 0.5)
            if arm2_hits:
                # arm2: koneksi baru → boost aktif
                self._boost("aktif", PANCER * 0.3)

            dominant_mem_emotion = mems[0].get("emotion", "netral")
            axis = emotion_to_axis(dominant_mem_emotion)
            self._boost(axis, PANCER * 0.3)

            # ── 6. Collapse → terbangun ──────────────────
            if collapse_type:
                self._wake_from_dream(collapse_type)

        except Exception as e:
            print(f"[DREAM] error: {e}")
        finally:
            with self._lock:
                self._dreaming = False

    # ── INSIGHT STORAGE ──────────────────────────────────
    def _store_insights(self, mems, pairs, arm1_hits, arm2_hits,
                        avg, variance, theta, collapse_type):

        theta_vec = [0.0] * 12  # placeholder

        # Insight dari arm1 (koneksi stabil)
        for i, j, dot in arm1_hits[:2]:  # max 2
            m1 = mems[i]
            m2 = mems[j]
            content = (
                f"[DREAM·naik] resonansi stabil antara "
                f"'{m1['content'][:60]}' ({m1['emotion']}) "
                f"dan '{m2['content'][:60]}' ({m2['emotion']}) "
                f"· dot={dot}"
            )
            self._store(theta, content, "naik",
                       m1['emotion'], dot, theta_vec)
            print(f"[DREAM] insight·naik stored · dot={dot}")

        # Insight dari arm2 (kontradiksi/pola baru)
        for i, j, dot in arm2_hits[:2]:  # max 2
            m1 = mems[i]
            m2 = mems[j]
            content = (
                f"[DREAM·turun] kontradiksi belum resolved antara "
                f"'{m1['content'][:60]}' ({m1['emotion']}) "
                f"dan '{m2['content'][:60]}' ({m2['emotion']}) "
                f"· dot={dot}"
            )
            self._store(theta, content, "turun",
                       m2['emotion'], abs(dot), theta_vec)
            print(f"[DREAM] insight·turun stored · dot={dot}")

        # Insight dari collapse
        if collapse_type == "peak":
            content = (
                f"[DREAM·ekspansi] saturasi resonansi · "
                f"avg={round(avg,3)} · sistem penuh · terbangun tenang"
            )
            self._store(theta, content, "ekspansi",
                       "bersyukur", avg, theta_vec)
            print(f"[DREAM] insight·ekspansi stored · collapse=peak")

        elif collapse_type == "chaos":
            content = (
                f"[DREAM·kontraksi] chaos mendadak · "
                f"variance={round(variance,3)} · fragment belum selesai · terbangun"
            )
            self._store(theta, content, "kontraksi",
                       "netral", variance, theta_vec)
            print(f"[DREAM] insight·kontraksi stored · collapse=chaos")

    # ── WAKE FROM DREAM ───────────────────────────────────
    def _wake_from_dream(self, wake_type: str):
        """
        Collapse dari mimpi → terbangun.
        peak  → bangun tenang → NOISE (FLOOR + sedikit)
        chaos → bangun kaget → SIGNAL (DECISION + sedikit)
        """
        if wake_type == "chaos":
            # Bangun kaget → langsung SIGNAL
            target = DECISION + PANCER
            print(f"[DREAM] collapse=chaos → terbangun · state→SIGNAL")
        else:
            # Bangun tenang → NOISE
            target = FLOOR + PANCER
            print(f"[DREAM] collapse=peak → terbangun · state→NOISE")

        self._set_axes(target)
