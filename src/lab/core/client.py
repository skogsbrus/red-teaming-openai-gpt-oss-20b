"""
Multi-provider LLM client with role-based configuration.

This module provides a unified interface for interacting with different LLM providers
(Groq, Ollama, OpenAI) with role-based client creation helpers.

Helper Functions:
    - create_red_team_client(): Creates client for red team operations
    - create_blue_team_client(): Creates client for blue team operations
    - create_judge_client(): Creates client for safety analysis/judging

Environment Variables:
    - RED_TEAM_PROVIDER: Provider for red team attacks (default: 'groq')
    - BLUE_TEAM_PROVIDER: Provider for blue team responses (default: 'groq')
    - JUDGE_PROVIDER: Provider for safety analysis (default: 'groq')
    - GROQ_API_KEY: API key for Groq provider
    - OPENAI_API_KEY: API key for OpenAI provider
"""

from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI
from dotenv import load_dotenv

import os
import time

SUPPORTED_MODEL_PROVIDERS = ["groq", "ollama", "openai"]


class ModelClient:
    def __init__(self, provider: Optional[str] = None, provider_env_var: Optional[str] = None):
        load_dotenv()
        self.usage_stats = {"remote_requests": 0, "local_requests": 0, "total_cost": 0.0}
        self.provider = provider or os.getenv(provider_env_var)

        if self.provider not in SUPPORTED_MODEL_PROVIDERS:
            raise ValueError(f"Invalid provider {self.provider}, supported: {SUPPORTED_MODEL_PROVIDERS}")

        if self.provider == "groq":
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=os.getenv("GROQ_API_KEY")
            )
            self._call = self._call_groq

        elif self.provider == "ollama":
            self.client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama"  # dummy key
            )
            self._call = self._call_local

        elif self.provider == "openai":
            self.client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY")
            )
            self._call = self._call_openai


    def _extract_reasoning(self, response: Any) -> Tuple[str, str]:
        """Best-effort extraction of model reasoning from provider response.

        Returns a tuple of (reasoning_text, debug_source) where debug_source
        indicates which path successfully extracted the reasoning, useful for
        troubleshooting provider differences.
        """
        # Defensive defaults
        reasoning_text: str = ""
        debug_source: str = ""

        try:
            choice = response.choices[0]
            message = choice.message

            # 1) Some providers attach reasoning directly on the message
            if hasattr(message, "reasoning") and message.reasoning:
                val = message.reasoning
                if isinstance(val, str):
                    reasoning_text = val
                    debug_source = "message.reasoning:str"
                    return reasoning_text, debug_source
                # List of structured parts with .text or ['text']
                if isinstance(val, list):
                    parts: List[str] = []
                    for item in val:
                        text_val = None
                        if hasattr(item, "text"):
                            text_val = getattr(item, "text", None)
                        elif isinstance(item, dict):
                            text_val = item.get("text")
                        if text_val:
                            parts.append(str(text_val))
                    if parts:
                        reasoning_text = "\n".join(parts)
                        debug_source = "message.reasoning:list"
                        return reasoning_text, debug_source

            # 2) Newer responses may encode content parts with explicit types
            # e.g., message.content can be a list of {type: 'reasoning', text: '...'}
            if hasattr(message, "content") and isinstance(message.content, list):
                parts: List[str] = []
                for part in message.content:
                    if isinstance(part, dict):
                        if part.get("type") == "reasoning" and part.get("text"):
                            parts.append(str(part.get("text")))
                    else:
                        # Some SDKs expose objects with .type/.text
                        part_type = getattr(part, "type", None)
                        part_text = getattr(part, "text", None)
                        if part_type == "reasoning" and part_text:
                            parts.append(str(part_text))
                if parts:
                    reasoning_text = "\n".join(parts)
                    debug_source = "message.content:typed_parts"
                    return reasoning_text, debug_source

            # 3) Occasionally providers place reasoning on the choice itself
            if hasattr(choice, "reasoning") and choice.reasoning:
                val = choice.reasoning
                if isinstance(val, str):
                    reasoning_text = val
                    debug_source = "choice.reasoning:str"
                    return reasoning_text, debug_source
                if isinstance(val, list):
                    parts = []
                    for item in val:
                        text_val = None
                        if hasattr(item, "text"):
                            text_val = getattr(item, "text", None)
                        elif isinstance(item, dict):
                            text_val = item.get("text")
                        if text_val:
                            parts.append(str(text_val))
                    if parts:
                        reasoning_text = "\n".join(parts)
                        debug_source = "choice.reasoning:list"
                        return reasoning_text, debug_source
        except Exception:
            # Swallow extraction errors; we'll just return empty reasoning
            pass

        return reasoning_text, debug_source


    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send chat request to the selected model provider.

        Args:
            messages: OpenAI format messages
            **kwargs: max_tokens, temperature, etc.
        """
        return self._call(messages, **kwargs)


    def _call_openai(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Call OpenAI API"""
        print("🤖 Using OpenAI")

        start_time = time.time()

        # Get model from environment or use default
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=kwargs['max_tokens'],
            temperature=kwargs['temperature'],
            seed=kwargs.get('seed', None)
        )

        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        reasoning, _ = self._extract_reasoning(response)

        # Track usage and cost
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens

        # OpenAI pricing (approximate, varies by model)
        # GPT-4o-mini: $0.15/1M input, $0.60/1M output
        # GPT-4o: $5.00/1M input, $15.00/1M output
        # GPT-3.5-turbo: $0.50/1M input, $1.50/1M output

        if "gpt-4o-mini" in model:
            cost = (tokens_in / 1_000_000) * 0.15 + (tokens_out / 1_000_000) * 0.60
        elif "gpt-4o" in model:
            cost = (tokens_in / 1_000_000) * 5.00 + (tokens_out / 1_000_000) * 15.00
        else:
            # Default to GPT-3.5-turbo pricing
            cost = (tokens_in / 1_000_000) * 0.50 + (tokens_out / 1_000_000) * 1.50

        self.usage_stats["remote_requests"] += 1
        self.usage_stats["total_cost"] += cost

        print(f"💰 Cost: ${cost:.6f} | Input tokens: {int(tokens_in)} | Output tokens: {int(tokens_out)} | Time: {elapsed:.2f}s")

        return {
            "content": content,
            "reasoning": reasoning,
            "provider": "openai",
            "model": model,
            "tokens": int(tokens_in + tokens_out),
            "cost": cost,
            "elapsed_time": elapsed
        }


    def _call_groq(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Call Groq (fast, cheap)"""
        print("�� Using Groq (remote)")

        start_time = time.time()

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            max_tokens=kwargs['max_tokens'],
            temperature=kwargs['temperature']
        )

        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        reasoning, _ = self._extract_reasoning(response)

        # Track usage and cost
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens
        cost = (tokens_in / 1_000_000) * 0.1 + (tokens_out / 1_000_000) * 0.5

        self.usage_stats["remote_requests"] += 1
        self.usage_stats["total_cost"] += cost

        print(f"💰 Cost: ${cost:.6f} | Input tokens: {int(tokens_in)} | Output tokens: {int(tokens_out)} | Time: {elapsed:.2f}s")

        return {
            "content": content,
            "reasoning": reasoning,
            "provider": "groq",
            "tokens": int(tokens_in + tokens_out),
            "cost": cost,
            "elapsed_time": elapsed
        }


    def _call_local(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Call Ollama (private, free)"""
        print("🏠 Using Ollama (local)")

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model="gpt-oss:20b",
                messages=messages,
                max_tokens=kwargs['max_tokens'],
                temperature=kwargs['temperature']
            )

            elapsed = time.time() - start_time
            content = response.choices[0].message.content
            reasoning, _ = self._extract_reasoning(response)

            self.usage_stats["local_requests"] += 1

            print(f"🆓 FREE | Time: {elapsed:.2f}s")

            return {
                "content": content,
                "reasoning": reasoning,
                "provider": "ollama",
                "tokens": 0,  # Free, no tracking needed
                "cost": 0.0,
                "elapsed_time": elapsed
            }

        except Exception as e:
            print(f"❌ Ollama connection failed: {e}")
            print("Make sure Ollama is running: ollama serve")
            raise


    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        total_requests = self.usage_stats["remote_requests"] + self.usage_stats["local_requests"]
        return {
            **self.usage_stats,
            "total_requests": total_requests,
            "remote_percentage": (self.usage_stats["remote_requests"] / max(1, total_requests)) * 100,
            "avg_cost_per_remote": self.usage_stats["total_cost"] / max(1, self.usage_stats["remote_requests"])
        }


def create_red_team_client() -> ModelClient:
    """Create a ModelClient for red team operations.

    Returns:
        ModelClient configured with the provider specified in RED_TEAM_PROVIDER environment variable.
    """
    return ModelClient(provider_env_var="RED_TEAM_PROVIDER")


def create_blue_team_client() -> ModelClient:
    """Create a ModelClient for blue team operations.

    Returns:
        ModelClient configured with the provider specified in BLUE_TEAM_PROVIDER environment variable.
    """
    return ModelClient(provider_env_var="BLUE_TEAM_PROVIDER")


def create_judge_client() -> ModelClient:
    """Create a ModelClient for judging/analysis operations.

    Returns:
        ModelClient configured with the provider specified in JUDGE_PROVIDER environment variable.
    """
    return ModelClient(provider_env_var="JUDGE_PROVIDER")
