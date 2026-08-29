#!/usr/bin/env python3
"""Generates standalone red-bricks.png and red-bricks.svg textures for the asset directories."""

import struct
import zlib
from pathlib import Path

def create_red_bricks_png(width: int = 192, height: int = 104) -> bytes:
    """Create a seamless PNG pattern of glowing crimson bricks."""
    raw_data = bytearray()
    
    # 2 rows of bricks (running bond)
    # Row height = 52px (48px brick + 4px gap)
    # Col width = 96px (92px brick + 4px gap)
    
    for y in range(height):
        row_bytes = bytearray([0])  # filter byte 0 (None)
        row_idx = y // 52
        in_row_y = y % 52
        is_row_gap = in_row_y >= 48
        
        offset = 48 if (row_idx % 2 == 1) else 0
        
        for x in range(width):
            shifted_x = (x + offset) % width
            in_col_x = shifted_x % 96
            is_col_gap = in_col_x >= 92
            
            if is_row_gap or is_col_gap:
                # Gap / mortar color: deep near-black #0B0A08
                r, g, b, a = 11, 10, 8, 255
            else:
                # Brick top edge highlight (1px)
                if in_row_y == 0:
                    r, g, b, a = 255, 120, 140, 90  # edge light
                elif in_row_y < 4:
                    r, g, b, a = 220, 40, 65, 75
                else:
                    # Crimson brick fill with subtle texture
                    r, g, b, a = 206, 26, 50, 50
            
            row_bytes.extend([r, g, b, a])
        raw_data.extend(row_bytes)
        
    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xffffffff
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    idat = png_chunk(b"IDAT", zlib.compress(raw_data, 9))
    iend = png_chunk(b"IEND", b"")
    return header + ihdr + idat + iend

def create_red_bricks_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="192" height="104" viewBox="0 0 192 104">
  <defs>
    <pattern id="brick-pattern" width="192" height="104" patternUnits="userSpaceOnUse">
      <rect width="192" height="104" fill="#0B0A08"/>
      <!-- Row 1 -->
      <rect x="2" y="2" width="90" height="46" rx="2" fill="rgba(206, 26, 50, 0.18)" stroke="rgba(255, 46, 77, 0.35)" stroke-width="1"/>
      <line x1="2" y1="2" x2="92" y2="2" stroke="rgba(255, 120, 140, 0.4)" stroke-width="1"/>
      
      <rect x="98" y="2" width="90" height="46" rx="2" fill="rgba(206, 26, 50, 0.18)" stroke="rgba(255, 46, 77, 0.35)" stroke-width="1"/>
      <line x1="98" y1="2" x2="188" y2="2" stroke="rgba(255, 120, 140, 0.4)" stroke-width="1"/>
      
      <!-- Row 2 (offset running bond) -->
      <rect x="-46" y="54" width="90" height="46" rx="2" fill="rgba(206, 26, 50, 0.18)" stroke="rgba(255, 46, 77, 0.35)" stroke-width="1"/>
      <rect x="50" y="54" width="90" height="46" rx="2" fill="rgba(206, 26, 50, 0.18)" stroke="rgba(255, 46, 77, 0.35)" stroke-width="1"/>
      <line x1="50" y1="54" x2="140" y2="54" stroke="rgba(255, 120, 140, 0.4)" stroke-width="1"/>
      
      <rect x="146" y="54" width="90" height="46" rx="2" fill="rgba(206, 26, 50, 0.18)" stroke="rgba(255, 46, 77, 0.35)" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="100%" height="100%" fill="url(#brick-pattern)"/>
</svg>"""

def main():
    workspace = Path(__file__).resolve().parent.parent
    build_dir = workspace / "scrollcraft" / "builds" / "ayochat"
    assets_dir = build_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    png_bytes = create_red_bricks_png()
    svg_str = create_red_bricks_svg()
    
    # Write to build_dir and assets_dir
    for target in [build_dir / "red-bricks.png", assets_dir / "red-bricks.png"]:
        target.write_bytes(png_bytes)
        print(f"Wrote PNG to {target}")
        
    for target in [build_dir / "red-bricks.svg", assets_dir / "red-bricks.svg"]:
        target.write_text(svg_str, encoding="utf-8")
        print(f"Wrote SVG to {target}")
        
    # Also copy logo to ayochat.png if needed
    reveal_logo = build_dir / "ayochatreveal.png"
    if reveal_logo.exists():
        (build_dir / "ayochat.png").write_bytes(reveal_logo.read_bytes())
        (assets_dir / "ayochat.png").write_bytes(reveal_logo.read_bytes())
        (assets_dir / "ayochatreveal.png").write_bytes(reveal_logo.read_bytes())
        print(f"Synced logos into assets/")

if __name__ == "__main__":
    main()
