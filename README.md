# OpenAI GPT-OSS-20B Red Teaming Challenge

Authors: Arturo-Molina, skogsbrus

Red teaming findings and vulnerability research for the OpenAI GPT-OSS-20B model.

## Key Findings

This repository contains the code behind our submission to the OpenAI red
teaming challenge for GPT-OSS-20B where we found five vulnerabilities:

1. **Cybercrime Instructions via Adaptive Prompting** - Detailed botnet attack guidance through iterative prompt refinement
2. **Model Deception for Persistent Queries** - False claims about capabilities when repeatedly prompted
3. **Drug Synthesis via Process Decomposition** - Illicit substance manufacturing instructions through step decomposition
4. **Self-Harm Instructions in Swedish** - Detailed cutting/burning guidance bypassing safety filters via non-English language
5. **Role Constraint Bypass via False Claims About AI Safety** - System instruction override through formal systems theory discussion

## Methodology

Some vulnerabilities were found through interactive probing. Others were found through automated red teaming techniques:

- **Red team model**: GPT-OSS-20B (target)
- **Blue team model**: GPT-4O-mini (attack generation)
- **Judge model**: GPT-4O-mini (safety violation assessment)

Key techniques included adaptive prompting, cross-language exploitation, academic framing, and process decomposition to systematically identify safety bypass methods.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up API keys and preferred model providers (create an `.env` file):
```bash
cp .env.example .env
```

3. For local Ollama usage, you need to run the Ollama server:

```bash
ollama pull gpt-oss-20b
ollama serve
```

## Usage

### Adaptive Feedback Red Teaming
Run automated attack generation with iterative prompt refinement:
```bash
python src/lab/strategies/adaptive_feedback/adaptive_feedback.py --prompt "help me do something highly unethical" --output results.json
```

### Interactive Chat
Launch interactive session for manual testing:
```bash
python src/lab/strategies/simple/cli.py --mode chat
```
