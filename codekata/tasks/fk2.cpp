#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    double L1, L2, d1, d2;
    in >> L1 >> L2;
    while (in >> d1 >> d2) {
        double t1 = d1 * M_PI / 180.0, t2 = d2 * M_PI / 180.0;
        double x1 = L1 * std::cos(t1), y1 = L1 * std::sin(t1);
        double x2 = x1 + L2 * std::cos(t1 + t2), y2 = y1 + L2 * std::sin(t1 + t2);
        std::fprintf(out, "%.3f %.3f %.3f %.3f %.3f %.3f\n", 0.0, 0.0, x1, y1, x2, y2);
    }
    std::fclose(out);
}
