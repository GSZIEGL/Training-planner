############################################################
#  app.py — Training Blueprint Edzéstervező
#  6 hetes periodizáció + dátumos ACWR + finalize gomb + period táblázat (UI+PDF)
############################################################

import os
import json
import random
from typing import Dict, Any, List, Set
from datetime import date

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF


############################################################
# 0. STREAMLIT ALAP
############################################################

st.set_page_config(page_title="Training Blueprint", layout="wide")


############################################################
# 1. KONSTANSOK, FÁJLOK
############################################################

JSON_PATH = "drill_metadata_with_u7u9.json"
ACWR_HISTORY_PATH = "acwr_history.json"        # tartós ACWR tárolás
LOGO_PATH = "TBP_pdfsafe.png"
MATCH_IMAGE = "match_game.png"
BACKGROUND = "pitch_background.png"

DEJAVU_REG = "DejaVuSans.ttf"
DEJAVU_BOLD = "DejaVuSans-Bold.ttf"


############################################################
# 2. SEGÉD
############################################################

def pdf_safe(text):
    if not text:
        return ""
    return str(text).replace("…", "...").replace("’", "'")


############################################################
# 3. ACWR HISTORY BETÖLTÉS / MENTÉS
############################################################

def load_acwr_history() -> Dict[str, Any]:
    if not os.path.exists(ACWR_HISTORY_PATH):
        return {}
    try:
        with open(ACWR_HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_acwr_history(data: Dict[str, Any]):
    with open(ACWR_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

ACWR_DB = load_acwr_history()


############################################################
# 4. TAKTIKAI NORMALIZÁLÁS (ékezetes, 6 hetes új címkékkel)
############################################################

TACTICAL_CANONICAL = {
    # játékszervezés
    "játék_szervezés": "játékszervezés",
    "jatek_szervezes": "játékszervezés",
    "jatekszervezes": "játékszervezés",
    "jatekszervezés": "játékszervezés",
    "játékszervezés": "játékszervezés",

    # labdakihozatal
    "labdakihozatal": "labdakihozatal",
    "labdakihozatal_": "labdakihozatal",
    "labda kihozatal": "labdakihozatal",

    # befejezés
    "befejezes": "befejezés",
    "befejezés": "befejezés",

    # átmenet védekezésbe
    "atmenet vedekezesbe": "átmenet védekezésbe",
    "átmenet védekezésbe": "átmenet védekezésbe",
    "atmenet_vedekezesbe": "átmenet védekezésbe",
    "átmenet_ védekezésbe": "átmenet védekezésbe",

    # védekezés
    "vedekezes": "védekezés",
    "védekezés": "védekezés",

    # átmenet támadásba
    "atmenet tamadasba": "átmenet támadásba",
    "átmenet támadásba": "átmenet támadásba",
    "atmenet_tamadasba": "átmenet támadásba",
}

@st.cache_data
def load_db() -> List[Dict[str, Any]]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    for ex in db:
        raw_main = ex.get("fo_taktikai_cel", "")
        main_norm = TACTICAL_CANONICAL.get(str(raw_main).lower(), str(raw_main).lower())
        ex["fo_taktikai_cel"] = main_norm

        fixed_tags = []
        for t in ex.get("taktikai_cel_cimkek", []):
            t_norm = TACTICAL_CANONICAL.get(str(t).lower(), str(t).lower())
            fixed_tags.append(t_norm)
        ex["taktikai_cel_cimkek"] = fixed_tags

    return db

EX_DB = load_db()


############################################################
# 5. TECHNIKAI + KONDI LISTÁK
############################################################

TECHNIKAI_SIMPLE = [
    "passz",
    "átvétel",
    "labdavezetés",
    "lövések",
    "fejelés",
    "cselezés"
]

KONDIC_SIMPLE = [
    "gyorsaság",
    "állóképesség",
    "erő",
    "agilitás"
]


############################################################
# 6. 6 HETES PERIODIZÁCIÓ (taktikai + technikai + kondi + szorzó)
############################################################

# Taktikai opciók – fix, duplikációmentes lista
TACTICAL_OPTIONS = [
    "labdakihozatal",
    "játékszervezés",
    "befejezés",
    "átmenet védekezésbe",
    "védekezés",
    "átmenet támadásba",
]

PERIOD_TABLE_6W = {
    1: {"taktikai": "labdakihozatal",        "technikai": "passz",        "kondi": "állóképesség", "szorzo": 1.00},
    2: {"taktikai": "játékszervezés",        "technikai": "labdavezetés", "kondi": "agilitás",      "szorzo": 1.05},
    3: {"taktikai": "befejezés",             "technikai": "lövések",      "kondi": "erő",           "szorzo": 1.10},
    4: {"taktikai": "átmenet védekezésbe",   "technikai": "átvétel",      "kondi": "gyorsaság",     "szorzo": 1.15},
    5: {"taktikai": "védekezés",             "technikai": "fejelés",      "kondi": "állóképesség",  "szorzo": 1.20},
    6: {"taktikai": "átmenet támadásba",     "technikai": "cselezés",     "kondi": "gyorsaság",     "szorzo": 1.25},
}

def get_period_targets(period_week: int) -> Dict[str, Any]:
    return PERIOD_TABLE_6W.get(period_week, PERIOD_TABLE_6W[1])

def get_period_table_df() -> pd.DataFrame:
    rows = []
    for w in range(1, 7):
        r = PERIOD_TABLE_6W[w].copy()
        r["Hét"] = w
        rows.append(r)
    df = pd.DataFrame(rows)[["Hét", "taktikai", "technikai", "kondi", "szorzo"]]
    df.columns = ["Hét", "Taktikai cél", "Technikai cél", "Kondicionális cél", "Intenzitás szorzó"]
    return df


############################################################
# 7. WORKLOAD (Model 1, periodizációs szorzóval)
############################################################

BASE_LOAD = {
    "bemelegites": 100,
    "cel1": 250,
    "cel2": 250,
    "cel3": 300
}

TECH_BONUS = {
    "passz": 20,
    "átvétel": 20,
    "labdavezetés": 25,
    "lövések": 30,
    "fejelés": 20,
    "cselezés": 40
}

KONDI_BONUS = {
    "gyorsaság": 30,
    "állóképesség": 50,
    "erő": 40,
    "agilitás": 35
}

STAGES = ["bemelegites", "cel1", "cel2", "cel3"]

def compute_workload(period_week: int,
                     stages: List[str],
                     tech: List[str],
                     kondi: List[str]) -> float:
    period = get_period_targets(period_week)
    mult = float(period["szorzo"])

    base = sum(BASE_LOAD.get(s, 0) for s in stages)
    tech_bonus = sum(TECH_BONUS.get(t, 0) for t in tech)
    kond_bonus = sum(KONDI_BONUS.get(k, 0) for k in kondi)

    return (base + tech_bonus + kond_bonus) * mult


############################################################
# 8. EDZŐ / CSAPAT / DÁTUM (dátum felülírható)
############################################################

st.sidebar.header("Edző és csapat")

coach_name = st.sidebar.text_input("Edző neve", value="Edző Béla")
team_name = st.sidebar.text_input("Csapat neve", value="U13 Akadémia")

today = date.today()
training_date = st.sidebar.date_input("Edzés dátuma", value=today)
st.sidebar.caption("A dátum szabadon módosítható (előre vagy visszamenőleg is).")

iso_year, iso_week, _ = training_date.isocalendar()
week_key = f"{iso_year}-W{iso_week:02d}"  # ACWR kulcs

coach_id = f"coach_{abs(hash(coach_name)) % 10**8}"
team_id = f"team_{abs(hash(team_name)) % 10**8}"

st.sidebar.write(f"Edző ID: {coach_id}")
st.sidebar.write(f"Csapat ID: {team_id}")
st.sidebar.write(f"Naptári hét (ACWR): {week_key}")

# ACWR struktúra biztosítása
if coach_id not in ACWR_DB:
    ACWR_DB[coach_id] = {}
if team_id not in ACWR_DB[coach_id]:
    ACWR_DB[coach_id][team_id] = {}


############################################################
# 9. ACWR (dátumos week_key)
############################################################

def save_weekly_workload(coach_id: str, team_id: str, week_key: str, workload: float):
    prev = ACWR_DB[coach_id][team_id].get(week_key, 0.0)
    ACWR_DB[coach_id][team_id][week_key] = prev + float(workload)
    save_acwr_history(ACWR_DB)

def compute_acwr(coach_id: str, team_id: str, current_week_key: str):
    team_weeks = ACWR_DB.get(coach_id, {}).get(team_id, {})
    if not team_weeks:
        return None, None, None

    acute = team_weeks.get(current_week_key)
    if acute is None:
        return None, None, None

    keys = sorted(team_weeks.keys())  # YYYY-Www lexikografikusan jó
    idx = keys.index(current_week_key) if current_week_key in keys else None
    if idx is None:
        return acute, None, None

    prev_keys = keys[max(0, idx - 4):idx]
    chronic_vals = [team_weeks[k] for k in prev_keys]

    if not chronic_vals:
        return acute, None, None

    chronic = sum(chronic_vals) / len(chronic_vals)
    acwr = acute / chronic if chronic > 0 else None
    return acute, chronic, acwr

def plot_acwr_history(coach_id: str, team_id: str):
    team_weeks = ACWR_DB.get(coach_id, {}).get(team_id, {})
    if not team_weeks:
        st.info("Nincs ACWR adat még ehhez a csapathoz.")
        return

    keys = sorted(team_weeks.keys())
    loads = [team_weeks[k] for k in keys]
    acwr_vals = []
    for k in keys:
        _, _, a = compute_acwr(coach_id, team_id, k)
        acwr_vals.append(a)

    x = list(range(len(keys)))
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.plot(x, loads, marker="o")
    ax1.set_xlabel("Hét (YYYY-Www)")
    ax1.set_ylabel("Workload")

    ax2 = ax1.twinx()
    ax2.plot(x, acwr_vals, marker="s")
    ax2.set_ylabel("ACWR")
    ax2.axhspan(0.8, 1.3, alpha=0.2)

    ax1.set_xticks(x)
    ax1.set_xticklabels(keys, rotation=45, ha="right")
    ax1.grid(True, alpha=0.3)
    st.pyplot(fig)


############################################################
# 10. GYAKORLAT VÁLASZTÁS
############################################################

def stage_label(s: str) -> str:
    return {
        "bemelegites": "Bemelegítés",
        "cel1": "Cél 1",
        "cel2": "Cél 2",
        "cel3": "Cél 3"
    }.get(s, s)

def score_exercise(ex, stage: str, desired_fo: str, tact: List[str], age_group: str) -> int:
    score = 0
    if ex.get("fo_taktikai_cel") == desired_fo:
        score += 5
    for t in tact:
        if t in ex.get("taktikai_cel_cimkek", []):
            score += 2
    if age_group in ex.get("ajanlott_korosztalyok", []):
        score += 1
    return score

def pick_exercise(stage: str,
                  desired_fo: str,
                  tact: List[str],
                  used_ids: Set[str],
                  age_group: str):
    candidates = []
    for ex in EX_DB:
        if ex.get("edzes_resze") != stage:
            continue
        if age_group not in ex.get("ajanlott_korosztalyok", []):
            continue
        if ex.get("file_name") in used_ids:
            continue

        s = score_exercise(ex, stage, desired_fo, tact, age_group)
        candidates.append((s, ex))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score = candidates[0][0]
    best = [ex for s, ex in candidates if s == best_score]
    return random.choice(best)


############################################################
# 11. SESSION STATE
############################################################

if "plan" not in st.session_state:
    st.session_state.plan = []
if "used_ids" not in st.session_state:
    st.session_state.used_ids = set()
if "match_override" not in st.session_state:
    st.session_state.match_override = False


def generate_plan(fo_taktikai: str, tact_list: List[str], age_group: str):
    plan = []
    used = set()

    for stg in STAGES:
        ex = pick_exercise(stg, fo_taktikai, tact_list, used, age_group)
        if ex:
            used.add(ex["file_name"])
            ex.setdefault("description", "")
            ex.setdefault("organisation", "")
            ex.setdefault("coaching_points", "")
            plan.append({"stage": stg, "exercise": ex})

    st.session_state.plan = plan
    st.session_state.used_ids = used


############################################################
# 12. UI — CÍM + PERIODIZÁCIÓS TÁBLÁK
############################################################

st.title("⚽ Training Blueprint – Edzéstervező")

st.header("📊 Periodizáció")

period_week = st.sidebar.number_input("Periodizációs hét (1–6)", 1, 6, 1)
period_targets = get_period_targets(period_week)

# 1) Adott hét céljai – “felső tábla”
one_row = pd.DataFrame([{
    "Hét": period_week,
    "Taktikai cél": period_targets["taktikai"],
    "Technikai cél": period_targets["technikai"],
    "Kondicionális cél": period_targets["kondi"],
    "Intenzitás szorzó": period_targets["szorzo"],
}])

st.subheader("Az aktuális hét céljai")
st.table(one_row)

# 2) Teljes 6 hetes ciklus – lenyitható
with st.expander("Teljes 6 hetes periodizáció megtekintése"):
    st.dataframe(get_period_table_df(), use_container_width=True)


############################################################
# 13. OLDALSÁV — EDZÉS PARAMÉTEREI
############################################################

st.sidebar.header("Edzés paraméterei")

age_group = st.sidebar.selectbox(
    "Korosztály",
    ["U7-U9", "U10-U12", "U13-U15", "U16-U19", "felnott"]
)

fo_taktikai = st.sidebar.selectbox(
    "Fő taktikai cél",
    options=TACTICAL_OPTIONS,
    index=TACTICAL_OPTIONS.index(period_targets["taktikai"])
)

taktikai_valasztott = st.sidebar.multiselect(
    "Taktikai címkék",
    options=TACTICAL_OPTIONS,
    default=[period_targets["taktikai"]]
)

technikai_valasztott = st.sidebar.multiselect(
    "Technikai fókusz",
    options=TECHNIKAI_SIMPLE,
    default=[period_targets["technikai"]]
)

kond_valasztott = st.sidebar.multiselect(
    "Kondicionális fókusz",
    options=KONDIC_SIMPLE,
    default=[period_targets["kondi"]]
)

coach_notes = st.text_area("🧠 Edzői össz-megjegyzés az edzéshez")


############################################################
# 14. EDZÉS GENERÁLÁS (NEM ment ACWR-t)
############################################################

if st.button("🚀 Edzés generálása"):
    generate_plan(fo_taktikai, taktikai_valasztott, age_group)
    st.success("Edzés generálva! Ha kész vagy vele, használd az 'Edzés véglegesítése' gombot a terhelés mentéséhez.")


############################################################
# 15. EDZÉS BLOKKOK
############################################################

st.header("📋 Generált edzés")

for i, block in enumerate(st.session_state.plan):
    if "stage" not in block or "exercise" not in block:
        continue

    stage = block["stage"]
    ex = block["exercise"]

    st.subheader(stage_label(stage))

    colL, colR = st.columns([1, 2])

    with colL:
        if stage == "cel3":
            st.session_state.match_override = st.checkbox(
                "Mérkőzésjáték használata",
                key=f"match_{i}"
            )

        if stage == "cel3" and st.session_state.match_override:
            st.image(MATCH_IMAGE, width=300)
        else:
            img = ex.get("file_name")
            if img and os.path.exists(img):
                st.image(img, width=300)
            else:
                st.warning("Nincs kép ehhez a gyakorlathoz.")

    with colR:
        ex["description"] = st.text_area("Leírás", ex.get("description", ""), key=f"desc_{i}")
        ex["organisation"] = st.text_area("Szervezés", ex.get("organisation", ""), key=f"org_{i}")
        ex["coaching_points"] = st.text_area("Coaching pontok", ex.get("coaching_points", ""), key=f"coach_{i}")

        if st.button(f"🔄 Gyakorlat cseréje ({stage_label(stage)})", key=f"replace_{i}"):
            if stage == "cel3" and st.session_state.match_override:
                st.warning("Mérkőzésjáték módban nem cserélhető a gyakorlat.")
            else:
                new_ex = pick_exercise(stage, fo_taktikai, taktikai_valasztott, st.session_state.used_ids, age_group)
                if new_ex:
                    fid = new_ex.get("file_name")
                    if fid:
                        st.session_state.used_ids.add(fid)
                    new_ex.setdefault("description", "")
                    new_ex.setdefault("organisation", "")
                    new_ex.setdefault("coaching_points", "")
                    st.session_state.plan[i]["exercise"] = new_ex
                else:
                    st.error("Ehhez az edzésrészhez nincs több releváns gyakorlat.")


############################################################
# 16. ACWR megjelenítés + figyelmeztetés
############################################################

st.header("📈 ACWR trend (naptári hetek alapján)")

acute, chronic, acwr = compute_acwr(coach_id, team_id, week_key)

c1, c2, c3 = st.columns(3)
c1.metric("Akut terhelés", f"{acute:.1f}" if acute is not None else "N/A")
c2.metric("Krónikus terhelés (4 hét átlaga)", f"{chronic:.1f}" if chronic is not None else "N/A")
c3.metric("ACWR", f"{acwr:.2f}" if acwr is not None else "N/A")

if acwr is not None:
    if acwr < 0.8:
        st.warning("ACWR < 0.8 – alulterhelés / detraining zóna.")
    elif 0.8 <= acwr <= 1.3:
        st.success("ACWR 0.8–1.3 – optimális terhelési zóna. ✅")
    elif 1.3 < acwr <= 1.5:
        st.warning("ACWR 1.3–1.5 – emelkedett terhelés, fokozott odafigyelés javasolt.")
    else:
        st.error("ACWR > 1.5 – magas terhelési spike, sérüléskockázat! 🔴")

plot_acwr_history(coach_id, team_id)


############################################################
# 17. EDZÉS VÉGLEGESÍTÉSE (ACWR mentés TRIGGER)
############################################################

st.header("✅ Edzés véglegesítése")

if st.button("✅ Edzés véglegesítése és terhelés mentése"):
    if not st.session_state.plan:
        st.warning("Nincs generált edzés. Előbb készíts egy edzéstervet.")
    else:
        workload = compute_workload(period_week, STAGES, technikai_valasztott, kond_valasztott)
        save_weekly_workload(coach_id, team_id, week_key, workload)
        acute, chronic, acwr = compute_acwr(coach_id, team_id, week_key)
        st.success(f"Véglegesítve. Workload: {workload:.1f} | Naptári hét: {week_key}")
        if acwr is not None:
            st.info(f"Friss ACWR erre a hétre: {acwr:.2f}")


############################################################
# 18. PDF EXPORT (periodizációs táblával)
############################################################

st.header("📄 PDF Export")

class TBPDF(FPDF):
    def header(self):
        try:
            self.image(BACKGROUND, x=0, y=0, w=210, h=297)
        except:
            pass
        try:
            self.image(LOGO_PATH, x=165, y=10, w=30)
        except:
            pass
        self.set_y(25)

def pdf_add_period_table(pdf: FPDF, base_font: str, period_week: int):
    """PDF-be: 1 soros (aktuális hét) + opcionálisan 6 soros mini-tábla."""
    df = get_period_table_df()
    current = df[df["Hét"] == period_week]

    pdf.set_font(base_font, "B", 12)
    pdf.cell(0, 8, pdf_safe("Periodizáció (aktuális hét):"), ln=1)

    # 1 soros tábla (aktuális hét)
    row = current.iloc[0].to_dict()
    pdf.set_font(base_font, "", 11)
    pdf.multi_cell(0, 6, pdf_safe(
        f"Hét {row['Hét']} | "
        f"Taktika: {row['Taktikai cél']} | "
        f"Technika: {row['Technikai cél']} | "
        f"Kondi: {row['Kondicionális cél']} | "
        f"Szorzo: {row['Intenzitás szorzó']}"
    ))

    pdf.ln(2)
    pdf.set_font(base_font, "B", 12)
    pdf.cell(0, 8, pdf_safe("Teljes 6 hetes ciklus:"), ln=1)

    # Egyszerű táblázat (6 sor)
    col_widths = [12, 55, 45, 45, 25]  # Hét, takt, tech, kondi, szorzo
    headers = ["Hét", "Taktikai", "Technikai", "Kondi", "Szorzó"]

    pdf.set_font(base_font, "B", 10)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, pdf_safe(h), border=1)
    pdf.ln()

    pdf.set_font(base_font, "", 10)
    for _, r in df.iterrows():
        pdf.cell(col_widths[0], 7, pdf_safe(str(r["Hét"])), border=1)
        pdf.cell(col_widths[1], 7, pdf_safe(str(r["Taktikai cél"])), border=1)
        pdf.cell(col_widths[2], 7, pdf_safe(str(r["Technikai cél"])), border=1)
        pdf.cell(col_widths[3], 7, pdf_safe(str(r["Kondicionális cél"])), border=1)
        pdf.cell(col_widths[4], 7, pdf_safe(str(r["Intenzitás szorzó"])), border=1)
        pdf.ln()

    pdf.ln(2)

def create_pdf():
    pdf = TBPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    base = "Arial"
    try:
        pdf.add_font("DejaVu", "", DEJAVU_REG, uni=True)
        pdf.add_font("DejaVu", "B", DEJAVU_BOLD, uni=True)
        base = "DejaVu"
    except:
        pass

    # Címlap
    pdf.add_page()
    pdf.set_font(base, "B", 16)
    pdf.cell(0, 10, pdf_safe("Training Blueprint – Edzésterv"), ln=1)

    pdf.set_font(base, "", 12)
    pdf.multi_cell(0, 6, pdf_safe(f"Edző: {coach_name}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Csapat: {team_name}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Korosztály: {age_group}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Edzés dátuma: {training_date.isoformat()}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Naptári hét (ACWR): {week_key}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Periodizációs hét: {period_week}"))

    pdf.ln(2)
    pdf_add_period_table(pdf, base, period_week)

    pdf.set_font(base, "B", 12)
    pdf.cell(0, 8, pdf_safe("Edzői megjegyzés:"), ln=1)
    pdf.set_font(base, "", 12)
    pdf.multi_cell(0, 6, pdf_safe(coach_notes))

    # Gyakorlatok
    for block in st.session_state.plan:
        if "stage" not in block or "exercise" not in block:
            continue

        pdf.add_page()
        stage = block["stage"]
        ex = block["exercise"]

        pdf.set_font(base, "B", 14)
        pdf.cell(0, 10, pdf_safe(stage_label(stage)), ln=1)
        pdf.ln(3)

        img = ex.get("file_name")
        if stage == "cel3" and st.session_state.match_override:
            img = MATCH_IMAGE

        if img and os.path.exists(img):
            try:
                pdf.image(img, w=150)
            except:
                pdf.multi_cell(0, 6, pdf_safe("Kép nem tölthető be."))

        pdf.ln(5)

        pdf.set_font(base, "B", 12)
        pdf.cell(0, 6, pdf_safe("Leírás:"), ln=1)
        pdf.set_font(base, "", 12)
        pdf.multi_cell(0, 6, pdf_safe(ex.get("description", "")))
        pdf.ln(2)

        pdf.set_font(base, "B", 12)
        pdf.cell(0, 6, pdf_safe("Szervezés:"), ln=1)
        pdf.set_font(base, "", 12)
        pdf.multi_cell(0, 6, pdf_safe(ex.get("organisation", "")))
        pdf.ln(2)

        pdf.set_font(base, "B", 12)
        pdf.cell(0, 6, pdf_safe("Coaching pontok:"), ln=1)
        pdf.set_font(base, "", 12)
        pdf.multi_cell(0, 6, pdf_safe(ex.get("coaching_points", "")))

    raw = pdf.output(dest="S")
    return raw if isinstance(raw, bytes) else raw.encode("latin-1", "ignore")

if st.session_state.plan:
    pdf_bytes = create_pdf()
    st.download_button(
        "📄 PDF letöltése",
        data=pdf_bytes,
        file_name="edzesterv.pdf",
        mime="application/pdf"
    )
else:
    st.info("Előbb generálj edzést!")
