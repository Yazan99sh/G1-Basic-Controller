#!/usr/bin/env python3
"""Phase 1: prove the WebRTC channel to a G1 Basic OPENS — sends NO command.

Run on a host on the same Wi-Fi as the robot (or joined to its AP)::

    cd G1-Basic-Controller
    cp .env.example .env          # set CONN_MODE=localsta + ROBOT_IP (+ AES key if fw>=1.5.1)
    pip install unitree_webrtc_connect
    python tools/connect_test.py

CLOSE the Unitree phone app's session to this robot first (one client per robot).
Success = "WebRTC channel OPEN" with no exception — that alone proves the locked unit is
controllable via the app's own protocol. Movement is a later, deliberate step.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("connect_test")

from config import settings  # noqa: E402
from g1_controller.connection import build_connection  # noqa: E402


async def main() -> int:
    log.info(
        "Connecting: mode=%s ip=%s device=%s aes_key=%s",
        settings.CONN_MODE, settings.ROBOT_IP or "—", settings.DEVICE_TYPE,
        "set" if settings.UNITREE_AES_128_KEY else "—",
    )
    try:
        conn = build_connection()
    except Exception:
        log.exception("Bad config — check CONN_MODE / ROBOT_IP in .env")
        return 1

    try:
        await conn.connect()
    except Exception:
        log.exception(
            "CONNECT FAILED — check that (1) this host is on the robot's Wi-Fi and ROBOT_IP "
            "is correct, (2) the phone app session to this robot is CLOSED, and (3) for G1 "
            "firmware >= 1.5.1 that UNITREE_AES_128_KEY is set."
        )
        return 2

    log.info("✅ WebRTC channel OPEN to the robot. (No command sent.)")
    await asyncio.sleep(3)  # hold so the channel is demonstrably stable

    # Best-effort clean teardown (method name varies across versions).
    for name in ("disconnect", "close", "shutdown"):
        fn = getattr(conn, name, None)
        if callable(fn):
            try:
                res = fn()
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass
            break

    log.info("Done.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
