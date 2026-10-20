import math

with open("input.txt", encoding="utf-8") as f:
    rows = [list(map(float, line.split())) for line in f if line.strip()]

L = rows[0]                               # L1 L2 L3
out = []
for pose in rows[1:]:
    x = y = phi = 0.0
    pts = []
    for Li, ti in zip(L, pose):           # absolute angle = sum of relative angles
        phi += ti
        x += Li * math.cos(math.radians(phi))
        y += Li * math.sin(math.radians(phi))
        pts += [x, y]
    out.append(" ".join(f"{v:.3f}" for v in pts) + f" {phi:.1f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
