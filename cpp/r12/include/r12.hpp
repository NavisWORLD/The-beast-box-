#pragma once
#include <map>
#include <string>
#include <vector>

namespace zeref::r12 {
struct StateReport {
    bool ok = false;
    std::string state_sha256;
    std::map<std::string,double> vector;
    std::vector<std::string> errors;
};

struct LedgerReport {
    bool ok = false;
    std::string file_sha256;
    std::string tip_sha256;
    std::size_t event_count = 0;
    std::vector<std::string> errors;
};

StateReport parse_state_file(const std::string& path);
LedgerReport verify_ledger_file(const std::string& path, const std::string& expected_file_sha256);
const std::vector<std::string>& r12_names();
}
