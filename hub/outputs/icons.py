"""App icons, drawn in code (a gauge on a dark tile) so the repository holds no binary files."""
import math
import struct
import zlib

BG, GREEN, AMBER, RED, INK = (17, 19, 21), (10, 172, 35), (251, 179, 21), (220, 60, 61), (242, 242, 242)


def png(size, pad=0.0):
    """A square PNG. pad is extra margin (0.1 for 'maskable' icons, which get cropped to a circle)."""
    cx, cy = size / 2, size * 0.62
    r_out, r_in = size * (0.36 - pad * 0.6), size * (0.25 - pad * 0.6)
    needle = math.radians(180 - 180 * 0.68)
    nx, ny = math.cos(needle), -math.sin(needle)
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            col = BG
            if dy <= 0 and r_in <= d <= r_out:
                f = 1 - math.atan2(-dy, dx) / math.pi
                col = GREEN if f < 0.31 else AMBER if 0.35 < f < 0.65 else RED if f > 0.69 else BG
            t = dx * nx + dy * ny
            if 0 <= t <= r_in * 0.95 and abs(dx * ny - dy * nx) <= size * 0.022:
                col = INK
            if d <= size * 0.045:
                col = INK
            rows += bytes(col)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def write_all(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for name, size, pad in (("icon-192.png", 192, 0), ("icon-512.png", 512, 0), ("icon-maskable-512.png", 512, 0.1),
                            ("apple-touch-icon.png", 180, 0)):
        (folder / name).write_bytes(png(size, pad))
