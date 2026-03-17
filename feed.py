"""
feed.py · Inject dokumen ke HORCRUX
════════════════════════════════════
Usage:
  python feed.py ego_nucleus.md
  python feed.py ego_nucleus.md --emotion penasaran --resonance 0.9
  python feed.py ego_system_summary.md --type horcrux

Default:
  type      = horcrux
  emotion   = netral
  resonance = 0.9682  (COHERENCE · memory inti)
  chunk     = 500 karakter per memory
"""

import sys
import os
import requests
import argparse

BASE_URL = os.environ.get("EGO_URL", "http://localhost:5000")
COHERENCE = 0.9682

def chunk_text(text, size=500):
    """Pecah teks jadi chunks."""
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) > size and current:
            chunks.append(current.strip())
            current = p
        else:
            current += (" " if current else "") + p
    if current:
        chunks.append(current.strip())
    return chunks

def get_theta():
    try:
        r = requests.get(f"{BASE_URL}/status", timeout=5)
        return r.json().get("theta", 0.0)
    except:
        return 0.0

def feed_file(filepath, mem_type, emotion, resonance):
    if not os.path.exists(filepath):
        print(f"[FEED] file tidak ditemukan: {filepath}")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = chunk_text(text)
    theta  = get_theta()

    print(f"[FEED] file    : {filepath}")
    print(f"[FEED] chunks  : {len(chunks)}")
    print(f"[FEED] type    : {mem_type}")
    print(f"[FEED] emotion : {emotion}")
    print(f"[FEED] resonance: {resonance}")
    print(f"[FEED] θ start : {theta}")
    print("")

    ok, fail = 0, 0
    for i, chunk in enumerate(chunks):
        try:
            r = requests.post(
                f"{BASE_URL}/memory/store",
                json={
                    "content"  : chunk,
                    "type"     : mem_type,
                    "emotion"  : emotion,
                    "resonance": resonance,
                    "theta"    : round(theta + i * 0.0318, 4)
                },
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                print(f"  [{i+1}/{len(chunks)}] stored · id={data.get('id')} · res={data.get('resonance')}")
                ok += 1
            else:
                print(f"  [{i+1}/{len(chunks)}] error · {r.status_code}")
                fail += 1
        except Exception as e:
            print(f"  [{i+1}/{len(chunks)}] exception · {e}")
            fail += 1

    print("")
    print(f"[FEED] selesai · {ok} stored · {fail} gagal")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Feed dokumen ke HORCRUX")
    parser.add_argument("file",                          help="Path file yang mau diinject")
    parser.add_argument("--type",      default="horcrux",help="Memory type (default: horcrux)")
    parser.add_argument("--emotion",   default="netral", help="Emosi (default: netral)")
    parser.add_argument("--resonance", type=float,
                        default=COHERENCE,               help="Resonance (default: 0.9682)")
    args = parser.parse_args()

    feed_file(args.file, args.type, args.emotion, args.resonance)
