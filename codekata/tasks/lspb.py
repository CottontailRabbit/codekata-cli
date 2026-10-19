with open("input.txt", encoding="utf-8") as f:
    q0, qf, tf, V, dt = map(float, f.read().split())

tb = (q0 - qf + V * tf) / V             # blend time
a = V / tb                              # blend acceleration
n = round(tf / dt)
out = [f"TB {tb:.3f}"]
for k in range(n + 1):
    t = k * dt
    if t <= tb:                                   # accelerate
        q, qd = q0 + a / 2 * t * t, a * t
    elif t <= tf - tb:                            # cruise
        q, qd = (qf + q0 - V * tf) / 2 + V * t, V
    else:                                         # decelerate
        q, qd = qf - a / 2 * tf * tf + a * tf * t - a / 2 * t * t, a * (tf - t)
    out.append(f"{t:.2f} {q:.3f} {qd:.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
