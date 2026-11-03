import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="표면장력 게임", page_icon="💧", layout="centered")

GAME_HTML = r"""
<!doctype html><html lang="ko"><head><meta charset="utf-8">
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
  border:1px solid rgba(255,255,255,0.85); border-radius:999px; padding:7px 14px;
  color:#4a3b30; font-weight:800; font-size:13px; }
#turn { top:16px; left:50%; transform:translateX(-50%); font-size:15px; }
#players { position:absolute; top:56px; left:50%; transform:translateX(-50%); display:flex; gap:8px; flex-wrap:wrap; justify-content:center; max-width:94%; }
.chip { display:flex; flex-direction:column; align-items:center; gap:2px;
  background:rgba(255,255,255,0.55); border-radius:14px; padding:6px 10px;
  font-size:11px; font-weight:800; color:#6d5a4a; min-width:52px; border:2px solid transparent; }
.chip.active { border-color:#6F4E37; background:rgba(255,255,255,0.97); }
.chip.dead { opacity:0.35; text-decoration:line-through; }
.chip .ico { font-size:18px; }
#hint { bottom:86px; left:50%; transform:translateX(-50%); font-size:13px; text-align:center; max-width:88%; line-height:1.4; }
#flash { position:absolute; top:40%; left:50%; transform:translateX(-50%); font-size:28px; font-weight:900;
  color:#2E7D32; opacity:0; pointer-events:none; text-shadow:0 2px 8px rgba(255,255,255,.9); transition:opacity .12s; white-space:nowrap; }
.screen { position:absolute; inset:0; display:flex; flex-direction:column; gap:16px; align-items:center;
  justify-content:center; padding:24px; text-align:center; }
#start { background:rgba(247,241,227,0.98); }
#rps { background:rgba(247,241,227,0.98); display:none; }
#over { background:rgba(40,28,20,.62); -webkit-backdrop-filter:blur(4px); backdrop-filter:blur(4px); color:#fff; display:none; }
h2 { font-size:24px; color:#3E2723; } #over h2 { color:#fff; font-size:30px; }
p { font-size:13px; color:#6d5a4a; line-height:1.5; } #over p { color:#fff; font-size:16px; }
.btn { background:#6F4E37; color:#FFF8EF; border:none; border-radius:999px; padding:13px 30px;
  font-size:16px; font-weight:800; cursor:pointer; box-shadow:0 5px 0 #4E3626; }
.btn:active { transform:translateY(3px); box-shadow:0 2px 0 #4E3626; }
.opts { display:flex; gap:10px; }
.opt { background:#fff; border:2px solid #d8c7ad; border-radius:16px; padding:14px 18px; font-size:18px; font-weight:800; color:#6F4E37; cursor:pointer; }
.opt.sel { border-color:#6F4E37; background:#f1e4d2; }
.rps-btns { display:flex; gap:14px; }
.rps-btns div { font-size:40px; cursor:pointer; background:#fff; border:2px solid #d8c7ad; border-radius:20px; padding:10px 14px; }
.rps-btns div:active { transform:scale(0.92); }
#rpsResult { font-size:20px; font-weight:800; color:#3E2723; min-height:28px; }
</style></head><body>
<div id="wrap">
  <canvas id="c"></canvas>
  <div id="turn" class="pill">준비중</div>
  <div id="players"></div>
  <div id="hint" class="pill">한 번만 터치! 짧게 탭=조금, 꾹 누르면=콸콸</div>
  <div id="flash"></div>
  <div id="start" class="screen">
    <h2>💧 표면장력 버티기</h2>
    <p>돌아가며 컵에 물을 추가해요.<br>넘치게 만드는 사람(봇)이 패배!<br>컵 가장자리까지는 금방 차지만, 그 위로는 천천히 부풀어요.</p>
    <p style="font-weight:800;color:#3E2723">봇 몇 명과 할까요?</p>
    <div class="opts" id="opts">
      <div class="opt sel" data-n="1">1</div>
      <div class="opt" data-n="2">2</div>
      <div class="opt" data-n="3">3</div>
    </div>
    <button class="btn" id="startBtn">다음</button>
  </div>
  <div id="rps" class="screen">
    <h2>✊✌️🖐️ 가위바위보</h2>
    <p>이기면 내가 먼저! (비기면 다시)</p>
    <div id="rpsResult"></div>
    <div class="rps-btns" id="rpsBtns">
      <div data-m="0">✊</div><div data-m="1">✌️</div><div data-m="2">🖐️</div>
    </div>
  </div>
  <div id="over" class="screen">
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

const turnEl=document.getElementById('turn'), playersEl=document.getElementById('players'),
  hintEl=document.getElementById('hint'), flash=document.getElementById('flash'),
  startScreen=document.getElementById('start'), rpsScreen=document.getElementById('rps'),
  rpsResult=document.getElementById('rpsResult'), over=document.getElementById('over'),
  op=document.getElementById('op'), ot=document.getElementById('ot');

let botCount=1;
document.querySelectorAll('#opts .opt').forEach(function(o){
  o.addEventListener('click',function(){
    document.querySelectorAll('#opts .opt').forEach(function(x){x.classList.remove('sel');});
    o.classList.add('sel'); botCount=parseInt(o.dataset.n);
  });
});

let S=null, firstIdx=0;
function randCap(){ return 0.15+Math.random()*1.35; }

function buildPlayers(){
  const players=[{name:'나',ico:'🙂',bot:false,dead:false}];
  const bicons=['🤖','👻','🐱'];
  for(let i=0;i<botCount;i++) players.push({name:'봇'+(i+1),ico:bicons[i],bot:true,dead:false});
  return players;
}

const RPS=['✊','✌️','🖐️'];
document.querySelectorAll('#rpsBtns div').forEach(function(b){
  b.addEventListener('click',function(){
    const me=parseInt(b.dataset.m), bot=Math.floor(Math.random()*3);
    if(me===bot){ rpsResult.textContent='나:'+RPS[me]+' 봇:'+RPS[bot]+' → 비겼어요! 다시'; return; }
    const win=(me===0&&bot===2)||(me===1&&bot===0)||(me===2&&bot===1);
    firstIdx = win?0:1;
    rpsResult.textContent='나:'+RPS[me]+' 봇:'+RPS[bot]+' → '+(win?'내가 먼저! 🎉':'봇이 먼저!');
    setTimeout(startGame, 900);
  });
});

function startGame(){
  S={ players:buildPlayers(), cur:firstIdx, fill:0, bulge:0, capacity:randCap(),
      t:0, ripple:0, over:false, acting:false, pour:null };
  rpsScreen.style.display='none'; over.style.display='none';
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

function applyWater(amount, timed){
  if(S.fill<1){
    const room=1-S.fill;
    const used=Math.min(room, amount*0.9);
    S.fill+=used;
    const rest=amount*0.9-used;
    if(rest>0) S.bulge+=rest*0.28;
  } else { S.bulge+=amount*0.28; }
  S.ripple=1;
  if(timed){ const ph=ringPhase(); if(ph>0.72){ S.capacity+=0.05; showFlash('Perfect! 표면장력 ↑','#2E7D32'); } }
}

function resolveTurn(){
  if(S.bulge>S.capacity){
    S.players[S.cur].dead=true; renderPlayers();
    showFlash('🌊 넘쳤다!','#C84828');
    const left=alive();
    if(left.length<=1){ finish(left[0]); return; }
    S.fill=0; S.bulge=0; S.capacity=randCap();
    advance(); nextPrompt();
  } else { advance(); nextPrompt(); }
  S.acting=false;
}
function advance(){ do { S.cur=(S.cur+1)%S.players.length; } while(S.players[S.cur].dead); }

function nextPrompt(){
  if(S.over) return;
  const p=S.players[S.cur]; renderPlayers();
  if(p.bot){
    turnEl.textContent=p.ico+' '+p.name+' 차례...';
    hintEl.textContent='봇이 고민중이에요 🤔';
    S.acting=true; setTimeout(botStart, 700+Math.random()*700);
  } else {
    turnEl.textContent='🙂 내 차례!';
    hintEl.textContent='한 번만 터치! 짧게 탭=조금, 꾹 누르면=콸콸';
    S.acting=false;
  }
}

function botStart(){
  if(S.over) return;
  const head=S.capacity-S.bulge;
  let target;
  if(head<0.25) target=0.04+Math.random()*0.05;
  else if(head<0.6) target=0.1+Math.random()*0.12;
  else target=0.2+Math.random()*0.3;
  if(Math.random()<0.12) target+=0.25;
  const timed=Math.random()<0.5;
  S.pour={ who:'bot', poured:0, target:target, timed:timed, rate:0.9 };
  turnEl.textContent=S.players[S.cur].ico+' '+S.players[S.cur].name+' 부은… 💦';
}

function finish(winner){
  S.over=true;
  if(winner && !winner.bot){ ot.textContent='🏆 승리!'; op.textContent='끝까지 버텨어요! 축하해요 ☕'; }
  else if(winner){ ot.textContent='😵 패배...'; op.textContent=winner.ico+' '+winner.name+'이(가) 최후에 살아남았어요'; }
  else { ot.textContent='게임 종료'; op.textContent='모두 넘쳌어요'; }
  over.style.display='flex';
}
function showFlash(txt,color){ flash.textContent=txt; flash.style.color=color; flash.style.opacity=1; setTimeout(function(){flash.style.opacity=0;},600); }

let downT=0, held=false, holdTimer=null;
function onDown(e){ e.preventDefault();
  if(!S||S.over||S.acting||S.players[S.cur].bot||S.pour) return;
  downT=performance.now(); held=false;
  holdTimer=setTimeout(function(){ held=true; S.pour={who:'human',poured:0,target:999,timed:false,rate:0.9}; turnEl.textContent='🙂 부은… 💦'; }, 180);
}
function onUp(e){ e.preventDefault();
  if(!S||S.over||S.players[S.cur].bot) return;
  clearTimeout(holdTimer);
  if(held){ if(S.pour){ S.pour=null; finalizeHuman(); } }
  else { const dt=performance.now()-downT; if(dt<180 && !S.acting){ applyWater(0.06,true); finalizeHuman(); } }
}
function finalizeHuman(){ if(S.acting) return; S.acting=true; setTimeout(resolveTurn,460); }

wrap.addEventListener('pointerdown',onDown);
wrap.addEventListener('pointerup',onUp);
wrap.addEventListener('pointerleave',function(){ if(held&&S&&S.pour){ S.pour=null; finalizeHuman(); } clearTimeout(holdTimer); });
document.getElementById('startBtn').addEventListener('click',function(e){e.stopPropagation();startScreen.style.display='none';rpsResult.textContent='';rpsScreen.style.display='flex';});
document.getElementById('rb').addEventListener('click',function(e){e.stopPropagation();over.style.display='none';startScreen.style.display='flex';});

let last=performance.now();
function loop(now){
  const d=Math.min(0.05,(now-last)/1000); last=now;
  if(S && !S.over){
    S.t+=d; S.ripple=Math.max(0,S.ripple-2.2*d);
    if(S.pour){
      const step=S.pour.rate*d;
      applyWater(step,false); S.pour.poured+=step;
      if(S.pour.poured>=S.pour.target || S.bulge>S.capacity){
        const wasTimed=S.pour.timed, bot=(S.pour.who==='bot');
        S.pour=null;
        if(bot){
          if(wasTimed){ const ph=ringPhase(); if(ph>0.72){ S.capacity+=0.05; showFlash('봇 Perfect!','#2E7D32'); } }
          S.acting=true; setTimeout(resolveTurn,420);
        }
      }
    }
  }
  draw(); requestAnimationFrame(loop);
}
requestAnimationFrame(loop);

function draw(){
  ctx.clearRect(0,0,W,H);
  if(!S){ return; }
  const cx=W*0.5, gw=W*0.46, gh=H*0.4, topY=H*0.42, botY=topY+gh;
  const topL=cx-gw/2, topR=cx+gw/2, botL=cx-gw*0.36, botR=cx+gw*0.36;
  const waterTop=botY-(botY-topY)*S.fill;
  ctx.save();
  ctx.beginPath(); ctx.moveTo(topL,topY); ctx.lineTo(topR,topY); ctx.lineTo(botR,botY);
  ctx.quadraticCurveTo(cx,botY+22,botL,botY); ctx.closePath(); ctx.clip();
  const wob=Math.sin(S.t*6)*S.ripple*6;
  const g=ctx.createLinearGradient(0,waterTop,0,botY);
  g.addColorStop(0,'rgba(175,205,215,0.9)'); g.addColorStop(1,'rgba(150,185,200,0.96)');
  ctx.fillStyle=g;
  ctx.beginPath(); ctx.moveTo(topL,waterTop+wob);
  ctx.quadraticCurveTo(cx,waterTop-10+wob,topR,waterTop+wob);
  ctx.lineTo(botR,botY); ctx.lineTo(botL,botY); ctx.closePath(); ctx.fill();
  ctx.restore();
  if(S.bulge>0.005){
    const domeH=S.bulge/Math.max(0.3,S.capacity)*54;
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
  if(S.pour){
    ctx.fillStyle='rgba(160,195,210,0.95)';
    for(let i=0;i<4;i++){ const yy=(topY-150)+((S.t*460+i*38)%150); ctx.beginPath(); ctx.arc(cx,yy,5,0,Math.PI*2); ctx.fill(); }
  }
  if(!S.players[S.cur].bot && !S.acting && !S.over && !S.pour){
    const ph=ringPhase(), rr=28+ph*11;
    ctx.beginPath(); ctx.arc(cx,topY-92,rr,0,Math.PI*2);
    ctx.strokeStyle= ph>0.72?'rgba(46,125,50,0.9)':'rgba(140,110,90,0.5)'; ctx.lineWidth=4; ctx.stroke();
    ctx.beginPath(); ctx.arc(cx,topY-92,20,0,Math.PI*2);
    ctx.fillStyle= ph>0.72?'rgba(46,125,50,0.28)':'rgba(255,255,255,0.35)'; ctx.fill();
  }
}
</script></body></html>
"""

st.markdown("### 💧 표면장력 버티기 · 봇 대전")
st.caption("가위바위보로 선공을 정해요. 돌아가며 한 번씩 터치—짧게 탭=조금, 꾹 누르면=콸콸. 컵 가장자리까진 금방, 그 위는 천천히 부풀어요. 한계는 매판 랜덤!")
components.html(GAME_HTML, height=820, scrolling=False)
