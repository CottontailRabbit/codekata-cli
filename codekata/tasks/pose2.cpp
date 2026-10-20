#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    const double R = M_PI / 180.0;
    double L1, L2, t1, t2, d1, d2;
    in >> L1 >> L2 >> t1 >> t2;
    std::fprintf(out, "step,theta1,theta2,Bx,By,Cx,Cy\n");
    for (int step = 0;; ++step) {
        if (step > 0) {
            if (!(in >> d1 >> d2)) break;
            t1 += d1;
            t2 += d2;
        }
        double bx = L1 * std::cos(t1 * R), by = L1 * std::sin(t1 * R);
        double cx = bx + L2 * std::cos((t1 + t2) * R), cy = by + L2 * std::sin((t1 + t2) * R);
        std::fprintf(out, "%d,%.1f,%.1f,%.3f,%.3f,%.3f,%.3f\n", step, t1, t2, bx, by, cx, cy);
    }
    std::fclose(out);
}
