import heapq

with open("input.txt", encoding="utf-8") as f:
    rows = [list(map(int, line.split())) for line in f if line.strip()]

N, M, S, T = rows[0]
adj = [[] for _ in range(N)]
for u, v, w in rows[1:1 + M]:
    adj[u].append((v, w))
    adj[v].append((u, w))                # undirected

INF = float("inf")
dist, prev = [INF] * N, [-1] * N
dist[S] = 0
pq = [(0, S)]
while pq:
    d, u = heapq.heappop(pq)
    if d > dist[u]:
        continue
    for v, w in adj[u]:
        if d + w < dist[v]:
            dist[v], prev[v] = d + w, u
            heapq.heappush(pq, (dist[v], v))

with open("output.txt", "w", encoding="utf-8") as f:
    if dist[T] == INF:
        f.write("DIST -1\nPATH NONE\n")
    else:
        path, u = [], T
        while u != -1:
            path.append(u)
            u = prev[u]
        f.write(f"DIST {dist[T]}\nPATH {' '.join(map(str, path[::-1]))}\n")
