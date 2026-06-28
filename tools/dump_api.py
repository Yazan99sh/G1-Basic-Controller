#!/usr/bin/env python3
"""Phase 2 recon: dump the installed library's command vocabulary — NO robot connection.

Prints the exact topic + command tables and method signatures so we wire G1 commands from
the source of truth instead of guessing. Run on the host where unitree_webrtc_connect is
installed:

    python tools/dump_api.py

Paste the output back so we can finalize g1_controller/commands.py (correct api_ids and
parameter shapes for Move / StopMove / arm actions / state subscription on the G1).
"""
from __future__ import annotations

import inspect
from pathlib import Path


def show_dict(title: str, d: dict) -> None:
    print(f"\n===== {title} ({len(d)} entries) =====")
    for k in sorted(d, key=lambda x: str(x)):
        print(f"  {k!r}: {d[k]!r}")


def _get(modnames, attr):
    """Return attr from the first importable module that has it."""
    for mn in modnames:
        try:
            mod = __import__(mn, fromlist=[attr])
            if hasattr(mod, attr):
                return getattr(mod, attr)
        except Exception:
            continue
    return None


def main() -> None:
    import unitree_webrtc_connect as U

    print("unitree_webrtc_connect version:", getattr(U, "__version__", "unknown"))
    pkgdir = Path(U.__file__).resolve().parent
    print("package path:", pkgdir)
    print("top-level exports:", [n for n in dir(U) if not n.startswith("_")])

    mods = ["unitree_webrtc_connect", "unitree_webrtc_connect.constants"]

    # Command / topic tables (the important part).
    for name in ("RTC_TOPIC", "SPORT_CMD", "DATA_CHANNEL_TYPE"):
        val = _get(mods, name)
        if isinstance(val, dict):
            show_dict(name, val)
        elif val is not None:
            print(f"\n{name} = {val!r}")
        else:
            print(f"\n{name}: NOT FOUND")

    # Any other UPPER_CASE dict tables in the constants module (e.g. arm actions).
    try:
        from unitree_webrtc_connect import constants as C
        for n in dir(C):
            if n.isupper() and n not in ("RTC_TOPIC", "SPORT_CMD", "DATA_CHANNEL_TYPE"):
                v = getattr(C, n)
                if isinstance(v, dict):
                    show_dict(n, v)
    except Exception as e:
        print("\n(constants module introspection skipped:", e, ")")

    # Connection constructor + method surface.
    try:
        from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection as Conn
        print("\n===== UnitreeWebRTCConnection =====")
        print("  __init__", inspect.signature(Conn.__init__))
        print("  public methods:", [m for m in dir(Conn) if not m.startswith("_")])
    except Exception as e:
        print("\n(driver introspection failed:", e, ")")

    # Pub/sub method signatures (publish_request_new + subscribe shape).
    PS = _get(mods, "WebRTCDataChannelPubSub")
    if PS is not None:
        print("\n===== WebRTCDataChannelPubSub =====")
        print("  public methods:", [m for m in dir(PS) if not m.startswith("_")])
        for m in ("subscribe", "unsubscribe", "publish", "publish_request_new", "publish_without_callback"):
            fn = getattr(PS, m, None)
            if fn is not None:
                try:
                    print(f"  {m}{inspect.signature(fn)}")
                except (TypeError, ValueError):
                    print(f"  {m}(...)")

    # Installed examples for the G1 (often NOT shipped in the wheel — fine if empty).
    for base in (pkgdir, pkgdir.parent):
        ex = base / "examples" / "g1"
        if ex.exists():
            print("\n===== examples/g1 files =====")
            for p in sorted(ex.rglob("*.py")):
                print("  ", p)
            break
    else:
        print("\n(no examples/g1 shipped with the install — use the GitHub repo's examples)")


if __name__ == "__main__":
    main()
