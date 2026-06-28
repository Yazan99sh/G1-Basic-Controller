#!/usr/bin/env python3
"""Phase 2c: GATED locomotion test for the G1 — enter Walk mode, optional gentle move, stop.

⚠️⚠️ HIGHEST-RISK TEST — the G1 will STAND / BALANCE and may STEP. Before running:
  - robot standing ON THE GROUND in a LARGE CLEAR area (do NOT suspend it for the move steps),
  - a person holding the remote/app ESTOP at all times,
  - ALLOW_MOVEMENT=true in .env, and keep STICK_LIMIT small (0.2-0.3) for first tries.

Do the steps IN ORDER. Start with `mode` (just watch it stand/balance) before any motion.

    python tools/test_drive.py mode      # enter Walk mode only (robot stands) — DO THIS FIRST
    python tools/test_drive.py turn      # enter Walk, gentle turn in place, auto-stop
    python tools/test_drive.py forward   # enter Walk, tiny forward, auto-stop
    python tools/test_drive.py back      # enter Walk, tiny backward, auto-stop

After testing, return the robot to a safe state with the physical remote (damp / sit).
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("test_drive")

from config import settings  # noqa: E402
from g1_controller.connection import build_connection  # noqa: E402
from g1_controller.commands import G1Controller  # noqa: E402

ACTIONS = ("mode", "turn", "forward", "back")


async def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "mode"
    if action not in ACTIONS:
        log.error("action must be one of %s", list(ACTIONS))
        return 1
    if not settings.ALLOW_MOVEMENT:
        log.error("ALLOW_MOVEMENT is false — enable it in .env once the robot is on the ground "
                  "in a large clear area with the estop ready.")
        return 1

    log.warning("⚠️ LOCOMOTION TEST '%s' — robot will stand/balance%s. Estop ready?",
                action, " and move" if action != "mode" else "")

    conn = build_connection()
    try:
        await conn.connect()
    except Exception:
        log.exception("connect failed (close the phone app? check IP?)")
        return 2

    ctrl = G1Controller(conn)
    try:
        log.info("entering Walk mode (api_id 7101, data 500)...")
        await ctrl.set_mode("walk")
        await asyncio.sleep(3)  # let it stand / balance

        if action == "turn":
            log.info("gentle turn in place...")
            await ctrl.drive(turn=1.0, seconds=2.0)        # clamped to STICK_LIMIT
        elif action == "forward":
            log.info("tiny forward...")
            await ctrl.drive(forward=1.0, seconds=2.0)
        elif action == "back":
            log.info("tiny backward...")
            await ctrl.drive(forward=-1.0, seconds=2.0)

        await ctrl.stop()
        await asyncio.sleep(1)
        log.info("✅ drive test '%s' done — use the remote to damp/sit the robot now.", action)
    finally:
        # leave the robot stopped; do not auto-damp (operator does that on the remote)
        try:
            await ctrl.stop()
        except Exception:
            pass
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
