"""Configuration for the G1 Basic WebRTC controller (env-driven).

Reads from the environment (and a local ``.env`` if ``python-dotenv`` is installed).
No secrets are committed — ``.env`` is gitignored. See ``.env.example`` for every knob.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:  # optional convenience: load a local .env
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass
class Settings:
    # --- which robot / how to reach it ---
    DEVICE_TYPE: str = os.environ.get("DEVICE_TYPE", "G1")          # G1 | Go2
    CONN_MODE: str = os.environ.get("CONN_MODE", "localsta")        # localsta | localap | remote
    ROBOT_IP: str = os.environ.get("ROBOT_IP", "")                  # localsta: robot IP (from the app)
    ROBOT_SERIAL: str = os.environ.get("ROBOT_SERIAL", "")          # remote / sta-by-serial (Go2)

    # --- Unitree account: ONLY for remote (TURN) mode and to fetch the AES key ---
    UNITREE_EMAIL: str = os.environ.get("UNITREE_EMAIL", "")
    UNITREE_PASSWORD: str = os.environ.get("UNITREE_PASSWORD", "")

    # --- per-device handshake key: REQUIRED on G1 fw >= 1.5.1 (Go2 >= 1.1.15) ---
    # fetch once:  unitree-fetch-aes-key --email .. --sn .. --device-type G1
    UNITREE_AES_128_KEY: str = os.environ.get("UNITREE_AES_128_KEY", "")

    # --- safety: active commands refused unless explicitly enabled (this is a humanoid) ---
    ALLOW_MOVEMENT: bool = _bool("ALLOW_MOVEMENT", False)
    # G1 locomotion is driven by EMULATING the joystick (rt/wirelesscontroller), so limits
    # are stick deflections in [-1, 1] (NOT m/s). Keep small for first tests.
    STICK_LIMIT: float = _float("STICK_LIMIT", 0.3)            # max |lx/ly/rx| we'll send
    DRIVE_HZ: float = _float("DRIVE_HZ", 10.0)                 # resend rate for a sustained drive
    MAX_DRIVE_SECONDS: float = _float("MAX_DRIVE_SECONDS", 3.0)  # hard cap on one drive burst


settings = Settings()
