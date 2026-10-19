with open("input.txt", encoding="utf-8") as f:
    Kp, Ki, Kd, sp, tau, dt, steps = map(float, f.read().split())

x, integ, e_prev = 0.0, 0.0, None
out = []
for k in range(int(steps)):
    e = sp - x
    integ += e * dt
    deriv = 0.0 if e_prev is None else (e - e_prev) / dt   # no derivative kick at k = 0
    u = Kp * e + Ki * integ + Kd * deriv
    out.append(f"{k * dt:.2f} {x:.4f} {u:.4f}")
    x += dt * (-x + u) / tau                              # first-order plant (Euler)
    e_prev = e

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
