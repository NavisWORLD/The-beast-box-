#include "r12.hpp"
#include <iostream>
#include <string>

int main(int argc,char** argv){
    if(argc<2||std::string(argv[1])!="status"){
        std::cerr<<"usage: zeref-r12-native status --ledger FILE --state FILE --expected-ledger-sha256 HEX\n";return 2;
    }
    std::string ledger,state,expected;
    for(int i=2;i<argc;++i){std::string a=argv[i];if((a=="--ledger"||a=="--state"||a=="--expected-ledger-sha256")&&i+1<argc){std::string v=argv[++i];if(a=="--ledger")ledger=v;else if(a=="--state")state=v;else expected=v;}else{std::cerr<<"unknown/incomplete argument: "<<a<<"\n";return 2;}}
    if(ledger.empty()||state.empty()||expected.empty()){std::cerr<<"ledger, state and expected digest are required\n";return 2;}
    auto l=zeref::r12::verify_ledger_file(ledger,expected);auto s=zeref::r12::parse_state_file(state);
    std::cout<<"{\"ok\":"<<(l.ok&&s.ok?"true":"false")<<",\"event_count\":"<<l.event_count<<",\"ledger_sha256\":\""<<l.file_sha256<<"\",\"ledger_tip_sha256\":\""<<l.tip_sha256<<"\",\"state_sha256\":\""<<s.state_sha256<<"\",\"vector_count\":"<<s.vector.size()<<"}\n";
    for(const auto& e:l.errors)std::cerr<<"ledger: "<<e<<"\n";for(const auto& e:s.errors)std::cerr<<"state: "<<e<<"\n";
    return l.ok&&s.ok?0:1;
}
