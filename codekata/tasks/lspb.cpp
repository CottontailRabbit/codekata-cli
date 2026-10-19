#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    double q0, qf, tf, V, dt;
    in >> q0 >> qf >> tf >> V >> dt;
    double tb = (q0 - qf + V * tf) / V;
    double a = V / tb;
    long n = std::lround(tf / dt);
    std::fprintf(out, "TB %.3f\n", tb);
    for (long k = 0; k <= n; ++k) {
        double t = k * dt, q, qd;
        if (t <= tb) {
            q = q0 + a / 2 * t * t;
            qd = a * t;
        } else if (t <= tf - tb) {
            q = (qf + q0 - V * tf) / 2 + V * t;
            qd = V;
        } else {
            q = qf - a / 2 * tf * tf + a * tf * t - a / 2 * t * t;
            qd = a * (tf - t);
        }
        std::fprintf(out, "%.2f %.3f %.3f\n", t, q, qd);
    }
    std::fclose(out);
}
