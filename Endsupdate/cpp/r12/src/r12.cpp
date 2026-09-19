#include "r12.hpp"
#include "sha256.hpp"
#include <cmath>
#include <fstream>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace zeref::r12 {
namespace {
std::string slurp(const std::string& path){std::ifstream in(path);if(!in)throw std::runtime_error("cannot open file: "+path);std::ostringstream s;s<<in.rdbuf();return s.str();}
bool is_hex64(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
}
const std::vector<std::string>& r12_names(){static const std::vector<std::string> names={"source_integrity","temporal_novelty","measurement_confidence","distribution_energy","cross_condition_agreement","distribution_entropy","surprise","memory_relevance","retention_pressure","contradiction_pressure","adaptation_stability","reality_coupling"};return names;}

StateReport parse_state_file(const std::string& path){
    StateReport r;
    try{
        const auto text=slurp(path);
        std::smatch m;
        std::regex state_re("\\\"state_sha256\\\"\\s*:\\s*\\\"([0-9a-f]{64})\\\"");
        if(std::regex_search(text,m,state_re))r.state_sha256=m[1].str();else r.errors.push_back("missing state_sha256");
        for(const auto& name:r12_names()){
            std::regex re("\\\""+name+"\\\"\\s*:\\s*(-?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?)");
            if(!std::regex_search(text,m,re)){r.errors.push_back("missing vector value: "+name);continue;}
            double v=std::stod(m[1].str());
            if(!std::isfinite(v)||v<0.0||v>1.0)r.errors.push_back("out of range vector value: "+name);else r.vector[name]=v;
        }
        if(r.vector.size()!=12)r.errors.push_back("R12 vector must contain 12 valid values");
    }catch(const std::exception& e){r.errors.push_back(e.what());}
    r.ok=r.errors.empty();return r;
}

LedgerReport verify_ledger_file(const std::string& path,const std::string& expected_file_sha256){
    LedgerReport r;
    try{
        r.file_sha256=sha256_file(path);
        if(!expected_file_sha256.empty()&&r.file_sha256!=expected_file_sha256)r.errors.push_back("ledger file SHA-256 mismatch");
        std::ifstream in(path);if(!in)throw std::runtime_error("cannot open ledger: "+path);
        std::string line,last;while(std::getline(in,line)){if(line.find_first_not_of(" \t\r\n")==std::string::npos)continue;++r.event_count;last=line;}
        if(r.event_count==0)r.errors.push_back("ledger has no events");
        std::smatch m;std::regex re("\\\"event_sha256\\\"\\s*:\\s*\\\"([0-9a-f]{64})\\\"");
        if(!last.empty()&&std::regex_search(last,m,re))r.tip_sha256=m[1].str();else r.errors.push_back("cannot extract ledger tip");
        if(!r.tip_sha256.empty()&&!is_hex64(r.tip_sha256))r.errors.push_back("invalid ledger tip");
    }catch(const std::exception& e){r.errors.push_back(e.what());}
    r.ok=r.errors.empty();return r;
}
}
