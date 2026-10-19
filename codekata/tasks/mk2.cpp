#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    const double R = M_PI / 180.0;
    double L1, L2, a, b, c, d;
    in >> L1 >> L2;
    while (in >> a >> b >> c >> d) {
        double t1 = a * R, t2 = b * R, w1 = c * R, w2 = d * R;
        double vx = -L1 * std::sin(t1) * w1 - L2 * std::sin(t1 + t2) * (w1 + w2);
        double vy = L1 * std::cos(t1) * w1 + L2 * std::cos(t1 + t2) * (w1 + w2);
        std::fprintf(out, "%.4f %.4f\n", vx, vy);
    }
    std::fclose(out);
}
