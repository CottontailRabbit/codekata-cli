#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    double q0, qf, tf, dt;
    in >> q0 >> qf >> tf >> dt;
    double a2 = 3 * (qf - q0) / (tf * tf);
    double a3 = -2 * (qf - q0) / (tf * tf * tf);
    long n = std::lround(tf / dt);
    for (long k = 0; k <= n; ++k) {             // integer counter: no float drift at t = tf
        double t = k * dt;
        double q = q0 + a2 * t * t + a3 * t * t * t;
        double qd = 2 * a2 * t + 3 * a3 * t * t;
        double qdd = 2 * a2 + 6 * a3 * t;
        std::fprintf(out, "%.2f %.3f %.3f %.3f\n", t, q, qd, qdd);
    }
    std::fclose(out);
}
