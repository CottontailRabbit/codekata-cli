import math

with open("input.txt", encoding="utf-8") as f:
    rows = [line.split() for line in f if line.strip()]

L1, L2 = map(float, rows[0])
out = []
for r in rows[1:]:
    t1, t2, w1, w2 = (math.radians(float(v)) for v in r)   # deg, deg/s -> rad, rad/s
    s1, c1 = math.sin(t1), math.cos(t1)
    s12, c12 = math.sin(t1 + t2), math.cos(t1 + t2)
    vx = -L1 * s1 * w1 - L2 * s12 * (w1 + w2)
    vy = L1 * c1 * w1 + L2 * c12 * (w1 + w2)
    out.append(f"{vx:.4f} {vy:.4f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
