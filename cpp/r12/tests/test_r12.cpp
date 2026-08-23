#include "r12.hpp"
#include "sha256.hpp"
#include <cassert>
#include <fstream>
#include <iostream>

int main(){
    using namespace zeref::r12;
    assert(sha256_text("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    const std::string state="r12-native-test-state.json";
    {std::ofstream o(state);o<<"{\"state_sha256\":\""<<std::string(64,'a')<<"\",\"vector\":{";
     const auto& names=r12_names();for(std::size_t i=0;i<names.size();++i){if(i)o<<",";o<<"\""<<names[i]<<"\":"<<(i==0?1.0:0.5);}o<<"}}";}
    auto s=parse_state_file(state);assert(s.ok);assert(s.vector.size()==12);
    const std::string ledger="r12-native-test-ledger.jsonl";
    const std::string tip=std::string(64,'b');
    {std::ofstream o(ledger);o<<"{\"event_sha256\":\""<<tip<<"\"}\n";}
    auto digest=sha256_file(ledger);auto l=verify_ledger_file(ledger,digest);assert(l.ok);assert(l.event_count==1);assert(l.tip_sha256==tip);
    auto bad=verify_ledger_file(ledger,std::string(64,'0'));assert(!bad.ok);
    std::remove(state.c_str());std::remove(ledger.c_str());
    std::cout<<"R12 native tests passed\n";return 0;
}
