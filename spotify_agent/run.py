"""
SpotifyCares Support Agent — interactive CLI demo.

Usage:
  python run.py                   # interactive mode
  python run.py --msg "Your message here"   # single message
  python run.py --batch           # run demo on preset test cases
"""

import sys, json, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from agent import SpotifyAgent

def print_result(result):
    ev = result.retrieved_evidence if hasattr(result, 'retrieved_evidence') else result.get('retrieved_evidence', [])
    r = result if isinstance(result, dict) else vars(result)
    SEP = "─" * 60
    print(f"\n{SEP}")
    print(f"  INTENT     : {r['intent']}  (confidence={r['intent_confidence']:.2f})")
    print(f"  PLATFORM   : {r['platform']}")
    print(f"  RETRIEVAL  : {r['retrieval_mode']}")
    if ev:
        best = ev[0]
        print(f"  TOP EVIDENCE (sim={best.get('similarity',0):.3f}, "
              f"platform={best.get('platform','?')}):")
        print(f"    Q: {best['customer_msg'][:100]}")
        print(f"    A: {best['brand_response'][:120]}")
    else:
        print("  TOP EVIDENCE : none")
    print(f"\n  DECISION   : {r['decision']}")
    print(f"  REASON     : {r['reason']}")
    print(f"\n  DRAFT REPLY:")
    print(f"  {r['draft_response']}")
    print(SEP)

DEMO_MESSAGES = [
    "Spotify keeps crashing on my Android phone every time I try to play a song",
    "I was charged twice for premium this month — this is fraud!",
    "My entire playlist disappeared after the latest update",
    "Can't log into my account, forgot my password and email reset isn't working",
    "Alexa won't play my Spotify playlist, it just says it can't find it",
    "Song I want to listen to says not available in my country",
    "Downloaded songs aren't playing offline, even though they show as downloaded",
    "The app just freezes on startup on Windows 11",
    "Why was I charged $9.99 when I cancelled premium?",
]

def main():
    parser = argparse.ArgumentParser(description="SpotifyCares Support Agent")
    parser.add_argument("--msg",   type=str, help="Single customer message")
    parser.add_argument("--batch", action="store_true", help="Run demo batch")
    args = parser.parse_args()

    print("Loading SpotifyCares Support Agent ...", flush=True)
    agent = SpotifyAgent(use_platform_retrieval=True)

    if args.msg:
        result = agent.run(args.msg)
        print_result(result)

    elif args.batch:
        print(f"\nRunning batch demo ({len(DEMO_MESSAGES)} messages):\n")
        for msg in DEMO_MESSAGES:
            print(f"\nCUSTOMER: {msg}")
            result = agent.run(msg)
            print_result(result)

    else:
        # Interactive mode
        print("\nSpotifyCares Support Agent (type 'quit' to exit)\n")
        while True:
            try:
                msg = input("Customer message: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if msg.lower() in ("quit", "exit", "q"):
                break
            if not msg:
                continue
            result = agent.run(msg)
            print_result(result)

if __name__ == "__main__":
    main()
