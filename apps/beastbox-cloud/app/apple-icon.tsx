import {ImageResponse} from 'next/og';
export const size={width:180,height:180};
export const contentType='image/png';
export default function AppleIcon(){
  return new ImageResponse(
    <div style={{width:180,height:180,display:'flex',alignItems:'center',justifyContent:'center',borderRadius:40,background:'radial-gradient(circle at 45% 32%,#57429f,#0b122c 83%)',position:'relative'}}>
      <div style={{position:'absolute',top:12,left:77,color:'#ffe3a1',fontSize:35}}>✦</div>
      <div style={{width:142,height:142,display:'flex',alignItems:'center',justifyContent:'center',borderRadius:72,border:'7px solid #b2eaff',background:'radial-gradient(circle at 42% 34%,#ffdcf9,#8a64d8 48%,#281a72 95%)',boxShadow:'0 0 22px #ae87fd'}}>
        <div style={{display:'flex',flexDirection:'column',alignItems:'center',marginTop:14}}>
          <div style={{display:'flex',gap:23}}><span style={{width:24,height:34,background:'#161044',borderRadius:20,border:'3px solid #b1e6ff'}}/><span style={{width:24,height:34,background:'#161044',borderRadius:20,border:'3px solid #b1e6ff'}}/></div>
          <div style={{width:29,height:12,marginTop:10,borderRadius:'0 0 25px 25px',background:'#572247'}}/>
        </div>
      </div>
    </div>,size);
}