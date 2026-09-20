// Numerical parity reference, not the full fly engine.
use std::{env,fs};
fn run(p:&str)->Result<(),String>{
 let raw=fs::read_to_string(p).map_err(|e|e.to_string())?;
 let mut words=raw.split_whitespace();
 let mut next=||->Result<f64,String>{words.next().ok_or("truncated fixture".to_string())?.parse::<f64>().map_err(|e|e.to_string())};
 let steps=next()? as i64;let offset=next()? as i64;
 if !(0..=10000).contains(&steps){return Err("bad step count".into())}
 let mut w=[[0.;42];42];let mut drive=[0.;42];let mut state=[0.;42];let mut dyn12=[0.;12];
 for row in &mut w{for v in row{*v=next()?}}
 for v in &mut drive{*v=next()?}for v in &mut state{*v=next()?}for v in &mut dyn12{*v=next()?}
 for t in 0..steps{
  let mut new=[0.;42];
  for i in 0..42{let mut v=0.;for j in 0..42{v+=w[i][j]*state[j]}new[i]=(.61*state[i]+2.15*v+drive[i]).tanh()}
  state=new;let mut d=[0.;12];
  for i in 0..12{let mut v=0.;let mut n=0.;let mut j=i;while j<42{v+=state[j];n+=1.;j+=12}
   d[i]=(.86*dyn12[i]+.14*v/n+.015*((offset+t+1) as f64*(i+1) as f64*.17320508075688773).sin()).tanh()}
  dyn12=d;
 }
 print!("{{\"state\":[");
 for i in 0..42{if i>0{print!(",")}print!("{:.17}",state[i])}
 print!("],\"dyn12\":[");
 for i in 0..12{if i>0{print!(",")}print!("{:.17}",dyn12[i])}
 println!("]}}");Ok(())
}
fn main(){let a:Vec<String>=env::args().collect();if a.len()!=2{eprintln!("usage: neural_step <fixture>");std::process::exit(2)}
 if let Err(e)=run(&a[1]){eprintln!("{e}");std::process::exit(2)}
}