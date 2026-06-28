"""Build and open a WebRTC connection to a Unitree robot (G1 Basic by default).

Uses ``legion1581/unitree_webrtc_connect`` — the SAME WebRTC channel the Unitree phone
app uses — so it works on LOCKED consumer units (no SDK / no DDS / no jailbreak). The
connection API is verified against the repo's
``examples/g1/data_channel/sport_mode/sportmode.py``.
"""
from __future__ import annotations

import logging

from unitree_webrtc_connect.webrtc_driver import (  # type: ignore
    UnitreeWebRTCConnection,
    WebRTCConnectionMethod,
)

from config import settings

log = logging.getLogger("g1.connection")


def _new(method, **kw):
    """Construct the connection, tolerating SDK versions that don't accept device_type."""
    try:
        return UnitreeWebRTCConnection(method, **kw)
    except TypeError:
        if "device_type" in kw:  # older/newer builds may not take it
            kw.pop("device_type", None)
            return UnitreeWebRTCConnection(method, **kw)
        raise


def build_connection():
    """Create (but do not yet open) the connection from ``config.settings``.

    Call ``await conn.connect()`` afterwards. Raises ValueError on incomplete config.
    """
    mode = settings.CONN_MODE.strip().lower()
    common: dict = {}
    if settings.UNITREE_AES_128_KEY:
        common["aes_128_key"] = settings.UNITREE_AES_128_KEY
    if settings.DEVICE_TYPE:
        common["device_type"] = settings.DEVICE_TYPE

    if mode == "localap":
        return _new(WebRTCConnectionMethod.LocalAP, **common)

    if mode == "remote":
        if not (settings.ROBOT_SERIAL and settings.UNITREE_EMAIL and settings.UNITREE_PASSWORD):
            raise ValueError("remote mode needs ROBOT_SERIAL + UNITREE_EMAIL + UNITREE_PASSWORD")
        return _new(
            WebRTCConnectionMethod.Remote,
            serialNumber=settings.ROBOT_SERIAL,
            username=settings.UNITREE_EMAIL,
            password=settings.UNITREE_PASSWORD,
            **common,
        )

    # default: localsta (robot on your LAN)
    if settings.ROBOT_IP:
        return _new(WebRTCConnectionMethod.LocalSTA, ip=settings.ROBOT_IP, **common)
    if settings.ROBOT_SERIAL:
        return _new(WebRTCConnectionMethod.LocalSTA, serialNumber=settings.ROBOT_SERIAL, **common)
    raise ValueError("localsta mode needs ROBOT_IP (preferred) or ROBOT_SERIAL")
