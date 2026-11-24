"""Create a new local environment file without overwriting existing settings."""

import secrets
from pathlib import Path

if __name__ == "__main__":
    template = Path(".env.example").read_text(encoding="utf-8")
    try:
        with Path(".env").open("x", encoding="utf-8") as handle:
            handle.write(template.replace("ADMIN_KEY=\n", "ADMIN_KEY=" + secrets.token_urlsafe(32) + "\n"))
        print("Created .env with a random administrator key.")
    except FileExistsError:
        print("Using existing .env.")
