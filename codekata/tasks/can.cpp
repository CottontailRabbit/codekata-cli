#include <cstdint>
#include <cstdio>
#include <fstream>
#include <string>

int main() {
    std::ifstream in("input.txt");
    FILE* out = std::fopen("output.txt", "w");
    std::fprintf(out, "node,position_deg,velocity_rpm,temp_c,fault\n");
    std::string id;
    int dlc;
    while (in >> id >> dlc) {
        uint8_t b[8] = {0};
        for (int i = 0; i < dlc; ++i) {
            std::string h;
            in >> h;
            b[i] = (uint8_t)std::stoi(h, nullptr, 16);
        }
        int node = std::stoi(id, nullptr, 16) - 0x180;
        int32_t pos = (int32_t)((uint32_t)b[0] | (uint32_t)b[1] << 8 | (uint32_t)b[2] << 16 | (uint32_t)b[3] << 24);
        int16_t vel = (int16_t)(b[4] | b[5] << 8);
        std::fprintf(out, "%d,%.2f,%d,%d,%d\n", node, pos * 0.01, vel, b[6], b[7] & 1);
    }
    std::fclose(out);
}
