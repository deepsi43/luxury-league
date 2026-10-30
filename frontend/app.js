const API = "http://127.0.0.1:8000";
let roomCode = null, token = null, playerId = null, currentState = null, socket = null;
const $ = (id) => document.getElementById(id);

function show(id) { ["lobby","room","game","results"].forEach(x => $(x).classList.toggle("hidden", x !== id)); }
function saveSession(data) {
  roomCode = data.room_code; token = data.player_token; playerId = data.player_id;
  sessionStorage.setItem("ll_session", JSON.stringify({roomCode,token,playerId}));
}
function restoreSession() {
  try { const s = JSON.parse(sessionStorage.getItem("ll_session")); if(s){roomCode=s.roomCode;token=s.token;playerId=s.playerId;} } catch {}
}
async function request(path, method="GET", body=null) {
  const res = await fetch(API + path, {
    method, headers: {"Content-Type":"application/json", ...(token ? {"X-Player-Token":token}: {})},
    body: body ? JSON.stringify(body) : null
  });
  const data = await res.json().catch(()=>({detail:"Unexpected server response"}));
  if(!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}
function toast(msg) { $("eventToast").textContent = msg || ""; }
function cardMarkup(card) {
  const tier = card.tier;
  const symbols = ["♧","✦","♛"];
  const tierName = ["","ACCESSIBLE LUXURY","PREMIUM LUXURY","ULTRA LUXURY"][tier];
  return `<div class="lux-card tier-${tier}">
    <div class="card-tier">${tierName}</div>
    <div class="card-gem">${symbols[tier-1]}</div>
    <div class="card-name">${escapeHtml(card.name)}</div>
    <div class="card-points">+${card.points} PTS</div>
  </div>`;
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}
function render(state) {
  currentState = state;
  $("roomCodeLabel").textContent = state.room_code;
  $("playerCount").textContent = `${state.players.length} / 4`;
  $("players").innerHTML = state.players.map(p => `<div class="player-tile">
    <div class="avatar">${escapeHtml(p.name.slice(0,1).toUpperCase())}</div>
    <strong>${escapeHtml(p.name)} ${p.is_host ? "✦" : ""}</strong>
    <small>${p.is_host ? "HOST" : "PLAYER"} · ${p.turns_taken}/15 turns</small>
  </div>`).join("");
  const isHost = state.you?.is_host;
  $("hostControls").classList.toggle("hidden", !(isHost && state.status==="lobby" && state.players.length===4));
  $("waitingMessage").classList.toggle("hidden", state.status!="lobby" || state.players.length===4);
  if(state.status==="lobby"){show("room");return;}
  if(state.status==="playing"){
    show("game");
    $("deckCount").textContent = state.deck_remaining;
    $("turnLabel").textContent = state.active_player_id===playerId ? "YOUR TURN" : `${state.players.find(p=>p.id===state.active_player_id)?.name || "PLAYER"}'S TURN`;
    $("scoreboard").innerHTML = state.players.map(p=>`<div class="score-tile ${p.id===state.active_player_id?"active":""}">
      <strong>${escapeHtml(p.name)} ${p.id===playerId?"(YOU)":""}</strong>
      <div class="score">${p.score.toLocaleString()}</div>
      <small>${p.pairs} PAIRS · ${p.turns_taken}/15 TURNS</small>
    </div>`).join("");
    $("yourName").textContent = state.you.name;
    $("turnsTaken").textContent = state.players.find(p=>p.id===playerId).turns_taken;
    $("hand").innerHTML = state.hand.map(cardMarkup).join("");
    $("emptyHand").classList.toggle("hidden", state.hand.length>0);
    const me = state.players.find(p=>p.id===playerId);
    const canDraw = state.active_player_id===playerId && me.turns_taken<15 && state.deck_remaining>0;
    $("drawBtn").disabled = !canDraw;
    $("turnHint").textContent = canDraw ? "Draw one card. Matching pairs are completed automatically." : "Wait for your turn. Your cards are private.";
    $("collections").innerHTML = state.completed_pairs.length ? state.completed_pairs.map(p=>`<div class="collection-chip">${escapeHtml(p.brand_name)}<b>+${p.total_points} points</b></div>`).join("") : '<span class="hint">No pairs yet. Your first match will appear here.</span>';
    toast(state.recent_event);
  }
  if(state.status==="finished"){
    show("results");
    const winner=state.players.find(p=>p.id===state.winner_id);
    $("winnerTitle").textContent = `${winner?.name || "A player"} wins!`;
    $("winnerSub").textContent = "The Luxury League crown has been claimed.";
    const scores=state.players.map(p=>({name:p.name,score:state.final_scores?.[p.id] ?? p.score,pairs:p.pairs,id:p.id})).sort((a,b)=>b.score-a.score);
    $("finalScores").innerHTML=scores.map((p,i)=>`<div class="final-row ${i===0?"winner":""}"><span>${i+1}. ${escapeHtml(p.name)} ${i===0?"♛":""}</span><b>${p.score.toLocaleString()} pts · ${p.pairs} pairs</b></div>`).join("");
  }
}
function connectSocket() {
  if(socket) socket.close();
  socket = new WebSocket(API.replace("http","ws")+`/ws/rooms/${roomCode}`);
  socket.onopen=()=>{$("connection").textContent="● LIVE";};
  socket.onclose=()=>{$("connection").textContent="● RECONNECTING";setTimeout(()=>{if(roomCode)connectSocket()},1800);};
  socket.onmessage=async()=>{try{const s=await request(`/api/rooms/${roomCode}`);render(s);}catch(e){toast(e.message)}};
}
$("createBtn").onclick=async()=>{
  try{const name=$("playerName").value.trim();if(!name)throw Error("Enter your display name.");
    const d=await request("/api/rooms","POST",{player_name:name});saveSession(d);render(d.state);connectSocket();
  }catch(e){alert(e.message)}
};
$("joinBtn").onclick=async()=>{
  try{const name=$("playerName").value.trim(),code=$("roomCode").value.trim().toUpperCase();if(!name||!code)throw Error("Enter your name and invite code.");
    const d=await request(`/api/rooms/${code}/join`,"POST",{player_name:name});saveSession(d);render(d.state);connectSocket();
  }catch(e){alert(e.message)}
};
$("startBtn").onclick=async()=>{
  try{const s=await request(`/api/rooms/${roomCode}/start`,"POST");render(s);}catch(e){alert(e.message)}
};
$("drawBtn").onclick=async()=>{
  try{const s=await request(`/api/rooms/${roomCode}/draw`,"POST");render(s);}catch(e){alert(e.message)}
};
$("copyCodeBtn").onclick=async()=>{try{await navigator.clipboard.writeText(roomCode);$("copyCodeBtn").textContent="Copied!";setTimeout(()=>{$("copyCodeBtn").textContent="Copy invite code"},1500)}catch{}}
$("backToLobby").onclick=async()=>{try{const s=await request(`/api/rooms/${roomCode}`);render(s)}catch{show("lobby")}};
restoreSession();
if(roomCode&&token){request(`/api/rooms/${roomCode}`).then(s=>{render(s);connectSocket()}).catch(()=>{sessionStorage.removeItem("ll_session");roomCode=null;token=null;show("lobby")});}
