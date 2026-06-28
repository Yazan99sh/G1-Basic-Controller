# G1 Basic Controller

Control **locked consumer Unitree robots** (starting with the **G1 Basic**) over Wi-Fi
using the **same WebRTC protocol the Unitree phone app uses** — no Edu SDK, no DDS, no
jailbreak, no opening the robot. Built on
[`legion1581/unitree_webrtc_connect`](https://github.com/legion1581/unitree_webrtc_connect).

See **`PLAN.md`** for the roadmap and **`docs/FINDINGS.md`** for the sourced research.

## Quick start (Phase 1 — prove the connection, no movement)

On a host on the **same Wi-Fi as the robot** (e.g. `altkamul2-g1`, conda env `tv`):

```bash
# 1. install the driver (it needs pyaudio, a C extension — satisfy it first)
conda install -y -c conda-forge pyaudio        # recommended: prebuilt, no compiler/sudo
#   ...or, without conda:  sudo apt install -y build-essential portaudio19-dev
pip install unitree_webrtc_connect

# 2. configure
cp .env.example .env
#   set CONN_MODE=localsta and ROBOT_IP=<robot ip from the Unitree app>
#   if the G1 firmware is >= 1.5.1, also fetch + set the AES key:
#     unitree-fetch-aes-key --email you@x.com --sn <SN> --device-type G1
#     -> put the printed key in UNITREE_AES_128_KEY

# 3. CLOSE the Unitree phone app's session to this robot (one client per robot)

# 4. prove the channel opens (sends NO command)
python tools/connect_test.py
```
Success looks like: `✅ WebRTC channel OPEN to the robot.`

## ⚠️ Before any movement
- This is a **humanoid** — motion commands are refused unless you set `ALLOW_MOVEMENT=true`,
  and are velocity-capped. Test motion only with the robot in a **clear / supported** space
  and the app/remote **estop** ready.
- G1 over WebRTC gives **sport + arm + video** only (no low-level joint control).

## Layout
- `config.py` — env-driven settings + safety gates
- `g1_controller/connection.py` — builds & opens the WebRTC connection (verified API)
- `g1_controller/commands.py` — `G1Controller` (verified send mechanism; `set_mode` verified)
- `tools/connect_test.py` — Phase 1 connect proof
- `server/app.py` — (Phase 3) unified REST/WS API — not built yet

## Troubleshooting
- **`RobotBusyError: Robot is connected by another WebRTC client`** — this means the
  connection path WORKS; the robot just allows **one client at a time**. Fully close the
  Unitree phone app's session to this robot (and any other client), wait ~10–20 s for a
  stale session to time out, then re-run.
- **`pip install` fails building pyaudio (`gcc: No such file or directory`)** — the host
  has no C compiler. Use `conda install -y -c conda-forge pyaudio` (no compiler) or
  `sudo apt install -y build-essential portaudio19-dev`, then re-run the pip install.
- **`LAN Signaling Method: legacy /offer`** + connects without an AES error → your firmware
  is the legacy kind (G1 < 1.5.1), so `UNITREE_AES_128_KEY` is not needed.

## Status
Connection path **verified on hardware** (host reached a real G1 Basic over WebRTC; only
the one-client lock remained). Connection/command API verified against the library's own
G1 example. Next: free the client slot for the Phase 1 "channel OPEN", then Phase 2.
