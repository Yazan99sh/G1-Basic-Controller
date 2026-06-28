# G1 Basic Controller — Plan

**Goal:** control LOCKED consumer Unitree robots (starting with the **G1 Basic**)
programmatically and centrally — **without** the Edu SDK, **without** opening the robots,
and **without** intercepting the handheld remote — by speaking the **same WebRTC protocol
the Unitree phone app uses**, over Wi-Fi.

## Why this approach (sourced detail in `docs/FINDINGS.md`)
- Consumer G1/Go2 do **not** expose the `unitree_sdk2`/DDS sport API — that's Edu-only.
- Intercepting the RF remote is impractical (proprietary 2.4 GHz, no MITM), and the
  in-robot controller topic (`rt/wirelesscontroller`) is **read-only** anyway.
- The phone app drives the robot over a **WebRTC data channel** every unit runs. The
  community library **`legion1581/unitree_webrtc_connect`** reimplements that client —
  no jailbreak, no firmware mod. Supports both **G1 and Go2**.

## Capabilities & limits — G1 over WebRTC
- ✅ Sport/locomotion (FSM mode switch + move), **arm actions**, **video** (receive).
- ❌ No low-level joint/torque (`rt/lowcmd` — Edu+DDS only). No LiDAR / audio / LED on G1.
- **One client per robot** — close the app's session to that robot before connecting.

## The one hard dependency: firmware version
- **G1 < 1.5.1** → static key; the library connects automatically.
- **G1 ≥ 1.5.1** → **per-device AES-128 key**; fetch once with `unitree-fetch-aes-key`
  (needs your Unitree account), set `UNITREE_AES_128_KEY`.
- 👉 **Step 0 is: check each unit's firmware in the app.** It decides whether Phase 1 is
  plug-and-play or needs the key fetch.

## Milestones

### Phase 0 — Prereqs & recon  (host: `altkamul2-g1`, conda env `tv`)
- [ ] Put the G1 in **STA mode** on the same Wi-Fi as the host; note its **IP** (from the app).
- [ ] Read the **firmware version** in the app (decides the AES-key step).
- [ ] `pip install unitree_webrtc_connect` (+ `sudo apt install portaudio19-dev`).
- [ ] If fw ≥ 1.5.1: `unitree-fetch-aes-key …` → set `UNITREE_AES_128_KEY` in `.env`.

### Phase 1 — First contact (NO movement)  ✅ DONE (2026-06-28)
- [x] `python tools/connect_test.py` → **"WebRTC channel OPEN"** on a real G1 Basic at
      192.168.0.56. Data-channel validation OK, heartbeats + audio/video tracks received.
      Confirmed: legacy firmware (< 1.5.1) → **no AES key needed**.

### Phase 2 — Command vocabulary  (robot in a SAFE, clear / supported state)
- [ ] Dump `RTC_TOPIC` + `SPORT_CMD` from the installed lib; read `examples/g1/`; confirm
      exact `api_id`s + parameter shapes for `Move`/`StopMove`/arm actions on **G1**.
- [ ] Test `set_mode` (verified: api_id 7101 → walk / walk_waist / run), then a small
      **guarded** `move` + `stop` with `ALLOW_MOVEMENT=true`.

### Phase 3 — Unified API (one robot)
- [ ] FastAPI/WS service wrapping `G1Controller`, mirroring the Go2-Edu
      `~/go2_app/backend.py` pattern (REST: mode/move/stop/arm; WS: telemetry; video later).

### Phase 4 — Fleet
- [ ] Robot registry (IP + firmware + AES key per unit), **one WebRTC client per robot**,
      one central API + a simple dashboard. Each robot needs its app session closed.

### Phase 5 — Hardening
- [ ] Auto-reconnect, **estop/damp** safety, health/telemetry, run as a service, per-unit
      firmware tracking; document the Unitree-cloud/account dependency for keys.

## Risks / watch-items
- **Firmware updates** can change the handshake (AES) — pin & track firmware per unit.
- **AES-key fetch touches Unitree's cloud/account** — plan for that dependency offline-caching.
- **Humanoid safety:** every motion is gated behind `ALLOW_MOVEMENT` + velocity caps + a
  clear/supported test setup; always keep the app/remote estop ready.
- **EULA/warranty:** WebRTC is the app's own protocol (low risk, no firmware mod) but
  unofficial — don't update firmware on a working unit without re-checking the key path.
- Extending to **Go2 AIR** later: it's the most locked SKU (narrower command set).

## Repo layout
```
config.py                     env-driven settings (+ safety gates)
g1_controller/connection.py   build & open the WebRTC connection (verified API)
g1_controller/commands.py     G1Controller — verified send mechanism; set_mode verified
tools/connect_test.py         Phase 1: connect proof (no movement)
docs/FINDINGS.md              sourced research + caveats
server/app.py                 (Phase 3) unified REST/WS API — not yet built
```

## Status
- [x] Scaffold + verified connection/command API wired (from the lib's own G1 example)
- [x] Phase 0 prereqs on host (driver installed; robot on LAN at 192.168.0.56)
- [x] Phase 1 connect proof on a real G1 Basic — **WebRTC channel OPEN** ✅
- [ ] Phase 2 command vocabulary (run tools/dump_api.py → reconcile commands.py → gated test)
- [ ] Phase 3 unified API
- [ ] Phase 4 fleet
