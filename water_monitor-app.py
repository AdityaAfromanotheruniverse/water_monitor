import streamlit as st
import json
import pandas as pd

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
    # key,        label,                 unit,      category,        acc,    perm,   min,  max,    step,  default, dec
    ("ph",        "pH",                  "",        "Physical",      None,   None,   4.0,  11.0,   0.1,   7.2,     1),
    ("turb",      "Turbidity",           "NTU",     "Physical",      1.0,    5.0,    0.0,  10.0,   0.1,   0.3,     1),
    ("tds",       "Total Dissolved Solids", "mg/L", "Physical",      500.0,  2000.0, 0.0,  3000.0, 10.0,  200.0,   0),
    ("pb",        "Lead (Pb)",           "mg/L",    "Metals",        0.01,   0.01,   0.0,  0.03,   0.001, 0.003,   3),
    ("as",        "Arsenic (As)",        "mg/L",    "Metals",        0.01,   0.05,   0.0,  0.15,   0.001, 0.003,   3),
    ("hg",        "Mercury (Hg)",        "mg/L",    "Metals",        0.001,  0.001,  0.0,  0.003,  0.0001, 0.0003, 4),
    ("cd",        "Cadmium (Cd)",        "mg/L",    "Metals",        0.003,  0.003,  0.0,  0.009,  0.0001, 0.001,  4),
    ("cr",        "Chromium (Cr)",       "mg/L",    "Metals",        0.05,   0.05,   0.0,  0.15,   0.001, 0.01,    3),
    ("ni",        "Nickel (Ni)",         "mg/L",    "Metals",        0.02,   0.02,   0.0,  0.06,   0.001, 0.005,   3),
    ("fe",        "Iron (Fe)",           "mg/L",    "Metals",        1.0,    1.0,    0.0,  3.0,    0.01,  0.2,     2),
    ("cu",        "Copper (Cu)",         "mg/L",    "Metals",        0.05,   1.5,    0.0,  2.5,    0.01,  0.01,    2),
    ("mn",        "Manganese (Mn)",      "mg/L",    "Metals",        0.1,    0.3,    0.0,  0.6,    0.01,  0.02,    2),
    ("zn",        "Zinc (Zn)",           "mg/L",    "Metals",        5.0,    15.0,   0.0,  20.0,   0.1,   1.0,     1),
    ("al",        "Aluminium (Al)",      "mg/L",    "Metals",        0.03,   0.2,    0.0,  0.4,    0.001, 0.01,    3),
    ("f",         "Fluoride (F)",        "mg/L",    "Chemicals",     1.0,    1.5,    0.0,  3.0,    0.01,  0.4,     2),
    ("no3",       "Nitrate (NO3)",       "mg/L",    "Chemicals",     45.0,   45.0,   0.0,  100.0,  1.0,   15.0,    0),
    ("cn",        "Cyanide (CN)",        "mg/L",    "Chemicals",     0.05,   0.05,   0.0,  0.15,   0.001, 0.01,    3),
    ("ecoli",     "E. coli",             "CFU/100mL", "Pathogens",   0,      0,      0,    20,     1,     0,       0),
    ("coliform",  "Total Coliform",      "CFU/100mL", "Pathogens",   0,      0,      0,    20,     1,     0,       0),
]

PARAMS = []
for (key, label, unit, cat, acc, perm, vmin, vmax, step, default, dec) in RAW_PARAMS:
    PARAMS.append(dict(key=key, label=label, unit=unit, cat=cat, acc=acc, perm=perm,
                       vmin=vmin, vmax=vmax, step=step, default=default, dec=dec,
                       is_range=(key == "ph")))

CATEGORY_ORDER = ["Physical", "Metals", "Chemicals", "Pathogens"]
CATEGORY_TITLE = {
    "Physical": "🧪 Physical / General",
    "Metals": "🔩 Heavy & Other Metals",
    "Chemicals": "☣️ Hazardous Chemicals",
    "Pathogens": "🦠 Pathogens",
}


def reset_all():
    for p in PARAMS:
        st.session_state[p["key"]] = p["default"]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🎛️ Water Composition")
    mode = st.radio(
        "Safety limit used to close the city valve",
        ["Acceptable limit (strict)", "Permissible limit (no alternate source)"],
        help="IS 10500:2012 lists an Acceptable limit and a looser Permissible limit that applies only when "
             "no better water source is available. Strict is the safer default.",
    )
    speed = st.slider("⚡ Flow animation speed", 0.5, 3.0, 1.5, 0.25)
    st.button("♻️ Reset all to safe values", on_click=reset_all, type="primary")

    values = {}
    for cat in CATEGORY_ORDER:
        with st.expander(CATEGORY_TITLE[cat], expanded=(cat in ("Metals", "Pathogens"))):
            for p in [x for x in PARAMS if x["cat"] == cat]:
                unit = f" ({p['unit']})" if p["unit"] else ""
                if p["dec"] == 0 and p["key"] in ("ecoli", "coliform", "no3", "tds"):
                    # integer-valued sliders
                    values[p["key"]] = st.slider(
                        p["label"] + unit, int(p["vmin"]), int(p["vmax"]),
                        int(p["default"]), int(p["step"]), key=p["key"])
                else:
                    values[p["key"]] = st.slider(
                        p["label"] + unit, float(p["vmin"]), float(p["vmax"]),
                        float(p["default"]), float(p["step"]),
                        format=f"%.{p['dec']}f", key=p["key"])

strict = mode.startswith("Acceptable")

# ---------------------------------------------------------------------------
# Evaluate every parameter against the standard
# ---------------------------------------------------------------------------
payload = []
table_rows = []
violations = []
for p in PARAMS:
    v = round(float(values[p["key"]]), p["dec"])
    if p["is_range"]:
        lo, hi = 6.5, 8.5  # IS 10500:2012: no relaxation for pH
        violated = (v < lo) or (v > hi)
        limit_txt = f"{lo} – {hi}"
    else:
        limit = p["acc"] if strict else p["perm"]
        violated = v > limit
        if p["cat"] == "Pathogens":
            limit_txt = "Absent (0)"
        else:
            limit_txt = f"≤ {limit:g}"
    if violated:
        violations.append(p["label"])
    payload.append(dict(
        label=p["label"], unit=p["unit"], cat=p["cat"], dec=p["dec"],
        value=v, limit=limit_txt, violated=bool(violated)))
    table_rows.append({"Parameter": p["label"], "Value": v, "Unit": p["unit"],
                       "Limit": limit_txt, "Status": "🚨 UNSAFE" if violated else "✅ OK"})

city_open = len(violations) == 0

# Remember the previous valve state so the valve animates from where it was
prev_open = st.session_state.get("prev_city_open", True)
st.session_state.prev_city_open = city_open

if city_open:
    st.success(f"✅ All {len(PARAMS)} parameters within limits — city valve OPEN.")
else:
    st.error("🚨 UNFIT FOR DRINKING — city valve CLOSED. Violations: " + ", ".join(violations))

# ---------------------------------------------------------------------------
# Canvas animation + live readings panel
# ---------------------------------------------------------------------------
html_template = """
<div style="background:#111; padding:20px; border-radius:12px; font-family:sans-serif; color:white;">
    <div id="liveLine" style="text-align:center; font-size:14px; margin-bottom:4px; color:#aaa;"></div>
    <div id="statusLine" style="text-align:center; font-size:16px; font-weight:bold; margin-bottom:10px; height:22px;"></div>
    <canvas id="plant" width="900" height="340" style="display:block; margin:0 auto; max-width:100%; background:#1a1a1a; border-radius:8px; border:1px solid #333;"></canvas>

    <div style="margin-top:16px; max-height:340px; overflow-y:auto; border-radius:8px; border:1px solid #333;">
        <table style="width:100%; border-collapse:collapse; font-size:13px; color:#ddd;">
            <thead>
                <tr style="position:sticky; top:0; background:#1a1a1a;">
                    <th style="padding:8px; text-align:left; color:#00c0f2;">Parameter</th>
                    <th style="padding:8px; text-align:left; color:#00c0f2;">Group</th>
                    <th style="padding:8px; text-align:left; color:#00c0f2;">Reading</th>
                    <th style="padding:8px; text-align:left; color:#00c0f2;">IS 10500 Limit</th>
                    <th style="padding:8px; text-align:left;">Status</th>
                </tr>
            </thead>
            <tbody id="tbody"></tbody>
        </table>
    </div>
</div>

<script>
const P = __PARAMS__;
const cityOpen = __CITY_OPEN__;
const prevOpen = __PREV_OPEN__;
const speed = __SPEED__;

const canvas = document.getElementById('plant');
const ctx = canvas.getContext('2d');

// ---------- Layout ----------
const trunk    = [[170,170],[300,170]];
const cityPre  = [[300,170],[300,80],[520,80]];
const cityPost = [[520,80],[760,80]];
const testPipe = [[300,170],[300,260],[760,260]];

let openness = prevOpen ? 1 : 0;           // 0 = closed, 1 = open (animates toward target)
const target = cityOpen ? 1 : 0;
let offTrunk = 0, offPre = 0, offPost = 0, offTest = 0;
let pulse = 0;

// ---------- Live readings table ----------
const tbody = document.getElementById('tbody');
let html = '';
P.forEach(function(p, i) {
    const col = p.violated ? '#ff4b4b' : '#28a745';
    html += '<tr id="r' + i + '" style="border-bottom:1px solid #222;">' +
        '<td style="padding:8px;">' + p.label + '</td>' +
        '<td style="padding:8px; color:#777;">' + p.cat + '</td>' +
        '<td style="padding:8px; color:' + col + ';">' + p.value.toFixed(p.dec) + ' ' + p.unit + '</td>' +
        '<td style="padding:8px; color:#aaa;">' + p.limit + '</td>' +
        '<td style="padding:8px; color:' + col + '; font-weight:bold;">' + (p.violated ? '🚨 UNSAFE' : '✅ OK') + '</td></tr>';
});
tbody.innerHTML = html;

// ---------- Status text ----------
const bad = P.filter(function(p) { return p.violated; }).map(function(p) { return p.label; });
const st = document.getElementById('statusLine');
if (cityOpen) {
    st.innerText = '✅ Water is safe — city valve OPEN';
    st.style.color = '#28a745';
} else {
    st.innerText = '🚨 UNSAFE: ' + bad.join(', ') + ' — city valve CLOSED';
    st.style.color = '#ff4b4b';
}

// ---------- Continuous monitoring ticker (scans each sensor in turn) ----------
let sample = 0, scanIdx = 0;
function tick() {
    const prev = document.getElementById('r' + scanIdx);
    if (prev) prev.style.background = '';
    scanIdx = (scanIdx + 1) % P.length;
    sample++;
    const row = document.getElementById('r' + scanIdx);
    if (row) row.style.background = '#1c2733';
    document.getElementById('liveLine').innerHTML =
        '<span style="color:#ff4b4b;">●</span> LIVE MONITORING — sample #' + sample +
        ' — scanning <b style="color:#00c0f2;">' + P[scanIdx].label + '</b>';
}
tick();
setInterval(tick, 700);

// ---------- Drawing helpers ----------
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
    ctx.rotate((1 - open) * Math.PI / 2);   // along the pipe when open, across it when closed
    ctx.strokeStyle = color; ctx.lineWidth = 5; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(-14, 0); ctx.lineTo(14, 0); ctx.stroke();
    ctx.restore();
    ctx.fillStyle = color;
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(label, x, y - 26);
    ctx.textAlign = 'left';
}

// ---------- Main loop ----------
function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    pulse += 0.06;

    // valve moves smoothly toward the commanded state
    openness += (target - openness) * 0.06;
    if (Math.abs(target - openness) < 0.01) openness = target;

    const base = 2.2 * speed;
    offTrunk += base;
    offTest  += base;
    offPre   += base * openness;     // upstream water stops when valve closes
    offPost  += base * openness;

    // Pipes (trunk and tester ALWAYS flow)
    drawPipe(trunk, 1, offTrunk);
    drawPipe(cityPre, 1, offPre);
    drawPipe(cityPost, openness, offPost);   // drains when closed
    drawPipe(testPipe, 1, offTest);

    // Valves
    drawValve(520, 80, openness, false, 'CITY VALVE: ' + (openness > 0.5 ? 'OPEN' : 'CLOSED'));
    drawValve(520, 260, 1, true, 'TESTER VALVE: ALWAYS OPEN 🔒');

    // Water plant
    drawBox(20, 120, 150, 100, '🏭 WATER PLANT', 'Source supply', 'Continuous output', '#00c0f2', true);

    // City
    const cityColor = openness > 0.5 ? '#28a745' : '#ff4b4b';
    drawBox(760, 30, 120, 100, '🏙️ CITY', openness > 0.5 ? 'Receiving water' : 'SUPPLY CUT OFF',
            openness > 0.5 ? 'Flow: ON' : 'Flow: OFF', cityColor, false);

    // Tester (pulsing ring = continuous sampling)
    const testColor = cityOpen ? '#28a745' : '#ff4b4b';
    drawBox(760, 210, 120, 100, '🧪 TESTER', 'Sampling 24x7', cityOpen ? 'Water: SAFE' : 'Water: UNSAFE', testColor, true);
    ctx.strokeStyle = testColor;
    ctx.globalAlpha = 0.5 * (1 - (Math.sin(pulse) + 1) / 2);
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(820, 275, 14 + 10 * ((Math.sin(pulse) + 1) / 2), 0, Math.PI * 2); ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.fillStyle = testColor;
    ctx.beginPath(); ctx.arc(820, 275, 6, 0, Math.PI * 2); ctx.fill();

    // Pipe labels
    ctx.fillStyle = '#777';
    ctx.font = '11px sans-serif';
    ctx.fillText('Pipeline 1 → City', 330, 66);
    ctx.fillText('Pipeline 2 → Tester (never stops)', 330, 246);

    requestAnimationFrame(animate);
}
animate();
</script>
"""

html_canvas = (html_template
               .replace("__PARAMS__", json.dumps(payload))
               .replace("__CITY_OPEN__", str(city_open).lower())
               .replace("__PREV_OPEN__", str(prev_open).lower())
               .replace("__SPEED__", str(speed)))

st.components.v1.html(html_canvas, height=900, scrolling=True)

st.caption("Limits: BIS IS 10500:2012 (Indian drinking water specification). Verify against the latest BIS revision "
           "before any real-world use. This is an educational simulation, not a certified monitoring system.")

with st.expander("📋 Raw readings table"):
    st.dataframe(pd.DataFrame(table_rows).set_index("Parameter"), use_container_width=True)
