#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    double q0, qf, tf, dt;
    in >> q0 >> qf >> tf >> dt;
    double a = 4 * (qf - q0) / (tf * tf);
    long n = std::lround(tf / dt);
    for (long k = 0; k <= n; ++k) {
        double t = k * dt, q, qd, qdd;
        if (t <= tf / 2) {
            q = q0 + a / 2 * t * t;
            qd = a * t;
            qdd = a;
        } else {
            q = qf - a / 2 * (tf - t) * (tf - t);
            qd = a * (tf - t);
            qdd = -a;
        }
        std::fprintf(out, "%.2f %.3f %.3f %.3f\n", t, q, qd, qdd);
    }
    std::fclose(out);
}
