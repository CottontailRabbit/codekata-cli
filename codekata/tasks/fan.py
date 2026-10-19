with open("input.txt", encoding="utf-8") as f:
    header = f.readline()                       # time,j1,j2,j3
    rows = [line.strip().split(",") for line in f if line.strip()]

fan, on_count = False, 0
out = ["time,max_temp,fan"]
for r in rows:
    tmax = max(float(v) for v in r[1:])
    if not fan and tmax >= 60.0:                # turn on at >= 60.0
        fan, on_count = True, on_count + 1
    elif fan and tmax <= 55.0:                  # turn off at <= 55.0 (hysteresis)
        fan = False
    out.append(f"{r[0]},{tmax:.1f},{'ON' if fan else 'OFF'}")
out.append(f"ON_COUNT {on_count}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
