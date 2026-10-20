#include <cmath>
#include <cstdio>
#include <fstream>
#include <functional>
#include <queue>
#include <tuple>
#include <vector>

int main() {
    std::ifstream in("input.txt");
    int R, C;
    in >> R >> C;
    std::vector<std::vector<int>> grid(R, std::vector<int>(C));
    for (auto& row : grid)
        for (auto& cell : row) in >> cell;
    int sr, sc, gr, gc;
    in >> sr >> sc >> gr >> gc;
    const double SQ2 = std::sqrt(2.0);
    auto h = [&](int r, int c) {
        int dr = std::abs(r - gr), dc = std::abs(c - gc);
        return (dr + dc) + (SQ2 - 2) * std::min(dr, dc);
    };
    std::vector<std::vector<double>> g(R, std::vector<double>(C, INFINITY));
    using Node = std::tuple<double, double, int, int>;
    std::priority_queue<Node, std::vector<Node>, std::greater<>> pq;
    g[sr][sc] = 0;
    pq.push({h(sr, sc), 0.0, sr, sc});
    double best = -1;
    while (!pq.empty()) {
        auto [f, d, r, c] = pq.top();
        pq.pop();
        if (d > g[r][c]) continue;
        if (r == gr && c == gc) {
            best = d;
            break;
        }
        for (int dr = -1; dr <= 1; ++dr)
            for (int dc = -1; dc <= 1; ++dc) {
                int nr = r + dr, nc = c + dc;
                if (!dr && !dc) continue;
                if (nr < 0 || nr >= R || nc < 0 || nc >= C || grid[nr][nc]) continue;
                if (dr && dc && (grid[r][nc] || grid[nr][c])) continue;
                double nd = d + (dr && dc ? SQ2 : 1.0);
                if (nd < g[nr][nc]) {
                    g[nr][nc] = nd;
                    pq.push({nd + h(nr, nc), nd, nr, nc});
                }
            }
    }
    FILE* out = std::fopen("output.txt", "w");
    if (best < 0) std::fprintf(out, "LENGTH -1\n");
    else std::fprintf(out, "LENGTH %.3f\n", best);
    std::fclose(out);
}
