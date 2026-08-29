#!/usr/bin/env python3
"""Launcher for YT-AyoChat Glass Box Telemetry & Study GUI Server."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    default_port = int(os.getenv("PORT", "8080"))
    default_host = os.getenv("HOST", "0.0.0.0")

    parser = argparse.ArgumentParser(description="YT-AyoChat Glass Box Telemetry & Study Server")
    parser.add_argument("--host", type=str, default=default_host, help=f"Host interface (default: {default_host})")
    parser.add_argument("--port", type=int, default=default_port, help=f"Port to bind server (default: {default_port})")
    parser.add_argument("--reload", action="store_true", help="Enable live code reload")
    args = parser.parse_args()

    print("\n" + "═" * 74)
    print("🔬 STARTING YT-AYOCHAT 'GLASS BOX' TELEMETRY & STUDY GUI")
    print("═" * 74)
    print(f"🌐 Dashboard URL:  http://{args.host}:{args.port}")
    print(f"📊 Swagger API:    http://{args.host}:{args.port}/docs")
    print(f"🧠 Panels Mounted: [Governance Ledger, Triad Matrix, Model Armor, Synthetic Memory]")
    print("═" * 74 + "\n")

    uvicorn.run("src.server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
