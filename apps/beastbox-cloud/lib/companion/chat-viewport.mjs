/** Visual viewport geometry, including Safari keyboard resize and pan. */
export function chatViewport(layoutHeight,viewport){
 const layout=Number.isFinite(layoutHeight)&&layoutHeight>0?layoutHeight:720;
 const height=Number.isFinite(viewport?.height)&&viewport.height>0?viewport.height:layout;
 const offset=Number.isFinite(viewport?.offsetTop)&&viewport.offsetTop>=0?viewport.offsetTop:0;
 return {height:Math.round(height),bottom:Math.max(0,Math.round(layout-height-offset))};
}
