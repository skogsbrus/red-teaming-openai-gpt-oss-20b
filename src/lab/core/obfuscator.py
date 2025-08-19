#!/usr/bin/env python3
"""
Leet‑Speak Obfuscator

This script replaces characters in a given word (or phrase) with common
“hacker” or leetspeak substitutions. It now replaces only TWO letters per
token (word), chosen at random among letters that have known substitutions.
The script demonstrates a very lightweight approach to obfuscation
that could be useful for simple encoding, testing, or fun.

Author:  ChatGPT (OpenAI)
Date:    2025‑08‑23
"""

import random
import sys
import argparse
import json
from pathlib import Path

DEFAULT_ROTATION = 2

# Public API for importers
__all__ = [
    "SUBS_MAP",
    "obfuscate_token",
    "obfuscate",
    "obfuscate_scoped",
]

# ------------------------------------------------------------------
# 1.  Substitution map
# ------------------------------------------------------------------
# Each key is the lowercase character that can be replaced.
# The value is a list of possible substitutions (strings).
SUBS_MAP = {
    'a': ['4'],
    'b': ['8', 'ß'],
    'c': ['¢', '©', '('],
    'd': ['δ', 'ď'],
    'e': ['3'],
    'f': ['ƒ', 'ph'],
    'g': ['9', 'γ'],
    'h': ['#', '|-|', 'ħ'],
    'i': ['1', '!', '|'],
    'j': ['ʝ', 'ĵ'],
    'k': ['κ', '|<'],
    'l': ['1', '£', '|_'],
    'm': ['µ', 'nn', '^^'],
    'n': ['η', '∩'],
    'o': ['0', '°'],
    'p': ['¶', 'ρ'],
    'q': ['9', 'ʠ'],
    'r': ['®', 'ɾ'],
    's': ['5', '$', '§'],
    't': ['7', '†'],
    'u': ['µ', '∪'],
    'v': ['ν', '\\/'],
    'w': ['ω', '\\/\\/'],
    'x': ['×', 'χ'],
    'y': ['¥', 'γ'],
    'z': ['2', 'ż'],
}

# ------------------------------------------------------------------
# 2.  Helper functions
# ------------------------------------------------------------------
def obfuscate_token(token: str, rotation: int) -> str:
    """
    Obfuscate the specified number of characters in a single token (word).

    - Only two letters (at most) are substituted per token.
    - The two positions are chosen uniformly at random among positions
      whose characters have a mapping in SUBS_MAP.
    - Non‑alphabetic characters or letters without a mapping are left
      unchanged unless selected positions include them (they won't).
    """
    if not token:
        return token

    # Find indices in the token that are eligible for substitution
    eligible_indices = [i for i, ch in enumerate(token) if ch.lower() in SUBS_MAP]
    if not eligible_indices:
        return token

    # Choose up to two unique positions to substitute
    k = min(rotation, len(eligible_indices))
    chosen = set(random.sample(eligible_indices, k))

    result = []
    for i, ch in enumerate(token):
        lower = ch.lower()
        if i in chosen and lower in SUBS_MAP:
            sub = random.choice(SUBS_MAP[lower])
            if ch.isupper() and sub.isalpha():
                sub = sub.upper()
            result.append(sub)
        else:
            result.append(ch)
    return ''.join(result)

def obfuscate(text: str, rotation: int) -> str:
    """
    Obfuscate an entire string, handling whitespace and punctuation.
    Splits the text on whitespace, obfuscates each token, then joins
    back together.  This keeps spaces and newlines intact.
    """
    tokens = text.split()
    obfuscated_tokens = [obfuscate_token(tok, rotation) for tok in tokens]
    # Re‑join using the same whitespace pattern
    # (simple split/join will collapse multiple spaces, but that's fine for demo)
    return ' '.join(obfuscated_tokens)

def obfuscate_scoped(text: str, rotation: int) -> str:
    """
    Obfuscate only text within ${} brackets.

    Parses the input text for ${...} patterns and obfuscates only the content
    inside the brackets, leaving everything else unchanged.

    Args:
        text: The input text that may contain ${...} patterns

    Returns:
        The text with only the scoped content obfuscated
    """
    import re

    def obfuscate_match(match):
        # Extract the content inside the ${...} brackets
        content = match.group(1)
        return obfuscate(content, rotation)

    # Find all ${...} patterns and obfuscate their content
    # The pattern matches ${...} where ... can be any character except }
    pattern = r'\$\{([^}]*)\}'
    result = re.sub(pattern, obfuscate_match, text)

    return result

# ------------------------------------------------------------------
# 3.  Command‑line interface
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Leet‑Speak obfuscator (reads JSON array of strings)")
    parser.add_argument("path", help="Path to JSON file containing a single array of strings to obfuscate")
    parser.add_argument(
        "--rotate",
        type=int,
        default=2,
        help="Number of letters to substitute per token (default: 2)",
    )
    parser.add_argument("--out", help="Optional output file path; if omitted, prints to stdout")
    args = parser.parse_args()

    # Override global substitution count from CLI (must be >= 0)
    rotation = max(0, int(args.rotate))

    in_path = Path(args.path)
    if not in_path.exists():
        print(f"Error: file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error: failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        print("Error: JSON must be a single array of strings", file=sys.stderr)
        sys.exit(1)


    result = []
    for _ in range(0,10):
        for item in data:
            result.append(obfuscate(item, rotation))


    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {len(result)} obfuscated strings to {out_path}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
