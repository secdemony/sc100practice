const TOTAL_Q = QUESTIONS.length;

const QMAP = {};
QUESTIONS.forEach(q => QMAP[q.n] = q);

// ---------------------------------------------------------------------------
// SECTIONS AND NUMBERING
//
// The source PDF numbers each of its three sections from 1, so "question 7"
// is only unique once you also say which section it belongs to. Questions are
// therefore addressed the way the document addresses them — section + number —
// and `q.n` is an internal sequential id, used for ordering and saved state and
// never shown.
// ---------------------------------------------------------------------------
const SECTIONS = [
  {key:'cs1', label:'Case Study 1: Fabrikam, Inc.', short:'Fabrikam'},
  {key:'cs2', label:'Case Study 2: Litware, Inc.',  short:'Litware'},
  {key:'std', label:'Standalone Questions',         short:'Standalone'}
];
const SECTION_MAX = {};
SECTIONS.forEach(s=>{
  SECTION_MAX[s.key] = QUESTIONS.reduce((m,q)=> q.sec === s.key ? Math.max(m, q.num) : m, 0);
});
function sectionOf(key){ return SECTIONS.find(s => s.key === key); }

// How a question is cited anywhere outside its own screen.
function citation(q){
  return q.sec === 'std' ? `Standalone ${q.num}` : `${sectionOf(q.sec).short} ${q.num}`;
}

// ---------------------------------------------------------------------------
// DOMAIN WEIGHTING (for the 50-question weighted practice exam)
//
// The bank's `c` field already holds the four official SC-100 skill-area names
// exactly as Microsoft words them, so the mapping is identity — but it is kept
// explicit so a future edit that adds a differently-worded label falls through
// to domain 1 rather than silently vanishing from every weighted draw.
//
// Target counts are pre-computed from the midpoint of each published weight
// range against a fixed 50-question exam (22.5/27.5/27.5/22.5% of 50 =
// 11.25/13.75/13.75/11.25, rounded to 11/14/14/11 — which sums to exactly 50)
// rather than computed at draw time, so the breakdown shown on the setup
// screen always matches what actually gets drawn.
// ---------------------------------------------------------------------------
const DOMAIN_WEIGHTS = [
  {num:1, name:'Design solutions that align with security best practices and priorities', pct:'20–25%', target:11},
  {num:2, name:'Design security operations, identity, and compliance capabilities',        pct:'25–30%', target:14},
  {num:3, name:'Design security solutions for infrastructure',                             pct:'25–30%', target:14},
  {num:4, name:'Design security solutions for applications and data',                      pct:'20–25%', target:11}
];

const CATEGORY_DOMAIN = {};
DOMAIN_WEIGHTS.forEach(d => { CATEGORY_DOMAIN[d.name] = d.num; });
function domainOf(q){ return CATEGORY_DOMAIN[q.c] || 1; }

function shuffled(arr){
  const a = arr.slice();
  for(let i=a.length-1;i>0;i--){
    const j = Math.floor(Math.random()*(i+1));
    [a[i],a[j]] = [a[j],a[i]];
  }
  return a;
}

// Draws a 50-question set proportioned to DOMAIN_WEIGHTS, from scorable items
// only — a weighted exam is a score, so unscorable items have no place in it.
// Returns the shuffled order plus a per-domain {picked, target} tally so the UI
// can say so plainly if a skill area's pool ever runs short.
function buildWeightedOrder(){
  const tally = [];
  let combined = [];
  DOMAIN_WEIGHTS.forEach(d=>{
    const pool = QUESTIONS.filter(q => isScorable(q) && domainOf(q) === d.num).map(q => q.n);
    const picked = shuffled(pool).slice(0, d.target);
    tally.push({num:d.num, name:d.name, target:d.target, picked:picked.length});
    combined = combined.concat(picked);
  });
  return {order: shuffled(combined), tally};
}

// Storage keys carry a version suffix: an earlier build numbered questions
// differently, so state saved against those numbers would now point at the
// wrong items. Bumping the key ignores it rather than silently mismapping it.
const SESSION_KEY = 'sc100-active-session-v2';
const HISTORY_KEY = 'sc100-history-v2';
const WRONG_POOL_KEY = 'sc100-wrong-pool-v2';
const AUTH_KEY = 'sc100-authed';
// Microsoft scores its role-based exams out of 1000 and passes at 700, so a
// practice run is marked "on track" at 70% or better.
const PASS_THRESHOLD = 70;

// ---------------------------------------------------------------------------
// SHARED ACCESS CODE — change this to whatever you want the group password
// to be. This is a simple front-door gate (not real security): anyone who
// views the page source can find this value. It's meant to keep casual
// visitors and search engines out, not to protect sensitive data.
// ---------------------------------------------------------------------------
const ACCESS_CODE = 'SecPlus2026';

let state = {
  screen: 'loading', // loading | gate | setup | exam | finished | review | history
  session: null,
  historyList: [],
  wrongPool: [],
  caseOpen: {},
  loadError: null
};

function letterOf(i){ return String.fromCharCode(65+i); }

function rangeLabelFor(s){
  if(s.isWrongPool) return `All-time missed · ${s.total} question${s.total===1?'':'s'}`;
  if(s.isRetake) return `Retake · ${s.total} question${s.total===1?'':'s'} (incorrect & skipped)`;
  if(s.isWeighted) return `Weighted exam · ${s.total} questions (by skill-area %)`;
  if(s.secKey === 'all') return `All sections · ${s.total} questions`;
  const sec = sectionOf(s.secKey);
  const label = sec ? sec.label : 'Questions';
  return `${label} ${s.rangeStart}–${s.rangeEnd}`;
}

// History rows and live sessions describe their range with the same fields, so
// both go through rangeLabelFor via this shim.
function rangeLabelOf(o){
  return rangeLabelFor({
    isWrongPool:o.isWrongPool, isRetake:o.isRetake, isWeighted:o.isWeighted,
    secKey:o.secKey, rangeStart:o.rangeStart, rangeEnd:o.rangeEnd,
    total:(o.total != null ? o.total : (o.order ? o.order.length : 0))
  });
}

function parseAnswerLetters(a){
  if(!a) return [];
  return a.split(/[,\s]+/).filter(Boolean);
}

// Formats a millisecond duration as H:MM:SS (or M:SS under an hour).
function formatDuration(ms){
  const totalSec = Math.max(0, Math.round(ms/1000));
  const h = Math.floor(totalSec/3600);
  const m = Math.floor((totalSec%3600)/60);
  const s = totalSec%60;
  const pad = n => String(n).padStart(2,'0');
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

// ---------------------------------------------------------------------------
// GRADING
//
// Three question shapes exist:
//   choice - q.o + q.a, an ordinary multiple-choice item
//   match  - q.boxes, a Microsoft "answer area" item. The source gives a label
//            and correct value per drop-down but never the option list, so each
//            drop-down offers that item's own values shuffled.
//   info   - neither. The source PDF records no gradeable question for it, so
//            it is shown for reading and never scored.
// Every place that asks "was this answered?" or "was this right?" goes through
// these helpers so the three shapes can never drift apart.
// ---------------------------------------------------------------------------

function isMatch(q){ return !!(q && q.boxes && q.boxes.length); }
function isChoice(q){ return !!(q && q.o && q.o.length); }
// An item counts towards a score only if there is something to get right.
function isScorable(q){ return isChoice(q) || isMatch(q); }
function isInfo(q){ return !!q && !isScorable(q); }

// Does every drop-down on this item carry its own real choice list? Items whose
// options were supplied from outside the PDF do; ones recovered from the PDF
// alone do not, because the source never recorded the alternatives.
function hasRealOptions(q){
  return isMatch(q) && q.boxes.every(b => b.options && b.options.length);
}

// The choices for one drop-down. A supplied option list is used as given — that
// is the list the exam shows, in the order it shows it. Otherwise the item falls
// back to a matching exercise over its own correct values (see matchOptions).
function boxOptions(q, idx){
  const box = q.boxes[idx];
  return (box.options && box.options.length) ? box.options : matchOptions(q);
}

// Fallback for items recovered from the PDF: every drop-down offers the same
// list, the correct values of all of that item's own boxes. The source never
// supplies distractors, so inventing them would mean inventing exam content —
// instead the item becomes a self-contained matching exercise built only from
// what the source states.
//
// The order is shuffled but STABLE: seeded off the internal id so the same item
// always presents its choices in the same order, across re-renders and across a
// save/resume, and never in the giveaway order of the answer key.
function matchOptions(q){
  // A few items give two boxes the same correct value; listing it twice in the
  // drop-down would look like a rendering fault, and grading compares values
  // rather than positions, so one entry serves both boxes.
  const vals = [...new Set(q.boxes.map(b => b.value))];
  // Small deterministic PRNG (mulberry32) seeded from the question's id.
  let t = (q.n * 2654435761) >>> 0;
  const rnd = ()=>{
    t = (t + 0x6D2B79F5) >>> 0;
    let x = Math.imul(t ^ (t >>> 15), 1 | t);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
  for(let i=vals.length-1;i>0;i--){
    const j = Math.floor(rnd()*(i+1));
    [vals[i],vals[j]] = [vals[j],vals[i]];
  }
  return vals;
}

// Matching responses live in rec.boxes as {boxIndex: value}.
function matchResponse(rec){ return (rec && rec.boxes) ? rec.boxes : {}; }

function matchCellCorrect(q, idx, rec){
  const picked = matchResponse(rec)[idx];
  return !!picked && picked === q.boxes[idx].value;
}

// Number of drop-downs answered correctly, and the total number of drop-downs.
function matchScore(q, rec){
  let got = 0;
  q.boxes.forEach((b, i)=>{ if(matchCellCorrect(q, i, rec)) got++; });
  return {got, total: q.boxes.length};
}

// Did the candidate put anything down at all? Blank counts as skipped, not
// wrong. An info item has nothing to put down, so it is never "answered".
function hasResponse(q, rec){
  if(isInfo(q)) return false;
  if(isMatch(q)){
    const resp = matchResponse(rec);
    return q.boxes.some((b, i) => !!resp[i]);
  }
  return !!(rec && rec.selected && rec.selected.length > 0);
}

// Matching items are all-or-nothing: every drop-down must be right, which is
// how Microsoft scores its own answer-area items.
function isCorrectAnswer(q, rec){
  if(isInfo(q)) return false;
  if(!hasResponse(q, rec)) return false;
  if(isMatch(q)){
    const {got, total} = matchScore(q, rec);
    return got === total;
  }
  return arraysEqualAsSets(rec.selected, parseAnswerLetters(q.a));
}

function el(tag, attrs, children){
  const e = document.createElement(tag);
  if(attrs){
    for(const k in attrs){
      const v = attrs[k];
      if(v === null || v === undefined) continue; // don't set attributes explicitly passed as null/undefined
      if(k === 'class') e.className = v;
      else if(k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v);
    }
  }
  (children||[]).forEach(c => {
    if(c === null || c === undefined) return;
    if(typeof c === 'string') e.appendChild(document.createTextNode(c));
    else e.appendChild(c);
  });
  return e;
}

// Question text, explanations and case narratives all arrive as an ordered list
// of nodes — {p: text} for a paragraph, {img: file} for a diagram — so prose and
// exhibits render in the order the exam presents them.
function renderNodes(target, nodes, imgClass){
  (nodes||[]).forEach(node=>{
    if(node.img){
      // Scaled to the column by default. Many exhibits are screenshots of
      // tables whose text is unreadable at that size, so clicking shows the
      // image at full resolution and lets the figure scroll sideways.
      const fig = el('figure',{class:'exhibit-wrap ' + (imgClass||'')});
      const cap = el('figcaption',{},['Click to enlarge']);
      fig.appendChild(el('img',{
        class:'exhibit', src:node.img, alt:'Exhibit from the question', loading:'lazy',
        width: node.w ? String(node.w) : null, height: node.h ? String(node.h) : null,
        onclick: ()=>{
          const on = fig.classList.toggle('zoomed');
          cap.textContent = on ? 'Full size · scroll sideways · click to fit' : 'Click to enlarge';
        }
      }));
      fig.appendChild(cap);
      target.appendChild(fig);
    } else if(node.p){
      // A bullet keeps its own line; the source writes requirement lists this way.
      const cls = node.p.startsWith('•') ? 'qpara bullet' : 'qpara';
      target.appendChild(el('div',{class:cls}, linkify(node.p)));
    }
  });
}

// Explanations in the source are often nothing but Microsoft Learn links, so
// they are turned into real anchors. Built with DOM nodes rather than innerHTML
// so nothing in the bank can be interpreted as markup.
function linkify(text){
  const out = [];
  (text||'').split(/(\s+)/).forEach(part=>{
    if(/^https?:\/\/\S+$/.test(part)){
      out.push(el('a',{href:part, target:'_blank', rel:'noopener noreferrer'},[part]));
    } else if(part){
      out.push(document.createTextNode(part));
    }
  });
  return out;
}


// Persistence layer: uses Claude.ai's window.storage when running inside an
// artifact, and transparently falls back to the browser's own localStorage
// when this file is hosted anywhere else (GitHub Pages, Netlify, a local
// file://), so "save progress" keeps working either way.
const storageBackend = (typeof window !== 'undefined' && window.storage)
  ? window.storage
  : {
      async get(key){
        const v = localStorage.getItem(key);
        return v !== null ? {key, value: v} : null;
      },
      async set(key, value){
        localStorage.setItem(key, value);
        return {key, value};
      },
      async delete(key){
        localStorage.removeItem(key);
        return {key, deleted: true};
      }
    };

async function loadSession(){
  try{
    const r = await storageBackend.get(SESSION_KEY, false);
    return r ? JSON.parse(r.value) : null;
  }catch(e){ return null; }
}
async function saveSession(session){
  try{
    await storageBackend.set(SESSION_KEY, JSON.stringify(session), false);
  }catch(e){ console.error('save session failed', e); }
}
async function clearSession(){
  try{ await storageBackend.delete(SESSION_KEY, false); }catch(e){}
}
async function loadHistory(){
  try{
    const r = await storageBackend.get(HISTORY_KEY, false);
    return r ? JSON.parse(r.value) : [];
  }catch(e){ return []; }
}
async function saveHistory(list){
  try{
    await storageBackend.set(HISTORY_KEY, JSON.stringify(list.slice(0,100)), false);
  }catch(e){ console.error('save history failed', e); }
}

// ---------------------------------------------------------------------------
// ALL-TIME MISSED-QUESTION POOL
//
// The pool is CUMULATIVE and ADDITIVE. Every question answered incorrectly or
// left unanswered — in any run, across any number of runs, including runs that
// are abandoned part-way through — is added and STAYS in the list. Nothing is
// ever removed automatically; the only things that take a question out are the
// explicit user actions ("Clear list", or "Remove correct from missed list"
// on the results screen). Items that cannot be scored never enter it.
// ---------------------------------------------------------------------------

function normalizeWrongPool(arr){
  const seen = new Set();
  const out = [];
  (Array.isArray(arr) ? arr : []).forEach(v => {
    const n = Number(v);
    if(!Number.isFinite(n) || seen.has(n)) return;
    if(!isScorable(QMAP[n])) return;
    seen.add(n);
    out.push(n);
  });
  return out.sort((a,b)=>a-b);
}

async function loadWrongPool(){
  try{
    const r = await storageBackend.get(WRONG_POOL_KEY, false);
    return normalizeWrongPool(r ? JSON.parse(r.value) : []);
  }catch(e){ return []; }
}
async function saveWrongPool(arr){
  try{
    await storageBackend.set(WRONG_POOL_KEY, JSON.stringify(arr), false);
  }catch(e){ console.error('save wrong pool failed', e); }
}

// Merge question ids into the persistent pool. Never removes. Writes to storage
// only when something actually changed, so this is cheap enough to call once
// per graded question. Returns true if the pool grew.
async function addToWrongPool(qns){
  const list = Array.isArray(qns) ? qns : [qns];
  const merged = normalizeWrongPool((state.wrongPool || []).concat(list));
  if(merged.length === (state.wrongPool || []).length) return false;
  state.wrongPool = merged;
  await saveWrongPool(state.wrongPool);
  return true;
}

// The only removal path other than a full clear — driven by an explicit click.
async function removeFromWrongPool(qns){
  const drop = new Set((Array.isArray(qns) ? qns : [qns]).map(Number));
  const kept = (state.wrongPool || []).filter(n => !drop.has(n));
  if(kept.length === (state.wrongPool || []).length) return false;
  state.wrongPool = kept;
  await saveWrongPool(state.wrongPool);
  return true;
}

// Is this recorded answer a miss (wrong OR never answered)? Empty selection
// counts as a miss for pool purposes even though it scores as "skipped".
// Unscorable items are never misses.
function isMissedAnswer(qn, rec){
  const q = QMAP[qn];
  return isScorable(q) && !isCorrectAnswer(q, rec);
}

async function checkAuthed(){
  try{
    const r = await storageBackend.get(AUTH_KEY, false);
    return !!(r && r.value === '1');
  }catch(e){ return false; }
}
async function setAuthed(){
  try{ await storageBackend.set(AUTH_KEY, '1', false); }catch(e){}
}

// Handle for the exam screen's live-ticking clock. It updates its own DOM node
// on a 1s interval rather than going through the full render() cycle, since a
// full re-render every second would rebuild dropdowns and could disturb
// in-progress selections. Every render() pass clears it first: if the exam
// screen is being (re)drawn, renderExam() starts a fresh one pointed at the
// new node; if we've navigated away, the old node is simply gone.
let examTimerInterval = null;

function render(){
  if(examTimerInterval){ clearInterval(examTimerInterval); examTimerInterval = null; }
  const app = document.getElementById('app');
  app.innerHTML = '';
  if(state.screen === 'loading'){
    app.appendChild(el('div',{class:'card'},[el('div',{class:'pad empty-note'},['Loading…'])]));
    return;
  }
  if(state.screen === 'gate') return renderGate(app);
  if(state.screen === 'setup') return renderSetup(app);
  if(state.screen === 'exam') return renderExam(app);
  if(state.screen === 'finished') return renderFinished(app);
  if(state.screen === 'review') return renderReview(app);
  if(state.screen === 'history') return renderHistory(app);
}

// ---------------- GATE ----------------
function renderGate(app){
  const card = el('div',{class:'card'});
  const pad = el('div',{class:'pad'});
  pad.appendChild(el('div',{class:'top-title'},['Microsoft SC-100 · Cybersecurity Architect Expert']));
  pad.appendChild(el('h1',{},['Access Required']));
  pad.appendChild(el('div',{class:'subtitle'},['Enter the access code to continue.']));

  pad.appendChild(el('label',{},['Access code']));
  const codeInput = el('input',{type:'password', id:'gateInput', placeholder:'Access code'});
  pad.appendChild(codeInput);

  const errDiv = el('div',{class:'err', style:'display:none;'},['Incorrect code — try again.']);
  pad.appendChild(errDiv);

  const tryEnter = async ()=>{
    if(codeInput.value === ACCESS_CODE){
      await setAuthed();
      state.session = await loadSession();
      state.historyList = await loadHistory();
      state.wrongPool = await loadWrongPool();
      state.screen = 'setup';
      render();
    } else {
      errDiv.style.display = 'block';
      codeInput.value = '';
    }
  };

  codeInput.addEventListener('keydown', (e)=>{ if(e.key === 'Enter') tryEnter(); });

  pad.appendChild(el('div',{class:'btn-row'},[
    el('button',{class:'btn btn-primary btn-block', onclick: tryEnter},['Enter'])
  ]));

  card.appendChild(pad);
  app.appendChild(card);
  if(codeInput.focus) codeInput.focus();
}

// ---------------- SETUP ----------------

// The ids of every question in a chosen section and source-number range, in
// document order. `secKey` of 'all' spans the whole bank.
function idsInRange(secKey, start, end, includeUnscored){
  return QUESTIONS.filter(q=>{
    if(secKey !== 'all'){
      if(q.sec !== secKey) return false;
      if(q.num < start || q.num > end) return false;
    }
    return includeUnscored || isScorable(q);
  }).map(q => q.n);
}

function renderSetup(app){
  const card = el('div',{class:'card'});
  const pad = el('div',{class:'pad'});
  pad.appendChild(el('div',{class:'top-title'},['Microsoft SC-100 · Cybersecurity Architect Expert']));
  pad.appendChild(el('h1',{},['Practice Exam Simulator']));
  pad.appendChild(el('div',{class:'subtitle'},[
    `All ${TOTAL_Q} questions from the source set · ${SCORABLE_COUNT} of them scored`
  ]));

  if(state.session && !state.session.completed){
    const s = state.session;
    const answered = s.order.filter(qn => hasResponse(QMAP[qn], (s.answers||{})[qn])).length;
    const at = QMAP[s.order[s.currentIndex]];
    pad.appendChild(el('div',{class:'resume-box'},[
      el('div',{class:'title'},[`Resume in progress: ${s.candidateName || 'Unnamed'}`]),
      el('div',{class:'sub'},[`${rangeLabelOf(s)} · ${answered}/${s.order.length} answered · currently at ${citation(at)}`]),
      el('div',{class:'btn-row', style:'margin-top:0;'},[
        el('button',{class:'btn btn-primary', onclick: ()=>{ state.screen='exam'; render(); }},['Resume exam']),
        el('button',{class:'btn btn-outline', onclick: async ()=>{
          if(confirm('Discard the in-progress exam? This cannot be undone.')){
            await clearSession();
            state.session = null;
            render();
          }
        }},['Discard'])
      ])
    ]));
  }

  pad.appendChild(el('label',{},['Candidate name']));
  const nameInput = el('input',{type:'text', id:'nameInput', placeholder:'e.g. Jordan Diaz'});
  pad.appendChild(nameInput);

  // ---- Section, then a range in that section's own numbering ----
  pad.appendChild(el('label',{},['Section']));
  const selStyle = 'width:100%;padding:10px 12px;border:1px solid var(--gray-300);border-radius:7px;font-size:14.5px;margin-bottom:16px;font-family:inherit;';
  const secSel = el('select',{id:'secSelect', style:selStyle},[
    el('option',{value:'all'},[`All sections (${TOTAL_Q} questions, in document order)`])
  ].concat(SECTIONS.map(s =>
    el('option',{value:s.key},[`${s.label} (1–${SECTION_MAX[s.key]})`])
  )));
  pad.appendChild(secSel);

  const rangeRow = el('div',{class:'row'},[
    el('div',{},[
      el('label',{},['Start question #']),
      el('input',{type:'number', id:'startInput', min:'1', value:'1'})
    ]),
    el('div',{},[
      el('label',{},['End question #']),
      el('input',{type:'number', id:'endInput', min:'1', value:'1'})
    ])
  ]);
  pad.appendChild(rangeRow);

  const presetWrap = el('div',{class:'presets'});
  pad.appendChild(presetWrap);

  const rangeNote = el('div',{class:'helper'});
  pad.appendChild(rangeNote);

  // Range inputs are meaningless spanning three independently-numbered
  // sections, so "All sections" hides them and takes the whole bank.
  function syncSection(){
    const key = secSel.value;
    const startEl = document.getElementById('startInput');
    const endEl = document.getElementById('endInput');
    presetWrap.innerHTML = '';
    if(key === 'all'){
      rangeRow.style.display = 'none';
      rangeNote.textContent = `All ${TOTAL_Q} questions, in the order they appear in the source: ` +
        SECTIONS.map(s => `${s.label} 1–${SECTION_MAX[s.key]}`).join(', ') + '.';
      return;
    }
    const max = SECTION_MAX[key];
    rangeRow.style.display = '';
    startEl.max = String(max); endEl.max = String(max);
    startEl.value = '1'; endEl.value = String(max);
    rangeNote.textContent = `${sectionOf(key).label} is numbered 1–${max} in the source PDF, and those are the numbers used here.`;
    const presets = [[`All (1–${max})`, 1, max]];
    for(let a=1; a<=max; a+=50){
      const b = Math.min(a+49, max);
      if(!(a === 1 && b === max)) presets.push([`${a}–${b}`, a, b]);
    }
    presets.forEach(p=>{
      presetWrap.appendChild(el('button',{class:'preset-btn', onclick: ()=>{
        startEl.value = p[1]; endEl.value = p[2];
      }},[p[0]]));
    });
  }
  secSel.addEventListener('change', syncSection);

  pad.appendChild(el('label',{},['Question order']));
  const orderSel = el('select',{id:'orderSelect', style:selStyle},[
    el('option',{value:'sequential'},['Sequential (document order)']),
    el('option',{value:'random'},['Shuffled (random order)'])
  ]);
  pad.appendChild(orderSel);

  const incWrap = el('label',{class:'check-row'});
  const incBox = el('input',{type:'checkbox', id:'includeUnscored'});
  incBox.checked = true;
  incWrap.appendChild(incBox);
  incWrap.appendChild(el('span',{},[
    `Include the ${UNSCORED_COUNT} answer-area items (hotspot, drag-and-drop, yes/no). ` +
    'The source draws their answers rather than writing them, so they are shown ' +
    'with the recorded answer but never counted for or against your score.'
  ]));
  pad.appendChild(incWrap);

  const errDiv = el('div',{class:'err', style:'display:none;'});
  pad.appendChild(errDiv);

  pad.appendChild(el('div',{class:'btn-row'},[
    el('button',{class:'btn btn-primary btn-block', onclick: async ()=>{
      const name = nameInput.value.trim();
      if(!name){ errDiv.textContent = 'Please enter the candidate name.'; errDiv.style.display='block'; return; }
      const key = secSel.value;
      let start = 1, end = 0;
      if(key === 'all'){
        end = TOTAL_Q;
      } else {
        start = parseInt(document.getElementById('startInput').value,10);
        end = parseInt(document.getElementById('endInput').value,10);
        const max = SECTION_MAX[key];
        if(!start || !end || start<1 || end>max || start>end){
          errDiv.textContent = `Enter a valid range between 1 and ${max} for ${sectionOf(key).label}.`;
          errDiv.style.display='block'; return;
        }
      }
      let nums = idsInRange(key, start, end, incBox.checked);
      if(nums.length===0){
        errDiv.textContent = 'No questions in that range.'; errDiv.style.display='block'; return;
      }
      if(orderSel.value === 'random') nums = shuffled(nums);
      const session = {
        candidateName: name,
        secKey: key,
        rangeStart: key === 'all' ? null : start,
        rangeEnd: key === 'all' ? null : end,
        order: nums,
        currentIndex: 0,
        answers: {},
        flags: {},
        startedAt: new Date().toISOString(),
        completed: false
      };
      state.session = session;
      await saveSession(session);
      state.screen = 'exam';
      render();
    }},['Start exam'])
  ]));

  card.appendChild(pad);
  app.appendChild(card);
  syncSection();

  // ---- Weighted 50-question practice exam ----
  const weightedCard = el('div',{class:'card'});
  const weightedPad = el('div',{class:'pad'});
  weightedPad.appendChild(el('h2',{style:'margin-bottom:2px;'},['Weighted Practice Exam (50 Questions)']));
  weightedPad.appendChild(el('div',{class:'subtitle'},[
    'Randomly draws 50 scored questions proportioned to the official SC-100 skill-area weights, then shuffles the mix.'
  ]));
  weightedPad.appendChild(el('div',{class:'domain-weight-list'}, DOMAIN_WEIGHTS.map(d=>
    el('div',{class:'domain-weight-row'},[
      el('span',{class:'dname'},[d.name]),
      el('span',{class:'dcount'},[`${d.pct} · ${d.target}q`])
    ])
  )));
  weightedPad.appendChild(el('div',{class:'btn-row'},[
    el('button',{class:'btn btn-primary', onclick: async ()=>{
      const nameVal = nameInput.value.trim();
      if(!nameVal){ errDiv.textContent = 'Please enter the candidate name.'; errDiv.style.display='block'; return; }
      const {order, tally} = buildWeightedOrder();
      const short = tally.filter(t => t.picked < t.target);
      if(short.length){
        // Extremely unlikely at the current bank size (every pool holds at least
        // four times its target), but if a skill area ever runs short, say so
        // rather than silently handing back a shorter exam.
        errDiv.textContent = 'Not enough scored questions in: ' +
          short.map(t=>`${t.name} (${t.picked}/${t.target})`).join(', ') + '.';
        errDiv.style.display='block';
        return;
      }
      state.session = {
        candidateName: nameVal,
        secKey: 'all',
        rangeStart: null, rangeEnd: null,
        isWeighted: true,
        order: order,
        currentIndex: 0,
        answers: {},
        flags: {},
        startedAt: new Date().toISOString(),
        completed: false
      };
      await saveSession(state.session);
      state.screen = 'exam';
      render();
    }},['Start Weighted Exam (50 Q)'])
  ]));
  weightedCard.appendChild(weightedPad);
  app.appendChild(weightedCard);

  if(state.wrongPool && state.wrongPool.length > 0){
    const wrongCard = el('div',{class:'card'});
    const wrongPad = el('div',{class:'pad'});
    wrongPad.appendChild(el('h2',{style:'margin-bottom:2px;'},[`All-Time Missed Questions (${state.wrongPool.length})`]));
    wrongPad.appendChild(el('div',{class:'subtitle'},[
      "Every question you've gotten wrong or skipped, accumulated across every exam you've taken on this device — including runs you exited part-way. Questions stay on this list until you remove them yourself."
    ]));
    wrongPad.appendChild(el('div',{class:'btn-row'},[
      el('button',{class:'btn btn-primary', onclick: async ()=>{
        const nameVal = nameInput.value.trim();
        if(!nameVal){ errDiv.textContent = 'Please enter the candidate name.'; errDiv.style.display='block'; return; }
        state.session = {
          candidateName: nameVal,
          secKey: 'all',
          rangeStart: null, rangeEnd: null,
          isWrongPool: true,
          order: state.wrongPool.slice(),
          currentIndex: 0,
          answers: {},
          flags: {},
          startedAt: new Date().toISOString(),
          completed: false
        };
        await saveSession(state.session);
        state.screen = 'exam';
        render();
      }},[`Practice All-Time Missed Questions (${state.wrongPool.length})`]),
      el('button',{class:'btn btn-outline', onclick: async ()=>{
        if(confirm("Clear your all-time missed-questions list? This can't be undone.")){
          state.wrongPool = [];
          await saveWrongPool([]);
          render();
        }
      }},['Clear list'])
    ]));
    wrongCard.appendChild(wrongPad);
    app.appendChild(wrongCard);
  }

  app.appendChild(el('div',{class:'card'},[
    el('div',{class:'pad', style:'display:flex;justify-content:space-between;align-items:center;gap:12px;'},[
      el('div',{},[
        el('h2',{style:'margin-bottom:2px;'},['Past results']),
        el('div',{class:'subtitle', style:'margin-bottom:0;'},[`${state.historyList.length} completed exam${state.historyList.length===1?'':'s'} saved`])
      ]),
      el('button',{class:'btn btn-outline', onclick: ()=>{ state.screen='history'; render(); }},['View history'])
    ])
  ]));

  // Plain statement of what the bank holds, so nobody mistakes a thin stem or an
  // unscored item for a rendering fault.
  app.appendChild(el('div',{class:'card'},[
    el('div',{class:'pad'},[
      el('h2',{style:'margin-bottom:2px;'},['About this bank']),
      el('div',{class:'subtitle', style:'margin-bottom:10px;'},['Every question from the SC-100 set you supplied']),
      el('ul',{style:'margin:0;padding-left:20px;font-size:14.5px;line-height:1.7;color:var(--gray-700);'},[
        el('li',{},[
          `All ${TOTAL_Q} items are here, keeping the source's own numbering: ` +
          SECTIONS.map(s => `${s.label} 1–${SECTION_MAX[s.key]}`).join(', ') + '.'
        ]),
        el('li',{},[`${CHOICE_COUNT} are multiple choice and ${MATCH_COUNT} are answer-area drop-down items scored all-or-nothing — ${SCORABLE_COUNT} scored questions in total.`]),
        el('li',{},[`The other ${UNSCORED_COUNT} are answer-area items whose answers the source records as pictures rather than text. There is nothing to click, so they are not scored — but the recorded answer is shown when you reveal it, and no answer is invented.`]),
        el('li',{},[`${EXHIBIT_COUNT} questions carry the diagrams, tables and screenshots they refer to, and ${EXPLAINED_COUNT} carry the source's explanation.`]),
        el('li',{},['Both case studies include their full scenario, which opens from a panel above the question.']),
        el('li',{},[`Answer keys are being reviewed against Microsoft Learn. ${REVIEWED_COUNT} of ${TOTAL_Q} have been checked so far — ${CORRECTED_COUNT} were wrong and have been corrected, ${FLAGGED_COUNT} are flagged as doubtful. A reviewed question shows its verdict and a Microsoft Learn link with the answer.`]),
        el('li',{},[`The remaining ${TOTAL_Q - REVIEWED_COUNT} keys are reproduced from the source as-is and have not been independently checked. Treat them as a dump, not as fact.`])
      ])
    ])
  ]));
}

// ---------------- EXAM ----------------
function currentQ(){
  const s = state.session;
  return QMAP[s.order[s.currentIndex]];
}

function renderExam(app){
  const s = state.session;
  const q = currentQ();
  const letters = parseAnswerLetters(q.a);
  const isMulti = letters.length > 1;
  const rec = s.answers[q.n];
  const selected = rec ? (rec.selected || []) : [];
  const checked = rec ? rec.checked : false;

  const card = el('div',{class:'card'});

  const timerEl = el('div',{class:'exam-timer'},[formatDuration(Date.now() - new Date(s.startedAt).getTime())]);
  card.appendChild(el('div',{class:'topbar'},[
    el('div',{},[
      el('div',{class:'qnum'},[`Question ${q.num}`]),
      el('div',{class:'cat'},[q.c])
    ]),
    el('div',{class:'meta-wrap'},[
      timerEl,
      el('div',{class:'meta'},[`${s.candidateName} · ${s.currentIndex+1} of ${s.order.length}`])
    ])
  ]));

  // Live-tick the timer once a second without a full re-render. startedAt is
  // set when the session was created and persists across save/resume, so the
  // clock reflects true elapsed time even if the candidate left and came back.
  const startedMs = new Date(s.startedAt).getTime();
  examTimerInterval = setInterval(()=>{
    timerEl.textContent = formatDuration(Date.now() - startedMs);
  }, 1000);

  const pct = Math.round((s.currentIndex / s.order.length) * 100);
  card.appendChild(el('div',{class:'progress-wrap'},[el('div',{class:'progress-fill', style:`width:${pct}%`})]));

  // A case-study question says so above everything else, the way the source
  // groups it — the stem alone gives no clue which scenario it belongs to.
  if(q.cs){
    card.appendChild(el('div',{class:'case-banner'},[
      el('span',{class:'case-banner-label'},[`Case study ${q.cs.n}`]),
      el('span',{class:'case-banner-name'},[q.cs.name]),
      el('span',{class:'case-banner-q'},[`Question ${q.num} of ${SECTION_MAX[q.sec]}`])
    ]));
  }

  // A case-study question is unanswerable without its scenario, which runs to
  // pages. It sits in a panel that opens on demand and stays open while you
  // work through that case study's questions.
  if(q.cs && CASES[q.sec]){
    const open = !!state.caseOpen[q.sec];
    const panel = el('div',{class:'case-panel' + (open ? ' open' : '')});
    panel.appendChild(el('button',{class:'case-toggle', onclick: ()=>{
      state.caseOpen[q.sec] = !state.caseOpen[q.sec];
      render();
    }},[(open ? '▾ Hide' : '▸ Show') + ` the ${q.cs.name} case study`]));
    if(open){
      const body = el('div',{class:'case-body'});
      renderNodes(body, CASES[q.sec]);
      panel.appendChild(body);
    }
    card.appendChild(panel);
  }

  const bodyWrap = el('div',{class:'qtext'});
  renderNodes(bodyWrap, q.body);
  card.appendChild(bodyWrap);
  if(q.review && ['MANUAL_REVIEW','AMBIGUOUS','OUTDATED'].includes(q.review.status)){
    card.appendChild(el('div',{class:'warn-note'},[
      q.review.status === 'OUTDATED'
        ? 'This item tests a feature that has since been retired. The source’s key is kept and graded as-is; see the note with the answer for what replaced it.'
        : 'This item is flagged: its answer key is doubtful or the question admits more than one defensible answer. The source’s key is kept and graded as-is. See the note with the answer.'
    ]));
  }
  if(q.warn){
    card.appendChild(el('div',{class:'warn-note'},[q.warn]));
  }
  if(isMulti){
    card.appendChild(el('div',{class:'qhint'},[`Select ${letters.length} answers.`]));
  }

  if(isInfo(q)){
    renderInfoBody(card, q, checked);
  } else if(isMatch(q)){
    renderMatchBody(card, q, rec, checked);
  } else {
    const choicesWrap = el('div',{class:'choices'});
    q.o.forEach((opt, i)=>{
      const letter = letterOf(i);
      const isSelected = selected.includes(letter);
      const isRight = letters.includes(letter);
      let cls = 'choice';
      if(!checked && isSelected) cls += ' selected';
      if(checked){
        cls += ' disabled';
        if(isRight) cls += ' correct';
        else if(isSelected) cls += ' incorrect';
      }
      const inputEl = el('input',{type: isMulti ? 'checkbox' : 'radio', name:'choice'});
      inputEl.checked = isSelected;
      if(checked) inputEl.disabled = true;
      inputEl.addEventListener('change', ()=>{ toggleSelect(letter, isMulti); });

      const markSpan = checked ? el('span',{class:'mark'},[ isRight ? '✓ Correct' : (isSelected ? '✗ Your pick' : '') ]) : null;

      choicesWrap.appendChild(el('div',{class:cls, onclick: (e)=>{
        if(checked) return;
        if(e.target.tagName !== 'INPUT'){ toggleSelect(letter, isMulti); }
      }},[
        inputEl,
        el('span',{},[el('span',{class:'letter'},[letter+'.']), ' ', opt]),
        markSpan
      ]));
    });
    card.appendChild(choicesWrap);
  }

  if(checked){
    if(!isInfo(q)){
      const revealedOnly = !hasResponse(q, rec);
      const allCorrect = isCorrectAnswer(q, rec);
      let bannerClass, bannerText;
      if(isMatch(q)){
        const {got, total} = matchScore(q, rec);
        if(revealedOnly){
          bannerClass = 'revealed';
          bannerText = 'Answers revealed — the correct value is marked on each drop-down below';
        } else if(allCorrect){
          bannerClass = 'correct';
          bannerText = `✓ Correct! ${got} of ${total} drop-downs right`;
        } else {
          bannerClass = 'incorrect';
          bannerText = `✗ Incorrect — ${got} of ${total} drop-downs right (all ${total} must be correct to score)`;
        }
      } else if(revealedOnly){
        bannerClass = 'revealed';
        bannerText = `Answer revealed — correct answer: ${letters.join(', ') || '—'}`;
      } else if(allCorrect){
        bannerClass = 'correct';
        bannerText = '✓ Correct!';
      } else {
        bannerClass = 'incorrect';
        bannerText = `✗ Incorrect — correct answer: ${letters.join(', ')}`;
      }
      card.appendChild(el('div',{class:'result-banner ' + bannerClass},[bannerText]));
    }

    // Where the key was corrected against the source, say so — but only after
    // the answer is revealed, since naming both keys would give the item away.
    // Two cases share this panel: a key corrected against the source, which
    // names both keys, and a key supplied where the source has none at all.
    // The answer-key review, where this item has been checked against Microsoft
    // Learn. It comes before the source's own explanation, because for a
    // corrected item that explanation argues for the key we just overruled.
    if(q.review) card.appendChild(reviewPanel(q));

    const suppliedKey = !!q.keynote;
    if(q.keynote){
      card.appendChild(el('div',{class:'key-note'},[
        el('div',{class:'head'},['HOW THIS ITEM IS GRADED']),
        el('div',{class:'body'},[q.keynote])
      ]));
    }

    // The dump draws every answer-area answer rather than writing it, so where
    // it recorded one, that picture is the answer.
    if(q.ansimg){
      const wrap = el('div',{class:'source-answer'});
      wrap.appendChild(el('div',{class:'head'},['THE ANSWER, AS THE SOURCE RECORDS IT']));
      renderNodes(wrap, q.ansimg);
      card.appendChild(wrap);
    }

    if(q.e){
      const body = el('div',{class:'body'});
      // The source's explanation is frequently nothing but reference links.
      // Label that case so it doesn't read as a truncated paragraph.
      const onlyLinks = q.e.every(n => n.img || /^https?:\/\/\S+$/.test((n.p||'').trim()));
      if(onlyLinks && q.e.some(n => n.p)){
        body.appendChild(el('div',{class:'links-only-note'},['The source gives reference links only:']));
      }
      renderNodes(body, q.e);
      card.appendChild(el('div',{class:'explanation'},[
        el('div',{class:'head'},['EXPLANATION']),
        body
      ]));
    } else if(!isInfo(q) && !suppliedKey){
      // Skipped for supplied-key items: the panel above has already said the
      // source gives no key at all, which this would flatly contradict.
      card.appendChild(el('div',{class:'explanation'},[
        el('div',{class:'head'},['NOTE']),
        el('div',{class:'body'},['The source question set gives an answer key for this item but no written explanation.'])
      ]));
    }
  }

  const footer = el('div',{class:'footer-actions'});
  const leftActions = el('div',{class:'left-actions'});
  leftActions.appendChild(el('button',{class:'btn btn-outline', disabled: s.currentIndex===0?'true':null, onclick: ()=>{
    s.currentIndex = Math.max(0, s.currentIndex-1);
    saveSession(s);
    render();
  }},['← Previous']));
  const flagged = !!s.flags[q.n];
  leftActions.appendChild(el('button',{class:'flag-star' + (flagged?' on':''), title:'Flag for review', onclick: ()=>{
    s.flags[q.n] = !s.flags[q.n];
    saveSession(s);
    render();
  }},[flagged ? '★' : '☆']));

  const answerActions = el('div',{class:'answer-actions'});
  const rightActions = el('div',{class:'right-actions'});
  const isLast = s.currentIndex === s.order.length-1;

  const advance = async ()=>{
    if(isLast){ await finishExam(); }
    else { s.currentIndex += 1; await saveSession(s); render(); }
  };

  if(isInfo(q)){
    // Nothing to grade. Offer to reveal only what is actually held back —
    // statements are already on screen, so they alone don't earn the button.
    if(!checked && (q.ansimg || q.e)){
      answerActions.appendChild(el('button',{class:'btn btn-outline', onclick: async ()=>{
        s.answers[q.n] = {selected: [], checked:true};
        await saveSession(s);
        render();
      }},['Reveal recorded answer']));
    }
    rightActions.appendChild(el('button',{class:'btn btn-primary', onclick: advance},
      [isLast ? 'Finish exam' : 'Next Question']));
  } else if(!checked){
    // Show Answer lives in its own container so that on small screens it can be
    // ordered onto its own full-width row above the Previous/Next pair.
    answerActions.appendChild(el('button',{class:'btn btn-outline', onclick: async ()=>{
      s.answers[q.n] = Object.assign({}, rec, {selected: selected.slice(), checked:true});
      // Grade it now and bank the miss immediately, so it survives even if this
      // run is abandoned instead of finished.
      if(isMissedAnswer(q.n, s.answers[q.n])) await addToWrongPool(q.n);
      await saveSession(s);
      render();
    }},['Show Answer']));
    rightActions.appendChild(el('button',{class:'btn btn-primary', onclick: async ()=>{
      s.answers[q.n] = Object.assign({}, rec, {selected: selected.slice(), checked:true});
      const wasCorrect = isCorrectAnswer(q, s.answers[q.n]);
      // Same here: a wrong or unanswered question joins the all-time list the
      // instant it's graded, not at the end of the exam.
      if(!wasCorrect) await addToWrongPool(q.n);
      if(wasCorrect){
        // Correct: skip the explanation, advance straight on.
        await advance();
      } else {
        // Incorrect, or nothing selected: reveal the answer/explanation first,
        // same as Show Answer. Scoring still counts an empty selection as
        // "skipped" rather than "incorrect" — see finishExam.
        await saveSession(s);
        render();
      }
    }},['Next Question']));
  } else {
    rightActions.appendChild(el('button',{class:'btn btn-primary', onclick: advance},
      [isLast ? 'Finish exam' : 'Next Question']));
  }

  // DOM order is the MOBILE order (Show Answer first, then Prev/Next on one row).
  // Desktop re-orders visually with CSS `order` in the base stylesheet.
  if(answerActions.childNodes.length) footer.appendChild(answerActions);
  footer.appendChild(leftActions);
  footer.appendChild(rightActions);
  card.appendChild(footer);

  app.appendChild(card);

  const scoredSoFar = s.order.filter(qn => isScorable(QMAP[qn])).length;
  app.appendChild(el('div',{class:'card'},[
    el('div',{class:'pad', style:'padding:12px 24px;display:flex;justify-content:space-between;align-items:center;gap:12px;'},[
      el('div',{class:'subtitle', style:'margin:0;'},[
        `Progress is saved automatically. Answered: ${s.order.filter(qn => hasResponse(QMAP[qn], s.answers[qn])).length}/${scoredSoFar} scored questions`
      ]),
      el('button',{class:'btn btn-outline', onclick: ()=>{ state.screen='setup'; render(); }},['Save & exit to menu'])
    ])
  ]));
}

// ---------------- UNSCORED (info) ITEM ----------------
function renderInfoBody(card, q, checked){
  card.appendChild(el('div',{class:'unscored-note'},[
    el('b',{},['Not scored. ']),
    q.ansimg
      ? 'This is a hotspot, drag-and-drop or drop-down item. The source records its answer as a picture rather than as text, so there is nothing here to click and nothing to grade — work it out from the exhibit, then reveal the recorded answer. It never counts for or against your percentage.'
      : 'The source records neither options nor an answer for this item, so there is nothing to grade and nothing to reveal. Inventing an answer would be worse than leaving it blank. It is here so the bank matches the document, and never counts for or against your percentage.'
  ]));
}


// ---------------- ANSWER-KEY REVIEW ----------------
// Rendered from q.review, which bank.py merges in from build/review.json. The
// same record drives the graded key, so what is displayed here and what the
// scoring engine believes can never disagree.
const REVIEW_LABEL = {
  VERIFIED: 'Verified against Microsoft Learn',
  CORRECTED: 'Answer key corrected',
  MANUAL_REVIEW: 'Flagged for manual review',
  AMBIGUOUS: 'Ambiguous question',
  OUTDATED: 'Outdated question'
};

function answerText(q){
  if(isMatch(q)) return q.boxes.map(b => `${b.label}: ${b.value}`).join(' · ');
  // An info item has no text key at all — the source drew its answer as a
  // picture instead, rendered separately below this panel — so there is
  // nothing to echo here.
  if(isInfo(q)) return 'See the recorded answer below.';
  const letters = parseAnswerLetters(q.a);
  if(!letters.length) return '—';
  return letters.map(l => {
    const i = l.charCodeAt(0) - 65;
    const opt = (q.o || [])[i];
    return opt ? `${l}. ${opt}` : l;
  }).join('  |  ');
}

function reviewPanel(q){
  const r = q.review;
  const cls = r.status === 'CORRECTED' ? 'corrected'
            : (r.status === 'VERIFIED' ? 'verified' : 'flagged');
  const panel = el('div',{class:'review-panel ' + cls});
  panel.appendChild(el('div',{class:'head'},[
    REVIEW_LABEL[r.status] || r.status,
    el('span',{class:'conf'},['confidence: ' + r.confidence])
  ]));

  panel.appendChild(el('div',{class:'label'},['Correct Answer']));
  panel.appendChild(el('div',{class:'answer'},[answerText(q)]));

  panel.appendChild(el('div',{class:'label'},['Explanation']));
  // A corrected item leads with the banner on its own line, so it cannot be
  // mistaken for part of the prose.
  const body = el('div',{class:'body'});
  let text = r.explanation;
  if(r.corrected){
    const banner = 'THIS ANSWER WAS CORRECTED BY AI';
    body.appendChild(el('div',{class:'ai-banner'},[banner]));
    // The banner is stored in some explanations too; do not print it twice.
    text = text.replace(banner, '').replace(/^\s+/, '');
    // A box-type correction names which drop-down it fixed; the graded value
    // then lives on that box, not on q.a (which match items don't have).
    const gradedNow = r.boxLabel
      ? ((q.boxes || []).find(b => b.label === r.boxLabel) || {}).value
      : q.a;
    const was = r.boxLabel
      ? `The source's key for "${r.boxLabel}" was ${r.originalAnswer}. This bank grades ${gradedNow}.`
      : `The source's key was ${r.originalAnswer}. This bank grades ${gradedNow}.`;
    body.appendChild(el('div',{class:'was'},[was]));
  }
  text.split(/\n{2,}/).forEach(para=>{
    if(para.trim()) body.appendChild(el('div',{class:'para'}, linkify(para.trim())));
  });
  panel.appendChild(body);

  if(r.whyWrong && r.whyWrong.length){
    panel.appendChild(el('div',{class:'label'},['Why the other options are wrong']));
    panel.appendChild(el('ul',{class:'why'}, r.whyWrong.map(t => el('li',{},[t]))));
  }

  if(r.source && r.source.url){
    panel.appendChild(el('div',{class:'src'},[
      'Source: ',
      el('a',{href:r.source.url, target:'_blank', rel:'noopener noreferrer'},
        [r.source.title || r.source.url])
    ]));
  }
  return panel;
}

// ---------------- ANSWER-AREA (matching) ITEM ----------------
function renderMatchBody(card, q, rec, checked){
  card.appendChild(el('div',{class:'match-note'},[
    el('b',{},['Answer area. ']),
    `Choose a value for each of the ${q.boxes.length} drop-downs; all ${q.boxes.length} must be correct for the item to score.`,
    hasRealOptions(q) ? null :
      ' The source PDF records the correct value for each box but not the list of choices the ' +
      'real exam offers, so each drop-down here lists this item’s own values — match each one ' +
      'to the right box.'
  ]));

  const wrap = el('div',{class:'match-wrap'});
  q.boxes.forEach((box, i)=>{
    const opts = boxOptions(q, i);
    const picked = matchResponse(rec)[i] || '';
    const ok = matchCellCorrect(q, i, rec);
    const rowEl = el('div',{class:'match-row'});
    rowEl.appendChild(el('label',{class:'match-label'},[box.label]));

    const sel = el('select',{class:'match-select' + (checked ? (ok ? ' correct' : ' incorrect') : '')});
    sel.appendChild(el('option',{value:''},['-- Select --']));
    opts.forEach(opt=>{
      const o = el('option',{value:opt},[opt]);
      if(opt === picked) o.selected = true;
      sel.appendChild(o);
    });
    sel.value = picked;
    if(checked) sel.disabled = true;
    else sel.addEventListener('change', ()=>{ setMatchValue(q.n, i, sel.value); });
    rowEl.appendChild(sel);

    if(checked){
      rowEl.appendChild(el('div',{class:'match-mark ' + (ok ? 'ok' : 'bad')},[
        ok ? '✓ Correct' : '✗ Correct answer: ' + box.value
      ]));
    }
    wrap.appendChild(rowEl);
  });
  card.appendChild(wrap);

  if(!checked){
    card.appendChild(el('div',{class:'match-reset-row'},[
      el('button',{class:'btn btn-outline', onclick: ()=>{ resetMatch(q.n); }},['Reset All'])
    ]));
  }
}

// Record one drop-down selection without disturbing the others.
function setMatchValue(qn, idx, value){
  const s = state.session;
  const rec = s.answers[qn] || {};
  const boxes = Object.assign({}, rec.boxes);
  if(value) boxes[idx] = value; else delete boxes[idx];
  s.answers[qn] = {selected: [], boxes, checked:false};
  saveSession(s);
  render();
}

// "Reset All" — clears every drop-down on this item only.
function resetMatch(qn){
  const s = state.session;
  s.answers[qn] = {selected: [], boxes: {}, checked:false};
  saveSession(s);
  render();
}

function toggleSelect(letter, isMulti){
  const s = state.session;
  const q = currentQ();
  const rec = s.answers[q.n];
  let selected = rec ? (rec.selected || []).slice() : [];
  if(isMulti){
    const idx = selected.indexOf(letter);
    if(idx>=0) selected.splice(idx,1); else selected.push(letter);
  } else {
    selected = [letter];
  }
  s.answers[q.n] = {selected, checked:false};
  saveSession(s);
  render();
}

function arraysEqualAsSets(a,b){
  if(a.length!==b.length) return false;
  return [...a].sort().join(',') === [...b].sort().join(',');
}

async function finishExam(){
  const s = state.session;
  s.completed = true;
  s.finishedAt = new Date().toISOString();
  // Elapsed wall-clock time from session creation to now. startedAt is set once
  // and never touched again, so this is true elapsed time even if the candidate
  // left mid-exam and came back later.
  const durationMs = Date.now() - new Date(s.startedAt).getTime();
  await saveSession(s);

  let correct=0, incorrect=0, skipped=0, notScored=0;
  const catStats = {};
  // Final sweep into the persistent all-time "missed questions" pool. Misses
  // are normally recorded the moment a question is graded (see the Show Answer
  // / Next Question handlers) so that abandoned runs still count; this pass is
  // the backstop that catches anything never reached or never graded.
  //
  // IMPORTANT: this is add-only. A question answered correctly here is NOT
  // pulled out of the pool — the list is a cumulative record of everything
  // ever missed and only the user clears it.
  const newMisses = [];
  s.order.forEach(qn=>{
    const q = QMAP[qn];
    const rec = s.answers[qn];
    // Items the source cannot grade sit outside the score entirely: they are
    // neither correct, incorrect, nor skipped, and never reach the missed pool.
    if(isInfo(q)){ notScored++; return; }
    if(!catStats[q.c]) catStats[q.c] = {correct:0,total:0};
    catStats[q.c].total++;
    // No answer was ever put down (whether the question was left untouched, or
    // revealed via Next Question / Show Answer without a selection) counts as
    // skipped, not incorrect — "checked" only means the answer was viewed.
    if(!hasResponse(q, rec)){ skipped++; newMisses.push(qn); return; }
    if(isCorrectAnswer(q, rec)){ correct++; catStats[q.c].correct++; }
    else { incorrect++; newMisses.push(qn); }
  });
  await addToWrongPool(newMisses);

  const summary = {
    candidateName: s.candidateName,
    secKey: s.secKey,
    rangeStart: s.rangeStart,
    rangeEnd: s.rangeEnd,
    isRetake: !!s.isRetake,
    isWrongPool: !!s.isWrongPool,
    isWeighted: !!s.isWeighted,
    total: s.order.length,
    scored: s.order.length - notScored,
    correct, incorrect, skipped, notScored,
    durationMs,
    date: new Date().toISOString()
  };
  state.historyList.unshift(summary);
  await saveHistory(state.historyList);

  state.lastResult = {summary, catStats, session: JSON.parse(JSON.stringify(s))};
  await clearSession();
  state.session = null;
  state.screen = 'finished';
  render();
}

// Percentage over scored questions only. Older history rows predate the
// `scored` field, so they fall back to their total.
function scorePct(h){
  const denom = (h.scored != null ? h.scored : h.total);
  return denom > 0 ? Math.round((h.correct/denom)*100) : null;
}

// ---------------- FINISHED ----------------
function renderFinished(app){
  const r = state.lastResult;
  if(!r){ state.screen='setup'; render(); return; }
  const {summary, catStats, session} = r;
  const pct = scorePct(summary);
  const passed = pct != null && pct >= PASS_THRESHOLD;

  const card = el('div',{class:'card'});
  card.appendChild(el('div',{class:'score-hero'},[
    el('div',{class:'report-label'},['Final Report']),
    el('div',{class:'subtitle', style:'margin-bottom:0;'},[`Candidate: ${summary.candidateName}`]),
    el('div',{class:'big'},[pct == null ? '—' : pct+'%']),
    el('div',{class:'pct'},[
      (pct == null
        ? 'No scored questions in this run'
        : `${summary.correct} of ${summary.scored} scored questions correct`) +
      ` · ${rangeLabelOf(summary)}` +
      (summary.durationMs != null ? ' · Time: ' + formatDuration(summary.durationMs) : '')
    ]),
    pct == null ? null : el('div',{class:'pass ' + (passed?'yes':'no')},
      [passed ? 'Practice score: on track' : 'Practice score: needs review'])
  ]));

  const tiles = [
    el('div',{class:'stat correct'},[el('div',{class:'num'},[String(summary.correct)]), el('div',{class:'lbl'},['Correct'])]),
    el('div',{class:'stat incorrect'},[el('div',{class:'num'},[String(summary.incorrect)]), el('div',{class:'lbl'},['Incorrect'])]),
    el('div',{class:'stat skipped'},[el('div',{class:'num'},[String(summary.skipped)]), el('div',{class:'lbl'},['Skipped'])])
  ];
  if(summary.notScored){
    tiles.push(el('div',{class:'stat unscored'},[
      el('div',{class:'num'},[String(summary.notScored)]),
      el('div',{class:'lbl'},['Not scored'])
    ]));
  }
  card.appendChild(el('div',{class:'stat-grid' + (summary.notScored ? ' four' : '')}, tiles));
  if(summary.notScored){
    card.appendChild(el('div',{class:'unscored-footnote'},[
      `${summary.notScored} item${summary.notScored===1?'':'s'} in this run had no answer key in the source, so ` +
      `the percentage is out of the ${summary.scored} scored question${summary.scored===1?'':'s'}.`
    ]));
  }

  const catWrap = el('div',{class:'cat-breakdown'});
  catWrap.appendChild(el('h2',{},['By skill area']));
  Object.keys(catStats).forEach(cat=>{
    const cs = catStats[cat];
    const p = cs.total>0 ? (cs.correct/cs.total)*100 : 0;
    catWrap.appendChild(el('div',{class:'cat-row'},[
      el('div',{class:'name', title:cat},[cat]),
      el('div',{class:'bar-wrap'},[el('div',{class:'bar', style:`width:${p}%`})]),
      el('div',{class:'frac'},[`${cs.correct}/${cs.total} (${Math.round(p)}%)`])
    ]));
  });
  card.appendChild(catWrap);

  // Scored questions that were missed or left blank, for the retake button.
  const retakeNums = session.order.filter(qn =>
    isScorable(QMAP[qn]) && !isCorrectAnswer(QMAP[qn], session.answers[qn]));

  // Questions in this run that are on the all-time missed list but were
  // answered correctly here. The list is never pruned automatically, so this
  // gives a targeted way to retire ones that have been mastered.
  const wrongPoolSet = new Set(state.wrongPool || []);
  const masteredNums = session.order.filter(qn => wrongPoolSet.has(qn) && !isMissedAnswer(qn, session.answers[qn]));

  const leftBtns = [
    el('button',{class:'btn btn-outline', onclick: ()=>{ state.screen='review'; state.reviewSession = session; render(); }},['Review answers'])
  ];
  if(masteredNums.length > 0){
    leftBtns.push(el('button',{class:'btn btn-outline', onclick: async ()=>{
      if(confirm(`Remove ${masteredNums.length} question${masteredNums.length===1?'':'s'} you answered correctly from your all-time missed list?`)){
        await removeFromWrongPool(masteredNums);
        render();
      }
    }},[`Remove ${masteredNums.length} Correct from Missed List`]));
  }
  if(retakeNums.length > 0){
    leftBtns.push(el('button',{class:'btn btn-outline', onclick: async ()=>{
      state.session = {
        candidateName: summary.candidateName,
        secKey: 'all',
        rangeStart: null, rangeEnd: null,
        isRetake: true,
        order: retakeNums.slice(),
        currentIndex: 0,
        answers: {},
        flags: {},
        startedAt: new Date().toISOString(),
        completed: false
      };
      await saveSession(state.session);
      state.screen = 'exam';
      render();
    }},[`Retake Incorrect & Skipped Questions (${retakeNums.length})`]));
  }

  card.appendChild(el('div',{class:'footer-actions'},[
    el('div',{class:'left-actions'},leftBtns),
    el('div',{class:'right-actions'},[
      el('button',{class:'btn btn-primary', onclick: ()=>{ state.screen='setup'; render(); }},['Back to menu'])
    ])
  ]));

  app.appendChild(card);
}

function renderReview(app){
  const session = state.reviewSession;
  const card = el('div',{class:'card'});
  card.appendChild(el('div',{class:'pad'},[
    el('h1',{},['Answer review']),
    el('div',{class:'subtitle'},[`${session.candidateName} · ${rangeLabelOf(session)}`]),
    el('div',{class:'btn-row', style:'margin-top:0;'},[
      el('button',{class:'btn btn-outline', onclick: ()=>{ state.screen='finished'; render(); }},['← Back to results']),
      el('button',{class:'btn btn-outline', onclick: ()=>{ state.screen='setup'; render(); }},['Back to menu'])
    ])
  ]));
  const list = el('div',{class:'review-list'});
  session.order.forEach(qn=>{
    const q = QMAP[qn];
    const rec = session.answers[qn];
    const letters = parseAnswerLetters(q.a);
    const sel = rec ? (rec.selected || []) : [];
    const answered = hasResponse(q, rec);
    const correct = isCorrectAnswer(q, rec);
    let badge;
    if(isInfo(q)) badge = el('span',{class:'badge unscored'},['Not scored']);
    else if(!answered) badge = el('span',{class:'badge', style:'background:var(--gray-200);color:var(--gray-700);'},['Skipped']);
    else badge = el('span',{class:'badge ' + (correct?'correct':'incorrect')},[correct?'Correct':'Incorrect']);

    const item = el('div',{class:'review-item'},[
      el('div',{class:'qh'},[citation(q), badge]),
      el('div',{class:'qtxt'},[q.q])
    ]);
    if(isInfo(q)){
      item.appendChild(el('div',{class:'ans'},[
        q.ansimg ? 'The source records this answer as a picture — open the question to see it'
                 : 'The source records no answer for this item'
      ]));
    } else if(isMatch(q)){
      const resp = matchResponse(rec);
      const {got, total} = matchScore(q, rec);
      item.appendChild(el('div',{class:'ans'},[`${got} of ${total} drop-downs correct`]));
      q.boxes.forEach((box, i)=>{
        const picked = resp[i];
        const ok = matchCellCorrect(q, i, rec);
        item.appendChild(el('div',{class:'ans'},[
          `${box.label}: ${box.value}`,
          picked ? ` · Your answer: ${picked}${ok ? ' ✓' : ' ✗'}` : ' · Your answer: —'
        ]));
      });
    } else {
      item.appendChild(el('div',{class:'ans'},[
        `Correct answer: ${letters.join(', ') || '—'}`,
        answered ? ` · Your answer: ${sel.join(', ') || '—'}` : ''
      ]));
    }
    list.appendChild(item);
  });
  card.appendChild(list);
  app.appendChild(card);
}

// ---------------- HISTORY ----------------
function renderHistory(app){
  const card = el('div',{class:'card'});
  card.appendChild(el('div',{class:'pad'},[
    el('h1',{},['Past results']),
    el('div',{class:'subtitle'},['All completed practice exams saved on this device']),
    el('button',{class:'btn btn-outline', onclick: ()=>{ state.screen='setup'; render(); }},['← Back to menu'])
  ]));
  const listWrap = el('div',{class:'pad', style:'padding-top:0;'});
  if(state.historyList.length===0){
    listWrap.appendChild(el('div',{class:'empty-note'},['No completed exams yet.']));
  } else {
    state.historyList.forEach(h=>{
      const pct = scorePct(h);
      const d = new Date(h.date);
      const denom = (h.scored != null ? h.scored : h.total);
      listWrap.appendChild(el('div',{class:'history-item'},[
        el('div',{},[
          el('div',{class:'name'},[h.candidateName]),
          el('div',{class:'range'},[`${rangeLabelOf(h)} · ${d.toLocaleDateString()} ${d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}${h.durationMs != null ? ' · ' + formatDuration(h.durationMs) : ''}`])
        ]),
        el('div',{class:'score', style:`color:${pct != null && pct>=PASS_THRESHOLD?'var(--green)':'var(--red)'}`},
          [pct == null ? '—' : `${pct}% (${h.correct}/${denom})`])
      ]));
    });
  }
  card.appendChild(listWrap);
  app.appendChild(card);
}

// ---------------- INIT ----------------
async function init(){
  const authed = await checkAuthed();
  if(!authed){
    state.screen = 'gate';
    render();
    return;
  }
  state.session = await loadSession();
  state.historyList = await loadHistory();
  state.wrongPool = await loadWrongPool();
  state.screen = 'setup';
  render();
}
init();
