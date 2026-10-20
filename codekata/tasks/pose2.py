import math

with open("input.txt", encoding="utf-8") as f:
    rows = [list(map(float, line.split())) for line in f if line.strip()]

L1, L2 = rows[0]
t1, t2 = rows[1]                          # initial joint angles [deg]
out = ["step,theta1,theta2,Bx,By,Cx,Cy"]
for step, row in enumerate(rows[1:]):
    if step > 0:                          # later rows are CHANGES, so accumulate
        t1, t2 = t1 + row[0], t2 + row[1]
    a1, a12 = math.radians(t1), math.radians(t1 + t2)
    bx, by = L1 * math.cos(a1), L1 * math.sin(a1)
    cx, cy = bx + L2 * math.cos(a12), by + L2 * math.sin(a12)
    out.append(f"{step},{t1:.1f},{t2:.1f},{bx:.3f},{by:.3f},{cx:.3f},{cy:.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
