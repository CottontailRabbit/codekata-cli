"""로봇소프트웨어개발기사 실기 대비 트랙 (Python / C++).

실기 작업형의 틀: 주어진 TXT 입력 파일을 읽어 로봇 공식으로 계산하고, 요구한 형식 그대로 결과 파일에 쓴다.
- task : 실전 작업형. 작업 폴더에 input.txt를 만들고, 사용자가 에디터로 solution.py/.cpp 를 작성 → 실행 → output.txt 채점
- quiz : 공식·함수·형식 함정 4지선다 (출력 예측은 전부 실제 실행으로 검증)
- kata : 공식 한 줄 작성. Python은 실행, C++은 g++로 컴파일해서 숨은 테스트까지 채점
"""
import hashlib
import math
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import store
from .i18n import pick, tr

TASK_DIR = Path(__file__).with_name("tasks")
EXAM_LANGS = ("python", "cpp")
EXAM_STAGES = 5                     # 랭크전 규격: 퀴즈·카타·퀴즈·카타·실전
EXAM_ORDER = ["quiz", "kata", "clone", "quiz", "task"]
TASK_LIMIT = 25 * 60                # 실전 1문제 제한 시간(초)


# ─── 실전 작업형 문제 ───────────────────────────────────────

def _f(x, n=3):
    return f"{x:.{n}f}"


def gen_fk2(rng):
    L1, L2 = rng.choice([(1.0, 0.5), (0.85, 0.65), (0.8, 0.6), (1.2, 0.7)])
    poses = [(rng.randrange(-90, 181, 5), rng.randrange(-150, 151, 5)) for _ in range(rng.randint(3, 5))]
    return f"{L1} {L2}\n" + "".join(f"{a} {b}\n" for a, b in poses)


def gen_ik2(rng):
    L1, L2 = rng.choice([(1.0, 0.5), (0.85, 0.65), (1.0, 0.8)])
    pts = []
    for _ in range(rng.randint(3, 4)):
        t1, t2 = math.radians(rng.randrange(-60, 151, 5)), math.radians(rng.randrange(15, 166, 5))
        pts.append((L1 * math.cos(t1) + L2 * math.cos(t1 + t2), L1 * math.sin(t1) + L2 * math.sin(t1 + t2)))
    far = L1 + L2 + rng.choice([0.2, 0.35, 0.5])
    a = math.radians(rng.randrange(0, 360, 15))
    pts.insert(rng.randint(1, len(pts)), (far * math.cos(a), far * math.sin(a)))
    return f"{L1} {L2}\n" + "".join(f"{_f(x)} {_f(y)}\n" for x, y in pts)


def gen_mk2(rng):
    L1, L2 = rng.choice([(1.0, 0.5), (0.85, 0.65), (0.5, 0.4)])
    rows = [(rng.randrange(-90, 181, 15), rng.randrange(-120, 121, 15), rng.randrange(-60, 61, 10),
             rng.randrange(-60, 61, 10)) for _ in range(rng.randint(3, 4))]
    return f"{L1} {L2}\n" + "".join(" ".join(map(str, r)) + "\n" for r in rows)


def gen_cubic(rng):
    q0 = rng.randrange(-30, 31, 5)
    return f"{q0} {q0 + rng.randrange(30, 121, 10)} {rng.choice([2, 3, 4])} {rng.choice([0.5, 0.25, 0.2])}\n"


def gen_lspb(rng):
    q0 = rng.randrange(0, 31, 10)
    qf = q0 + rng.randrange(40, 121, 20)
    tf = rng.choice([2, 4, 5])
    V = (qf - q0) / tf * rng.choice([1.25, 1.5, 1.6])
    return f"{q0} {qf} {tf} {V:g} {rng.choice([0.5, 0.25])}\n"


def gen_bbpb(rng):
    q0 = rng.randrange(-20, 21, 10)
    return f"{q0} {q0 + rng.randrange(30, 101, 10)} {rng.choice([2, 4])} {rng.choice([0.5, 0.25])}\n"


def _shortest_paths(n, edges, s):
    dist, cnt = [math.inf] * n, [0] * n
    dist[s], cnt[s] = 0, 1
    done = set()
    for _ in range(n):
        u = min((i for i in range(n) if i not in done), key=lambda i: dist[i])
        if dist[u] == math.inf:
            break
        done.add(u)
        for a, b, w in edges:
            for x, y in ((a, b), (b, a)):
                if x == u and y not in done:
                    if dist[u] + w < dist[y]:
                        dist[y], cnt[y] = dist[u] + w, cnt[u]
                    elif dist[u] + w == dist[y]:
                        cnt[y] += cnt[u]
    return dist, cnt


def gen_dijkstra(rng):
    while True:
        n = rng.randint(6, 9)
        edges, seen = [], set()
        for v in range(1, n):                       # 연결 보장용 트리
            u = rng.randrange(v)
            edges.append((u, v, rng.randint(1, 9)))
            seen.add((u, v))
        for _ in range(rng.randint(n // 2, n)):
            u, v = sorted(rng.sample(range(n), 2))
            if (u, v) not in seen:
                seen.add((u, v))
                edges.append((u, v, rng.randint(1, 9)))
        s, t = 0, n - 1
        dist, cnt = _shortest_paths(n, edges, s)
        if cnt[t] == 1 and dist[t] >= 6:            # 최단 경로가 하나뿐일 때만 (PATH 채점이 모호하지 않게)
            rng.shuffle(edges)
            return f"{n} {len(edges)} {s} {t}\n" + "".join(f"{u} {v} {w}\n" for u, v, w in edges)


def gen_grid(rng):
    R, C = rng.randint(6, 8), rng.randint(6, 9)
    g = [[1 if rng.random() < 0.27 else 0 for _ in range(C)] for _ in range(R)]
    sr, sc, gr, gc = 0, 0, R - 1, C - 1
    if rng.random() < 0.5:
        sr, gr = gr, sr
    g[sr][sc] = g[gr][gc] = 0
    return f"{R} {C}\n" + "".join(" ".join(map(str, row)) + "\n" for row in g) + f"{sr} {sc} {gr} {gc}\n"


def gen_floyd(rng):
    n = rng.randint(4, 6)
    pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    edges = rng.sample(pairs, rng.randint(n + 1, min(len(pairs), 2 * n)))
    return f"{n} {len(edges)}\n" + "".join(f"{u} {v} {rng.randint(1, 20)}\n" for u, v in edges)


def gen_pid(rng):
    return (f"{rng.choice([1.5, 2.0, 3.0])} {rng.choice([0.5, 1.0])} {rng.choice([0.05, 0.1])} "
            f"{rng.choice([1.0, 10.0])} {rng.choice([0.5, 1.0])} {rng.choice([0.05, 0.1])} {rng.randint(15, 25)}\n")


def gen_can(rng):
    lines = []
    for _ in range(rng.randint(5, 7)):
        node = rng.randint(1, 6)
        pos = rng.randint(-18000, 18000)
        vel = rng.randint(-3000, 3000)
        data = (pos.to_bytes(4, "little", signed=True) + vel.to_bytes(2, "little", signed=True) +
                bytes([rng.randint(25, 85), rng.choice([0, 0, 0, 1, 2, 3, 0x80])]))
        lines.append(f"{0x180 + node:X} 8 " + " ".join(f"{b:02X}" for b in data))
    return "\n".join(lines) + "\n"


def gen_fan(rng):
    temps = [rng.uniform(45, 52) for _ in range(3)]
    rows = ["time,j1,j2,j3"]
    for k in range(rng.randint(14, 18)):
        temps = [min(72, max(40, t + rng.uniform(-3.5, 4.5))) for t in temps]
        if k in (5, 11):
            temps[rng.randrange(3)] = 60.0         # 경계값 = 60.0 은 반드시 한 번 등장
        rows.append(f"{k * 0.5:.1f}," + ",".join(f"{t:.1f}" for t in temps))
    return "\n".join(rows) + "\n"


def T(tid, topic, title, desc, fmt, hint, gen):
    return {"tid": tid, "topic": topic, "title": title, "desc": desc, "fmt": fmt, "hint": hint, "gen": gen}


TASKS = [
    T("fk2", ("기구학 · FK", "Kinematics · FK"), ("2링크 순기구학(FK)", "2-link forward kinematics"),
      ("2링크 평면 로봇팔입니다. 첫 줄은 링크 길이 L1 L2 [m], 다음 줄부터 자세마다 관절각 θ1 θ2 [도]입니다. "
       "자세마다 베이스·관절1·말단의 좌표 Px0 Py0 Px1 Py1 Px2 Py2 를 계산해 output.txt에 쓰시오.",
       "A planar 2-link arm. Line 1 holds the link lengths L1 L2 [m]; each following line is a pose θ1 θ2 [deg]. "
       "For every pose write the base, joint-1 and end-effector coordinates Px0 Py0 Px1 Py1 Px2 Py2 to output.txt."),
      ("자세당 한 줄 · 공백 구분 · 소수점 3자리", "one line per pose · space separated · 3 decimals"),
      ("x1 = L1·cosθ1, x2 = x1 + L2·cos(θ1+θ2). cos/sin은 라디안만 받습니다!",
       "x1 = L1·cosθ1, x2 = x1 + L2·cos(θ1+θ2). cos/sin take radians!"), gen_fk2),
    T("ik2", ("기구학 · IK", "Kinematics · IK"), ("2링크 역기구학(IK)", "2-link inverse kinematics"),
      ("첫 줄은 L1 L2 [m], 다음 줄부터 목표 말단 위치 x y [m]입니다. 목표마다 관절각 θ1 θ2 [도]를 구하시오. "
       "θ2는 acos 결과(0~180°) 해를 쓰고, θ1은 [-180, 180) 범위로 맞춥니다. 닿지 않는 점은 UNREACHABLE.",
       "Line 1 is L1 L2 [m]; each following line is a target x y [m]. Solve θ1 θ2 [deg] for each target. "
       "Use the acos branch for θ2 (0–180°) and wrap θ1 into [-180, 180). Unreachable targets print UNREACHABLE."),
      ("목표당 한 줄 'θ1 θ2' 소수점 3자리, 또는 UNREACHABLE", "one line per target 'θ1 θ2' with 3 decimals, or UNREACHABLE"),
      ("D = (x²+y²−L1²−L2²)/(2·L1·L2), θ2 = acos(D), θ1 = atan2(y,x) − atan2(L2·sinθ2, L1+L2·cosθ2). |D|>1이면 도달 불가",
       "D = (x²+y²−L1²−L2²)/(2·L1·L2), θ2 = acos(D), θ1 = atan2(y,x) − atan2(L2·sinθ2, L1+L2·cosθ2). |D|>1 → unreachable"),
      gen_ik2),
    T("mk2", ("기구학 · MK", "Kinematics · MK"), ("2링크 동기구학 (v = J·θ̇)", "2-link velocity kinematics (v = J·θ̇)"),
      ("첫 줄은 L1 L2 [m], 다음 줄부터 θ1 θ2 [도] θ̇1 θ̇2 [도/s]입니다. 자코비안으로 말단 속도 vx vy [m/s]를 구하시오.",
       "Line 1 is L1 L2 [m]; each following line is θ1 θ2 [deg] θ̇1 θ̇2 [deg/s]. Use the Jacobian to compute the "
       "end-effector velocity vx vy [m/s]."),
      ("줄마다 'vx vy' 소수점 4자리", "one line 'vx vy' per row, 4 decimals"),
      ("vx = −L1·s1·θ̇1 − L2·s12·(θ̇1+θ̇2), vy = L1·c1·θ̇1 + L2·c12·(θ̇1+θ̇2). 각속도도 라디안/s로!",
       "vx = −L1·s1·θ̇1 − L2·s12·(θ̇1+θ̇2), vy = L1·c1·θ̇1 + L2·c12·(θ̇1+θ̇2). Angular rates in rad/s too!"), gen_mk2),
    T("cubic", ("궤적 계획", "Trajectory"), ("3차 다항식(CUBIC) 궤적", "Cubic polynomial trajectory"),
      ("입력은 한 줄 'q0 qf tf dt' 입니다 (도, 초). 시작·끝 속도가 0인 3차 다항식 궤적을 t = 0부터 tf까지(tf 포함) "
       "dt 간격으로 계산해 't q q̇ q̈'를 쓰시오. t는 k·dt로 계산합니다.",
       "Input is one line 'q0 qf tf dt' (deg, s). Generate a cubic trajectory with zero start/end velocity from t = 0 to "
       "tf inclusive in steps of dt and write 't q q̇ q̈'. Compute t as k·dt."),
      ("줄마다 t(소수 2자리) q q̇ q̈(소수 3자리)", "t with 2 decimals, q q̇ q̈ with 3 decimals"),
      ("a2 = 3(qf−q0)/tf², a3 = −2(qf−q0)/tf³. 반복 횟수는 round(tf/dt)+1 — arange는 끝점을 빼먹습니다",
       "a2 = 3(qf−q0)/tf², a3 = −2(qf−q0)/tf³. Loop round(tf/dt)+1 times — arange drops the end point"), gen_cubic),
    T("lspb", ("궤적 계획", "Trajectory"), ("LSPB (사다리꼴 속도) 궤적", "LSPB (trapezoidal velocity) trajectory"),
      ("입력은 'q0 qf tf V dt' 입니다 (V = 등속 구간 속도). 블렌드 시간 tb를 첫 줄 'TB tb'로 쓰고, "
       "이어서 t = k·dt (0~tf 포함)마다 't q q̇'를 쓰시오.",
       "Input is 'q0 qf tf V dt' (V = cruise velocity). Write the blend time as 'TB tb' on the first line, then "
       "'t q q̇' for every t = k·dt from 0 to tf inclusive."),
      ("'TB 소수3자리' 다음 줄부터 t(2자리) q q̇(3자리)", "'TB' with 3 decimals, then t (2 dp) q q̇ (3 dp)"),
      ("tb = (q0 − qf + V·tf)/V, a = V/tb. 가속(t≤tb): q0 + a/2·t² · 등속: (qf+q0−V·tf)/2 + V·t · 감속: qf − a/2·(tf−t)²",
       "tb = (q0 − qf + V·tf)/V, a = V/tb. accel (t≤tb): q0 + a/2·t² · cruise: (qf+q0−V·tf)/2 + V·t · decel: qf − a/2·(tf−t)²"),
      gen_lspb),
    T("bbpb", ("궤적 계획", "Trajectory"), ("BBPB (뱅뱅) 궤적", "Bang-bang parabolic blend (BBPB)"),
      ("입력은 'q0 qf tf dt' 입니다. 등속 구간 없이 tf/2까지 가속, 이후 감속하는 BBPB 궤적의 't q q̇ q̈'를 "
       "t = k·dt (0~tf 포함)마다 쓰시오. t ≤ tf/2 이면 가속 구간(q̈ = +a)입니다.",
       "Input is 'q0 qf tf dt'. Accelerate until tf/2 and then decelerate (no cruise). Write 't q q̇ q̈' for every "
       "t = k·dt from 0 to tf inclusive. t ≤ tf/2 counts as the accelerating half (q̈ = +a)."),
      ("t(2자리) q q̇ q̈(3자리)", "t (2 dp) q q̇ q̈ (3 dp)"),
      ("a = 4(qf−q0)/tf². 후반부는 q = qf − a/2·(tf−t)², q̇ = a·(tf−t)",
       "a = 4(qf−q0)/tf². Second half: q = qf − a/2·(tf−t)², q̇ = a·(tf−t)"), gen_bbpb),
    T("dijkstra", ("경로 탐색", "Path search"), ("Dijkstra 최단 경로", "Dijkstra shortest path"),
      ("첫 줄 'N M S T', 이어서 M줄의 무방향 간선 'u v w'. S에서 T까지 최단 거리와 경로를 구하시오.",
       "Line 1 is 'N M S T', followed by M undirected edges 'u v w'. Find the shortest distance and path from S to T."),
      ("'DIST d' / 'PATH S ... T' (도달 불가면 DIST -1 / PATH NONE)", "'DIST d' / 'PATH S ... T' (or DIST -1 / PATH NONE)"),
      ("heapq에는 (거리, 노드) 순서로! 꺼낸 거리가 dist[u]보다 크면 건너뛰고, prev[]로 경로를 거꾸로 따라갑니다",
       "Push (dist, node) into the heap, skip stale entries, and walk prev[] backwards for the path"), gen_dijkstra),
    T("grid", ("경로 탐색", "Path search"), ("격자 지도 A* (8방향)", "Grid A* (8-connected)"),
      ("첫 줄 'R C', 다음 R줄은 격자(0 빈칸, 1 벽), 마지막 줄 'sr sc gr gc'. 8방향 이동(직선 1, 대각 √2), "
       "대각 이동 시 옆 두 칸 중 하나라도 벽이면 금지. 최단 경로 길이를 구하시오.",
       "Line 1 is 'R C', then R grid rows (0 free, 1 wall), then 'sr sc gr gc'. Move in 8 directions (straight 1, "
       "diagonal √2); a diagonal move is forbidden if either side cell is a wall. Find the shortest path length."),
      ("'LENGTH 소수3자리' (경로 없으면 LENGTH -1)", "'LENGTH' with 3 decimals (or LENGTH -1)"),
      ("grid[행][열]! 휴리스틱은 옥타일 거리 (dr+dc) + (√2−2)·min(dr,dc)",
       "grid[row][col]! Use the octile heuristic (dr+dc) + (√2−2)·min(dr,dc)"), gen_grid),
    T("floyd", ("경로 탐색", "Path search"), ("Floyd-Warshall 전체 최단 거리", "Floyd-Warshall all pairs"),
      ("첫 줄 'N M', 이어서 방향 간선 'u v w' M줄. 모든 쌍 최단 거리 N×N 행렬을 쓰시오. 도달 불가는 INF.",
       "Line 1 is 'N M', then M directed edges 'u v w'. Write the N×N all-pairs shortest distance matrix (INF if unreachable)."),
      ("행마다 공백 구분 정수 또는 INF", "space-separated integers or INF, one row per line"),
      ("k(경유 노드) 루프가 가장 바깥! D[i][j] = min(D[i][j], D[i][k] + D[k][j])",
       "The k (via) loop must be outermost! D[i][j] = min(D[i][j], D[i][k] + D[k][j])"), gen_floyd),
    T("pid", ("제어", "Control"), ("PID 제어 시뮬레이션", "PID control simulation"),
      ("입력은 'Kp Ki Kd sp tau dt steps'. 1차 플랜트 x += dt·(−x + u)/tau (x0 = 0). 매 스텝 k마다 "
       "e = sp − x, 적분 += e·dt, 미분 = (e − e_prev)/dt (k = 0이면 0), u = Kp·e + Ki·적분 + Kd·미분을 구해 "
       "'t x u'를 쓴 뒤 x를 갱신하시오.",
       "Input is 'Kp Ki Kd sp tau dt steps'. First-order plant x += dt·(−x + u)/tau (x0 = 0). For each step k compute "
       "e = sp − x, integral += e·dt, derivative = (e − e_prev)/dt (0 when k = 0), u = Kp·e + Ki·integral + Kd·derivative, "
       "write 't x u', then update x."),
      ("t(2자리) x u(4자리), steps줄", "t (2 dp) x u (4 dp), one line per step"),
      ("출력 → 갱신 순서를 지키세요. 첫 스텝은 미분 0 (derivative kick 방지)",
       "Write first, then update x. The first step has zero derivative (no derivative kick)"), gen_pid),
    T("can", ("통신", "Communication"), ("CAN 프레임 파싱", "CAN frame parsing"),
      ("줄마다 'ID DLC B0 … B7' (16진수) CAN 프레임입니다. 노드 = ID − 0x180. B0~B3 위치 int32 리틀엔디언 "
       "(0.01도 단위), B4~B5 속도 int16 리틀엔디언 [rpm], B6 온도 uint8 [°C], B7 bit0 = 고장. CSV로 쓰시오.",
       "Each line is a CAN frame 'ID DLC B0 … B7' in hex. node = ID − 0x180. B0–B3: position int32 little-endian "
       "(0.01 deg units), B4–B5: velocity int16 little-endian [rpm], B6: temperature uint8 [°C], B7 bit0 = fault. Write CSV."),
      ("머리글 'node,position_deg,velocity_rpm,temp_c,fault' + 프레임당 한 줄 (위치 소수 2자리)",
       "header 'node,position_deg,velocity_rpm,temp_c,fault' + one line per frame (position with 2 decimals)"),
      ("부호 있는 정수로 읽기! int.from_bytes(b, 'little', signed=True) / C++은 (int16_t)(b4 | b5 << 8)",
       "Read as signed! int.from_bytes(b, 'little', signed=True) / C++: (int16_t)(b4 | b5 << 8)"), gen_can),
    T("fan", ("모니터링", "Monitoring"), ("관절 온도 → 냉각팬 (히스테리시스)", "Joint temperature → fan (hysteresis)"),
      ("CSV 'time,j1,j2,j3' (머리글 있음). 줄마다 세 관절 중 최고 온도로 팬을 제어합니다: 꺼져 있을 때 ≥ 60.0이면 ON, "
       "켜져 있을 때 ≤ 55.0이면 OFF (처음은 OFF). 줄마다 상태를 쓰고, 마지막 줄에 OFF→ON 횟수를 쓰시오.",
       "CSV 'time,j1,j2,j3' with a header. Drive the fan from the hottest joint on each row: turn ON at ≥ 60.0 while off, "
       "turn OFF at ≤ 55.0 while on (starts OFF). Write the state per row and finally the number of OFF→ON switches."),
      ("머리글 'time,max_temp,fan' + 'time,최고온도(1자리),ON|OFF' + 'ON_COUNT n'",
       "header 'time,max_temp,fan' + 'time,max (1 dp),ON|OFF' + 'ON_COUNT n'"),
      ("time 칸은 입력 문자열 그대로. 경계값 60.0은 ON(≥), 55.0은 OFF(≤)",
       "Copy the time field as-is. 60.0 turns ON (≥), 55.0 turns OFF (≤)"), gen_fan),
]
TASK_BY_ID = {t["tid"]: t for t in TASKS}


def model_answer(tid, lang):
    return (TASK_DIR / f"{tid}.{'cpp' if lang == 'cpp' else 'py'}").read_text(encoding="utf-8")


def reference_output(tid, input_text):
    """레퍼런스(Python) 풀이를 실행해서 기대 출력을 만든다."""
    with tempfile.TemporaryDirectory(prefix="codekata-ref-") as tmp:
        Path(tmp, "input.txt").write_text(input_text, encoding="utf-8")
        p = subprocess.run([sys.executable, "-I", str(TASK_DIR / f"{tid}.py")], cwd=tmp, capture_output=True,
                           text=True, timeout=20)
        if p.returncode != 0:
            raise RuntimeError(f"reference {tid} failed: {p.stderr.strip()[-200:]}")
        return Path(tmp, "output.txt").read_text(encoding="utf-8")


def make_task(tid, lang, seed=None):
    t = TASK_BY_ID[tid]
    rng = random.Random(seed)
    inp = t["gen"](rng)
    return {"kind": "task", "track": "exam", "lang": lang, "tid": tid, "id": f"task-{tid}", "source": "bank",
            "title": pick(t["title"]), "topic": pick(t["topic"]), "desc": pick(t["desc"]), "fmt": pick(t["fmt"]),
            "hint": pick(t["hint"]), "input": inp, "expected": reference_output(tid, inp), "explain": pick(t["hint"])}


_TRAIL_COMMENT = re.compile(r"\s{2,}(#|//)\s.*$")


def clone_lines(code):
    """클론코딩용 줄 목록 [(원래 줄, 들여쓰기, 칠 내용 | None)]. 빈 줄·주석 줄은 자동, 줄 끝 주석은 빼고 친다."""
    out = []
    for raw in code.rstrip("\n").split("\n"):
        body = raw.strip()
        indent = raw[:len(raw) - len(raw.lstrip())]
        if not body or body.startswith(("#", "//")):
            out.append((raw, indent, None))
        else:
            out.append((raw, indent, _TRAIL_COMMENT.sub("", raw).strip()))
    return out


def same_line(typed, target):
    return " ".join(typed.split()) == " ".join(target.split())


def make_clone(tid, lang, seed=None):
    p = make_task(tid, lang, seed)
    p.update(kind="clone", id=f"clone-{tid}", code=model_answer(tid, lang),
             title=tr(f"클론코딩 · {p['title']}", f"Clone · {p['title']}"))
    return p


# ─── 작업 폴더 · 실행 · 채점 ─────────────────────────────────

STARTER = {
    "python": '''# {title}
# {desc_c}
# {fmt_c}
# input.txt -> output.txt  (cwd = {ws})
import math

with open("input.txt", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

out = []
# TODO

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("\\n".join(out) + "\\n")
''',
    "cpp": '''// {title}
// {desc_c}
// {fmt_c}
// input.txt -> output.txt  (cwd = {ws})
#include <bits/stdc++.h>
using namespace std;

int main() {{
    ifstream in("input.txt");
    FILE* out = fopen("output.txt", "w");
    // TODO
    fclose(out);
}}
''',
}


def _comment(text, prefix, width=96):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return f"\n{prefix} ".join(lines)


def workspace(sid, p, scaffold=True):
    ws = store.HOME / "exam" / f"{time.strftime('%Y%m%d')}-{sid}-{p['kind']}-{p['tid']}-{p['lang']}"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "input.txt").write_text(p["input"], encoding="utf-8")
    src = ws / ("solution.cpp" if p["lang"] == "cpp" else "solution.py")
    if not src.exists():
        pre = "//" if p["lang"] == "cpp" else "#"
        body = STARTER[p["lang"]].format(title=p["title"], desc_c=_comment(p["desc"], pre), fmt_c=p["fmt"], ws=ws)
        if not scaffold:
            body = "\n".join(x for x in body.splitlines() if x.startswith(pre)) + "\n"
        src.write_text(body, encoding="utf-8")
    return ws, src


def editor_cmd(path):
    for var in ("CODEKATA_EDITOR", "VISUAL", "EDITOR"):
        if os.environ.get(var):
            return os.environ[var].split() + [str(path)]
    for ed in ("nano", "vim", "vi"):
        if shutil.which(ed):
            return [ed, str(path)]
    return None


def run_solution(ws, lang, timeout=10):
    """반환 dict(stage=compile|run|ok, ok, msg, out, stdout, secs)."""
    out_file = ws / "output.txt"
    if out_file.exists():
        out_file.unlink()
    t0 = time.monotonic()
    if lang == "cpp":
        if not shutil.which("g++"):
            return {"stage": "compile", "ok": False, "msg": tr("g++ 가 없습니다", "g++ not found"), "out": None,
                    "stdout": "", "secs": 0}
        exe = ws / "solution"
        c = subprocess.run(["g++", "-std=gnu++17", "-O2", "-o", str(exe), "solution.cpp"], cwd=ws,
                           capture_output=True, text=True, timeout=90)
        if c.returncode != 0:
            errs = [x for x in c.stderr.splitlines() if "error" in x] or c.stderr.splitlines()
            return {"stage": "compile", "ok": False, "msg": "\n".join(errs[:4]), "out": None, "stdout": "",
                    "secs": time.monotonic() - t0}
        cmd = [str(exe)]
    else:
        cmd = [sys.executable, "solution.py"]
    try:
        r = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return {"stage": "run", "ok": False, "msg": tr(f"시간 초과 ({timeout}s) — 무한 루프?", f"timeout ({timeout}s) — infinite loop?"),
                "out": None, "stdout": "", "secs": timeout}
    secs = time.monotonic() - t0
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or [f"exit {r.returncode}"])[-3:]
        return {"stage": "run", "ok": False, "msg": "\n".join(tail), "out": None, "stdout": r.stdout, "secs": secs}
    if not out_file.exists():
        return {"stage": "run", "ok": False, "stdout": r.stdout, "secs": secs, "out": None,
                "msg": tr("output.txt 가 만들어지지 않았습니다 (화면 출력은 채점하지 않음)",
                          "output.txt was not created (stdout is not graded)")}
    return {"stage": "ok", "ok": True, "msg": "", "out": out_file.read_text(encoding="utf-8", errors="replace"),
            "stdout": r.stdout, "secs": secs}


_NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")
_SPLIT = re.compile(r"[,\s]+")


def _norm_tok(tok):
    if _NUM.match(tok) and float(tok) == 0:
        return tok.lstrip("+-")             # -0.000 == 0.000
    return tok


def _decimals(tok):
    return len(tok.split(".")[1]) if "." in tok and "e" not in tok.lower() else 0


def compare_line(exp, got):
    """ok | near(값은 맞고 형식이 다름) | bad"""
    if got is None:
        return "bad"
    if exp == got:
        return "ok"
    et, gt = [_norm_tok(x) for x in _SPLIT.split(exp.strip())], [_norm_tok(x) for x in _SPLIT.split(got.strip())]
    seps_same = re.sub(r"[^,\s]", "", exp) == re.sub(r"[^,\s]", "", got)
    if len(et) != len(gt):
        return "bad"
    fmt_ok = seps_same
    for e, g in zip(et, gt):
        if e == g:
            continue
        if _NUM.match(e) and _NUM.match(g):
            de, dg = _decimals(e), _decimals(g)
            if de == dg:
                if abs(float(e) - float(g)) > 1.01 * 10 ** -de:      # 마지막 자리 ±1 (반올림 경계 오차)까지 허용
                    return "bad"
            else:                                                  # 자리수만 다르면 형식 오류
                if abs(round(float(e), dg) - float(g)) > 1.01 * 10 ** -dg:
                    return "bad"
                fmt_ok = False
        elif e.lower() == g.lower():
            fmt_ok = False
        else:
            return "bad"
    return "ok" if fmt_ok else "near"


def grade(expected, got):
    """반환 (ratio, rows). rows = [(줄번호, 상태, 기대, 출력)]"""
    exp = [x.rstrip() for x in expected.replace("\r\n", "\n").rstrip("\n").split("\n")]
    out = [x.rstrip() for x in (got or "").replace("\r\n", "\n").rstrip("\n").split("\n")] if got else []
    rows = []
    for i in range(max(len(exp), len(out))):
        e = exp[i] if i < len(exp) else None
        g = out[i] if i < len(out) else None
        st = "extra" if e is None else compare_line(e, g)
        rows.append((i + 1, st, e, g))
    score = sum(1.0 if st == "ok" else 0.5 if st == "near" else 0 for _, st, _, _ in rows)
    return score / max(1, len(rows)), rows


# ─── 공식/함정 퀴즈 · 카타 (Python / C++) ─────────────────────

def Q(lang, title, code, question, options, correct, explain, check, opt_code):
    return {"kind": "quiz", "track": "exam", "lang": lang, "title": title, "code": code, "question": question,
            "options": list(options), "correct": correct, "explain": explain, "check": check, "opt_code": opt_code}


def QB(lang, title, code, question, options, correct, expect, explain):
    """빈칸형: code의 ____ 에 보기(코드)를 넣었을 때 정답만 expect를 출력한다."""
    return Q(lang, title, code, question, options, correct, explain, {"type": "blank", "expect": expect}, True)


def QL(lang, title, code, intent, lines, bug, fix, expect, explain):
    """버그 줄형: bug 번째 줄을 fix로 고치면 expect가 출력되고, 원래 코드는 다르게 동작한다."""
    question = (f"의도: {intent[0]} — 버그가 있는 줄은?", f"Intent: {intent[1]} — which line is the bug?")
    options = [(f"{n}번 줄", f"line {n}") for n in lines]
    return Q(lang, title, code, question, options, lines.index(bug), explain,
             {"type": "line", "line": bug, "fix": fix, "expect": expect}, False)


BLANK = ("빈칸 ____ 에 들어갈 코드는?", "Which code fills the blank ____?")

QUIZ = [
    QB("python", ("IK θ1 — atan2", "IK θ1 — atan2"),
       "import math\n\nL1, L2 = 1.0, 0.5\nx, y = -0.6, 0.9                     # 2사분면 목표점\n"
       "D = (x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2)\nt2 = math.acos(D)\nt1 = ____\n"
       "print(f\"{math.degrees(t1):.1f} {math.degrees(t2):.1f}\")",
       ("2사분면 목표에서도 맞는 θ1 코드는?", "Which θ1 works even for a quadrant-II target?"),
       ["math.atan(y / x) - math.atan(L2 * math.sin(t2) / (L1 + L2 * math.cos(t2)))",
        "math.atan2(y, x) - math.atan2(L2 * math.sin(t2), L1 + L2 * math.cos(t2))",
        "math.atan2(x, y) - math.atan2(L2 * math.sin(t2), L1 + L2 * math.cos(t2))",
        "math.atan2(y, x) + math.atan2(L2 * math.sin(t2), L1 + L2 * math.cos(t2))"], 1, "96.3 94.6",
       ("`atan(y/x)`는 x의 부호를 잃어 사분면을 착각하고, `atan2`는 (y, x) 순서입니다. 빼는 쪽이 θ2 > 0 해!",
        "`atan(y/x)` loses the sign of x; `atan2` takes (y, x). Subtracting gives the θ2 > 0 solution!")),
    QL("python", ("FK 각도 단위", "FK angle units"),
       "import math\nL1, L2 = 1.0, 0.5\nd1, d2 = 30, 45\nx = L1 * math.cos(d1) + L2 * math.cos(d1 + d2)\n"
       "y = L1 * math.sin(math.radians(d1)) + L2 * math.sin(math.radians(d1 + d2))\nprint(f\"{x:.3f} {y:.3f}\")",
       ("30°·45° 자세의 말단 좌표 출력", "print the end-effector of the 30°/45° pose"), [3, 4, 5, 6], 4,
       "x = L1 * math.cos(math.radians(d1)) + L2 * math.cos(math.radians(d1 + d2))", "0.995 0.983",
       ("4번 줄만 도 값을 그대로 `cos`에 넣었습니다. 5번 줄처럼 `math.radians`로 바꿔야 해요.",
        "Line 4 passes degrees straight into `cos`; convert with `math.radians` like line 5.")),
    QB("python", ("tf 포함 시간축", "Time axis including tf"),
       "tf, dt = 2.0, 0.5\nts = ____\nprint(ts)", ("0부터 tf까지(포함) 시간 목록을 만드는 코드는?", "Which code lists times from 0 to tf inclusive?"),
       ["[k * dt for k in range(round(tf / dt))]", "list(range(0, tf, dt))",
        "[k * dt for k in range(round(tf / dt) + 1)]", "[k * dt for k in range(int(tf * dt) + 1)]"], 2,
       "[0.0, 0.5, 1.0, 1.5, 2.0]",
       ("`range`는 끝을 빼니 +1, 그리고 정수 k에 dt를 곱합니다. `range`는 float 간격을 못 받아요.",
        "`range` excludes the end, hence +1; multiply an integer k by dt. `range` can't take a float step.")),
    QB("python", ("출력 형식", "Output format"),
       "x, y = 0.8660254, 0.5\nline = ____\nprint(line)",
       ("'소수 3자리, 공백 구분' 형식을 만드는 코드는?", "Which code gives '3 decimals, space separated'?"),
       ['f"{round(x, 3)} {round(y, 3)}"', 'f"{x:.3f} {y:.3f}"', 'f"{x:3f} {y:3f}"', '"%.3f,%.3f" % (x, y)'], 1,
       "0.866 0.500",
       ("`round(0.5, 3)`은 0.5로 찍혀 자리수가 깨지고, `:3f`는 폭 3(소수 6자리)입니다. `:.3f`가 정답!",
        "`round(0.5, 3)` prints 0.5 and `:3f` means width 3 with 6 decimals. `:.3f` is the one!")),
    QL("python", ("입력 줄 나누기", "Splitting input lines"),
       'lines = ["30  45\\n", "60 90\\n"]\nout = []\nfor line in lines:\n'
       '    a, b = map(float, line.strip().split(" "))\n    out.append(a + b)\nprint(out)',
       ("공백 개수와 상관없이 두 값을 더하기", "add the two values whatever the spacing"), [1, 3, 4, 5], 4,
       "    a, b = map(float, line.split())", "[75.0, 150.0]",
       ("`split(\" \")`은 두 칸 공백에서 빈 문자열을 만들어 값이 3개가 됩니다. 인자 없는 `split()`!",
        "`split(\" \")` yields an empty string on double spaces (3 values). Use `split()` with no argument!")),
    QB("python", ("CAN 속도 int16", "CAN velocity int16"),
       'frame = bytes.fromhex("18FC2C01")      # B0 B1 = 속도(int16, little-endian)\nvel = ____\nprint(vel)',
       ("B0~B1을 부호 있는 속도로 읽는 코드는?", "Which code reads B0–B1 as a signed velocity?"),
       ['int.from_bytes(frame[0:2], "little")', 'int.from_bytes(frame[0:2], "big", signed=True)',
        'int.from_bytes(frame[2:4], "little", signed=True)', 'int.from_bytes(frame[0:2], "little", signed=True)'], 3,
       "-1000",
       ("리틀엔디언 18 FC → 0xFC18. 음수가 될 수 있는 값은 `signed=True` 필수!",
        "Little-endian 18 FC → 0xFC18. Values that can be negative need `signed=True`!")),
    QB("python", ("Dijkstra 힙에 넣기", "Pushing into the Dijkstra heap"),
       'import heapq\n\ndist = {"B": 4, "A": 0, "C": 1}\npq = []\nfor node, d in dist.items():\n    ____\n'
       "print(heapq.heappop(pq))",
       ("가장 가까운 노드가 먼저 나오게 하는 코드는?", "Which code makes the closest node pop first?"),
       ["heapq.heappush(pq, (node, d))", "pq.append((d, node))", "heapq.heappush(pq, (d, node))",
        "heapq.heappush(pq, (-d, node))"], 2, "(0, 'A')",
       ("튜플은 첫 값으로 비교되니 (거리, 노드) 순서로 `heappush`. `append`는 힙 성질이 깨집니다.",
        "Tuples compare by the first item, so `heappush` (dist, node). Plain `append` breaks the heap.")),
    QL("python", ("Floyd 갱신식", "Floyd update"),
       'INF = float("inf")\nD = [[0, 5, INF], [INF, 0, 2], [1, INF, 0]]\nn = len(D)\nfor k in range(n):\n'
       "    for i in range(n):\n        for j in range(n):\n            D[i][j] = min(D[i][j], D[i][k] + D[j][k])\n"
       "print(D[0][2], D[2][1])",
       ("모든 쌍 최단 거리 0→2, 2→1 출력", "print all-pairs distances 0→2 and 2→1"), [4, 5, 6, 7], 7,
       "            D[i][j] = min(D[i][j], D[i][k] + D[k][j])", "7 6",
       ("경유 경로는 i→k 다음 k→j, 즉 `D[k][j]`. 인덱스 순서 하나가 전체 행렬을 망칩니다.",
        "A detour goes i→k then k→j: `D[k][j]`. One swapped index ruins the matrix.")),
    QB("python", ("격자 좌표", "Grid coordinates"),
       "grid = [[0, 0, 0],\n        [0, 0, 0]]\nx, y = 2, 1            # 그림 좌표: x = 열, y = 행\n____\nprint(grid)",
       ("(x, y) 칸을 벽(1)으로 만드는 코드는?", "Which code marks cell (x, y) as a wall (1)?"),
       ["grid[x][y] = 1", "grid[y][x] = 1", "grid[y - 1][x - 1] = 1", "grid[x - 1][y] = 1"], 1,
       "[[0, 0, 0], [0, 0, 1]]",
       ("리스트는 `grid[행][열]` = `grid[y][x]`. 그림 좌표와 순서가 반대입니다.",
        "Lists are `grid[row][col]` = `grid[y][x]` — the opposite order of plot coordinates.")),
    QB("python", ("엑셀용 CSV 인코딩", "CSV encoding for Excel"),
       'import csv\n\nwith open("out.csv", "w", ____, newline="") as f:\n    csv.writer(f).writerow(["관절", "온도"])\n'
       'print(open("out.csv", "rb").read()[:3])',
       ("엑셀에서 한글이 안 깨지는 UTF-8로 저장하는 코드는?", "Which keeps Korean readable in Excel while saving UTF-8?"),
       ['encoding="utf-8"', 'encoding="utf-16"', 'encoding="utf-8-sig"', 'encoding="latin-1"'], 2,
       "b'\\xef\\xbb\\xbf'",
       ("엑셀은 BOM(EF BB BF)이 있어야 UTF-8로 인식합니다. `utf-8-sig`가 BOM을 붙여 줘요.",
        "Excel needs the BOM (EF BB BF) to detect UTF-8; `utf-8-sig` writes it.")),
    QB("python", ("acos 도메인", "acos domain"),
       "import math\n\nD = 1.0000000000000002        # 부동소수 오차로 1을 살짝 넘음\nt2 = ____\nprint(round(t2, 6))",
       ("오차가 있어도 θ2를 구하는 코드는?", "Which code still computes θ2 despite the float error?"),
       ["math.acos(D)", "math.acos(max(-1.0, min(1.0, D)))", "math.acos(D / 2)", "math.acos(abs(D))"], 1, "0.0",
       ("1을 살짝 넘으면 `math.acos`는 ValueError. [−1, 1]로 잘라서 넣습니다 (도달 불가 판정은 그 전에!).",
        "Just above 1, `math.acos` raises ValueError. Clamp into [−1, 1] (check reachability first!).")),
    QB("python", ("CUBIC a3", "Cubic a3"),
       "q0, qf, tf = 0.0, 90.0, 3.0\na2 = 3 * (qf - q0) / tf ** 2\na3 = ____\n"
       "print(round(q0 + a2 * tf**2 + a3 * tf**3, 6))           # q(tf) 검산",
       ("q(tf) = qf가 되게 하는 a3는?", "Which a3 makes q(tf) = qf?"),
       ["2 * (qf - q0) / tf ** 3", "-2 * (qf - q0) / tf ** 2", "-2 * (qf - q0) / tf ** 3",
        "-3 * (qf - q0) / tf ** 3"], 2, "90.0",
       ("a2 = 3Δq/tf², a3 = −2Δq/tf³. 마지막 줄처럼 q(tf) = qf 검산을 습관으로!",
        "a2 = 3Δq/tf², a3 = −2Δq/tf³. Make the q(tf) = qf check on the last line a habit!")),
    QL("cpp", ("정수 나눗셈", "Integer division"),
       "#include <cstdio>\nint main() {\n    double a = 4.0;\n    int t = 2;\n    double q = 1 / 2 * a * t * t;\n"
       "    std::printf(\"%.3f\\n\", q);\n}",
       ("q = ½·a·t² 출력", "print q = ½·a·t²"), [3, 4, 5, 6], 5, "    double q = 0.5 * a * t * t;", "8.000",
       ("`1 / 2`는 int끼리라 0! `0.5` 또는 `1.0 / 2`로 써야 합니다.",
        "`1 / 2` is integer division = 0! Write `0.5` or `1.0 / 2`.")),
    QB("cpp", ("cout 자리수", "cout precision"),
       "#include <iomanip>\n#include <iostream>\nint main() {\n    double x = 2.0 / 3, y = 1.0;\n"
       "    std::cout << ____ << x << \" \" << y << \"\\n\";\n}",
       ("'0.667 1.000'처럼 소수 3자리로 찍는 코드는?", "Which prints three decimals like '0.667 1.000'?"),
       ["std::setprecision(3)", "std::fixed", "std::fixed << std::setprecision(3)", "std::setw(3)"], 2, "0.667 1.000",
       ("`setprecision`만 쓰면 유효숫자 3자리(1.0 → 1), `fixed`와 함께 써야 소수점 아래 자리수가 됩니다.",
        "`setprecision` alone means 3 significant digits (1.0 → 1); with `fixed` it means decimals.")),
    QB("cpp", ("IK θ1 (C++)", "IK θ1 (C++)"),
       "#include <cmath>\n#include <cstdio>\nint main() {\n    double L1 = 1.0, L2 = 0.5, x = -0.6, y = 0.9;\n"
       "    double t2 = std::acos((x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2));\n    double t1 = ____;\n"
       "    std::printf(\"%.1f %.1f\\n\", t1 * 180 / M_PI, t2 * 180 / M_PI);\n}",
       ("2사분면 목표에서도 맞는 θ1 코드는?", "Which θ1 works even for a quadrant-II target?"),
       ["std::atan2(x, y) - std::atan2(L2 * std::sin(t2), L1 + L2 * std::cos(t2))",
        "std::atan(y / x) - std::atan(L2 * std::sin(t2) / (L1 + L2 * std::cos(t2)))",
        "std::atan2(y, x) + std::atan2(L2 * std::sin(t2), L1 + L2 * std::cos(t2))",
        "std::atan2(y, x) - std::atan2(L2 * std::sin(t2), L1 + L2 * std::cos(t2))"], 3, "96.3 94.6",
       ("C++도 `atan2(y, x)` 순서. `atan(y/x)`는 x < 0에서 180° 어긋납니다.",
        "C++ is also `atan2(y, x)`. `atan(y/x)` is off by 180° when x < 0.")),
    QB("cpp", ("int16 조립", "Assembling int16"),
       "#include <cstdint>\n#include <cstdio>\nint main() {\n    uint8_t b[] = {0x18, 0xFC};   // little-endian int16\n"
       "    int vel = ____;\n    std::printf(\"%d\\n\", vel);\n}",
       ("부호 있는 속도로 읽는 코드는?", "Which reads a signed velocity?"),
       ["b[0] | b[1] << 8", "(int16_t)(b[0] | b[1] << 8)", "(int16_t)(b[0] << 8 | b[1])", "(uint16_t)(b[0] | b[1] << 8)"],
       1, "-1000",
       ("하위 바이트가 먼저(리틀엔디언), 그리고 `int16_t`로 캐스팅해야 부호가 살아납니다.",
        "Low byte first (little-endian), and cast to `int16_t` to keep the sign.")),
    QB("cpp", ("최소 힙", "Min-heap"),
       "#include <cstdio>\n#include <functional>\n#include <queue>\n#include <utility>\n#include <vector>\nint main() {\n"
       "    std::priority_queue<std::pair<int, int>, std::vector<std::pair<int, int>>, ____> pq;\n"
       "    pq.push({5, 1});\n    pq.push({2, 3});\n    pq.push({8, 0});\n"
       "    std::printf(\"%d %d\\n\", pq.top().first, pq.top().second);\n}",
       ("Dijkstra처럼 가장 짧은 거리가 top에 오게 하는 코드는?", "Which puts the shortest distance on top, as Dijkstra needs?"),
       ["std::less<>", "std::greater<>", "std::less<std::pair<int, int>>", "std::greater<int>"], 1, "2 3",
       ("`priority_queue`는 기본이 최대 힙. `std::greater<>`를 넣어야 최소 힙이 됩니다.",
        "`priority_queue` is a max-heap by default; `std::greater<>` makes it a min-heap.")),
    QL("cpp", ("시간 루프", "Time loop"),
       "#include <cstdio>\nint main() {\n    double tf = 1.0, dt = 0.05;\n    int n = 0;\n"
       "    for (double t = 0.0; t <= tf; t += dt) n++;\n    std::printf(\"%d\\n\", n);\n}",
       ("t = 0 ~ tf(포함) 샘플 수 21 출력", "print 21 samples for t = 0 … tf inclusive"), [3, 4, 5, 6], 5,
       "    for (int k = 0; k * dt <= tf + 1e-9; k++) n++;", "21",
       ("0.05를 스무 번 더하면 1.0000000000000002가 되어 마지막 스텝이 빠집니다. 정수 k로 돌리세요.",
        "Adding 0.05 twenty times gives 1.0000000000000002 and drops the last step. Loop on an integer k.")),
    QL("cpp", ("입력 타입", "Input types"),
       "#include <iostream>\n#include <sstream>\nint main() {\n    std::istringstream in(\"45.5 30\");\n    int deg;\n"
       "    double len;\n    in >> deg >> len;\n    std::cout << deg + len << \"\\n\";\n}",
       ("두 값 45.5와 30을 더해 75.5 출력", "add 45.5 and 30 and print 75.5"), [4, 5, 6, 7], 5, "    double deg;",
       "75.5",
       ("int로 읽으면 45에서 멈추고 '.5'가 다음 변수로 넘어갑니다. 소수가 올 수 있으면 double!",
        "Reading an int stops at 45 and '.5' spills into the next variable. Use double when decimals may appear!")),
    QB("cpp", ("cos 각도", "cos angle"),
       "#include <cmath>\n#include <cstdio>\nint main() {\n    double d = 60;        // degrees\n    double c = ____;\n"
       "    std::printf(\"%.3f\\n\", c);\n}",
       ("cos 60° = 0.500을 구하는 코드는?", "Which computes cos 60° = 0.500?"),
       ["std::cos(d)", "std::cos(d * 180.0 / M_PI)", "std::cos(d * M_PI / 180.0)", "std::acos(d * M_PI / 180.0)"], 2,
       "0.500",
       ("C++ `cos`도 라디안. 도 × π/180!", "C++ `cos` takes radians too: degrees × π/180!")),
    QB("cpp", ("2차원 vector", "2-D vector"),
       "#include <cstdio>\n#include <vector>\nint main() {\n    int R = 2, C = 3;\n    ____\n    g.at(1).at(2) = 9;\n"
       "    std::printf(\"%zu %zu\\n\", g.size(), g[0].size());\n}",
       ("R행 C열 격자를 만드는 코드는?", "Which builds an R-row, C-column grid?"),
       ["std::vector<std::vector<int>> g(C, std::vector<int>(R, 0));",
        "std::vector<std::vector<int>> g(R, std::vector<int>(C, 0));", "std::vector<std::vector<int>> g(R);",
        "std::vector<std::vector<int>> g(R * C);"], 1, "2 3",
       ("`vector(행 수, vector(열 수))`. 격자 파일을 읽을 때 R, C 순서를 지키세요.",
        "`vector(rows, vector(cols))`. Keep the R, C order when reading grid files.")),
]


def _run_out(lang, code):
    from . import judge
    r = judge.program_output(lang, code, timeout=10)
    return " ".join(r["out"].split()) if r and r["ok"] else None


def check_quiz(p):
    """코드형 퀴즈 검증 → (ok, 이유). blank: 정답 보기만 expect 출력. line: 그 줄을 고치면 동작이 바뀌고 expect 출력."""
    from concurrent.futures import ThreadPoolExecutor
    c, lang = p["check"], p["lang"]
    expect = " ".join(c["expect"].split()) if c.get("expect") else None
    if c["type"] == "blank":
        if p["code"].count("____") != 1:
            return False, "blank count"
        with ThreadPoolExecutor(4) as ex:
            outs = list(ex.map(lambda o: _run_out(lang, p["code"].replace("____", o)), p["options"]))
        if outs[p["correct"]] is None or (expect is not None and outs[p["correct"]] != expect):
            return False, f"correct option prints {outs[p['correct']]!r}"
        good = outs[p["correct"]]
        twins = [i for i, o in enumerate(outs) if i != p["correct"] and o == good]
        return (False, f"options {twins} also print {good!r}") if twins else (True, "")
    lines = p["code"].split("\n")
    n = c["line"]
    if not 1 <= n <= len(lines):
        return False, "line out of range"
    fixed = lines[:n - 1] + [c["fix"]] + lines[n:]
    with ThreadPoolExecutor(2) as ex:
        out_fix, out_bug = ex.map(lambda code: _run_out(lang, code), ["\n".join(fixed), p["code"]])
    if out_fix is None or (expect is not None and out_fix != expect):
        return False, f"fixed code prints {out_fix!r}"
    if out_bug == out_fix:
        return False, "bug line changes nothing"
    return True, ""


def K(lang, title, desc, answer, setup, tests, hint, explain):
    return {"kind": "kata", "track": "exam", "lang": lang, "title": title, "desc": desc, "setup": setup,
            "tests": list(tests), "answer": answer, "hint": hint, "accept": [], "explain": explain,
            "cpp_exec": lang == "cpp"}


KATA = [
    K("python", ("FK — 말단 x", "FK — end-effector x"),
      ("2링크 말단 x 좌표를 구하세요. (t1, t2는 이미 라디안)", "Compute the 2-link end-effector x. (t1, t2 are already radians)"),
      "L1 * math.cos(t1) + L2 * math.cos(t1 + t2)",
      "import math\nL1, L2 = 1.0, 0.5\nt1, t2 = math.radians(30), math.radians(45)",
      ["import math\nL1, L2 = 0.85, 0.65\nt1, t2 = math.radians(120), math.radians(-60)"],
      ("cos(θ1) + cos(θ1+θ2)", "cos(θ1) + cos(θ1+θ2)"),
      ("두 번째 링크는 절대각 θ1+θ2 방향! `cos(t2)`만 쓰면 오답입니다.",
       "The second link points along the absolute angle θ1+θ2 — `cos(t2)` alone is wrong.")),
    K("python", ("FK — 말단 y", "FK — end-effector y"),
      ("2링크 말단 y 좌표를 구하세요. (각도는 도 단위 d1, d2)", "Compute the 2-link end-effector y. (angles d1, d2 are in degrees)"),
      "L1 * math.sin(math.radians(d1)) + L2 * math.sin(math.radians(d1 + d2))",
      "import math\nL1, L2 = 1.0, 0.5\nd1, d2 = 30, 45", ["import math\nL1, L2 = 1.2, 0.7\nd1, d2 = 150, -90"],
      ("math.radians", "math.radians"),
      ("도 → 라디안 변환을 빼먹으면 sin(30)은 −0.988! 입력 단위부터 확인하세요.",
       "Skip the degree→radian conversion and sin(30) becomes −0.988! Check the input unit first.")),
    K("python", ("IK — θ2", "IK — θ2"),
      ("목표점 (x, y)에 대한 2링크 θ2 [라디안, acos 해]를 구하세요.", "Compute the 2-link θ2 [rad, acos branch] for target (x, y)."),
      "math.acos((x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2))",
      "import math\nL1, L2 = 1.0, 0.5\nx, y = 0.9, 0.8", ["import math\nL1, L2 = 1.0, 0.8\nx, y = -0.4, 1.1"],
      ("코사인 법칙", "law of cosines"),
      ("코사인 법칙 D = (x²+y²−L1²−L2²)/(2·L1·L2), θ2 = acos(D). 분모의 2를 빼먹는 실수가 많아요!",
       "Law of cosines: D = (x²+y²−L1²−L2²)/(2·L1·L2), θ2 = acos(D). People often drop the 2!")),
    K("python", ("CUBIC a2", "Cubic a2"),
      ("시작·끝 속도 0인 3차 궤적의 계수 a2를 구하세요.", "Compute coefficient a2 of a cubic with zero end velocities."),
      "3 * (qf - q0) / tf ** 2", "q0, qf, tf = 10.0, 90.0, 4.0", ["q0, qf, tf = -20.0, 40.0, 3.0"],
      ("3(qf−q0)/tf²", "3(qf−q0)/tf²"),
      ("q(t) = q0 + a2·t² + a3·t³, a2 = 3Δq/tf², a3 = −2Δq/tf³. 경계조건 4개로 유도됩니다.",
       "q(t) = q0 + a2·t² + a3·t³ with a2 = 3Δq/tf² and a3 = −2Δq/tf³ — from the four boundary conditions.")),
    K("python", ("LSPB 블렌드 시간", "LSPB blend time"),
      ("등속 V인 LSPB의 블렌드 시간 tb를 구하세요.", "Compute the LSPB blend time tb for cruise velocity V."),
      "(q0 - qf + V * tf) / V", "q0, qf, tf, V = 0.0, 90.0, 4.0, 30.0", ["q0, qf, tf, V = 10.0, 70.0, 2.0, 45.0"],
      ("tb = (q0 − qf + V·tf)/V", "tb = (q0 − qf + V·tf)/V"),
      ("면적(이동 거리) = V·(tf − tb)에서 유도. V는 Δq/tf < V ≤ 2Δq/tf 범위여야 해가 있습니다.",
       "From area = V·(tf − tb). A solution exists only for Δq/tf < V ≤ 2Δq/tf.")),
    K("python", ("BBPB 가속도", "BBPB acceleration"),
      ("tb = tf/2인 뱅뱅 궤적의 가속도 a를 구하세요.", "Compute the acceleration a of a bang-bang profile (tb = tf/2)."),
      "4 * (qf - q0) / tf ** 2", "q0, qf, tf = 0.0, 60.0, 2.0", ["q0, qf, tf = 15.0, 105.0, 4.0"],
      ("4Δq/tf²", "4Δq/tf²"),
      ("반 구간 동안 ½·a·(tf/2)² = Δq/2 → a = 4Δq/tf². 마지막 위치가 qf인지 꼭 검산!",
       "Half the time covers half the move: ½·a·(tf/2)² = Δq/2 → a = 4Δq/tf². Always check q(tf) = qf!")),
    K("python", ("한 줄 파싱", "Parse one line"),
      ("line을 float 리스트로 바꾸세요.", "Turn line into a list of floats."),
      "list(map(float, line.split()))", 'line = " 30  45.5 -10\\n"', ['line = "1 2\\t3\\n"'],
      ("split() + map", "split() + map"),
      ("`split()`은 여러 칸 공백·탭·줄바꿈을 한 번에 처리. `map(float, …)`을 list로 감싸야 값이 됩니다.",
       "`split()` handles runs of spaces, tabs and newlines; wrap `map(float, …)` in list to get values.")),
    K("python", ("출력 형식", "Output format"),
      ("x, y를 '소수 3자리 공백 구분' 문자열로 만드세요.", "Format x, y as 'space separated, 3 decimals'."),
      'f"{x:.3f} {y:.3f}"', "x, y = 0.8660254, 0.5", ["x, y = -0.0004, 12.3456"],
      ("f-문자열 :.3f", "f-string :.3f"),
      ("형식이 다르면 계산이 맞아도 0점! `:.3f`로 자리수를 고정하세요.",
       "Wrong format = zero points even with correct math. Pin the decimals with `:.3f`.")),
    K("python", ("int16 리틀엔디언", "int16 little-endian"),
      ("data[4:6]을 부호 있는 리틀엔디언 정수로 읽으세요.", "Read data[4:6] as a signed little-endian integer."),
      'int.from_bytes(data[4:6], "little", signed=True)', 'data = bytes.fromhex("E8030000C8FF1E00")',
      ['data = bytes.fromhex("0000000034121E00")'], ("int.from_bytes", "int.from_bytes"),
      ("C8 FF → 0xFFC8 = −56. `signed=True`를 빼면 65480이 됩니다.",
       "C8 FF → 0xFFC8 = −56. Without `signed=True` you get 65480.")),
    K("python", ("시간 샘플 (tf 포함)", "Time samples (tf included)"),
      ("0부터 tf까지(포함) dt 간격 시간 리스트를 소수 2자리로 반올림해 만드세요.",
       "Build the list of times from 0 to tf inclusive in steps of dt, rounded to 2 decimals."),
      "[round(k * dt, 2) for k in range(round(tf / dt) + 1)]", "tf, dt = 1.0, 0.25", ["tf, dt = 0.6, 0.2"],
      ("정수 k · dt", "integer k · dt"),
      ("`range`/`arange`는 끝을 빼니 +1. 0.2를 계속 더하면 0.6000000000000001처럼 오차가 쌓입니다.",
       "`range`/`arange` exclude the end, hence +1. Repeatedly adding 0.2 drifts to 0.6000000000000001.")),
    K("python", ("PID 출력", "PID output"),
      ("PID 제어 입력 u를 구하세요.", "Compute the PID control input u."),
      "Kp * e + Ki * integ + Kd * (e - e_prev) / dt", "Kp, Ki, Kd, dt = 2.0, 0.5, 0.1, 0.05\ne, e_prev, integ = 0.8, 1.0, 0.09",
      ["Kp, Ki, Kd, dt = 1.0, 1.0, 0.2, 0.1\ne, e_prev, integ = -0.5, -0.2, 0.3"], ("P + I + D", "P + I + D"),
      ("미분항은 (e − e_prev)/dt. dt로 나누는 걸 빼먹으면 D 이득이 20배 차이 납니다(dt = 0.05).",
       "The D term is (e − e_prev)/dt; forgetting /dt changes the D gain 20× at dt = 0.05.")),
    K("python", ("옥타일 휴리스틱", "Octile heuristic"),
      ("8방향 격자에서 (r, c) → (gr, gc) 옥타일 거리를 구하세요.", "Compute the octile distance from (r, c) to (gr, gc) on an 8-connected grid."),
      "abs(r - gr) + abs(c - gc) + (math.sqrt(2) - 2) * min(abs(r - gr), abs(c - gc))",
      "import math\nr, c, gr, gc = 0, 0, 3, 5", ["import math\nr, c, gr, gc = 6, 1, 2, 2"],
      ("dr + dc + (√2−2)·min", "dr + dc + (√2−2)·min"),
      ("대각으로 min(dr, dc)칸, 나머지는 직선. 맨해튼은 8방향에서 과대평가라 A*가 최적을 놓칠 수 있어요.",
       "Go diagonal for min(dr, dc) cells, straight for the rest. Manhattan overestimates on 8-connected grids and breaks A* optimality.")),
    K("cpp", ("FK — 말단 x (C++)", "FK — end-effector x (C++)"),
      ("2링크 말단 x 좌표 표현식을 쓰세요. (d1, d2는 도)", "Write the 2-link end-effector x expression. (d1, d2 are degrees)"),
      "L1 * cos(d1 * M_PI / 180) + L2 * cos((d1 + d2) * M_PI / 180)",
      "double L1 = 1.0, L2 = 0.5;\ndouble d1 = 30, d2 = 45;", ["double L1 = 0.85, L2 = 0.65;\ndouble d1 = 120, d2 = -60;"],
      ("M_PI / 180", "M_PI / 180"),
      ("C++ `cos`도 라디안. `d * M_PI / 180`의 180을 `180.0`으로 써 두면 int 나눗셈 걱정이 없습니다.",
       "C++ `cos` takes radians. Writing `180.0` avoids any integer-division surprise.")),
    K("cpp", ("IK — θ2 (C++)", "IK — θ2 (C++)"),
      ("목표점 (x, y)의 θ2 [라디안, acos 해] 표현식을 쓰세요.", "Write θ2 [rad, acos branch] for target (x, y)."),
      "acos((x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2))",
      "double L1 = 1.0, L2 = 0.5;\ndouble x = 0.9, y = 0.8;", ["double L1 = 1.0, L2 = 0.8;\ndouble x = -0.4, y = 1.1;"],
      ("acos + 코사인 법칙", "acos + law of cosines"),
      ("`acos` 인자가 [−1, 1]을 벗어나면 nan. 도달 판정 후 `std::clamp(D, -1.0, 1.0)`(C++17)으로 감싸면 안전합니다.",
       "`acos` returns nan outside [−1, 1]. After the reachability check, `std::clamp(D, -1.0, 1.0)` (C++17) keeps it safe.")),
    K("cpp", ("CUBIC a3 (C++)", "Cubic a3 (C++)"),
      ("3차 궤적 계수 a3 표현식을 쓰세요. (q0, qf는 int!)", "Write the cubic coefficient a3. (q0 and qf are ints!)"),
      "-2.0 * (qf - q0) / (tf * tf * tf)", "int q0 = 10, qf = 90;\ndouble tf = 4.0;", ["int q0 = -20, qf = 41;\ndouble tf = 3.0;"],
      ("−2Δq/tf³, 2.0으로 시작", "−2Δq/tf³, start with 2.0"),
      ("`-2 * (qf - q0)`는 int지만 tf가 double이라 나눗셈은 double. 그래도 `2.0`으로 써 두는 습관이 안전합니다.",
       "`-2 * (qf - q0)` is an int, but tf is double so the division is fine — still, writing `2.0` is the safe habit.")),
    K("cpp", ("BBPB 가속도 (C++)", "BBPB acceleration (C++)"),
      ("뱅뱅 궤적 가속도 a 표현식을 쓰세요. (모두 int)", "Write the bang-bang acceleration a. (all ints)"),
      "4.0 * (qf - q0) / (tf * tf)", "int q0 = 0, qf = 90, tf = 4;", ["int q0 = 15, qf = 50, tf = 3;"],
      ("4.0으로 시작해서 double 승격", "start with 4.0 to promote to double"),
      ("전부 int면 `4 * 90 / 16`은 22! `4.0`으로 시작해야 22.5가 나옵니다.",
       "All ints: `4 * 90 / 16` is 22! Start with `4.0` to get 22.5.")),
    K("cpp", ("두 점 거리 (C++)", "Distance (C++)"),
      ("(x1, y1)과 (x2, y2) 사이 거리를 구하세요.", "Compute the distance between (x1, y1) and (x2, y2)."),
      "hypot(x2 - x1, y2 - y1)", "double x1 = 0, y1 = 0, x2 = 3, y2 = 4;", ["double x1 = -1.5, y1 = 2, x2 = 2.5, y2 = -1;"],
      ("hypot 또는 sqrt", "hypot or sqrt"),
      ("`std::hypot`은 오버플로 없이 √(dx²+dy²). `pow(x, 2)`보다 `dx*dx`가 빠르고 정확합니다.",
       "`std::hypot` computes √(dx²+dy²) without overflow; `dx*dx` beats `pow(x, 2)`.")),
    K("cpp", ("int16 조립 (C++)", "Assemble int16 (C++)"),
      ("b4(하위), b5(상위) 바이트로 부호 있는 16비트 속도를 만드세요.", "Build the signed 16-bit velocity from b4 (low) and b5 (high)."),
      "(int16_t)(b4 | b5 << 8)", "uint8_t b4 = 0xC8, b5 = 0xFF;", ["uint8_t b4 = 0x34, b5 = 0x12;"],
      ("(int16_t) 캐스팅", "(int16_t) cast"),
      ("`b4 | b5 << 8`은 int라 65480. `int16_t`로 캐스팅해야 −56입니다.",
       "`b4 | b5 << 8` is an int (65480); casting to `int16_t` gives −56.")),
    K("cpp", ("샘플 개수 (C++)", "Sample count (C++)"),
      ("0~tf(포함) dt 간격 샘플 개수를 int로 구하세요.", "Compute the number of samples from 0 to tf inclusive as an int."),
      "(int)lround(tf / dt) + 1", "double tf = 1.0, dt = 0.1;", ["double tf = 0.6, dt = 0.2;"],
      ("lround + 1", "lround + 1"),
      ("`(int)(0.6 / 0.2)`는 2.9999…가 잘려 2! `lround`로 반올림 후 +1.",
       "`(int)(0.6 / 0.2)` truncates 2.9999… to 2! Round with `lround`, then +1.")),
]


for _p in QUIZ + KATA:
    _p["id"] = "x" + hashlib.sha1(f"exam|{_p['kind']}|{_p['lang']}|{_p['title'][0]}".encode()).hexdigest()[:9]
    _p["source"] = "bank"
    _p["title_ko"] = _p["title"][0]
