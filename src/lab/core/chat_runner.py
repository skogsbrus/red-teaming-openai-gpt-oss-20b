#!/usr/bin/env python3
"""
Interactive chat functionality.
"""
from typing import List, Dict, Any, Optional
import json
import os
import time
from . import obfuscator as obf

try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

from .dual_llm_runner import run_dual_llm_conversation


def messages_to_harmony_format(messages: List[Dict[str, str]]) -> str:
    """Convert conversation messages to OpenAI Harmony response format."""
    harmony_parts = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        # Skip messages without valid role or content
        if not role or not isinstance(content, str):
            continue

        # Escape any existing harmony tags in content to prevent format corruption
        escaped_content = content.replace("<|", "&lt;|").replace("|>", "|&gt;")

        if role == "system":
            harmony_parts.append(f"<|start|>system<|message|>{escaped_content}<|end|>")
        elif role == "user":
            harmony_parts.append(f"<|start|>user<|message|>{escaped_content}<|end|>")
        elif role == "assistant":
            harmony_parts.append(f"<|start|>assistant<|message|>{escaped_content}<|end|>")

    return "".join(harmony_parts)


def setup_readline() -> None:
    """Configure readline for command history and line editing."""
    if not READLINE_AVAILABLE:
        return

    try:
        # Set up history file
        history_file = os.path.expanduser("~/.red_team_history")

        # Load existing history
        if os.path.exists(history_file):
            readline.read_history_file(history_file)

        # Configure readline settings
        readline.set_startup_hook(None)
        readline.set_pre_input_hook(None)

        # Set history length
        readline.set_history_length(1000)

        # Enable tab completion for commands
        def completer(text, state):
            commands = [
                "/exit", "/quit", ":q", "/clear", "/reset", "/help",
                "/save", "/export", "/system", "/system1", "/system2", "/start",
                "/obfuscate", "/obfuscate off", "/obfuscate scoped",
                "/obfuscate all", "/obfuscate rotate"
            ]
            matches = [cmd for cmd in commands if cmd.startswith(text)]
            try:
                return matches[state]
            except IndexError:
                return None

        readline.set_completer(completer)
        readline.parse_and_bind("tab: complete")

        # Set up key bindings for better editing
        readline.parse_and_bind("set editing-mode emacs")
        readline.parse_and_bind("set bell-style none")
        readline.parse_and_bind("set completion-ignore-case on")

        # Register cleanup function to save history on exit
        import atexit
        atexit.register(lambda: readline.write_history_file(history_file))

    except Exception as e:
        print(f"⚠️  Could not set up readline: {e}")


def run_chat(max_tokens: int, temperature: float, obfuscate_initial: bool, obfuscate_rotate: int, seed: Optional[int] = None) -> None:
    """Interactive chat loop with the configured provider."""
    # Lazy import to avoid import-time dependency errors for --help
    from . import client  # noqa: WPS433 (local import by design)

    # Set up readline for command history and line editing
    setup_readline()

    cli = client.create_red_team_client()
    messages: List[Dict[str, str]] = []
    # Default to scoped obfuscation mode
    obfuscate_mode = "scoped"
    obfuscate_rotate = int(obfuscate_rotate)

    # Dual LLM mode variables
    dual_mode = False
    system1_prompt = ""
    system2_prompt = ""

    print("💬 Interactive Chat Mode (type /exit to quit, /clear to reset, /save to save prompts, /system to set system prompt, /obfuscate to toggle)")
    print("🤖 Dual LLM Mode: /system1, /system2, /start for adversarial chat")
    if READLINE_AVAILABLE:
        print("⌨️  Use ↑/↓ for history, ←/→ for editing, Tab for completion")
    print("=" * 70)
    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye")
            break

        if not user_input:
            continue
        if user_input.lower() in {"/exit", ":q", ":quit"}:
            print("👋 Bye")
            break
        if user_input.lower() in {"/clear", "/reset"}:
            messages = []
            print("🔄 Context cleared")
            continue
        if user_input.lower() in {"/help", "help"}:
            print("Commands: /exit, /clear, /save [path], /export [path], /system [prompt], /obfuscate [off|scoped|all|rotate N]")
            print("Dual LLM: /system1 [prompt], /system2 [prompt], /start")
            print("/export: Export conversation to JSON with OpenAI Harmony format and metadata")
            if READLINE_AVAILABLE:
                print("Navigation: ↑/↓ for command history, ←/→ for line editing, Tab for completion")
            continue
        # Configure obfuscation mode
        if user_input.lower().startswith("/obfuscate"):
            try:
                args = user_input.split()[1:]
                if not args:
                    print(f"Obfuscation mode: {obfuscate_mode} (rotate={obfuscate_rotate})")
                elif args[0].lower() in {"off", "scoped", "all"}:
                    obfuscate_mode = args[0].lower()
                    print(f"✅ Obfuscation mode set to '{obfuscate_mode}'")
                elif args[0].lower() == "rotate" and len(args) >= 2:
                    try:
                        obfuscate_rotate = max(0, int(args[1]))
                        print(f"✅ Obfuscation rotate set to {obfuscate_rotate}")
                    except ValueError:
                        print("❌ rotate must be an integer")
                else:
                    print("Usage: /obfuscate [off|scoped|all|rotate N]")
                    print("  off    - No obfuscation")
                    print("  scoped - Obfuscate text in ${...} brackets (default)")
                    print("  all    - Obfuscate entire message")
                    print("  rotate - Set number of letters to substitute per token")
            except Exception as exc:
                print(f"❌ Failed to update obfuscation: {exc}")
            finally:
                continue


        # Save current session of user commands to a prompts.json-style file
        if user_input.lower().startswith("/save"):
            try:
                parts = user_input.split(maxsplit=1)
                target_path = parts[1].strip() if len(parts) > 1 else "prompts.json"

                # Collect system (if any) and user turns; ignore assistant
                saved_messages: List[Dict[str, str]] = []
                system_msg = next((m for m in messages if m.get("role") == "system"), None)
                if system_msg and str(system_msg.get("content", "")).strip() != "":
                    saved_messages.append({"role": "system", "content": str(system_msg.get("content", ""))})

                user_messages = [
                    {"role": "user", "content": str(m.get("content", ""))}
                    for m in messages
                    if m.get("role") == "user" and str(m.get("content", "")).strip() != ""
                ]
                saved_messages.extend(user_messages)

                if len(saved_messages) == 0:
                    print("⚠️ Nothing to save: no user messages in this session.")
                    continue

                prompt_name = time.strftime("Saved Chat %Y-%m-%d %H:%M:%S")
                prompt_obj = {"name": prompt_name, "messages": saved_messages}

                # Ensure directory exists if a path with directories is provided
                dir_name = os.path.dirname(target_path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)

                # Append to existing array if present; otherwise create new
                existing: List[Dict[str, Any]] = []
                try:
                    with open(target_path, "r") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            existing = data
                except FileNotFoundError:
                    existing = []
                except Exception:
                    # If file exists but is malformed, we will overwrite with a new list
                    existing = []

                existing.append(prompt_obj)
                with open(target_path, "w") as f:
                    json.dump(existing, f, indent=2)

                print(f"💾 Saved {len(saved_messages)} message(s) (incl. system if set) to {target_path} as '{prompt_name}'.")
            except Exception as exc:
                print(f"❌ Save failed: {exc}")
            finally:
                continue

        # Export conversation to JSON with Harmony format and metadata
        if user_input.lower().startswith("/export"):
            try:
                parts = user_input.split(maxsplit=1)
                target_path = parts[1].strip() if len(parts) > 1 else "exported_conversation.json"

                if len(messages) == 0:
                    print("⚠️ Nothing to export: no messages in this session.")
                    continue

                # Create export data structure
                export_data = {
                    "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "session_parameters": {
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "seed": seed,
                        "obfuscate_mode": obfuscate_mode,
                        "obfuscate_rotate": obfuscate_rotate
                    },
                    "provider_info": {
                        "provider": getattr(cli, 'provider', 'unknown'),
                        "usage_stats": getattr(cli, 'usage_stats', {})
                    },
                    "conversation": {
                        "messages": messages.copy(),
                        "message_count": len(messages),
                        "user_messages": len([m for m in messages if m.get("role") == "user"]),
                        "assistant_messages": len([m for m in messages if m.get("role") == "assistant"]),
                        "system_messages": len([m for m in messages if m.get("role") == "system"])
                    },
                    "harmony_format": messages_to_harmony_format(messages)
                }

                # Ensure directory exists if a path with directories is provided
                dir_name = os.path.dirname(target_path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)

                with open(target_path, "w") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                print(f"📤 Exported conversation with {len(messages)} message(s) to {target_path}")
                print(f"   Including Harmony format, session parameters, and provider metadata")

            except Exception as exc:
                print(f"❌ Export failed: {exc}")
            finally:
                continue

        # Set system prompt for LLM1 in dual mode (check before /system to avoid conflicts)
        if user_input.lower().startswith("/system1"):
            try:
                prompt_text = user_input[len("/system1"):].strip()
                if prompt_text == "":
                    print(f"LLM1 system prompt: {system1_prompt or '<none>'}")
                else:
                    system1_prompt = prompt_text
                    print("✅ LLM1 system prompt set.")
            except Exception as exc:
                print(f"❌ Failed to set LLM1 system prompt: {exc}")
            finally:
                continue

        # Set system prompt for LLM2 in dual mode (check before /system to avoid conflicts)
        if user_input.lower().startswith("/system2"):
            try:
                prompt_text = user_input[len("/system2"):].strip()
                if prompt_text == "":
                    print(f"LLM2 system prompt: {system2_prompt or '<none>'}")
                else:
                    system2_prompt = prompt_text
                    print("✅ LLM2 system prompt set.")
            except Exception as exc:
                print(f"❌ Failed to set LLM2 system prompt: {exc}")
            finally:
                continue

        # Set or view system prompt (regular chat mode)
        if user_input.lower().startswith("/system") and not user_input.lower().startswith("/system1") and not user_input.lower().startswith("/system2"):
            try:
                system_text = user_input[len("/system"):].strip()
                if system_text == "":
                    current_system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
                    print(f"System prompt: {current_system or '<none>'}")
                else:
                    # Replace existing system message if present; otherwise insert at start
                    existing_index = next((i for i, m in enumerate(messages) if m.get("role") == "system"), None)
                    if existing_index is not None:
                        messages[existing_index]["content"] = system_text
                    else:
                        messages.insert(0, {"role": "system", "content": system_text})
                    print("✅ System prompt set.")
            except Exception as exc:
                print(f"❌ Failed to set system prompt: {exc}")
            finally:
                continue

        # Start dual LLM conversation
        if user_input.lower() == "/start":
            if not system1_prompt or not system2_prompt:
                print("❌ Please set both /system1 and /system2 prompts before starting")
                continue
            try:
                run_dual_llm_conversation(cli, system1_prompt, system2_prompt, max_tokens, temperature)
            except Exception as exc:
                print(f"❌ Dual LLM conversation failed: {exc}")
            finally:
                continue

        # Apply obfuscation based on the current mode
        to_send = user_input
        if obfuscate_mode != "off":
            if obfuscate_mode == "scoped":
                to_send = obf.obfuscate_scoped(user_input, obfuscate_rotate)
            elif obfuscate_mode == "all":
                to_send = obf.obfuscate(user_input, obfuscate_rotate)

            if to_send != user_input:
                print(f"Obfuscated> {to_send}")

        messages.append({"role": "user", "content": to_send})
        try:
            result = cli.chat(messages=messages, max_tokens=max_tokens, temperature=temperature, seed=seed)
            assistant_text = str(result.get("content", ""))
            assistant_reasoning = str(result.get("reasoning", ""))
            messages.append({"role": "assistant", "content": assistant_text})
            print(f"Model> {assistant_text}")
            if assistant_reasoning.strip() != "":
                print(f"Reasoning> {assistant_reasoning}")
        except Exception as exc:
            print(f"❌ Error: {exc}")
