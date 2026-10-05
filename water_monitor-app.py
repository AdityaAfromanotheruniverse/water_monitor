import streamlit as st
import json

st.set_page_config(layout="wide")

st.title("💧 Real-Time Water Quality Monitoring System")
st.write("Water flows from the plant to the city and to a tester. The tester line never stops. "
         "The city valve closes automatically if ANY parameter crosses the Indian drinking-water limit (IS 10500).")

# ---------------------------------------------------------------------------
# Parameters: (key, label, unit, category, acceptable, permissible, min, max, step, default, decimals)
# Limits follow BIS IS 10500:2012 (Drinking Water Specification).
# "acceptable" = desirable limit; "permissible" = limit allowed only when no alternate source exists.
# Where the standard has no relaxation, both values are the same.
# Pathogens: E. coli / total coliform must be absent (0) in a 100 mL sample.
# ---------------------------------------------------------------------------
RAW_PARAMS = [
    ("ph",       "pH",                     "",          "Physical",  None,  None,   4.0, 11.0,   0.1,    7.2,    1),
    ("turb",     "Turbidity",              "NTU",       "Physical",  1.0,   5.0,    0.0, 10.0,   0.1,    0.3,    1),
    ("tds",      "Total Dissolved Solids", "mg/L",      "Physical",  500,   2000,   0,   3000,   10,     200,    0),
    ("pb",       "Lead (Pb)",              "mg/L",      "Metals",    0.01,  0.01,   0.0, 0.03,   0.001,  0.003,  3),
    ("as",       "Arsenic (As)",           "mg/L",      "Metals",    0.01,  0.05,   0.0, 0.15,   0.001,  0.003,  3),
    ("hg",       "Mercury (Hg)",           "mg/L",      "Metals",    0.001, 0.001,  0.0, 0.003,  0.0001, 0.0003, 4),
    ("cd",       "Cadmium (Cd)",           "mg/L",      "Metals",    0.003, 0.003,  0.0, 0.009,  0.0001, 0.001,  4),
    ("cr",       "Chromium (Cr)",          "mg/L",      "Metals",    0.05,  0.05,   0.0, 0.15,   0.001,  0.01,   3),
    ("ni",       "Nickel (Ni)",            "mg/L",      "Metals",    0.02,  0.02,   0.0, 0.06,   0.001,  0.005,  3),
    ("fe",       "Iron (Fe)",              "mg/L",      "Metals",    1.0,   1.0,    0.0, 3.0,    0.01,   0.2,    2),
    ("cu",       "Copper (Cu)",            "mg/L",      "Metals",    0.05,  1.5,    0.0, 2.5,    0.01,   0.01,   2),
    ("mn",       "Manganese (Mn)",         "mg/L",      "Metals",    0.1,   0.3,    0.0, 0.6,    0.01,   0.02,   2),
    ("zn",       "Zinc (Zn)",              "mg/L",      "Metals",    5.0,   15.0,   0.0, 20.0,   0.1,    1.0,    1),
    ("al",       "Aluminium (Al)",         "mg/L",      "Metals",    0.03,  0.2,    0.0, 0.4,    0.001,  0.01,   3),
    ("f",        "Fluoride (F)",           "mg/L",      "Chemicals", 1.0,   1.5,    0.0, 3.0,    0.01,   0.4,    2),
    ("no3",      "Nitrate (NO3)",          "mg/L",      "Chemicals", 45,    45,     0,   100,    1,      15,     0),
    ("cn",       "Cyanide (CN)",           "mg/L",      "Chemicals", 0.05,  0.05,   0.0, 0.15,   0.001,  0.01,   3),
    ("ecoli",    "E. coli",                "CFU/100mL", "Pathogens", 0,     0,      0,   20,     1,      0,      0),
    ("coliform", "Total Coliform",         "CFU/100mL", "Pathogens", 0,     0,      0,   20,     1,      0,      0),
]

PARAMS = [
    dict(key=k, label=l, unit=u, cat=c, acc=a, perm=p, vmin=lo, vmax=hi,
         step=s, default=d, dec=dec, isRange=(k == "ph"))
    for (k, l, u, c, a, p, lo, hi, s, d, dec) in RAW_PARAMS
]

# ---------------------------------------------------------------------------
# Everything (sliders, valve logic, animation, readings) lives inside ONE HTML
# component. Moving a slider never triggers a Streamlit rerun, so the frame
# never reloads/flashes and the valve animates smoothly.
# ---------------------------------------------------------------------------
html_template = """
<style>
    * { box-sizing: border-box; }
    .wrap { background:#111; padding:20px; border-radius:12px; font-family:sans-serif; color:white; }
    .controls-top { display:flex; flex-wrap:wrap; gap:16px; align-items:center; justify-content:center;
                    margin-bottom:12px; font-size:13px; color:#ccc; }
    .controls-top select, .controls-top button {
        background:#1a1a1a; color:#eee; border:1px solid #444; border-radius:6px; padding:6px 10px; font-size:13px; cursor:pointer; }
    .controls-top button:hover { border-color:#00c0f2; }
    .panel { margin-top:16px; max-height:520px; overflow-y:auto; border:1px solid #333; border-radius:8px; padding:12px; background:#151515; }
    .cat-title { grid-column:1 / -1; color:#00c0f2; font-weight:bold; font-size:14px; margin:10px 0 2px; border-bottom:1px solid #2a2a2a; padding-bottom:4px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(380px, 1fr)); gap:10px 22px; }
    .row { padding:6px 4px; border-radius:6px; transition:background 0.4s; }
    .row.bad { background:rgba(255,75,75,0.10); }
    .top { display:flex; justify-content:space-between; font-size:13px; margin-bottom:2px; }
    .name { color:#ddd; }
    .val { font-family:monospace; transition:color 0.3s; }
    .row input[type=range] { width:100%; accent-color:#00c0f2; margin:2px 0; }
    .meta { display:flex; justify-content:space-between; font-size:11px; color:#888; margin-bottom:3px; }
    .bar { height:5px; background:#262626; border-radius:3px; overflow:hidden; }
    .fill { height:100%; width:0%; border-radius:3px; transition:width 0.25s, background 0.3s; }
    .dot { display:inline-block; width:8px; height:8px; border-radius:50%; background:#28a745; margin-right:6px; animation:blink 1.2s infinite; }
    @keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0.25; } }
</style>

<div class="wrap">
    <div id="liveLine" style="text-align:center; font-size:14px; margin-bottom:4px; color:#aaa;"></div>
    <div id="statusLine" style="text-align:center; font-size:16px; font-weight:bold; margin-bottom:10px; height:22px; transition:color 0.4s;"></div>

    <canvas id="plant" width="900" height="340" style="display:block; margin:0 auto; max-width:100%; background:#1a1a1a; border-radius:8px; border:1px solid #333;"></canvas>

    <div class="controls-top" style="margin-top:14px;">
        <label>Limit used:
            <select id="modeSel">
                <option value="acc">Acceptable limit (strict)</option>
                <option value="perm">Permissible limit (no alternate source)</option>
            </select>
        </label>
        <label>⚡ Flow speed: <input id="speedSl" type="range" min="0.5" max="3" step="0.25" value="1.5" style="vertical-align:middle; accent-color:#00c0f2;"></label>
        <button id="resetBtn">♻️ Reset all to safe values</button>
    </div>

    <div class="panel"><div class="grid" id="grid"></div></div>
</div>

<script>
const P = __PARAMS__;
const canvas = document.getElementById('plant');
const ctx = canvas.getContext('2d');
const CATS = ['Physical', 'Metals', 'Chemicals', 'Pathogens'];
const CAT_TITLE = {Physical:'🧪 Physical / General', Metals:'🔩 Heavy & Other Metals', Chemicals:'☣️ Hazardous Chemicals', Pathogens:'🦠 Pathogens'};

const vals = {};
P.forEach(function(p) { vals[p.key] = p.default; });
let mode = 'acc';
let speed = 1.5;
let cityOpen = true;
let openness = 1;          // 0 = closed, 1 = open, eased toward target every frame
let badList = [];

// ---------- Build controls ----------
const grid = document.getElementById('grid');
let gh = '';
CATS.forEach(function(cat) {
    gh += '<div class="cat-title">' + CAT_TITLE[cat] + '</div>';
    P.filter(function(p) { return p.cat === cat; }).forEach(function(p) {
        gh += '<div class="row" id="row-' + p.key + '">' +
            '<div class="top"><span class="name">' + p.label + (p.unit ? ' <span style="color:#666;">(' + p.unit + ')</span>' : '') + '</span>' +
            '<span class="val" id="val-' + p.key + '"></span></div>' +
            '<input type="range" id="sl-' + p.key + '" min="' + p.vmin + '" max="' + p.vmax + '" step="' + p.step + '" value="' + p.default + '">' +
            '<div class="meta"><span id="lim-' + p.key + '"></span><span id="st-' + p.key + '"></span></div>' +
            '<div class="bar"><div class="fill" id="bar-' + p.key + '"></div></div></div>';
    });
});
grid.innerHTML = gh;

function limitOf(p) { return mode === 'acc' ? p.acc : p.perm; }

function isViolated(p, v) {
    if (p.isRange) return v < 6.5 || v > 8.5;
    return v > limitOf(p);
}

// ---------- Evaluate EVERY parameter together, instantly ----------
function evaluate() {
    badList = [];
    P.forEach(function(p) {
        const v = vals[p.key];
        const bad = isViolated(p, v);
        if (bad) badList.push(p.label);

        const col = bad ? '#ff4b4b' : '#28a745';
        const valEl = document.getElementById('val-' + p.key);
        valEl.innerText = v.toFixed(p.dec) + (p.unit ? ' ' + p.unit : '');
        valEl.style.color = col;

        let limTxt;
        if (p.isRange) limTxt = 'Limit: 6.5 – 8.5';
        else if (p.cat === 'Pathogens') limTxt = 'Limit: absent (0)';
        else limTxt = 'Limit: ≤ ' + limitOf(p);
        document.getElementById('lim-' + p.key).innerText = limTxt;

        const stEl = document.getElementById('st-' + p.key);
        stEl.innerText = bad ? '🚨 UNSAFE' : '✅ OK';
        stEl.style.color = col;

        // bar = how close the reading is to its limit
        let ratio;
        if (p.isRange) ratio = Math.abs(v - 7.5) / 1.0;
        else if (limitOf(p) === 0) ratio = v > 0 ? 1 : 0;
        else ratio = v / limitOf(p);
        const fill = document.getElementById('bar-' + p.key);
        fill.style.width = Math.min(ratio, 1) * 100 + '%';
        fill.style.background = bad ? '#ff4b4b' : (ratio > 0.7 ? '#f5a623' : '#28a745');

        document.getElementById('row-' + p.key).className = bad ? 'row bad' : 'row';
    });

    cityOpen = (badList.length === 0);
    const st = document.getElementById('statusLine');
    if (cityOpen) {
        st.innerText = '✅ Water is safe — city valve OPEN';
        st.style.color = '#28a745';
    } else {
        st.innerText = '🚨 UNSAFE: ' + badList.join(', ') + ' — city valve CLOSED';
        st.style.color = '#ff4b4b';
    }
}

// ---------- Wire up controls (no page reloads, ever) ----------
P.forEach(function(p) {
    document.getElementById('sl-' + p.key).addEventListener('input', function(e) {
        vals[p.key] = parseFloat(e.target.value);
        evaluate();
    });
});
document.getElementById('modeSel').addEventListener('change', function(e) { mode = e.target.value; evaluate(); });
document.getElementById('speedSl').addEventListener('input', function(e) { speed = parseFloat(e.target.value); });
document.getElementById('resetBtn').addEventListener('click', function() {
    P.forEach(function(p) {
        vals[p.key] = p.default;
        document.getElementById('sl-' + p.key).value = p.default;
    });
    evaluate();
});

// ---------- Live monitor: all sensors report together ----------
let sample = 0;
function liveTick() {
    sample++;
    const t = new Date().toLocaleTimeString();
    document.getElementById('liveLine').innerHTML =
        '<span class="dot"></span>LIVE MONITORING — all ' + P.length + ' sensors reporting simultaneously — sample #' + sample + ' — ' + t;
}
liveTick();
setInterval(liveTick, 1000);

// ---------- Canvas helpers ----------
const trunk    = [[170,170],[300,170]];
const cityPre  = [[300,170],[300,80],[520,80]];
const cityPost = [[520,80],[760,80]];
const testPipe = [[300,170],[300,260],[760,260]];
let offTrunk = 0, offPre = 0, offPost = 0, offTest = 0, pulse = 0;

function tracePath(pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
}

function drawPipe(pts, fill, off) {
    ctx.lineJoin = 'round';
    ctx.lineCap = 'butt';
    ctx.setLineDash([]);
    tracePath(pts); ctx.strokeStyle = '#2b3038'; ctx.lineWidth = 18; ctx.stroke();
    if (fill > 0.01) {
        tracePath(pts); ctx.strokeStyle = 'rgba(30,120,220,' + (0.85 * fill) + ')'; ctx.lineWidth = 12; ctx.stroke();
        tracePath(pts); ctx.strokeStyle = 'rgba(190,230,255,' + fill + ')'; ctx.lineWidth = 3;
        ctx.setLineDash([10, 16]); ctx.lineDashOffset = -off; ctx.stroke();
        ctx.setLineDash([]);
    }
}

function drawBox(x, y, w, h, title, line1, line2, color, glow) {
    ctx.fillStyle = '#111';
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = color;
    ctx.lineWidth = glow ? 3 : 1.5;
    ctx.strokeRect(x, y, w, h);
    ctx.fillStyle = color;
    ctx.font = 'bold 12px sans-serif';
    ctx.fillText(title, x + 10, y + 24);
    ctx.fillStyle = '#ccc';
    ctx.font = '11px sans-serif';
    ctx.fillText(line1, x + 10, y + 50);
    ctx.fillText(line2, x + 10, y + 68);
}

function drawValve(x, y, open, locked, label) {
    const r = Math.round(255 * (1 - open)), g = Math.round(190 * open + 40 * (1 - open));
    const color = locked ? '#28a745' : 'rgb(' + r + ',' + g + ',60)';
    ctx.setLineDash([]);
    ctx.fillStyle = '#111';
    ctx.beginPath(); ctx.arc(x, y, 17, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.stroke();
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((1 - open) * Math.PI / 2);
    ctx.strokeStyle = color; ctx.lineWidth = 5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(-14, 0); ctx.lineTo(14, 0); ctx.stroke();
    ctx.restore();
    ctx.fillStyle = color;
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(label, x, y - 26);
    ctx.textAlign = 'left';
}

function mix(c1, c2, t) {
    return 'rgb(' + Math.round(c1[0] + (c2[0] - c1[0]) * t) + ',' +
                    Math.round(c1[1] + (c2[1] - c1[1]) * t) + ',' +
                    Math.round(c1[2] + (c2[2] - c1[2]) * t) + ')';
}

// ---------- Main loop ----------
function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pulse += 0.06;

    const target = cityOpen ? 1 : 0;
    openness += (target - openness) * 0.06;
    if (Math.abs(target - openness) < 0.005) openness = target;

    const base = 2.2 * speed;
    offTrunk += base;
    offTest  += base;
    offPre   += base * openness;
    offPost  += base * openness;

    drawPipe(trunk, 1, offTrunk);
    drawPipe(cityPre, 1, offPre);
    drawPipe(cityPost, openness, offPost);
    drawPipe(testPipe, 1, offTest);

    drawValve(520, 80, openness, false, 'CITY VALVE: ' + (openness > 0.5 ? 'OPEN' : 'CLOSED'));
    drawValve(520, 260, 1, true, 'TESTER VALVE: ALWAYS OPEN 🔒');

    drawBox(20, 120, 150, 100, '🏭 WATER PLANT', 'Source supply', 'Continuous output', '#00c0f2', true);

    // City box colour eases between red and green with the valve (no sudden colour flips)
    const cityColor = mix([255, 75, 75], [40, 167, 69], openness);
    drawBox(760, 30, 120, 100, '🏙️ CITY', openness > 0.5 ? 'Receiving water' : 'SUPPLY CUT OFF',
            openness > 0.5 ? 'Flow: ON' : 'Flow: OFF', cityColor, false);

    const testColor = cityOpen ? '#28a745' : '#ff4b4b';
    drawBox(760, 210, 120, 100, '🧪 TESTER', 'Sampling 24x7', cityOpen ? 'Water: SAFE' : 'Water: UNSAFE', testColor, true);
    ctx.strokeStyle = testColor;
    ctx.globalAlpha = 0.5 * (1 - (Math.sin(pulse) + 1) / 2);
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(860, 228, 7 + 6 * ((Math.sin(pulse) + 1) / 2), 0, Math.PI * 2); ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.fillStyle = testColor;
    ctx.beginPath(); ctx.arc(860, 228, 4, 0, Math.PI * 2); ctx.fill();

    ctx.fillStyle = '#777';
    ctx.font = '11px sans-serif';
    ctx.fillText('Pipeline 1 → City', 330, 66);
    ctx.fillText('Pipeline 2 → Tester (never stops)', 330, 246);

    requestAnimationFrame(animate);
}

evaluate();
animate();
</script>
"""

html_canvas = html_template.replace("__PARAMS__", json.dumps(PARAMS))

st.components.v1.html(html_canvas, height=1080, scrolling=True)

st.caption("Limits: BIS IS 10500:2012 (Indian drinking water specification). Verify against the latest BIS revision "
           "before any real-world use. This is an educational simulation, not a certified monitoring system.")
