#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace zeref::r12 {
std::string sha256_bytes(const std::vector<std::uint8_t>& data);
std::string sha256_text(const std::string& text);
std::string sha256_file(const std::string& path);
}
