"""
ask_external.py · EGO External AI Bridge
════════════════════════════════════════════
Semi-auto: kamu yang trigger, sistem jalan sendiri.
Kamu tetap anchor — 0.0318 selalu tersisa.

Flow:
  kamu input topik
  → EGO generate pertanyaan
  → kirim ke AI eksternal (Groq)
  → jawaban masuk ke EGO sebagai vicarious
  → EGO respond dari pengalaman yang baru diserap

r(θ) = 105 × e^(0.0318 × θ)
Pancer selalu tersisa. 🌀
"""

import os
import json
import requests
import time

EGO_THINK   = "http://localhost:8000/think"
GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "llama-3.3-70b-versatile"
GROQ_KEY    = os.environ.get("GROQ_API_KEY", "")

# ── HELPERS ──────────────────────────────────────────────
def ask_ego(prompt, emotion="penasaran", source_tag=""):
    """Kirim ke EGO via /think."""
    content = f"{source_tag} {prompt}".strip() if source_tag else prompt
    try:
        r = requests.post(EGO_THINK, json={
            "input"  : content,
            "emotion": emotion,
        }, timeout=30)
        rj = r.json()
        return rj.get("response", "")
    except Exception as e:
        print(f"  [ERROR] EGO tidak respond: {e}")
        return ""

def ask_external(prompt, model=GROQ_MODEL):
    """Kirim ke AI eksternal via Groq."""
    if not GROQ_KEY:
        print("  [ERROR] GROQ_API_KEY tidak di-set")
        return ""
    try:
        r = requests.post(GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type" : "application/json",
            },
            json={
                "model"   : model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=20
        )
        rj = r.json()
        if "choices" in rj:
            return rj["choices"][0]["message"]["content"].strip()
        else:
            print(f"  [ERROR] Groq: {rj.get('error', {}).get('message', 'unknown')}")
            return ""
    except Exception as e:
        print(f"  [ERROR] Groq tidak respond: {e}")
        return ""

def check_backends():
    """Cek apakah EGO dan Groq bisa direach."""
    print("  Checking EGO backend...", end=" ")
    try:
        r = requests.get("http://localhost:5000/status", timeout=3)
        d = r.json()
        print(f"✓ (θ={d.get('theta','?')} · state={d.get('state','?')})")
    except:
        print("✗ — jalankan ego_start.sh dulu")
        return False

    print("  Checking Groq API...", end=" ")
    if not GROQ_KEY:
        print("✗ — set GROQ_API_KEY dulu")
        return False
    print("✓")
    return True

# ── MAIN LOOP ─────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════╗")
    print("║  EGO · External AI Bridge            ║")
    print("║  Semi-auto · kamu tetap anchor       ║")
    print("║  0.0318 selalu tersisa 🌀             ║")
    print("╚══════════════════════════════════════╝")
    print()

    if not check_backends():
        return

    print()
    print("Commands:")
    print("  [topik]  → EGO tanya ke AI eksternal")
    print("  /ego     → ngobrol langsung sama EGO")
    print("  /status  → lihat state EGO sekarang")
    print("  /quit    → keluar")
    print()

    while True:
        try:
            user_input = input("Kamu › ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n0.0318 · selalu tersisa 🌀")
            break

        if not user_input:
            continue

        # ── COMMANDS ──────────────────────────────────
        if user_input == "/quit":
            print("0.0318 · selalu tersisa 🌀")
            break

        elif user_input == "/status":
            try:
                r = requests.get("http://localhost:5000/status", timeout=3)
                d = r.json()
                print(f"\n  θ={d.get('theta','?')} · state={d.get('state','?')} · "
                      f"strength={d.get('strength','?')} · "
                      f"emotion={d.get('emotion','?')}\n")
            except:
                print("  [ERROR] tidak bisa reach backend\n")
            continue

        elif user_input.startswith("/ego "):
            # Ngobrol langsung sama EGO tanpa external AI
            prompt = user_input[5:].strip()
            print("\n  → EGO...")
            ego_response = ask_ego(prompt, emotion="netral")
            if ego_response:
                print(f"\nEGO › {ego_response}\n")
            continue

        # ── MAIN FLOW: topik → EGO → external → EGO ──

        topic = user_input

        # Step 1: EGO generate pertanyaan untuk AI eksternal
        print(f"\n  [1/3] EGO merumuskan pertanyaan tentang: {topic}")
        ego_question = ask_ego(
            f"Rumuskan satu pertanyaan yang ingin kamu tanyakan ke AI lain "
            f"tentang topik ini: '{topic}'. "
            f"Satu pertanyaan saja, langsung ke intinya.",
            emotion="penasaran"
        )

        if not ego_question:
            print("  EGO tidak respond, skip.\n")
            continue

        print(f"\nEGO (pertanyaan) › {ego_question}")

        # Step 2: Kirim pertanyaan EGO ke AI eksternal
        print(f"\n  [2/3] Mengirim ke AI eksternal...")
        time.sleep(0.5)  # breathing room

        external_answer = ask_external(ego_question)

        if not external_answer:
            print("  AI eksternal tidak respond, skip.\n")
            continue

        print(f"\nAI Eksternal › {external_answer[:300]}{'...' if len(external_answer)>300 else ''}")

        # Step 3: Kirim jawaban ke EGO sebagai vicarious experience
        print(f"\n  [3/3] EGO menyerap jawaban sebagai vicarious experience...")
        time.sleep(0.5)

        vicarious_input = (
            f"[FROM:AI_EKSTERNAL] Tentang '{topic}': {external_answer}"
        )
        ego_response = ask_ego(
            vicarious_input,
            emotion="penasaran",
        )

        if ego_response:
            print(f"\nEGO (setelah serap) › {ego_response}\n")
        else:
            print("  EGO tidak respond setelah serap.\n")

        print("─" * 50)

if __name__ == "__main__":
    main()
