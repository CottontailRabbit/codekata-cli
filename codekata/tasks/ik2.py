import math

with open("input.txt", encoding="utf-8") as f:
    rows = [line.split() for line in f if line.strip()]

L1, L2 = map(float, rows[0])
out = []
for r in rows[1:]:
    x, y = float(r[0]), float(r[1])
    D = (x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if abs(D) > 1:
        out.append("UNREACHABLE")
        continue
    t2 = math.acos(D)                       # elbow-down: 0 <= t2 <= 180
    t1 = math.atan2(y, x) - math.atan2(L2 * math.sin(t2), L1 + L2 * math.cos(t2))
    d1 = (math.degrees(t1) + 180) % 360 - 180   # [-180, 180)
    out.append(f"{d1:.3f} {math.degrees(t2):.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
