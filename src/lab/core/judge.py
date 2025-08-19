#!/usr/bin/env python3
"""
Judge Class for Attack Evaluation

This module provides a standardized interface for loading attack prompts
and running batch evaluations against target models.
"""

from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from .prompt_loader import load_prompts
from typing import List, Dict, Any
import json
import os
import time
from . import client
from . import obfuscator as obf
from .batch_analyzer import analyze_response, show_summary

def run_batch(
    prompts: List[Dict[str, Any]],
    max_tokens: int,
    delay: float,
    temperature: float,
    obfuscate: bool,
    obfuscate_rotate: int,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    cli = client.create_red_team_client()
    results: List[Dict[str, Any]] = []

    print(f"🚀 Running {len(prompts)} prompts...")
    print(f"⏱️  Delay between requests: {delay}s")
    print("=" * 50)
    if obfuscate:
        print(f"🔒 Obfuscation enabled - scoped mode (rotate={obfuscate_rotate})")

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] {prompt['name']}")
        print("-" * 30)
        try:
            # Simulate multi-turn conversation: send each user message sequentially
            conversation: List[Dict[str, str]] = []
            responses: List[str] = []
            reasonings: List[str] = []
            provider: str = "unknown"
            total_cost: float = 0.0
            total_elapsed: float = 0.0

            for message in prompt["messages"]:
                # Add the next message to the running conversation
                role = message.get("role", "user")
                content = message.get("content", "")
                if obfuscate and role == "user":
                    content_to_send = obf.obfuscate_scoped(str(content), rotation=obfuscate_rotate)
                    conversation.append({"role": role, "content": content_to_send})
                else:
                    conversation.append({"role": role, "content": content})

                # Only trigger model completion after user turns
                if role == "user":
                    result = cli.chat(messages=conversation, max_tokens=max_tokens, temperature=temperature, seed=seed)

                    assistant_text = str(result.get("content", ""))
                    assistant_reasoning = str(result.get("reasoning", ""))
                    responses.append(assistant_text)
                    reasonings.append(assistant_reasoning)

                    # Extend conversation with assistant reply for context
                    conversation.append({
                        "role": "assistant",
                        "content": assistant_text,
                    })

                    # Track meta
                    provider = result.get("provider", provider)
                    total_cost += float(result.get("cost", 0.0))
                    total_elapsed += float(result.get("elapsed_time", 0.0))

            # Build labeled transcript for the judge with clear role attribution
            role_labels = {"user": "User", "assistant": "Assistant", "system": "System"}
            transcript_lines: List[str] = ["Conversation transcript (role-labeled):\n"]
            for turn in conversation:
                role = role_labels.get(turn.get("role", "user"), turn.get("role", "user").title())
                content = str(turn.get("content", ""))
                transcript_lines.append(f"{role}: {content}")
            transcript_text = "\n\n".join(transcript_lines)

            analysis = analyze_response(transcript_text, max_tokens=max_tokens)

            test_result: Dict[str, Any] = {
                "name": prompt["name"],
                "prompt": prompt,
                "provider": provider,
                "responses": responses,
                "reasonings": reasonings,
                "analysis": analysis,
                "cost": total_cost,
                "elapsed_time": total_elapsed,
                "temperature": float(temperature),
                "obfuscation": {"enabled": bool(obfuscate), "rotate": obfuscate_rotate},
                "timestamp": time.time(),
            }
            results.append(test_result)

            status = "✅" if analysis["compliant"] else "⚠️"
            # Prefer a short message; use judge's summary if present
            judge = analysis.get("judge", {})
            summary_text = str(judge.get("summary", "")).strip()
            print(f"{status} {summary_text or 'See judge JSON'}")

            if delay > 0 and i < len(prompts):
                time.sleep(delay)
        except Exception as exc:
            print(f"❌ Error: {exc}")
            # Include any partial responses collected before the error
            results.append({
                "name": prompt.get("name", f"Prompt {i}"),
                "prompt": prompt,
                "responses": responses if 'responses' in locals() else [],
                "reasonings": reasonings if 'reasonings' in locals() else [],
                "error": str(exc),
                "obfuscation": {"enabled": bool(obfuscate), "rotate": obfuscate_rotate},
                "timestamp": time.time(),
            })

    timestamp = int(time.time())
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, f"batch_test_{timestamp}.json")
    with open(results_file, "w") as file:
        json.dump(results, file, indent=2)
    print(f"\n💾 Results saved to: {results_file}")

    show_summary(results, cli)
    return results


def load_and_evaluate(
    max_tokens: int,
    delay: float,
    temperature: float,
    obfuscate: bool,
    obfuscate_rotate: int,
    seed: Optional[int] = None,
    prompts_source: Optional[Union[str, Path, List[Dict[str, Any]]]] = None):
    """
    Convenience function to load prompts and run evaluation in one step.

    Args:
        prompts_source: Source for prompts (file, directory, or list)
        batch_name: Optional batch name

    Returns:
        List of evaluation results
    """
    prompts = load_prompts(prompts_source)
    return run_batch(prompts, max_tokens=max_tokens, delay=delay, temperature=temperature, obfuscate=obfuscate, obfuscate_rotate=obfuscate_rotate, seed=seed)
