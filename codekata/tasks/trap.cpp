#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    std::fprintf(out, "set,t,x,v,a\n");
    double x0, xf, vmax, acc, dt;
    int s = 0;
    while (in >> x0 >> xf >> vmax >> acc >> dt) {
        ++s;
        double ta = vmax / acc;
        double T = (xf - x0) / vmax + ta;
        long ka = std::lround(ta / dt), kd = std::lround((T - ta) / dt), n = std::lround(T / dt);
        for (long k = 0; k <= n; ++k) {
            double t = k * dt, a, v, x;
            if (k < ka) {
                a = acc;
                v = acc * t;
                x = x0 + 0.5 * acc * t * t;
            } else if (k < kd) {
                a = 0.0;
                v = vmax;
                x = x0 + 0.5 * acc * ta * ta + vmax * (t - ta);
            } else {
                double r = T - t;
                a = -acc;
                v = acc * r;
                x = xf - 0.5 * acc * r * r;
            }
            std::fprintf(out, "%d,%.1f,%.3f,%.3f,%.3f\n", s, t, x, v, a);
        }
    }
    std::fclose(out);
}
