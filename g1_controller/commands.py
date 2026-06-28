"""High-level G1 commands over the WebRTC data channel.

Everything here is VERIFIED against the library's own G1 example
(``examples/g1/data_channel/sport_mode/sportmode.py``):

* Arm actions:  ``publish_request_new("rt/api/arm/request",
                  {"api_id": 7106, "parameter": {"data": <action_id>}})``
* Mode switch:  ``publish_request_new("rt/api/sport/request",
                  {"api_id": 7101, "parameter": {"data": <mode>}})``  500=Walk 501=Walk+waist 801=Run
* Move:         ``publish_without_callback("rt/wirelesscontroller",
                  {"lx":.., "ly":.., "rx":.., "ry":.., "keys":0})``   joystick axes in [-1, 1]
* Stop:         the same wireless-controller frame with all axes 0.

NOTE: on the G1, locomotion is driven by **emulating the joystick** (the
``rt/wirelesscontroller`` topic) — the data-channel form of "use the controller's commands".
The Go2-style ``SPORT_CMD["Move"]`` id is NOT how the G1 moves.
"""
from __future__ import annotations

import asyncio
import logging
import time

from config import settings

log = logging.getLogger("g1.commands")

SPORT_TOPIC = "rt/api/sport/request"
ARM_TOPIC = "rt/api/arm/request"
WIRELESS_TOPIC = "rt/wirelesscontroller"

API_SET_MODE = 7101    # sport: switch locomotion FSM mode
API_ARM_ACTION = 7106  # arm: play an arm action

# Verified G1 FSM modes (api_id 7101).
G1_MODE = {"walk": 500, "walk_waist": 501, "run": 801}

# Verified G1 arm actions (api_id 7106, parameter {"data": id}).
G1_ARM = {
    "handshake": 27, "high_five": 18, "hug": 19, "high_wave": 26, "clap": 17,
    "face_wave": 25, "left_kiss": 12, "arm_heart": 20, "right_heart": 21,
    "hands_up": 15, "xray": 24, "right_hand_up": 23, "reject": 22,
    "release": 99,  # cancel any action, return the arms to neutral
}


def _clamp(v: float, lim: float) -> float:
    return max(-lim, min(lim, float(v)))


class G1Controller:
    """Thin, verified command layer over an open ``UnitreeWebRTCConnection``."""

    def __init__(self, conn) -> None:
        self.conn = conn

    # ---- safety ----
    def _guard(self) -> None:
        if not settings.ALLOW_MOVEMENT:
            raise PermissionError(
                "Active command refused: set ALLOW_MOVEMENT=true AND ensure the G1 is in a "
                "clear / supported space with the estop ready (this is a humanoid)."
            )

    # ---- low-level senders ----
    async def _sport(self, api_id: int, parameter: dict | None = None):
        payload: dict = {"api_id": int(api_id)}
        if parameter is not None:
            payload["parameter"] = parameter
        log.info("sport %s", payload)
        return await self.conn.datachannel.pub_sub.publish_request_new(SPORT_TOPIC, payload)

    async def _arm(self, action_id: int):
        payload = {"api_id": API_ARM_ACTION, "parameter": {"data": int(action_id)}}
        log.info("arm %s", payload)
        return await self.conn.datachannel.pub_sub.publish_request_new(ARM_TOPIC, payload)

    def _wireless(self, lx: float = 0.0, ly: float = 0.0, rx: float = 0.0,
                  ry: float = 0.0, keys: int = 0) -> None:
        # fire-and-forget joystick frame (matches the example's publish_without_callback)
        self.conn.datachannel.pub_sub.publish_without_callback(
            WIRELESS_TOPIC, {"lx": lx, "ly": ly, "rx": rx, "ry": ry, "keys": keys}
        )

    # ---- escape hatches (for reconciling new commands) ----
    async def raw_sport(self, api_id: int, parameter: dict | None = None):
        return await self._sport(api_id, parameter)

    # ---- modes (api_id 7101) ----
    async def set_mode(self, mode: str):
        """Switch the G1 locomotion FSM: 'walk' | 'walk_waist' | 'run'.
        (The robot enters a standing/locomotion posture — this is motion → gated.)"""
        self._guard()
        if mode not in G1_MODE:
            raise ValueError(f"mode must be one of {list(G1_MODE)}")
        return await self._sport(API_SET_MODE, {"data": G1_MODE[mode]})

    # ---- arm actions (api_id 7106) ----
    async def arm_action(self, name: str):
        """Play a G1 arm action by name (see G1_ARM)."""
        self._guard()
        if name not in G1_ARM:
            raise ValueError(f"arm action must be one of {list(G1_ARM)}")
        return await self._arm(G1_ARM[name])

    async def arm_release(self):
        """Return the arms to neutral (cancel any action) — always safe to attempt."""
        return await self._arm(G1_ARM["release"])

    # ---- locomotion (joystick emulation via rt/wirelesscontroller) ----
    async def stop(self):
        """Zero the joystick — always safe to attempt."""
        self._wireless()

    async def move(self, forward: float = 0.0, strafe: float = 0.0, turn: float = 0.0):
        """Send ONE joystick frame (deflections in [-1, 1], capped by STICK_LIMIT):
        forward→ly, strafe→lx, turn→rx (verified: rx=1.0 turns). For a self-stopping
        burst use ``drive()`` instead (re-sends + auto-stops)."""
        self._guard()
        lim = settings.STICK_LIMIT
        self._wireless(lx=_clamp(strafe, lim), ly=_clamp(forward, lim), rx=_clamp(turn, lim))

    async def drive(self, forward: float = 0.0, strafe: float = 0.0, turn: float = 0.0,
                    seconds: float = 1.0):
        """Bounded, self-stopping drive: resend the joystick at DRIVE_HZ for ``seconds``
        (capped by MAX_DRIVE_SECONDS), then STOP. The safe way to test locomotion."""
        self._guard()
        lim = settings.STICK_LIMIT
        lx, ly, rx = _clamp(strafe, lim), _clamp(forward, lim), _clamp(turn, lim)
        dur = max(0.0, min(settings.MAX_DRIVE_SECONDS, float(seconds)))
        hz = max(1.0, settings.DRIVE_HZ)
        log.info("drive ly=%.2f lx=%.2f rx=%.2f for %.1fs", ly, lx, rx, dur)
        t_end = time.monotonic() + dur
        try:
            while time.monotonic() < t_end:
                self._wireless(lx=lx, ly=ly, rx=rx)
                await asyncio.sleep(1.0 / hz)
        finally:
            self._wireless()  # always stop, even on cancel/error
