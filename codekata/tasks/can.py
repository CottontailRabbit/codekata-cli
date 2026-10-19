with open("input.txt", encoding="utf-8") as f:
    frames = [line.split() for line in f if line.strip()]

out = ["node,position_deg,velocity_rpm,temp_c,fault"]
for fr in frames:
    can_id = int(fr[0], 16)
    data = bytes(int(b, 16) for b in fr[2:2 + int(fr[1])])
    node = can_id - 0x180                                          # TPDO1 = 0x180 + node id
    pos = int.from_bytes(data[0:4], "little", signed=True) * 0.01  # 0.01 deg/LSB
    vel = int.from_bytes(data[4:6], "little", signed=True)         # rpm
    temp = data[6]                                                 # uint8, deg C
    fault = data[7] & 0x01                                         # bit 0
    out.append(f"{node},{pos:.2f},{vel},{temp},{fault}")

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
