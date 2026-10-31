const D = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = (v, d=0) => Number(v).toLocaleString('en-US', {minimumFractionDigits:d, maximumFractionDigits:d});
const SEV = {bad:'需處理', warn:'需追蹤', info:'已知 / 不影響', ok:'正常'};
const TABS = [['cmp','兩端對照'], ['s2','Slot2 · 192.9.35.2'], ['s46','Slot46 · 192.9.35.46']];
let S = null, dir = 'tx', cdir = 'a';

$('#tabs').innerHTML = TABS.map(([k,l]) => `<button type="button" data-k="${k}" aria-pressed="false">${esc(l)}</button>`).join('');
$('#tabs').onclick = e => { const b = e.target.closest('button'); if (b) show(b.dataset.k); };

function show(k){
  document.querySelectorAll('#tabs button').forEach(b => b.setAttribute('aria-pressed', b.dataset.k === k));
  const cmp = k === 'cmp', src = cmp ? D.compare : D.slots[k];
  $('#view-slot').hidden = cmp; $('#view-cmp').hidden = !cmp;
  $('#title').textContent = src.title;
  $('#ids').innerHTML = src.ids.map(([a,b]) => `<span>${esc(a)} <b>${esc(b)}</b></span>`).join('');
  $('#vers').innerHTML = src.vers.map(([a,b]) => `<span>${esc(a)} <b>${esc(b)}</b></span>`).join('');
  $('#verdict').innerHTML = src.verdict.map(v => `<div><span class="eyebrow">${esc(v.k)}</span><span class="st s-${v.s}"><span class="dot bg-${v.s}"></span>${esc(v.st)}</span><span class="muted">${esc(v.d)}</span></div>`).join('');
  if (cmp) renderCmp(); else { S = D.slots[k]; renderSlot(); }
  try { history.replaceState(null, '', '#' + (cmp ? 'compare' : k === 's2' ? 'slot2' : 'slot46')); } catch (e) {}
}

/* ---------- findings with evidence ---------- */
function renderFinding(f){
  const li = a => a.map(x => `<li>${x}</li>`).join('');
  const sec = (cls, h, a) => a && a.length ? `<div class="ev-sec ${cls}"><h4>${h}</h4><ul>${li(a)}</ul></div>` : '';
  const raw = (f.ev || []).map(e => `<figure class="raw"><figcaption>${esc(e.file)}</figcaption><pre>${e.lines.map(([n,t]) => `<span class="ln">${n===''?'':esc(n)}</span>${esc(t)}`).join('\n')}</pre></figure>`).join('');
  return `<article class="fd"><span class="bar bg-${f.sev}"></span><div class="body">
    <div class="top"><h3>${esc(f.title)}</h3><span class="pill p-${f.sev}">${SEV[f.sev]}</span>${f.where?`<span class="pill p-info">${esc(f.where)}</span>`:''}${f.conf?`<span class="pill conf c-${f.conf==='已確認'?'y':'n'}">${esc(f.conf)}</span>`:''}</div>
    ${sec('facts','log 直接顯示',f.facts)}${sec('infer','推論（依據如下，非 log 直接寫明）',f.infer)}${sec('unk','log 沒有提供，無法判斷',f.unknown)}
    ${raw?`<details class="rawbox"><summary>原始資料（${f.ev.length} 個檔案摘錄，可人工核對）</summary>${raw}</details>`:''}</div></article>`;
}

/* ---------- single slot ---------- */
function drawThreads(){
  const arr = S.threads[dir], W=560, H=230, L=44, R=8, T=10, B=26, iw=W-L-R, ih=H-T-B;
  const max = 5000, bw = iw/arr.length, y = v => T + ih - v/max*ih;
  const avg = arr.reduce((a,b)=>a+b,0)/arr.length;
  let s = '';
  for (let v=0; v<=max; v+=1000) s += `<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${L-6}" y="${y(v)+4}" text-anchor="end">${v/1000}G</text>`;
  arr.forEach((v,i) => { s += `<rect x="${(L+i*bw+0.6).toFixed(2)}" y="${y(v).toFixed(2)}" width="${(bw-1.2).toFixed(2)}" height="${(T+ih-y(v)).toFixed(2)}" fill="var(--accent2)"><title>thread ${i}: ${fmt(v,1)} Mbps</title></rect>`; });
  s += `<line x1="${L}" x2="${W-R}" y1="${y(avg)}" y2="${y(avg)}" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="4 3"/><text x="${W-R}" y="${y(avg)-5}" text-anchor="end" style="fill:var(--accent)">平均 ${fmt(avg)} Mbps</text>`;
  [0,24,48,72,95].forEach(i => s += `<text x="${L+i*bw+bw/2}" y="${H-8}" text-anchor="middle">#${i}</text>`);
  $('#thr').innerHTML = s;
  const sd = Math.sqrt(arr.reduce((a,v)=>a+(v-avg)**2,0)/arr.length), tot = S.totals[dir];
  $('#thrstats').innerHTML = [
    [fmt(tot.gbps,1)+' Gbps','總吞吐量'], [fmt(Math.min(...arr))+' / '+fmt(Math.max(...arr)),'最小 / 最大 Mbps'],
    [fmt(sd/avg*100,1)+' %','thread 變異係數'], [fmt(tot.mb/1e6,1)+' TB','傳輸總量']
  ].map(([v,k]) => `<div><span class="v">${v}</span><span class="k">${k}</span></div>`).join('');
  $('#b-tx').setAttribute('aria-pressed', dir==='tx'); $('#b-rx').setAttribute('aria-pressed', dir==='rx');
}
$('#b-tx').onclick = () => { dir = 'tx'; drawThreads(); };
$('#b-rx').onclick = () => { dir = 'rx'; drawThreads(); };

function renderSlot(){
  $('#kpis').innerHTML = S.kpis.map(k => `<div class="kpi"><span class="eyebrow">${esc(k.k)}</span><span class="v">${k.v}<small>${esc(k.u||'')}</small></span><span class="d">${esc(k.d)}</span></div>`).join('');
  $('#sevlegend').innerHTML = ['bad','warn','info'].map(s => `<span class="pill p-${s}">${SEV[s]}</span>`).join('');
  $('#findings').innerHTML = S.findings.map(renderFinding).join('');
  $('#timeline').innerHTML = S.timeline.map(e => `<div class="row"><span class="t">${esc(e.t)}</span><span class="m"><span class="dot bg-${e.s}"></span></span><span class="x"><b>${esc(e.title)}</b>${e.d?`<span>${esc(e.d)}</span>`:''}</span></div>`).join('');
  $('#matrix').innerHTML = S.checks.map(c => {
    const cell = v => v ? `<span class="pill p-${v[0]}">${esc(v[1])}</span>` : '<span class="muted">—</span>';
    return `<tr><td>${esc(c.name)}</td><td>${cell(c.pre)}</td><td>${cell(c.post)}</td><td class="muted">${c.note}</td></tr>`;
  }).join('');
  drawThreads();

  const t0 = Date.parse(S.window.start), t1 = Date.parse(S.window.end), sx = Date.parse(S.stress.start), ex = Date.parse(S.stress.end);
  $('#sn-sub').textContent = `109 個感測器、每個約 ${S.nmax} 筆，藍色區段為 NTTTCP 執行期間`;
  $('#minis').innerHTML = S.key.map(k => {
    const pts = S.series[k.name] || [], st = S.statsMap[k.name];
    const W=260, H=70, T=4, B=4, x = t => (Date.parse(t)-t0)/(t1-t0)*W;
    const lo = st.min, hi = st.max, pad=(hi-lo)*0.08||1;
    const y = v => T + (H-T-B) - (v-(lo-pad))/((hi+pad)-(lo-pad))*(H-T-B);
    const d = pts.map((p,i) => `${i?'L':'M'}${x(p[0]).toFixed(1)} ${y(p[1]).toFixed(1)}`).join('');
    const last = pts[pts.length-1];
    const band = `<rect x="${((sx-t0)/(t1-t0)*W).toFixed(1)}" y="0" width="${((ex-sx)/(t1-t0)*W).toFixed(1)}" height="${H}" fill="var(--accent-soft)"/>`;
    return `<div class="mini"><div class="hd"><span class="nm" title="${esc(k.name)}">${esc(k.label)}</span><span class="val">${fmt(st.max,1)}<span class="muted" style="font-size:11px"> max ${esc(k.u)}</span></span></div>
      <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:70px" role="img" aria-label="${esc(k.label)} 趨勢">${band}<path d="${d}" fill="none" stroke="var(--accent)" stroke-width="1.4" vector-effect="non-scaling-stroke"/>${last?`<circle cx="${x(last[0])}" cy="${y(last[1])}" r="2.4" fill="var(--accent)"/>`:''}</svg>
      <span class="muted mono" style="font-size:11px">min ${fmt(st.min,1)} · avg ${fmt(st.avg,1)}</span></div>`;
  }).join('');
  const units = [...new Set(S.stats.map(s => s.unit))], cur = $('#unit').value;
  $('#unit').innerHTML = '<option value="">全部單位</option>' + units.map(u => `<option value="${esc(u)}">${esc(u)}</option>`).join('');
  $('#unit').value = units.includes(cur) ? cur : '';
  drawStats();
}
function drawStats(){
  if (!S) return;
  const q = $('#q').value.trim().toLowerCase(), u = $('#unit').value;
  const rows = S.stats.filter(s => (!u || s.unit===u) && (!q || s.name.toLowerCase().includes(q)));
  const umax = {}; S.stats.forEach(s => umax[s.unit] = Math.max(umax[s.unit]||0, s.max));
  $('#stbody').innerHTML = rows.length ? rows.map(s => {
    const m = umax[s.unit]||1, a = Math.max(0,s.min)/m*100, b = Math.max(0,s.max)/m*100;
    const flag = s.n < S.nmax ? ` <span class="pill p-warn">缺 ${S.nmax-s.n} 筆</span>` : '';
    return `<tr><td class="mono" style="font-size:12.5px">${esc(s.name)}${flag}</td><td class="muted">${esc(s.unit)}</td><td class="n">${s.n}</td><td class="n">${fmt(s.min,2)}</td><td class="n">${fmt(s.avg,2)}</td><td class="n">${fmt(s.max,2)}</td><td><div class="sbar"><i style="left:${a}%;width:${Math.max(1,b-a)}%"></i></div></td></tr>`;
  }).join('') : '<tr><td colspan="7" class="muted">沒有符合的感測器，請換個關鍵字或單位。</td></tr>';
}
$('#q').oninput = drawStats; $('#unit').onchange = drawStats;

/* ---------- compare ---------- */
const PAIRS = {
  a: {x:() => D.slots.s2.threads.tx,  y:() => D.slots.s46.threads.rx, xl:'Slot2 TX', yl:'Slot46 RX'},
  b: {x:() => D.slots.s46.threads.tx, y:() => D.slots.s2.threads.rx,  xl:'Slot46 TX', yl:'Slot2 RX'}
};
function drawScat(){
  const P = PAIRS[cdir], X = P.x(), Y = P.y(), W=400, H=300, L=46, R=10, T=10, B=34, iw=W-L-R, ih=H-T-B, lo=1000, hi=4500;
  const sx = v => L + (v-lo)/(hi-lo)*iw, sy = v => T + ih - (v-lo)/(hi-lo)*ih;
  let s = '';
  for (let v=1000; v<=4500; v+=500) s += `<line x1="${L}" x2="${W-R}" y1="${sy(v)}" y2="${sy(v)}" stroke="var(--grid)"/><line y1="${T}" y2="${T+ih}" x1="${sx(v)}" x2="${sx(v)}" stroke="var(--grid)"/>` + (v%1000===0 ? `<text x="${L-6}" y="${sy(v)+4}" text-anchor="end">${v/1000}G</text><text x="${sx(v)}" y="${T+ih+14}" text-anchor="middle">${v/1000}G</text>` : '');
  s += `<line x1="${sx(lo)}" y1="${sy(lo)}" x2="${sx(hi)}" y2="${sy(hi)}" stroke="var(--accent)" stroke-dasharray="4 3"/>`;
  X.forEach((v,i) => s += `<circle cx="${sx(v).toFixed(1)}" cy="${sy(Y[i]).toFixed(1)}" r="3" fill="var(--accent2)" fill-opacity=".75"><title>thread ${i}: ${fmt(v,1)} → ${fmt(Y[i],1)} Mbps</title></circle>`);
  s += `<text x="${L+iw/2}" y="${H-4}" text-anchor="middle">${P.xl}（Mbps）</text><text transform="rotate(-90)" x="${-(T+ih/2)}" y="11" text-anchor="middle">${P.yl}</text>`;
  $('#scat').innerHTML = s;
  const n = X.length, mx = X.reduce((a,b)=>a+b,0)/n, my = Y.reduce((a,b)=>a+b,0)/n;
  let sxy=0, sxx=0, syy=0, maxd=0; X.forEach((v,i) => { sxy += (v-mx)*(Y[i]-my); sxx += (v-mx)**2; syy += (Y[i]-my)**2; maxd = Math.max(maxd, Math.abs(v-Y[i])); });
  $('#scatstats').innerHTML = [[(sxy/Math.sqrt(sxx*syy)).toFixed(6),'相關係數 r'], [fmt(maxd,3),'單一 thread 最大差 Mbps'], [fmt(mx,1),P.xl+' 平均'], [fmt(my,1),P.yl+' 平均']].map(([v,k]) => `<div><span class="v">${v}</span><span class="k">${k}</span></div>`).join('');
  $('#c-a').setAttribute('aria-pressed', cdir==='a'); $('#c-b').setAttribute('aria-pressed', cdir==='b');
}
$('#c-a').onclick = () => { cdir = 'a'; drawScat(); };
$('#c-b').onclick = () => { cdir = 'b'; drawScat(); };

function renderCmp(){
  const C = D.compare;
  $('#xrows').innerHTML = C.cross.map(r => {
    const ok = Math.abs(r.diffPct) < 0.01;
    return `<tr><td>${esc(r.dir)}</td><td class="n">${fmt(r.tx,1)}</td><td class="n">${fmt(r.rx,1)}</td><td class="n">${r.diffPct>=0?'+':''}${r.diffPct.toFixed(4)} %</td><td class="n">${fmt(r.txMB)}<br>${fmt(r.rxMB)}</td><td><span class="pill ${ok?'p-ok':'p-warn'}">${ok?'吻合':'有差距'}</span></td></tr>`;
  }).join('');
  $('#cmpfind').innerHTML = C.findings.map(renderFinding).join('');
  $('#cmprows').innerHTML = C.rows.map(r => r.grp
    ? `<tr class="grp"><td colspan="4">${esc(r.grp)}</td></tr>`
    : `<tr><td>${esc(r.k)}</td><td class="${r.mono===false?'':'mono'}">${esc(r.a)}</td><td class="${r.mono===false?'':'mono'}">${esc(r.b)}</td><td>${r.diff?'<span class="pill p-warn">不同</span>':'<span class="muted">相同</span>'}${r.note?` <span class="muted">${r.note}</span>`:''}</td></tr>`).join('');
  drawScat();
}

const h = (location.hash || '').replace('#','');
show(h === 'slot2' ? 's2' : h === 'slot46' ? 's46' : 'cmp');
