#!/usr/bin/env python3
"""
JARVIS 3-Agent Adversarial Review — Simple Command Line Interface (CLI)
Usage:
  1. Direct command:
     python review.py "Should startups use a Modular Monolith over Microservices?"
  2. Interactive mode:
     python review.py
"""
import os
import sys
import logging
import warnings

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.CRITICAL)

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add workspace root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.adversarial_review import adversarial_review_engine

# ANSI Color codes for terminal styling
CYAN = "\033[96m"
AMBER = "\033[93m"
RED = "\033[91m"
GREEN = "\033[92m"
BOLD = "\033[1m"
RESET = "\033[0m"


def enable_windows_ansi():
    """Enable ANSI escape sequences on Windows consoles."""
    if os.name == "nt":
        os.system("")


def run_single_review(topic: str):
    """Stream the 3-agent adversarial debate directly to the console."""
    import re
    clean_topic = re.sub(
        r"^(?:/\s*(?:adversarial[\s_-]*review|review|adversarial|debate|truth|audit|ar|vs|r|3)|adversarial\s+review)[:\s]*",
        "",
        topic.strip(),
        flags=re.IGNORECASE
    ).strip()

    if not clean_topic:
        clean_topic = "Should early-stage startups choose a Modular Monolith over Microservices for mission-critical systems?"

    print(f"\n{CYAN}{BOLD}" + "=" * 72)
    print(f" 🏛️  JARVIS ADVERSARIAL REVIEW")
    print(f" 🎯  Topic: {AMBER}{clean_topic}{CYAN}")
    print("=" * 72 + f"{RESET}\n")

    try:
        for chunk in adversarial_review_engine.stream_review(clean_topic):
            if "AGENT 1: THE PROPONENT" in chunk:
                print(f"{CYAN}{BOLD}{chunk}{RESET}", end="", flush=True)
            elif "AGENT 2: THE ADVERSARY" in chunk:
                print(f"{RED}{BOLD}{chunk}{RESET}", end="", flush=True)
            elif "ROUND 2: DIRECT REBUTTAL" in chunk:
                print(f"{AMBER}{BOLD}{chunk}{RESET}", end="", flush=True)
            elif "AGENT 3: THE ARBITER" in chunk:
                print(f"{GREEN}{BOLD}{chunk}{RESET}", end="", flush=True)
            else:
                print(chunk, end="", flush=True)
        print("\n")
    except KeyboardInterrupt:
        print(f"\n\n{AMBER}⏹️ Review interrupted by user.{RESET}\n")
    except Exception as e:
        print(f"\n{RED}⚠️ Error during review: {e}{RESET}\n")


def main():
    enable_windows_ansi()

    # If topic passed via CLI arguments: python review.py "topic"
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:]).strip()
        run_single_review(topic)
        return

    # Interactive mode
    print(f"{CYAN}{BOLD}" + "=" * 72)
    print(" 🏛️  JARVIS ADVERSARIAL REVIEW")
    print("     Nodes: 🏛️ Proponent (Thesis) · ⚔️ Adversary (Red Team) · ⚖️ Arbiter")
    print("=" * 72 + f"{RESET}")
    print(f"Type any question, topic, or '/Adversarial Review' below (or {BOLD}'q'{RESET} to exit).\n")

    while True:
        try:
            topic = input(f"{AMBER}{BOLD}⚖️  Adversarial Review > {RESET}").strip()
            if not topic:
                continue
            if topic.lower() in {"q", "quit", "exit", "/quit", "/exit"}:
                print(f"{CYAN}Goodbye, Boss.{RESET}")
                break
            run_single_review(topic)
        except (KeyboardInterrupt, EOFError):
            print(f"\n{CYAN}Goodbye, Boss.{RESET}")
            break


if __name__ == "__main__":
    main()
