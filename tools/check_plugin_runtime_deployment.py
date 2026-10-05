"""Check the resolved Compose runtime flag and private gateway wiring."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Check defaults and explicit fallback without reading an operator's .env."""
    environment = {key: value for key, value in os.environ.items() if key != "NONBUBBLE_ENV"}
    with tempfile.TemporaryDirectory(prefix="uta-compose-check-") as directory:
        env_file = Path(directory) / "compose.env"
        for fallback in ("", "false", "true"):
            env_file.write_text(
                "POSTGRES_USER=test\nPOSTGRES_DB=test\nPOSTGRES_PASSWORD=compose-test-password\n"
                "SECRET_KEY=compose-test-secret\nPRIMARY_USER_PASSWORD=Compose-test-password1!\n"
                "PLUGIN_RUNTIME_TOKEN=compose-test-runtime-token-at-least-32-characters\n"
                f"NONBUBBLE_ENV={fallback}\n",
                encoding="utf-8",
            )
            for filename, gateway in (
                ("compose.yaml", "http://backend:8000"),
                ("example-docker-compose.yaml", "http://app"),
                ("src/docker-container/compose.yaml", "http://app"),
            ):
                result = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "--env-file",
                        str(env_file),
                        "-f",
                        str(ROOT / filename),
                        "config",
                        "--no-env-resolution",
                        "--format",
                        "json",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                service = json.loads(result.stdout)["services"]["plugin-runtime"]
                resolved = service["environment"]
                assert resolved.get("NONBUBBLE_ENV", "") == fallback, filename
                assert resolved["PLUGIN_GATEWAY_URL"] == gateway, filename
                assert service["read_only"] is True, filename
                assert "ALL" in service["cap_drop"], filename
    print(
        "Nine Compose runtime configurations passed: explicit flag, gateway and container boundaries."
    )


if __name__ == "__main__":
    main()
