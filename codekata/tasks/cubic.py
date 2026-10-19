with open("input.txt", encoding="utf-8") as f:
    q0, qf, tf, dt = map(float, f.read().split())

a2 = 3 * (qf - q0) / tf ** 2
a3 = -2 * (qf - q0) / tf ** 3
n = round(tf / dt)                      # include t = tf
out = []
for k in range(n + 1):
    t = k * dt
    q = q0 + a2 * t ** 2 + a3 * t ** 3
    qd = 2 * a2 * t + 3 * a3 * t ** 2
    qdd = 2 * a2 + 6 * a3 * t
    out.append(f"{t:.2f} {q:.3f} {qd:.3f} {qdd:.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
