import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="표면장력 게임", page_icon="💧", layout="wide")

GAME_HTML = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-user-select: none; user-select: none; }
  html, body { height: 100%; font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  #wrap { position: relative; width: 100%; max-width: 1024px; margin: 0 auto; aspect-ratio: 16/9;
          border-radius: 18px; overflow: hidden; touch-action: none; cursor: pointer;
          background: linear-gradient(135deg,#f3efe8 0%,#efe9df 45%,#e9e2d6 100%); }
  canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
  .pill { position: absolute; display: flex; align-items: center; gap: 8px;
          background: rgba(255,255,255,0.55); -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px);
          border: 1px solid rgba(255,255,255,0.8); border-radius: 999px;
          padding: 8px 16px; color: #4a4a4a; font-weight: 700; }
  #score { top: 18px; left: 18px; flex-direction: column; align-items: flex-start; gap: 0; padding: 8px 18px; }
  #score .k { font-size: 11px; opacity: .7; }
  #score .v { font-size: 22px; line-height: 1; }
  #timer { top: 18px; left: 50%; transform: translateX(-50%); font-size: 22px; letter-spacing: 1px; }
  #pause { top: 18px; right: 18px; width: 44px; height: 44px; justify-content: center; padding: 0; font-size: 16px; }
  #hint { top: 46%; left: 18px; font-size: 14px; max-width: 170px; line-height: 1.35; }
  #flash { position: absolute; top: 34%; left: 50%; transform: translateX(-50%);
           font-size: 34px; font-weight: 800; color: #2E7D32; opacity: 0; pointer-events: none;
           text-shadow: 0 2px 8px rgba(255,255,255,.8); transition: opacity .1s; }
  #over { position: absolute; inset: 0; display: none; flex-direction: column; gap: 14px;
          align-items: center; justify-content: center; background: rgba(40,28,20,.55);
          -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); color: #fff; text-align: center; }
  #over h2 { font-size: 34px; }
  #over p { font-size: 18px; opacity: .9; }
  #over button { margin-top: 8px; background: #6F4E37; color: #FFF8EF; border: none;
                 border-radius: 999px; padding: 12px 28px; font-size: 16px; font-weight: 800;
                 cursor: pointer; box-shadow: 0 5px 0 #4E3626; }
  #over button:active { transform: translateY(3px); box-shadow: 0 2px 0 #4E3626; }
  #tipbar { position:absolute; bottom:16px; left:50%; transform:translateX(-50%);
            font-size:12px; color:#8d6e63; background:rgba(255,255,255,.5);
            padding:6px 14px; border-radius:999px; text-align:center; }
</style>
</head>
<body>
<div id="wrap">
  <canvas id="c"></canvas>
  <div id="score" class="pill"><span class="k">Score</span><span class="v" id="sv">0</span></div>
  <div id="timer" class="pill">⏱ <span id="tv">00:30</span></div>
  <div id="pause" class="pill">‖</div>
  <div id="hint" class="pill">💧 꾹 누르면 좌좌, 탡탱 치면 한 방울!</div>
  <div id="flash"></div>
  <div id="tipbar">초록 링이 커질 때 탡! 터치하면 Perfect — 표면장력이 더 버펠요</div>
  <div id="over">
    <h2 id="ot">벤침!</h2>
    <p id="op"></p>
    <button id="rb">다시 하기</button>
  </div>
</div>
<script>
const cv=document.getElementById('c'), ctx=cv.getContext('2d');
const wrap=document.getElementById('wrap');
let W=1024,H=576;
function resize(){const r=wrap.getBoundingClientRect();cv.width=r.width*devicePixelRatio;cv.height=r.height*devicePixelRatio;W=r.width;H=r.height;ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);}
new ResizeObserver(resize).observe(wrap); resize();

const sv=document.getElementById('sv'), tv=document.getElementById('tv');
const flash=document.getElementById('flash'), over=document.getElementById('over'), op=document.getElementById('op'), ot=document.getElementById('ot');

let state;
function reset(){
  state={ fill:0.52, bulge:0, capacity:0.55+Math.random()*0.5, inst:0, score:0, time:30, over:false, pouring:false, t:0, ripple:0 };
  over.style.display='none';
}
reset();

function ringPhase(){ return (Math.sin(state.t*3.0)+1)/2; }

function addWater(amount, timed){
  if(state.over) return;
  if(state.fill<1){ state.fill=Math.min(1, state.fill+amount*0.6); if(state.fill>=1){ state.bulge+=amount*0.4; } }
  else { state.bulge+=amount; }
  state.ripple=1;
  let perfect=false;
  if(timed){
    const p=ringPhase();
    if(p>0.72){ perfect=true; state.capacity+=0.03; state.inst=Math.max(0,state.inst-0.08); showFlash('Perfect!','#2E7D32'); }
    else if(p<0.3){ state.inst+=0.10; }
  } else { state.inst+=amount*0.9; }
  if(state.bulge>state.capacity || state.inst>=1){ gameOver(); }
  else if(timed){ state.score+=perfect?25:10; }
}
function showFlash(txt,color){ flash.textContent=txt; flash.style.color=color; flash.style.opacity=1; setTimeout(function(){flash.style.opacity=0;},350); }

function gameOver(){ state.over=true; ot.textContent='🌊 넘쳤어요!'; op.textContent='최종 점수 '+Math.round(state.score)+'점'; over.style.display='flex'; }
function win(){ state.over=true; ot.textContent='☕ 성공!'; op.textContent='30초 동안 버킈어요 · 점수 '+Math.round(state.score)+'점'; over.style.display='flex'; }

let downT=0, held=false, holdTimer=null;
function onDown(e){ e.preventDefault(); if(state.over) return; downT=performance.now(); held=false; holdTimer=setTimeout(function(){ held=true; state.pouring=true; }, 180); }
function onUp(e){ e.preventDefault(); clearTimeout(holdTimer); if(state.over) return; const dt=performance.now()-downT; state.pouring=false; if(!held && dt<180){ addWater(0.045, true); } }
wrap.addEventListener('pointerdown',onDown);
wrap.addEventListener('pointerup',onUp);
wrap.addEventListener('pointerleave',function(){state.pouring=false;clearTimeout(holdTimer);});
document.getElementById('rb').addEventListener('click',function(e){e.stopPropagation();reset();});

let last=performance.now();
function loop(now){
  const d=Math.min(0.05,(now-last)/1000); last=now;
  if(!state.over){
    state.t+=d;
    if(state.pouring){ addWater(0.9*d,false); }
    state.inst=Math.max(0,state.inst-0.12*d);
    if(state.bulge>0.05){ state.score+=state.bulge*18*d; }
    state.ripple=Math.max(0,state.ripple-2.2*d);
    state.time-=d;
    if(state.time<=0){ state.time=0; win(); }
  }
  draw();
  sv.textContent=Math.round(state.score);
  const s=Math.max(0,Math.ceil(state.time));
  tv.textContent='00:'+String(s).padStart(2,'0');
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

function draw(){
  ctx.clearRect(0,0,W,H);
  const cx=W*0.52;
  const gw=W*0.30, gh=H*0.46, topY=H*0.44, botY=topY+gh;
  const topL=cx-gw/2, topR=cx+gw/2, botL=cx-gw*0.38, botR=cx+gw*0.38;
  const waterTop=botY-(botY-topY)*state.fill;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(topL,topY); ctx.lineTo(topR,topY); ctx.lineTo(botR,botY);
  ctx.quadraticCurveTo(cx,botY+18,botL,botY); ctx.closePath(); ctx.clip();
  const wobble=Math.sin(state.t*6)*state.ripple*6;
  const grad=ctx.createLinearGradient(0,waterTop,0,botY);
  grad.addColorStop(0,'rgba(175,205,215,0.85)'); grad.addColorStop(1,'rgba(150,185,200,0.95)');
  ctx.fillStyle=grad;
  ctx.beginPath(); ctx.moveTo(topL,waterTop+wobble);
  ctx.quadraticCurveTo(cx,waterTop-10+wobble,topR,waterTop+wobble);
  ctx.lineTo(botR,botY); ctx.lineTo(botL,botY); ctx.closePath(); ctx.fill();
  ctx.restore();
  if(state.bulge>0.01){
    const domeH=state.bulge/Math.max(0.3,state.capacity)*44;
    ctx.fillStyle='rgba(165,200,212,0.9)';
    ctx.beginPath(); ctx.moveTo(topL+6,topY);
    ctx.quadraticCurveTo(cx,topY-domeH-wobble,topR-6,topY); ctx.closePath(); ctx.fill();
    const risk=state.bulge/state.capacity;
    if(risk>0.8){ ctx.strokeStyle='rgba(200,80,40,'+(risk-0.8)*5+')'; ctx.lineWidth=3; ctx.stroke(); }
  }
  ctx.strokeStyle='rgba(120,120,120,0.55)'; ctx.lineWidth=3;
  ctx.beginPath(); ctx.moveTo(topL,topY); ctx.lineTo(botL,botY);
  ctx.quadraticCurveTo(cx,botY+18,botR,botY); ctx.lineTo(topR,topY); ctx.stroke();
  ctx.strokeStyle='rgba(255,255,255,0.7)'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.ellipse(cx,topY,gw/2,8,0,0,Math.PI*2); ctx.stroke();
  if(state.pouring){
    ctx.fillStyle='rgba(160,195,210,0.9)';
    for(let i=0;i<3;i++){ const yy=(topY-120)+ ((state.t*400+i*40)%120); ctx.beginPath(); ctx.arc(cx,yy,5,0,Math.PI*2); ctx.fill(); }
  }
  const ph=ringPhase(); const ringR=26+ph*10;
  ctx.beginPath(); ctx.arc(cx,topY-70,ringR,0,Math.PI*2);
  ctx.strokeStyle= ph>0.72? 'rgba(46,125,50,0.9)':'rgba(140,110,90,0.5)';
  ctx.lineWidth=4; ctx.stroke();
  ctx.beginPath(); ctx.arc(cx,topY-70,20,0,Math.PI*2);
  ctx.fillStyle= ph>0.72?'rgba(46,125,50,0.25)':'rgba(255,255,255,0.3)'; ctx.fill();
}
</script>
</body>
</html>
"""

st.markdown("### 💧 표면장력 챌링지 게임")
st.caption("꼹 누르면 물이 좌좌, 탡탱 치면 한 방울씩. 초록 링이 커질 때 탭하면 Perfect! — 한계치는 매 판 랜덤이에요.")
components.html(GAME_HTML, height=620, scrolling=False)
