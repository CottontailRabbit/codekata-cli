with open("input.txt", encoding="utf-8") as f:
    sets = [list(map(float, line.split())) for line in f if line.strip()]

out = ["set,t,x,v,a"]
for s, (x0, xf, vmax, acc, dt) in enumerate(sets, 1):
    ta = vmax / acc                       # accel (= decel) time
    T = (xf - x0) / vmax + ta             # total time of the trapezoid
    ka, kd, n = round(ta / dt), round((T - ta) / dt), round(T / dt)
    for k in range(n + 1):                # decide the phase with the integer k
        t = k * dt
        if k < ka:
            a, v, x = acc, acc * t, x0 + 0.5 * acc * t * t
        elif k < kd:
            a, v, x = 0.0, vmax, x0 + 0.5 * acc * ta * ta + vmax * (t - ta)
        else:
            r = T - t
            a, v, x = -acc, acc * r, xf - 0.5 * acc * r * r
        out.append(f"{s},{t:.1f},{x:.3f},{v:.3f},{a:.3f}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
