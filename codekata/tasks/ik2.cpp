#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    double L1, L2, x, y;
    in >> L1 >> L2;
    while (in >> x >> y) {
        double D = (x * x + y * y - L1 * L1 - L2 * L2) / (2 * L1 * L2);
        if (std::fabs(D) > 1) {
            std::fprintf(out, "UNREACHABLE\n");
            continue;
        }
        double t2 = std::acos(D);
        double k1 = L1 + L2 * std::cos(t2), k2 = L2 * std::sin(t2);
        double t1 = std::atan2(y, x) - std::atan2(k2, k1);
        double d1 = std::fmod(t1 * 180.0 / M_PI + 180.0, 360.0);
        if (d1 < 0) d1 += 360.0;               // fmod keeps the sign, Python % does not
        std::fprintf(out, "%.3f %.3f\n", d1 - 180.0, t2 * 180.0 / M_PI);
    }
    std::fclose(out);
}
