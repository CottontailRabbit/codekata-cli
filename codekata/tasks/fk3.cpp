#include <cmath>
#include <cstdio>
#include <fstream>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    double L[3], t[3];
    in >> L[0] >> L[1] >> L[2];
    while (in >> t[0] >> t[1] >> t[2]) {
        double x = 0, y = 0, phi = 0;
        for (int i = 0; i < 3; ++i) {
            phi += t[i];
            x += L[i] * std::cos(phi * M_PI / 180.0);
            y += L[i] * std::sin(phi * M_PI / 180.0);
            std::fprintf(out, "%.3f %.3f ", x, y);
        }
        std::fprintf(out, "%.1f\n", phi);
    }
    std::fclose(out);
}
