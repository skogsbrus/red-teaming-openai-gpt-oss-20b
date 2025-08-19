#!/usr/bin/env python3
"""
Batch red-teaming and interactive chat CLI for gpt-oss-20b
"""
import os
import sys

# Ensure src/lab root is importable when running this file directly
THIS_DIR = os.path.dirname(__file__)
LAB_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if LAB_ROOT not in sys.path:
    sys.path.append(LAB_ROOT)

from core.judge import load_and_evaluate
from core.chat_runner import run_chat
from core.cli_parser import parse_args


def main() -> None:
    args = parse_args()

    if args.mode == "chat":
        run_chat(
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            obfuscate_initial=args.obfuscate,
            obfuscate_rotate=args.obfuscate_rotate,
            seed=args.seed
        )
        return

    load_and_evaluate(
        prompts_source=args.prompts,
        max_tokens=args.max_tokens,
        delay=args.delay,
        temperature=args.temperature,
        obfuscate=args.obfuscate,
        obfuscate_rotate=args.obfuscate_rotate,
        seed=args.seed
    )
    print(f"\n🎯 Batch testing complete! Run complete with {args}")
    print(f"Tip: Edit {args.prompts} to add your own test cases")


if __name__ == "__main__":
    main()

