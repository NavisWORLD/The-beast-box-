// COSMIC FRUIT FLY: numerical research parity adapter (not complete game engine).
// SPDX-License-Identifier: MIT; original independent reference implementation.
use std::env;
use std::fs;
fn run(path: &str) -> Result<(), String> {
    let data=fs::read_to_string(path).map_err(|e|format!("fixture: {e}"))?;
    let mut words=data.split_whitespace();
    let mut next=|| -> Result<f64,String> {
        words.next().ok_or("truncated fixture".to_owned())?.parse::<f64>().map_err(|e|format!("numeric fixture: {e}"))
    };
    let steps=next()? as i64;
    let offset=next()? as i64;
    if !(0..=10000).contains(&steps) {return Err("invalid steps".into());}
    let mut w=[[0_f64;42];42];let mut drive=[0_f64;42];let mut state=[0_f64;42];let mut dyn12=[0_f64;12];
    for row in &mut w { for v in row.iter_mut(){*v=next()?;} }
    for v in &mut drive { *v=next()?; }
    for v in &mut state { *v=next()?; }
    for v in &mut dyn12 { *v=next()?; }
    for tick in 0..steps {
        let mut updated=[0_f64;42];
        for i in 0..42 {
            let mut propagation=0_f64;
            for j in 0..42 {propagation+=w[i][j]*state[j];}
            updated[i]=(.61*state[i]+2.15*propagation+drive[i]).tanh();
        }
        state=updated;
        let mut d=[0_f64;12];
        for i in 0..12 {
            let mut sum=0_f64;let mut count=0_f64;let mut j=i;
            while j<42 {sum+=state[j];count+=1.;j+=12;}
            let forcing=.015*((offset+tick+1) as f64*(i+1) as f64*0.17320508075688773).sin();
            d[i]=(.86*dyn12[i]+.14*(sum/count)+forcing).tanh();
        }
        dyn12=d;
    }
    print!("{{\"state\":[");
    for i in 0..42 {if i>0 {print!(",");} print!("{:.17}",state[i]);}
    print!("],\"dyn12\":[");
    for i in 0..12 {if i>0 {print!(",");} print!("{:.17}",dyn12[i]);}
    println!("]}}");
    Ok(())
}
fn main(){let args:Vec<String>=env::args().collect();if args.len()!=2{eprintln!("usage: cosmic_fruit_fly_neural_step <fixture.txt>");std::process::exit(2);}
 if let Err(e)=run(&args[1]){eprintln!("{e}");std::process::exit(2)} }
