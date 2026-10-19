#include <algorithm>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    std::string line;
    std::getline(in, line);                     // skip header
    std::fprintf(out, "time,max_temp,fan\n");
    bool fan = false;
    int on_count = 0;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string time, cell;
        std::getline(ss, time, ',');
        double tmax = -1e9;
        while (std::getline(ss, cell, ',')) tmax = std::max(tmax, std::stod(cell));
        if (!fan && tmax >= 60.0) {
            fan = true;
            ++on_count;
        } else if (fan && tmax <= 55.0) {
            fan = false;
        }
        std::fprintf(out, "%s,%.1f,%s\n", time.c_str(), tmax, fan ? "ON" : "OFF");
    }
    std::fprintf(out, "ON_COUNT %d\n", on_count);
    std::fclose(out);
}
