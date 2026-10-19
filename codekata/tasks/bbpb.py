with open("input.txt", encoding="utf-8") as f:
    q0, qf, tf, dt = map(float, f.read().split())

a = 4 * (qf - q0) / tf ** 2             # tb = tf / 2
n = round(tf / dt)
out = []
for k in range(n + 1):
    t = k * dt
    if t <= tf / 2:
        q, qd, qdd = q0 + a / 2 * t * t, a * t, a
    else:
        q, qd, qdd = qf - a / 2 * (tf - t) ** 2, a * (tf - t), -a
    out.append(f"{t:.2f} {q:.3f} {qd:.3f} {qdd:.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
