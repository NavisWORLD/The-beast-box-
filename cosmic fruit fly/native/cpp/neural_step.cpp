// COSMIC FRUIT FLY: numerical research parity adapter (not complete game engine).
// SPDX-License-Identifier: MIT; original independent reference implementation.
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
constexpr size_t N=42, D=12;
using State = std::array<double,N>;
using Dyn = std::array<double,D>;
int main(int argc,char **argv) {
  if(argc!=2) {std::cerr<<"usage: neural_step <fixture.txt>\n";return 2;}
  std::ifstream in(argv[1]); if(!in){std::cerr<<"missing fixture\n";return 2;}
  int count=0,offset=0; in>>count>>offset;
  if(count<0 || count>10000) {std::cerr<<"invalid step count\n";return 2;}
  std::array<State,N> W{}; State stimulus{},state{}; Dyn dyn{};
  for(auto &row:W)for(double &v:row)in>>v;
  for(double &v:stimulus)in>>v;
  for(double &v:state)in>>v;
  for(double &v:dyn)in>>v;
  if(!in) {std::cerr<<"invalid fixture shape\n";return 2;}
  for(int tick=0;tick<count;tick++) {
    State next{};
    for(size_t i=0;i<N;i++) {
      double propagation=0.;for(size_t j=0;j<N;j++) propagation+=W[i][j]*state[j];
      next[i]=std::tanh(.61*state[i]+2.15*propagation+stimulus[i]);
    }
    state=next;
    Dyn updated{};
    for(size_t i=0;i<D;i++) {
      double sum=0.;int n=0;for(size_t j=i;j<N;j+=D){sum+=state[j];n++;}
      const double u=sum/n;
      const double forcing=.015*std::sin((offset+tick+1)*(i+1)*0.17320508075688773);
      updated[i]=std::tanh(.86*dyn[i]+.14*u+forcing);
    }
    dyn=updated;
  }
  std::cout<<std::setprecision(17)<<"{\"state\":[";
  for(size_t i=0;i<N;i++)std::cout<<(i?",":"")<<state[i];
  std::cout<<"],\"dyn12\":[";
  for(size_t i=0;i<D;i++)std::cout<<(i?",":"")<<dyn[i];
  std::cout<<"]}\n";
}
