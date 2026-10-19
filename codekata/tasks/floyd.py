with open("input.txt", encoding="utf-8") as f:
    rows = [list(map(int, line.split())) for line in f if line.strip()]

N, M = rows[0]
INF = float("inf")
D = [[0 if i == j else INF for j in range(N)] for i in range(N)]
for u, v, w in rows[1:1 + M]:
    D[u][v] = min(D[u][v], w)                 # directed edge u -> v

for k in range(N):                           # k must be the OUTER loop
    for i in range(N):
        for j in range(N):
            if D[i][k] + D[k][j] < D[i][j]:
                D[i][j] = D[i][k] + D[k][j]

with open("output.txt", "w", encoding="utf-8") as f:
    for row in D:
        f.write(" ".join("INF" if d == INF else str(d) for d in row) + "\n")
