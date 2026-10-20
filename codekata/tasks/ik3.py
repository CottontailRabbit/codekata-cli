import math

with open("input.txt", encoding="utf-8") as f:
    rows = [list(map(float, line.split())) for line in f if line.strip()]

L1, L2, L3 = rows[0]
wrap = lambda d: (d + 180) % 360 - 180          # [-180, 180)
out = []
for x, y, phi in rows[1:]:
    p = math.radians(phi)
    wx, wy = x - L3 * math.cos(p), y - L3 * math.sin(p)    # wrist point
    D = (wx * wx + wy * wy - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if abs(D) > 1:
        out.append("UNREACHABLE")
        continue
    t2 = math.acos(D)
    t1 = math.atan2(wy, wx) - math.atan2(L2 * math.sin(t2), L1 + L2 * math.cos(t2))
    d1, d2 = wrap(math.degrees(t1)), math.degrees(t2)
    d3 = wrap(phi - d1 - d2)
    out.append(f"{d1:.3f} {d2:.3f} {d3:.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
