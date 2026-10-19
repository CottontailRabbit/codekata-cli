#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    double Kp, Ki, Kd, sp, tau, dt, steps;
    in >> Kp >> Ki >> Kd >> sp >> tau >> dt >> steps;
    double x = 0, integ = 0, e_prev = 0;
    for (int k = 0; k < (int)steps; ++k) {
        double e = sp - x;
        integ += e * dt;
        double deriv = k == 0 ? 0.0 : (e - e_prev) / dt;
        double u = Kp * e + Ki * integ + Kd * deriv;
        std::fprintf(out, "%.2f %.4f %.4f\n", k * dt, x, u);
        x += dt * (-x + u) / tau;
        e_prev = e;
    }
    std::fclose(out);
}
