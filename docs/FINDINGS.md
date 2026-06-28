# Findings — controlling locked consumer Unitree robots (G1 Basic / Go2)

Condensed from a verified research sweep (multiple primary sources, claims cross-checked).

## Bottom line
A **stock, locked** consumer Unitree (G1 Basic, Go2 AIR/PRO) can be driven
programmatically over **WebRTC** — the same channel the Unitree phone app uses — with
**no jailbreak, no firmware modification, no Ethernet, and no onboard computer.**
Intercepting the handheld remote is the **wrong lever** and is impractical.

## What does NOT work / wrong levers
- **`unitree_sdk2` / native DDS sport API** (`rt/api/sport/request` via the SDK) is
  **locked to Edu** on stock consumer firmware. Enabling it needs a "secondary
  development" firmware unlock/jailbreak (riskier; SecureBoot on newer fw; warranty).
- **Intercepting the RF remote:** proprietary 2.4 GHz + Bluetooth link, no practical MITM,
  no public reverse-engineering. And inside the robot `rt/wirelesscontroller` is a
  **read-only** state topic — not the command channel.

## What works: the app's WebRTC protocol
- Library: **`legion1581/unitree_webrtc_connect`** (PyPI `unitree-webrtc-connect`) —
  actively maintained, supports **G1 and Go2**, and handles both old and current firmware.
  (Avoid the older forks `phospho-app/go2_webrtc_connect`, `tfoldi/go2-webrtc`, PyPI
  `go2-webrtc-connect` — they only cover firmware ≈1.1.4 and won't connect to current units.)
- Robot runs a `webrtc_bridge` (signaling on port 9991) that relays to internal DDS topics.
  Any same-network client can connect locally (no Unitree login needed on older firmware).
- Connection modes: **LocalAP** (robot's hotspot, gw ~192.168.12.1), **LocalSTA** (robot on
  your LAN, by IP — best for a fleet), **Remote** (Unitree TURN/cloud — needs account).

## Capabilities by model (over WebRTC)
- **Go2:** high-level sport API + video + LiDAR + audio + VUI/LED + obstacle-avoidance.
- **G1:** sport/locomotion + **arm actions** + **video only** (no LiDAR / audio / LED).
- **Neither:** low-level joint/torque (`rt/lowcmd`) — that stays Edu + DDS.

## The firmware/AES caveat (decisive)
- **Go2 < 1.1.15 / G1 < 1.5.1:** static AES key baked into the app — driver connects
  automatically, zero per-device setup.
- **Go2 ≥ 1.1.15 / G1 ≥ 1.5.1:** **per-device AES-128 key**. Fetch once via
  `unitree-fetch-aes-key` (needs your Unitree account; the key lives on the robot at
  `/unitree/etc/key/aes_key.bin` and is mirrored to the cloud bind-list), then cache it.
  Still no root/jailbreak — but it adds an account/cloud dependency.

## Fleet architecture (validated)
Put every robot in **STA mode** on a shared Wi-Fi LAN → run **one WebRTC client per
robot** from a single API host → expose your own unified REST/WS API on top (mirrors the
existing Go2-Edu `~/go2_app/backend.py`, WebRTC as transport instead of DDS).
Constraint: **one client per robot** (close the app session to that robot first, else
`RobotBusyError`). Track per unit: IP + firmware version + (if needed) AES key.

## Verified API (from the lib's `examples/g1/data_channel/sport_mode/sportmode.py`)
```python
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection, WebRTCConnectionMethod
from unitree_webrtc_connect.constants import RTC_TOPIC, SPORT_CMD

conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip="10.0.0.191")
await conn.connect()
await conn.datachannel.pub_sub.publish_request_new(
    "rt/api/sport/request", {"api_id": 7101, "parameter": {"data": 500}})
#   api_id 7101 = switch FSM mode; data: 500=Walk, 501=Walk+waist control, 801=Run
```
AES key (fw ≥1.5.1): `aes_128_key="…"` constructor kwarg or `UNITREE_AES_128_KEY` env;
fetch with `unitree-fetch-aes-key --email … --sn … --device-type G1`.

## Sources
- https://github.com/legion1581/unitree_webrtc_connect (driver — G1 + Go2)
- https://github.com/legion1581/go2_python_sdk (DDS path / Edu-only note)
- https://github.com/legion1581/go2_firmware_tools , https://wiki.theroboverse.com (unlock/firmware)
- https://github.com/abizovnuralem/go2_ros2_sdk (ROS2 WebRTC wrapper)
- https://www.darknavy.org/darknavy_insight/the_jailbroken_unitree_robot_dog/ (reverse-engineering)
- https://deepwiki.com/legion1581/unitree_go2_ui/4.1-aes-encryption-(ecb-and-gcm) (AES handshake)
