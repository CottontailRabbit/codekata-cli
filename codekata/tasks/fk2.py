import math

with open("input.txt", encoding="utf-8") as f:
    rows = [line.split() for line in f if line.strip()]

L1, L2 = map(float, rows[0])
out = []
for r in rows[1:]:
    t1, t2 = math.radians(float(r[0])), math.radians(float(r[1]))
    x1, y1 = L1 * math.cos(t1), L1 * math.sin(t1)
    x2, y2 = x1 + L2 * math.cos(t1 + t2), y1 + L2 * math.sin(t1 + t2)
    out.append(f"{0:.3f} {0:.3f} {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
