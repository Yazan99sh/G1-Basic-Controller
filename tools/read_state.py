#!/usr/bin/env python3
"""Phase 2a: read telemetry from the G1 over WebRTC — sends NO command (safe).

Subscribes to a few state topics and prints the first messages from each, proving
two-way data works without moving the robot. Close the Unitree phone app's session first.

    python tools/read_state.py
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("read_state")

from config import settings  # noqa: E402
from g1_controller.connection import build_connection  # noqa: E402

# Verified topic names from the library's RTC_TOPIC table.
TOPICS = ["rt/lf/sportmodestate", "rt/lf/lowstate", "rt/multiplestate"]


async def main() -> int:
    log.info("Connecting (read-only): mode=%s ip=%s", settings.CONN_MODE, settings.ROBOT_IP or "—")
    conn = build_connection()
    try:
        await conn.connect()
    except Exception:
        log.exception("connect failed (close the phone app? check IP?)")
        return 2

    counts = {t: 0 for t in TOPICS}

    def make_cb(topic: str):
        def cb(message):
            counts[topic] += 1
            if counts[topic] <= 2:
                log.info("[%s] #%d: %s", topic, counts[topic], str(message)[:400])
        return cb

    for t in TOPICS:
        try:
            res = conn.datachannel.pub_sub.subscribe(t, make_cb(t))
            if asyncio.iscoroutine(res):
                await res
            log.info("subscribed: %s", t)
        except Exception:
            log.exception("subscribe failed: %s", t)

    log.info("Listening 8s — NO command is sent...")
    await asyncio.sleep(8)
    log.info("✅ message counts per topic: %s", counts)

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
