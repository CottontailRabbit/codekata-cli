#include <cmath>
#include <cstdio>
#include <fstream>

double wrap(double d) {                          // [-180, 180)
    double r = std::fmod(d + 180.0, 360.0);
    if (r < 0) r += 360.0;
    return r - 180.0;
}

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    const double R = M_PI / 180.0;
    double L1, L2, L3, x, y, phi;
    in >> L1 >> L2 >> L3;
    while (in >> x >> y >> phi) {
        double wx = x - L3 * std::cos(phi * R), wy = y - L3 * std::sin(phi * R);
        double D = (wx * wx + wy * wy - L1 * L1 - L2 * L2) / (2 * L1 * L2);
        if (std::fabs(D) > 1) {
            std::fprintf(out, "UNREACHABLE\n");
            continue;
        }
        double t2 = std::acos(D);
        double k1 = L1 + L2 * std::cos(t2), k2 = L2 * std::sin(t2);
        double t1 = std::atan2(wy, wx) - std::atan2(k2, k1);
        double d1 = wrap(t1 / R), d2 = t2 / R;
        std::fprintf(out, "%.3f %.3f %.3f\n", d1, d2, wrap(phi - d1 - d2));
    }
    std::fclose(out);
}
