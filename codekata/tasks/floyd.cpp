#include <algorithm>
#include <fstream>
#include <vector>

int main() {
    std::ifstream in("input.txt");
    std::ofstream out("output.txt");
    int N, M;
    in >> N >> M;
    const long long INF = 1LL << 60;
    std::vector<std::vector<long long>> D(N, std::vector<long long>(N, INF));
    for (int i = 0; i < N; ++i) D[i][i] = 0;
    for (int e = 0; e < M; ++e) {
        int u, v;
        long long w;
        in >> u >> v >> w;
        D[u][v] = std::min(D[u][v], w);
    }
    for (int k = 0; k < N; ++k)
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < N; ++j)
                if (D[i][k] < INF && D[k][j] < INF && D[i][k] + D[k][j] < D[i][j])
                    D[i][j] = D[i][k] + D[k][j];
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (j) out << ' ';
            if (D[i][j] >= INF) out << "INF";
            else out << D[i][j];
        }
        out << '\n';
    }
}
