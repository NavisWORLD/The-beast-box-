// 42-node software numerical reference; not a biological fly or complete game.
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
constexpr int N=42,D=12;
int main(int argc,char**argv){
 if(argc!=2)return 2;
 std::ifstream f(argv[1]);if(!f)return 2;
 int steps=0,offset=0;f>>steps>>offset;if(steps<0||steps>10000)return 2;
 std::array<std::array<double,N>,N>w{};
 std::array<double,N>drive{},state{};
 std::array<double,D>dyn{};
 for(auto &r:w)for(auto &x:r)f>>x;
 for(auto &x:drive)f>>x;
 for(auto &x:state)f>>x;
 for(auto &x:dyn)f>>x;
 if(!f)return 2;
 for(int t=0;t<steps;t++){
  std::array<double,N>updated{};
  for(int i=0;i<N;i++){
   double v=0;for(int j=0;j<N;j++)v+=w[i][j]*state[j];
   updated[i]=std::tanh(.61*state[i]+2.15*v+drive[i]);
  }
  state=updated;
  std::array<double,D>nd{};
  for(int i=0;i<D;i++){
   double v=0;int n=0;for(int j=i;j<N;j+=D){v+=state[j];n++;}
   nd[i]=std::tanh(.86*dyn[i]+.14*v/n+.015*std::sin((offset+t+1)*(i+1)*.17320508075688773));
  }
  dyn=nd;
 }
 std::cout<<std::setprecision(17)<<"{\"state\":[";
 for(int i=0;i<N;i++)std::cout<<(i?",":"")<<state[i];
 std::cout<<"],\"dyn12\":[";
 for(int i=0;i<D;i++)std::cout<<(i?",":"")<<dyn[i];
 std::cout<<"]}\n";
}