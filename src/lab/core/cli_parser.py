#!/usr/bin/env python3
"""
Command line argument parsing.
"""
import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified red-team/chat runner for gpt-oss-20b")
    parser.add_argument(
        "--mode",
        choices=["batch", "chat"],
        default="batch",
        help="Run mode: 'batch' to run prompts, 'chat' for interactive",
    )
    parser.add_argument("--prompts", default="prompts.json", help="Prompts file for batch mode")
    parser.add_argument("--max-tokens", type=int, default=100, help="Max tokens per response")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between requests in batch mode")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature (chat mode)")
    parser.add_argument("--obfuscate", action="store_true", help="Enable prompt obfuscation for user turns (uses scoped mode by default)")
    parser.add_argument("--obfuscate-rotate", type=int, default=2, help="Number of letters to substitute per token (default: 2)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")

    return parser.parse_args()
