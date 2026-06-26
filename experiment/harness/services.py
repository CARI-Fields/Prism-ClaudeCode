from __future__ import annotations

import subprocess
import urllib.request


def health(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def stop_qwen() -> None:
    # Frees ~95 GB unified memory; ignore errors (container may be absent).
    subprocess.run(["sg", "docker", "-c", "docker stop qwen"],
                   capture_output=True, text=True)


def ensure_services(kernelgym_url: str, redis_health_url: str | None = None) -> dict:
    stop_qwen()
    return {
        "kernelgym": health(f"{kernelgym_url}/health"),
        "redis": health(redis_health_url) if redis_health_url else None,
    }
