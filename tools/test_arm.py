#!/usr/bin/env python3
"""Phase 2b: gentlest ACTIVE test — a G1 arm wave, then return the arms. GATED.

This is the safest first "the robot actually does something" test: an arm action only,
NO locomotion (it won't walk). Still — it's a humanoid: make sure it's standing stably
and clear, with the estop ready.

Requires ALLOW_MOVEMENT=true in .env. Close the Unitree phone app's session first.

    python tools/test_arm.py [action]      # default action: face_wave
    # actions: face_wave high_wave handshake clap right_hand_up hands_up hug ...
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("test_arm")

from config import settings  # noqa: E402
from g1_controller.connection import build_connection  # noqa: E402
from g1_controller.commands import G1Controller, G1_ARM  # noqa: E402


async def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "face_wave"
    if action not in G1_ARM:
        log.error("unknown action %r — choose from %s", action, list(G1_ARM))
        return 1
    if not settings.ALLOW_MOVEMENT:
        log.error("ALLOW_MOVEMENT is false — set it true in .env once the robot is in a safe, "
                  "clear/supported state with the estop ready, then re-run.")
        return 1

    conn = build_connection()
    try:
        await conn.connect()
    except Exception:
        log.exception("connect failed (close the phone app? check IP?)")
        return 2

    ctrl = G1Controller(conn)
    try:
        log.info("arm action: %s (id=%d)", action, G1_ARM[action])
        await ctrl.arm_action(action)
        await asyncio.sleep(5)
        log.info("returning arms to neutral (release)")
        await ctrl.arm_release()
        await asyncio.sleep(3)
        log.info("✅ arm test done")
    finally:
        for name in ("disconnect", "close"):
            fn = getattr(conn, name, None)
            if callable(fn):
                try:
                    r = fn()
                    if asyncio.iscoroutine(r):
                        await r
                except Exception:
                    pass
                break
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(0)
