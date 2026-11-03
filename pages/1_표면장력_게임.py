import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="표면장력 게임", page_icon="💧", layout="centered")

GAME_HTML = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * { box-sizing:border-box; margin:0; padding:0; -webkit-user-select:none; user-select:none; }
  html,body { height:100%; font-family:'Pretendard',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
  #wrap { position:relative; width:100%; max-width:430px; margin:0 auto; aspect-ratio:9/16;
          border-radius:24px; overflow:hidden; touch-action:none; cursor:pointer;
          background:linear-gradient(160deg,#f5efe4 0%,#efe7d8 50%,#e7dcc9 100%); }
  canvas { position:absolute; inset:0; width:100%; height:100%; }
  .pill { position:absolute; display:flex; align-items:center; gap:6px;
          background:rgba(255,255,255,0.6); -webkit-backdrop-filter:blur(6px); backdrop-filter:blur(6px);
          border:1px solid rgba(255,255,255,0.85); border-radius:999px;
          padding:7px 14px; color:#4a3b30; font-weight:800; font-size:13px; }
  #turn { top:16px; left:50%; transform:translateX(-50%); font-size:15px; }
  #cap  { top:16px; right:16px; font-size:12px; }
  #players { position:absolute; top:58px; left:50%; transform:translateX(-50%); display:flex; gap:8px; }
  .chip { display:flex; flex-direction:column; align-items:center; gap:2px;
          background:rgba(255,255,255,0.55); border-radius:14px; padding:6px 10px;
          font-size:11px; font-weight:800; color:#6d5a4a; min-width:52px; border:2px solid transparent; }
  .chip.active { border-color:#6F4E37; background:rgba(255,255,255,0.95); }
  .chip.dead { opacity:0.35; text-decoration:line-through; }
  .chip .ico { font-size:18px; }
  #hint { bottom:92px; left:50%; transform:translateX(-50%); font-size:13px; text-align:center; max-width:88%; line-height:1.4; }
  #flash { position:absolute; top:40%; left:50%; transform:translateX(-50%);
           font-size:30px; font-weight:900; color:#2E7D32; opacity:0; pointer-events:none;
           text-shadow:0 2px 8px rgba(255,255,255,.9); transition:opacity .1s; white-space:nowrap; }
  #over { position:absolute; inset:0; display:none; flex-direction:column; gap:14px;
          align-items:center; justify-content:center; background:rgba(40,28,20,.6);
          -webkit-backdrop-filter:blur(4px); backdrop-filter:blur(4px); color:#fff; text-align:center; padding:20px; }
  #over h2 { font-size:30px; } #over p { font-size:16px; opacity:.92; line-height:1.5; }
  .btn { background:#6F4E37; color:#FFF8EF; border:none; border-radius:999px;
         padding:13px 30px; font-size:16px; font-weight:800; cursor:pointer; box-shadow:0 5px 0 #4E3626; }
  .btn:active { transform:translateY(3px); box-shadow:0 2px 0 #4E3626; }
  #start { position:absolute; inset:0; display:flex; flex-direction:column; gap:16px;
           align-items:center; justify-content:center; background:rgba(247,241,227,0.97); padding:24px; text-align:center; }
  #start h2 { font-size:24px; color:#3E2723; } #start p { font-size:13px; color:#6d5a4a; line-height:1.5; }
  .opts { display:flex; gap:10px; }
  .opt { background:#fff; border:2px solid #d8c7ad; border-radius:16px; padding:14px 18px;
         font-size:18px; font-weight:800; color:#6F4E37; cursor:pointer; }
  .opt.sel { border-color:#6F4E37; background:#f1e4d2; }
</style>
</head>
<body>
<div id="wrap">
  <canvas id="c"></canvas>
  <div id="turn" class="pill">준비중</div>
  <div id="cap" class="pill">🎲 한계 ???</div>
  <div id="players"></div>
  <div id="hint" class="pill">한 번만 터치! 짧게 탭 = 조금, 꾹 누르면 = 콸콸</div>
  <div id="flash"></div>
  <div id="start">
    <h2>💧 표면장력 버티기</h2>
    <p>돌아가며 컵에 물을 추가해요.<br>넘치게 만드는 사람(봇)이 패배!<br>내 차례엔 딱 한 번만 터치할 수 있어요.</p>
    <p style="font-weight:800;color:#3E2723">봇 몇 명과 할까요?</p>
    <div class="opts" id="opts">
      <div class="opt sel" data-n="1">1</div>
      <div class="opt" data-n="2">2</div>
      <div class="opt" data-n="3">3</div>
    </div>
    <button class="btn" id="startBtn">시작!</button>
  </div>
  <div id="over">
    <h2 id="ot">게임 종료</h2>
    <p id="op"></p>
    <button class="btn" id="rb">다시 하기</button>
  </div>
</div>
<script>
const cv=document.getElementById('c'), ctx=cv.getContext('2d'), wrap=document.getElementById('wrap');
let W=430,H=764;
function resize(){const r=wrap.getBoundingClientRect();cv.width=r.width*devicePixelRatio;cv.height=r.height*devicePixelRatio;W=r.width;H=r.height;ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);}
new ResizeObserver(resize).observe(wrap); resize();

const turnEl=document.getElementById('turn'), capEl=document.getElementById('cap'),
      playersEl=document.getElementById('players'), hintEl=document.getElementById('hint'),
      flash=document.getElementById('flash'), over=document.getElementById('over'),
      op=document.getElementById('op'), ot=document.getElementById('ot'),
      startScreen=document.getElementById('start');

let botCount=1;
document.querySelectorAll('#opts .opt').forEach(function(o){
  o.addEventListener('click',function(){
    document.querySelectorAll('#opts .opt').forEach(function(x){x.classList.remove('sel');});
    o.classList.add('sel'); botCount=parseInt(o.dataset.n);
  });
});

let S=null;
function newGame(){
  const players=[{name:'나',ico:'🙂',bot:false,dead:false}];
  const bicons=['🤖','👻','🐱'];
  for(let i=0;i<botCount;i++) players.push({name:'봇'+(i+1),ico:bicons[i],bot:true,dead:false});
  S={ players:players, cur:0, fill:0.4, bulge:0, capacity:0.6+Math.random()*0.55, t:0, ripple:0, over:false, acting:false };
  over.style.display='none'; startScreen.style.display='none';
  renderPlayers(); nextPrompt();
}

function renderPlayers(){
  playersEl.innerHTML='';
  S.players.forEach(function(p,i){
    const d=document.createElement('div');
    d.className='chip'+(i===S.cur?' active':'')+(p.dead?' dead':'');
    d.innerHTML='<span class="ico">'+p.ico+'</span>'+p.name;
    playersEl.appendChild(d);
  });
}
function alive(){ return S.players.filter(function(p){return !p.dead;}); }
function ringPhase(){ return (Math.sin(S.t*3.0)+1)/2; }

function nextPrompt(){
  if(S.over) return;
  const p=S.players[S.cur]; renderPlayers();
  if(p.bot){
    turnEl.textContent=p.ico+' '+p.name+' 차례...';
    hintEl.textContent='봇이 고민중이에요 🤔';
    S.acting=true; setTimeout(botMove, 600+Math.random()*700);
  } else {
    turnEl.textContent='🙂 내 차례!';
    hintEl.textContent='한 번만 터치! 짧게 탭 = 조금, 꾹 누르면 = 콸콸';
    S.acting=false;
  }
}

function applyWater(amount, timed){
  if(S.fill<1){ S.fill=Math.min(1,S.fill+amount*0.6); if(S.fill>=1) S.bulge+=amount*0.4; }
  else S.bulge+=amount;
  S.ripple=1;
  if(timed){ const ph=ringPhase(); if(ph>0.72){ S.capacity+=0.03; showFlash('Perfect! 표면장력 ↑','#2E7D32'); } }
}

function endTurnAfter(){
  setTimeout(function(){
    if(S.bulge>S.capacity){
      S.players[S.cur].dead=true; renderPlayers();
      showFlash('🌊 넘쳤다!','#C84828');
      capEl.textContent='🎲 한계 '+(Math.round(S.capacity*100)/100);
      const left=alive();
      if(left.length<=1){ finish(left[0]); return; }
      S.fill=0.4; S.bulge=0; S.capacity=0.6+Math.random()*0.55;
      setTimeout(function(){ capEl.textContent='🎲 한계 ???'; },900);
      advance(); nextPrompt();
    } else { advance(); nextPrompt(); }
    S.acting=false;
  }, 520);
}

function advance(){ do { S.cur=(S.cur+1)%S.players.length; } while(S.players[S.cur].dead); }

function botMove(){
  if(S.over) return;
  const risk=S.bulge; let amount;
  if(risk>0.45) amount=0.03+Math.random()*0.04;
  else if(risk>0.2) amount=0.06+Math.random()*0.08;
  else amount=0.1+Math.random()*0.14;
  if(Math.random()<0.12) amount+=0.15;
  applyWater(amount, Math.random()<0.5);
  turnEl.textContent=S.players[S.cur].ico+' '+S.players[S.cur].name+' 탁!';
  endTurnAfter();
}

function finish(winner){
  S.over=true;
  if(winner && !winner.bot){ ot.textContent='🏆 승리!'; op.textContent='끝까지 버텨어요! 축하해요 ☕'; }
  else if(winner){ ot.textContent='😵 패배...'; op.textContent=winner.ico+' '+winner.name+'이(가) 최후에 살아남았어요'; }
  else { ot.textContent='게임 종료'; op.textContent='모두 넘쳌어요'; }
  over.style.display='flex';
}
function showFlash(txt,color){ flash.textContent=txt; flash.style.color=color; flash.style.opacity=1; setTimeout(function(){flash.style.opacity=0;},500); }

let downT=0, held=false, holdTimer=null, pouring=false, pourAcc=0;
function onDown(e){ e.preventDefault();
  if(!S||S.over||S.acting||S.players[S.cur].bot) return;
  downT=performance.now(); held=false; pouring=false; pourAcc=0;
  holdTimer=setTimeout(function(){ held=true; pouring=true; pourLoop(); }, 180);
}
function pourLoop(){
  if(!pouring) return;
  const amt=0.9/60; pourAcc+=amt; applyWater(amt,false); S.ripple=1;
  if(pourAcc<0.9 && S.bulge<=S.capacity+0.05){ requestAnimationFrame(pourLoop); }
  else { pouring=false; finalizeHuman(); }
}
function onUp(e){ e.preventDefault();
  if(!S||S.over||S.acting||S.players[S.cur].bot) return;
  clearTimeout(holdTimer);
  if(held){ if(pouring){ pouring=false; finalizeHuman(); } }
  else { const dt=performance.now()-downT; if(dt<180){ applyWater(0.05,true); finalizeHuman(); } }
}
function finalizeHuman(){ if(S.acting) return; S.acting=true; turnEl.textContent='🙂 탁!'; endTurnAfter(); }

wrap.addEventListener('pointerdown',onDown);
wrap.addEventListener('pointerup',onUp);
wrap.addEventListener('pointerleave',function(){ if(pouring){ pouring=false; finalizeHuman(); } clearTimeout(holdTimer); });
document.getElementById('startBtn').addEventListener('click',function(e){e.stopPropagation();newGame();});
document.getElementById('rb').addEventListener('click',function(e){e.stopPropagation();startScreen.style.display='flex';over.style.display='none';});

let last=performance.now();
function loop(now){
  const d=Math.min(0.05,(now-last)/1000); last=now;
  if(S && !S.over){ S.t+=d; S.ripple=Math.max(0,S.ripple-2.2*d); }
  draw(); requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

function draw(){
  ctx.clearRect(0,0,W,H);
  if(!S) return;
  const cx=W*0.5;
  const gw=W*0.46, gh=H*0.4, topY=H*0.42, botY=topY+gh;
  const topL=cx-gw/2, topR=cx+gw/2, botL=cx-gw*0.36, botR=cx+gw*0.36;
  const waterTop=botY-(botY-topY)*S.fill;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(topL,topY); ctx.lineTo(topR,topY); ctx.lineTo(botR,botY);
  ctx.quadraticCurveTo(cx,botY+22,botL,botY); ctx.closePath(); ctx.clip();
  const wob=Math.sin(S.t*6)*S.ripple*6;
  const g=ctx.createLinearGradient(0,waterTop,0,botY);
  g.addColorStop(0,'rgba(175,205,215,0.9)'); g.addColorStop(1,'rgba(150,185,200,0.96)');
  ctx.fillStyle=g;
  ctx.beginPath(); ctx.moveTo(topL,waterTop+wob);
  ctx.quadraticCurveTo(cx,waterTop-10+wob,topR,waterTop+wob);
  ctx.lineTo(botR,botY); ctx.lineTo(botL,botY); ctx.closePath(); ctx.fill();
  ctx.restore();
  if(S.bulge>0.01){
    const domeH=S.bulge/Math.max(0.3,S.capacity)*52;
    ctx.fillStyle='rgba(165,200,212,0.92)';
    ctx.beginPath(); ctx.moveTo(topL+8,topY);
    ctx.quadraticCurveTo(cx,topY-domeH-wob,topR-8,topY); ctx.closePath(); ctx.fill();
    const risk=S.bulge/S.capacity;
    if(risk>0.78){ ctx.strokeStyle='rgba(200,80,40,'+Math.min(1,(risk-0.78)*4)+')'; ctx.lineWidth=3; ctx.stroke(); }
  }
  ctx.strokeStyle='rgba(120,110,100,0.55)'; ctx.lineWidth=3;
  ctx.beginPath(); ctx.moveTo(topL,topY); ctx.lineTo(botL,botY);
  ctx.quadraticCurveTo(cx,botY+22,botR,botY); ctx.lineTo(topR,topY); ctx.stroke();
  ctx.strokeStyle='rgba(255,255,255,0.75)'; ctx.lineWidth=2;
  ctx.beginPath(); ctx.ellipse(cx,topY,gw/2,9,0,0,Math.PI*2); ctx.stroke();
  if(pouring){
    ctx.fillStyle='rgba(160,195,210,0.9)';
    for(let i=0;i<3;i++){ const yy=(topY-130)+((S.t*420+i*44)%130); ctx.beginPath(); ctx.arc(cx,yy,5,0,Math.PI*2); ctx.fill(); }
  }
  if(!S.players[S.cur].bot && !S.acting && !S.over){
    const ph=ringPhase(), rr=28+ph*11;
    ctx.beginPath(); ctx.arc(cx,topY-86,rr,0,Math.PI*2);
    ctx.strokeStyle= ph>0.72?'rgba(46,125,50,0.9)':'rgba(140,110,90,0.5)'; ctx.lineWidth=4; ctx.stroke();
    ctx.beginPath(); ctx.arc(cx,topY-86,20,0,Math.PI*2);
    ctx.fillStyle= ph>0.72?'rgba(46,125,50,0.28)':'rgba(255,255,255,0.35)'; ctx.fill();
  }
}
</script>
</body>
</html>
"""

st.markdown("### 💧 표면장력 버티기 · 봇 대전")
st.caption("돌아가며 한 번씩 터치해 물을 추가! 넘치게 만드는 쪽이 패배. 짧게 탭=조금, 꾹 누르면=콸콸. 초록 링에서 탭하면 Perfect!")
components.html(GAME_HTML, height=820, scrolling=False)
