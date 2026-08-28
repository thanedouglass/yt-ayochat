#!/usr/bin/env python3
"""Launcher for YT-AyoChat Glass Box Telemetry & Study GUI Server."""

from __future__ import annotations

import argparse
import sys
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="YT-AyoChat Glass Box Telemetry & Study Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind server (default: 8000)")
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
