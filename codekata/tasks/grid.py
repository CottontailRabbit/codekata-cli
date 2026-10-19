import heapq
import math

with open("input.txt", encoding="utf-8") as f:
    rows = [line.split() for line in f if line.strip()]

R, C = map(int, rows[0])
grid = [list(map(int, r)) for r in rows[1:1 + R]]       # grid[row][col], 1 = wall
sr, sc, gr, gc = map(int, rows[1 + R])

def h(r, c):                                            # octile distance (admissible)
    dr, dc = abs(r - gr), abs(c - gc)
    return (dr + dc) + (math.sqrt(2) - 2) * min(dr, dc)

INF = float("inf")
g = [[INF] * C for _ in range(R)]
g[sr][sc] = 0.0
pq = [(h(sr, sc), 0.0, sr, sc)]
best = -1.0
while pq:
    f_, d, r, c = heapq.heappop(pq)
    if d > g[r][c]:
        continue
    if (r, c) == (gr, gc):
        best = d
        break
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            nr, nc = r + dr, c + dc
            if (dr, dc) == (0, 0) or not (0 <= nr < R and 0 <= nc < C) or grid[nr][nc]:
                continue
            if dr and dc and (grid[r][nc] or grid[nr][c]):  # no corner cutting
                continue
            nd = d + (math.sqrt(2) if dr and dc else 1.0)
            if nd < g[nr][nc]:
                g[nr][nc] = nd
                heapq.heappush(pq, (nd + h(nr, nc), nd, nr, nc))

with open("output.txt", "w", encoding="utf-8") as f:
    f.write("LENGTH -1\n" if best < 0 else f"LENGTH {best:.3f}\n")
