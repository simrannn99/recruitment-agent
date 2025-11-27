"""
Quick provider switcher for the recruitment agent.
Easily switch between Ollama (local) and OpenAI (cloud) providers.
"""

import os
from pathlib import Path


def read_env():
    """Read current .env file."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return {}

    env_vars = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


def write_env(env_vars):
    """Write .env file with updated variables."""
    env_path = Path(__file__).parent / ".env"

    lines = []
    lines.append("# LLM Configuration")
    lines.append(f"LLM_PROVIDER={env_vars.get('LLM_PROVIDER', 'ollama')}")
    lines.append("")
    lines.append("# Ollama Configuration (for local models)")
    lines.append(
        f"OLLAMA_BASE_URL={env_vars.get('OLLAMA_BASE_URL', 'http://localhost:11434')}"
    )
    lines.append(f"OLLAMA_MODEL={env_vars.get('OLLAMA_MODEL', 'llama3.2')}")
    lines.append("")
    lines.append("# OpenAI Configuration (for cloud models)")

    openai_key = env_vars.get("OPENAI_API_KEY", "")
    if openai_key and not openai_key.startswith("your_"):
        lines.append(f"OPENAI_API_KEY={openai_key}")
    else:
        lines.append("# OPENAI_API_KEY=your_openai_api_key_here")

    lines.append(f"OPENAI_MODEL={env_vars.get('OPENAI_MODEL', 'gpt-4o-mini')}")
    lines.append("")

    with open(env_path, "w") as f:
        f.write("\n".join(lines))


def switch_provider():
    """Interactive provider switcher."""
    print("🔧 LLM Provider Switcher")
    print("=" * 60)

    # Read current config
    env_vars = read_env()
    current_provider = env_vars.get("LLM_PROVIDER", "ollama")

    print(f"\n📍 Current provider: {current_provider.upper()}")
    print("\nAvailable providers:")
    print("  1. Ollama (local, free)")
    print("  2. OpenAI (cloud, paid)")
    print("  3. Show current configuration")
    print("  4. Exit")

    choice = input("\nSelect an option (1-4): ").strip()

    if choice == "1":
        env_vars["LLM_PROVIDER"] = "ollama"
        write_env(env_vars)
        print("\n✅ Switched to Ollama (local)")
        print(f"   Model: {env_vars.get('OLLAMA_MODEL', 'llama3.2')}")
        print("\n⚠️  Remember to restart your server for changes to take effect!")

    elif choice == "2":
        if not env_vars.get("OPENAI_API_KEY") or env_vars.get(
            "OPENAI_API_KEY", ""
        ).startswith("your_"):
            print("\n⚠️  OpenAI API key not configured!")
            print("\nTo use OpenAI:")
            print("  1. Get your API key from: https://platform.openai.com/api-keys")
            print("  2. Edit .env file and add: OPENAI_API_KEY=sk-your-key-here")
            print("  3. Run this script again")
            return

        env_vars["LLM_PROVIDER"] = "openai"
        write_env(env_vars)
        print("\n✅ Switched to OpenAI (cloud)")
        print(f"   Model: {env_vars.get('OPENAI_MODEL', 'gpt-4o-mini')}")
        print("\n⚠️  Remember to restart your server for changes to take effect!")

    elif choice == "3":
        print("\n📋 Current Configuration:")
        print("=" * 60)
        print(f"Provider: {env_vars.get('LLM_PROVIDER', 'ollama').upper()}")
        print(f"\nOllama:")
        print(
            f"  - Base URL: {env_vars.get('OLLAMA_BASE_URL', 'http://localhost:11434')}"
        )
        print(f"  - Model: {env_vars.get('OLLAMA_MODEL', 'llama3.2')}")
        print(f"\nOpenAI:")
        openai_key = env_vars.get("OPENAI_API_KEY", "Not configured")
        if openai_key and not openai_key.startswith("your_"):
            print(
                f"  - API Key: {openai_key[:15]}...{openai_key[-4:] if len(openai_key) > 20 else ''}"
            )
        else:
            print(f"  - API Key: Not configured")
        print(f"  - Model: {env_vars.get('OPENAI_MODEL', 'gpt-4o-mini')}")
        print("=" * 60)

    elif choice == "4":
        print("\n👋 Goodbye!")
        return
    else:
        print("\n❌ Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    try:
        switch_provider()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
