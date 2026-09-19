const $ = (s) => document.querySelector(s);
const state = { seeds: [], list: [], cur: null, tab: "onb", live: null };

const fmt = (n) => n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(0) + "K" : "" + (n || 0);
const money = (n) => "$" + fmt(n);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// Normalize pipeline live.json shape to seed shape; keep est_* + rank extras.
const norm = (x) => x.est_dl_mo != null ? { trackId: x.trackId, trackName: x.name, sellerName: x.seller,
  primaryGenreName: x.genre, price: x.price || 0, averageUserRating: x.rating || 0,
  userRatingCount: x.rating_count || 0, rank: x.rank, chart: x.chart, rc_velocity: x.rc_velocity,
  est_rev_mo: x.est_rev_mo, est_dl_mo: x.est_dl_mo, updated_ts: x.updated_ts, _est: true,
  screenshots: x.screenshots || [], keywords: x.keywords || [], description: x.description || "" } : x;
const est = (a) => a._est ? { rev: a.est_rev_mo, dl: a.est_dl_mo } : demoEstimate(a);
const estTag = (a) => a._est ? "est." : "demo";

function setStatus(html) { $("#status").innerHTML = html; }
function statusLine(n, src) { return `${n} app(s) · ${src}`; }

function sortList(list) {
  const k = $("#sort").value;
  const key = { rev: a => est(a).rev, dl: a => est(a).dl, rating: a => a.averageUserRating || 0,
    vel: a => a.rc_velocity == null ? -1 : a.rc_velocity }[k];
  return [...list].sort((a, b) => key(b) - key(a));
}

function render() {
  const genre = $("#genre").value;
  const list = sortList(state.list.filter(a => !genre || a.primaryGenreName === genre));
  $("#rows").innerHTML = list.map(a => {
    const e = est(a);
    const rk = a.rank ? `<span class="rank">#${a.rank}</span> ` : "";
    const vel = a.rc_velocity > 0 ? " ▲" : "";
    return `<tr data-id="${a.trackId}"${state.cur && state.cur.trackId === a.trackId ? ' class="sel"' : ""}>` +
      `<td>${rk}<b>${esc(a.trackName)}</b><br><span class="mut">${esc(a.sellerName)}</span></td>` +
      `<td>${esc(a.primaryGenreName)}</td><td>${money(e.rev)}/mo <span class="mut">${estTag(a)}</span></td>` +
      `<td>${fmt(e.dl)}/mo${vel}</td>` +
      `<td>${a.averageUserRating ? "★ " + a.averageUserRating.toFixed(1) : "—"}</td></tr>`;
  }).join("") || `<tr><td colspan="5"><div class="empty">No apps match. Try a different search or clear the genre filter.</div></td></tr>`;
  document.querySelectorAll("tr[data-id]").forEach(tr => tr.onclick = () => show(+tr.dataset.id));
}

function refreshGenres() {
  const sel = $("#genre"), cur = sel.value;
  const genres = [...new Set(state.list.map(a => a.primaryGenreName).filter(Boolean))].sort();
  sel.innerHTML = `<option value="">All genres</option>` + genres.map(g => `<option${g === cur ? " selected" : ""}>${esc(g)}</option>`).join("");
}

async function doSearch(q) {
  q = (q ?? $("#q").value).trim();
  if (!q) {
    state.list = state.seeds; refreshGenres(); render();
    setStatus(statusLine(state.seeds.length, state.live || "seed demo"));
    return;
  }
  setStatus(`<span class="spin"></span>Searching live App Store + local data...`);
  let live = [], offline = false;
  try {
    const r = await fetch("https://itunes.apple.com/search?term=" + encodeURIComponent(q) + "&entity=software&limit=12");
    if (!r.ok) throw new Error("http " + r.status);
    const j = await r.json();
    live = (j.results || []).map(x => ({ trackId: x.trackId, trackName: x.trackName, sellerName: x.sellerName, primaryGenreName: x.primaryGenre, price: x.price || 0, averageUserRating: x.averageUserRating || 0, userRatingCount: x.userRatingCount || 0, releaseDate: x.releaseDate }));
  } catch { offline = true; }
  const ql = q.toLowerCase();
  const base = state.seeds.filter(a => (a.trackName + " " + a.sellerName + " " + a.primaryGenreName).toLowerCase().includes(ql));
  const seen = new Set(), merged = [];
  for (const a of [...live, ...base]) if (!seen.has(a.trackId)) { seen.add(a.trackId); merged.push(a); }
  state.list = merged;
  refreshGenres(); render();
  if (offline) setStatus(`Live search unreachable — ${statusLine(merged.length, state.live || "seed demo")}.`);
  else if (!merged.length) setStatus(`No results for “${esc(q)}”. Try another term.`);
  else setStatus(statusLine(merged.length, `live App Store + ${state.live || "seed demo"}`));
}

async function show(id) {
  $("#detail").innerHTML = `<div class="card"><span class="spin"></span>Loading app…</div>`;
  let a = state.list.find(x => x.trackId === id) || state.seeds.find(x => x.trackId === id);
  if (!a) {
    try {
      const r = await fetch("https://itunes.apple.com/lookup?id=" + id);
      const j = await r.json(); const x = j.results[0];
      a = { trackId: x.trackId, trackName: x.trackName, sellerName: x.sellerName, primaryGenreName: x.primaryGenre, price: x.price || 0, averageUserRating: x.averageUserRating || 0, userRatingCount: x.userRatingCount || 0, releaseDate: x.releaseDate };
    } catch {
      $("#detail").innerHTML = `<div class="card empty">Couldn't load this app. You're likely offline — try again.</div>`;
      return;
    }
  }
  state.cur = a;
  const e = est(a), tag = estTag(a);
  const rankLine = a.rank ? ` · #${a.rank} ${esc(a.chart || "")}` : "";
  const velLine = a.rc_velocity > 0 ? ` · ▲${a.rc_velocity}/day ratings` : "";
  $("#detail").innerHTML = `<div class="card"><h2>${esc(a.trackName)}</h2>
    <p class="mut">${esc(a.sellerName)} · ${esc(a.primaryGenreName)} · ${a.price ? "$" + a.price : "Free"} · ★ ${(a.averageUserRating || 0).toFixed(1)} (${fmt(a.userRatingCount || 0)} ratings)${rankLine}${velLine}</p>
    <div class="warn">${a._est ? "Pipeline estimate (rank+velocity v1) — directional, not exact." : "Demo estimate — not real data. Formula: ratings × rating × price factor."}</div>
    <div class="grid"><div class="card"><b>Revenue (${tag})</b><br>${money(e.rev)}/mo</div><div class="card"><b>Downloads (${tag})</b><br>${fmt(e.dl)}/mo</div></div>
    <div class="tabs">${["ads", "viral", "kw", "onb"].map(t => `<button data-t="${t}"${t === state.tab ? ' class="on"' : ""}>${{ ads: "Ads", viral: "Viral", kw: "Keywords", onb: "Onboarding" }[t]}</button>`).join("")}</div>
    <div id="tab"></div></div>`;
  document.querySelectorAll(".tabs button").forEach(b => b.onclick = () => {
    state.tab = b.dataset.t;
    document.querySelectorAll(".tabs button").forEach(x => x.classList.toggle("on", x === b));
    renderTab();
  });
  renderTab();
  render();
  const p = new URLSearchParams(location.search);
  p.set("id", String(id));
  history.replaceState(null, "", "?" + p.toString());
  $("#detail").scrollIntoView({ behavior: "smooth" });
}

function renderTab() {
  const a = state.cur; if (!a) return;
  const t = state.tab;
  if (t === "ads") $("#tab").innerHTML = `<div class="empty">No ad library data. Production source: Meta Ad Library (token required).</div>`;
  if (t === "viral") $("#tab").innerHTML = `<div class="empty">No videos tracked. Production source: YouTube Data API.</div>`;
  if (t === "kw") {
    const kws = a.keywords || [];
    $("#tab").innerHTML = kws.length
      ? `<p class="mut">From title/genre. Not ranked search volume.</p><div class="card">${kws.map(esc).join(", ")}</div>`
      : `<div class="empty">No keywords for this app.</div>`;
  }
  if (t === "onb") {
    const shots = (a.screenshots || []).filter(u => String(u).startsWith("https://"));
    $("#tab").innerHTML = shots.length
      ? `<p class="mut">App Store screenshots (Apple lookup).</p>` + shots.map(u => `<img class="shot" src="${esc(u)}" alt="">`).join("")
      : `<div class="empty">No screenshots in lookup.</div>`;
  }
}

async function load() {
  let live = null;
  try {
    const r = await fetch("data/live.json");
    if (r.ok) { const j = await r.json(); if (j.length) live = j.map(norm); }
  } catch { /* no pipeline data yet */ }
  try {
    const r = await fetch("seed.json");
    state.seeds = live || (r.ok ? await r.json() : []);
  } catch { state.seeds = live || []; }
  if (!state.seeds.length) setStatus(`Couldn't load data — serve over http (python3 -m http.server).`);
  else {
    const newest = Math.max(...state.seeds.map(a => a.updated_ts || 0));
    state.live = live ? `Live pipeline data · updated ${Math.max(0, Math.round((Date.now() / 1000 - newest) / 3600))}h ago` : "seed demo";
    setStatus(statusLine(state.seeds.length, state.live));
  }
  state.list = state.seeds;
  refreshGenres(); render();
  const p = new URLSearchParams(location.search);
  const q = p.get("q");
  const id = p.get("id");
  if (q) { $("#q").value = q; await doSearch(q); }
  if (id) show(+id);
}

$("#go").onclick = () => doSearch();
$("#q").addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });
$("#genre").onchange = render;
$("#sort").onchange = render;
load();
