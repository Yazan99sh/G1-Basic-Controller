"""High-level G1 commands over the WebRTC data channel.

Send mechanism VERIFIED against the library's
``examples/g1/data_channel/sport_mode/sportmode.py``::

    await conn.datachannel.pub_sub.publish_request_new(
        "rt/api/sport/request", {"api_id": <id>, "parameter": {...}})

VERIFIED ids: ``api_id 7101`` = switch the G1 locomotion FSM; ``parameter {"data": <mode>}``
with 500=Walk, 501=Walk+waist control, 801=Run.

For motion (Move/StopMove/…) we source ``api_id``s from the library's ``SPORT_CMD`` table
(the source of truth) rather than hardcoding guesses. If a name is missing in the installed
version, the call raises a clear error so it can be reconciled in Phase 2 (read
``examples/g1`` + ``constants.py``) — never a silent wrong command on a humanoid.
"""
from __future__ import annotations

import logging

try:  # best-effort: constants give us correct topic + api_id tables
    from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD  # type: ignore
except Exception:  # pragma: no cover
    RTC_TOPIC, SPORT_CMD = {}, {}

from config import settings

log = logging.getLogger("g1.commands")

# Verified topic literal (matches RTC_TOPIC["SPORT_MOD"] in the lib).
SPORT_TOPIC = (RTC_TOPIC.get("SPORT_MOD") if isinstance(RTC_TOPIC, dict) else None) or "rt/api/sport/request"

# Verified G1 FSM mode switch.
API_SET_MODE = 7101
G1_MODE = {"walk": 500, "walk_waist": 501, "run": 801}


class G1Controller:
    """Thin command layer over an open ``UnitreeWebRTCConnection``."""

    def __init__(self, conn) -> None:
        self.conn = conn

    async def _request(self, api_id: int, parameter: dict | None = None):
        payload: dict = {"api_id": int(api_id)}
        if parameter is not None:
            payload["parameter"] = parameter
        log.info("sport request api_id=%s parameter=%s", api_id, parameter)
        return await self.conn.datachannel.pub_sub.publish_request_new(SPORT_TOPIC, payload)

    # ---- verified, non-motion ----
    async def set_mode(self, mode: str):
        """Switch the G1 locomotion FSM: 'walk' | 'walk_waist' | 'run' (api_id 7101)."""
        if mode not in G1_MODE:
            raise ValueError(f"mode must be one of {list(G1_MODE)}")
        return await self._request(API_SET_MODE, {"data": G1_MODE[mode]})

    async def raw(self, api_id: int, parameter: dict | None = None):
        """Escape hatch: send any sport request directly (used to reconcile the command set)."""
        return await self._request(api_id, parameter)

    # ---- motion (gated; api_id sourced from the library) ----
    def _api(self, name: str) -> int:
        api = SPORT_CMD.get(name) if isinstance(SPORT_CMD, dict) else None
        if api is None:
            raise NotImplementedError(
                f"api_id for '{name}' not found in the installed SPORT_CMD table — confirm it "
                f"from examples/g1 + constants.py (Phase 2) and use raw() meanwhile."
            )
        return api

    def _guard_motion(self) -> None:
        if not settings.ALLOW_MOVEMENT:
            raise PermissionError(
                "Motion refused: set ALLOW_MOVEMENT=true AND put the robot in a safe, clear / "
                "supported space with the estop ready before moving a humanoid."
            )

    async def move(self, vx: float, vy: float = 0.0, vyaw: float = 0.0):
        """Velocity move (clamped). NOTE: parameter shape {x,y,z} matches Go2; confirm the
        G1 shape against examples/g1 in Phase 2 before relying on it."""
        self._guard_motion()
        vx = max(-settings.MAX_VX, min(settings.MAX_VX, vx))
        vy = max(-settings.MAX_VY, min(settings.MAX_VY, vy))
        vyaw = max(-settings.MAX_VYAW, min(settings.MAX_VYAW, vyaw))
        return await self._request(self._api("Move"), {"x": vx, "y": vy, "z": vyaw})

    async def stop(self):
        """Stop locomotion — always safe to attempt."""
        return await self._request(self._api("StopMove"), {})
