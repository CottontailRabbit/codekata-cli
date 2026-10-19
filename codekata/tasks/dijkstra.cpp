#include <algorithm>
#include <climits>
#include <fstream>
#include <functional>
#include <queue>
#include <vector>

int main() {
    std::ifstream in("input.txt");
    std::ofstream out("output.txt");
    int N, M, S, T;
    in >> N >> M >> S >> T;
    std::vector<std::vector<std::pair<int, int>>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v, w;
        in >> u >> v >> w;
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }
    std::vector<long long> dist(N, LLONG_MAX);
    std::vector<int> prev(N, -1);
    // min-heap: priority_queue is a max-heap unless you pass std::greater
    std::priority_queue<std::pair<long long, int>, std::vector<std::pair<long long, int>>,
                        std::greater<>> pq;
    dist[S] = 0;
    pq.push({0, S});
    while (!pq.empty()) {
        auto [d, u] = pq.top();
        pq.pop();
        if (d > dist[u]) continue;
        for (auto [v, w] : adj[u]) {
            if (d + w < dist[v]) {
                dist[v] = d + w;
                prev[v] = u;
                pq.push({dist[v], v});
            }
        }
    }
    if (dist[T] == LLONG_MAX) {
        out << "DIST -1\nPATH NONE\n";
        return 0;
    }
    std::vector<int> path;
    for (int u = T; u != -1; u = prev[u]) path.push_back(u);
    std::reverse(path.begin(), path.end());
    out << "DIST " << dist[T] << "\nPATH";
    for (int u : path) out << ' ' << u;
    out << '\n';
}
