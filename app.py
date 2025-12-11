############################################################
#  app.py — Training Blueprint Edzéstervező (FULL)
############################################################

import os
import json
import random
from typing import Dict, Any, List, Set

import streamlit as st
import matplotlib.pyplot as plt
from fpdf import FPDF

# Ha később kell:
# from pitch_drawer import draw_drill


############################################################
# 0. STREAMLIT ALAP
############################################################

st.set_page_config(page_title="Training Blueprint", layout="wide")


############################################################
# 1. KONSTANSOK, FÁJLOK
############################################################

JSON_PATH = "drill_metadata_with_u7u9.json"
ACWR_HISTORY_PATH = "acwr_history.json"        # ACWR tartós tárolása
DRILL_IMAGE_FOLDER = "."
LOGO_PATH = "TBP_pdfsafe.png"
MATCH_IMAGE = "match_game.png"
BACKGROUND = "pitch_background.png"

DEJAVU_REG = "DejaVuSans.ttf"
DEJAVU_BOLD = "DejaVuSans-Bold.ttf"


############################################################
# 2. SEGÉDFÜGGVÉNYEK
############################################################

def pdf_safe(text):
    if not text:
        return ""
    return str(text).replace("…", "...").replace("’", "'")


############################################################
# 3. ACWR HISTORY BETÖLTÉSE / MENTÉSE
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
# 4. TAKTIKAI CÍMKÉK NORMALIZÁLÁSA
############################################################

TACTICAL_CANONICAL = {
    "játék_szervezés": "játékszervezés",
    "jatekszervezes": "játékszervezés",
    "jatek_szervezes": "játékszervezés",
    "játékszervezés": "játékszervezés",
    "jatekszervezés": "játékszervezés",
    "jatekszervezet": "játékszervezés",

    "labdakihozatal": "labdakihozatal",
    "labdakihozatal_": "labdakihozatal",

    "befejezes": "befejezés",
    "befejezés": "befejezés",

    "atmenet": "átmenet",
    "átmenet": "átmenet"
}


@st.cache_data
def load_db() -> List[Dict[str, Any]]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    for ex in db:
        # fő taktikai cél normalizálása
        raw = ex.get("fo_taktikai_cel", "").lower()
        ex["fo_taktikai_cel"] = TACTICAL_CANONICAL.get(raw, raw)

        # taktikai címkék normalizálása
        fixed = []
        for t in ex.get("taktikai_cel_cimkek", []):
            t_norm = TACTICAL_CANONICAL.get(t.lower(), t.lower())
            fixed.append(t_norm)
        ex["taktikai_cel_cimkek"] = fixed

    return db


EX_DB = load_db()


############################################################
# 5. TECHNIKAI ÉS KONDI CÉLOK
############################################################

TECHNIKAI_SIMPLE = [
    "passz",
    "átvétel",
    "labdavezetés",
    "lövések",
    "fejelés",
    "cselezés"  # új elem
]

KONDIC_SIMPLE = [
    "gyorsaság",
    "állóképesség",
    "erő",
    "agilitás"
]


############################################################
# 6. PERIODIZÁCIÓS TÁBLA (4 hetes ciklus)
############################################################

PERIOD_TABLE = {
    1: {
        "taktikai": "játékszervezés",
        "technikai": "passz",
        "kondi": "állóképesség",
        "szorzo": 1.00
    },
    2: {
        "taktikai": "labdakihozatal",
        "technikai": "labdavezetés",
        "kondi": "gyorsaság",
        "szorzo": 1.10
    },
    3: {
        "taktikai": "befejezés",
        "technikai": "lövések",
        "kondi": "erő",
        "szorzo": 1.20
    },
    4: {
        "taktikai": "átmenet",
        "technikai": "cselezés",
        "kondi": "agilitás",
        "szorzo": 1.30
    }
}

# tiszta taktikai opciók (nincs duplikáció)
TACTICAL_OPTIONS = ["játékszervezés", "labdakihozatal", "befejezés", "átmenet"]


def get_period_targets(week: int) -> Dict[str, Any]:
    return PERIOD_TABLE.get(week, PERIOD_TABLE[1])


############################################################
# 7. WORKLOAD SZÁMÍTÁS (Model 1)
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


def compute_workload(week: int,
                     stages: List[str],
                     tech: List[str],
                     kondi: List[str]) -> float:
    period = get_period_targets(week)
    mult = period["szorzo"]

    base = 0
    for s in stages:
        base += BASE_LOAD.get(s, 0)

    tech_bonus = sum(TECH_BONUS.get(t, 0) for t in tech)
    kond_bonus = sum(KONDI_BONUS.get(k, 0) for k in kondi)

    return (base + tech_bonus + kond_bonus) * mult


############################################################
# 8. EDZŐ ÉS CSAPAT ADATOK
############################################################

st.sidebar.header("Edző és csapat")

coach_name = st.sidebar.text_input("Edző neve", value="Edző Béla")
team_name = st.sidebar.text_input("Csapat neve", value="U13 Akadémia")

coach_id = f"coach_{abs(hash(coach_name)) % 10**8}"
team_id = f"team_{abs(hash(team_name)) % 10**8}"

st.sidebar.write(f"Edző ID: {coach_id}")
st.sidebar.write(f"Csapat ID: {team_id}")

# ACWR_DB struktúra biztosítása
if coach_id not in ACWR_DB:
    ACWR_DB[coach_id] = {}
if team_id not in ACWR_DB[coach_id]:
    ACWR_DB[coach_id][team_id] = {}


############################################################
# 9. ACWR FUNKCIÓK
############################################################

def save_weekly_workload(coach_id: str,
                         team_id: str,
                         week: int,
                         workload: float):
    """
    Ha ugyanarra a hétre többször generálsz edzést,
    ÖSSZEADJA a workloadokat (több edzés/hét).
    """
    if coach_id not in ACWR_DB:
        ACWR_DB[coach_id] = {}
    if team_id not in ACWR_DB[coach_id]:
        ACWR_DB[coach_id][team_id] = {}

    week_key = str(week)
    prev = ACWR_DB[coach_id][team_id].get(week_key, 0.0)
    ACWR_DB[coach_id][team_id][week_key] = prev + workload

    save_acwr_history(ACWR_DB)


def compute_acwr(coach_id: str,
                 team_id: str,
                 current_week: int):
    team_weeks = ACWR_DB.get(coach_id, {}).get(team_id, {})

    if not team_weeks:
        return None, None, None

    acute = team_weeks.get(str(current_week))
    if acute is None:
        return None, None, None

    chronic_values = []
    for w in range(current_week - 4, current_week):
        if w > 0:
            val = team_weeks.get(str(w))
            if val is not None:
                chronic_values.append(val)

    if len(chronic_values) == 0:
        chronic = None
        acwr = None
    else:
        chronic = sum(chronic_values) / len(chronic_values)
        acwr = acute / chronic if chronic > 0 else None

    return acute, chronic, acwr


def plot_acwr_history(coach_id: str, team_id: str):
    team_weeks = ACWR_DB.get(coach_id, {}).get(team_id, {})

    if not team_weeks:
        st.info("Nincs ACWR adat még ehhez a csapathoz.")
        return

    weeks = sorted([int(w) for w in team_weeks.keys()])
    loads = [team_weeks[str(w)] for w in weeks]

    acwr_values = []
    for w in weeks:
        _, _, acwr = compute_acwr(coach_id, team_id, w)
        acwr_values.append(acwr)

    fig, ax1 = plt.subplots(figsize=(8, 4))

    ax1.plot(weeks, loads, marker="o", label="Workload")
    ax1.set_xlabel("Hét")
    ax1.set_ylabel("Workload")

    ax2 = ax1.twinx()
    ax2.plot(weeks, acwr_values, marker="s", label="ACWR")
    ax2.set_ylabel("ACWR")

    # optimális zóna
    ax2.axhspan(0.8, 1.3, alpha=0.2)

    ax1.grid(True, alpha=0.3)
    st.pyplot(fig)


############################################################
# 10. SEGÉD — STAGE LABEL
############################################################

def stage_label(s: str) -> str:
    return {
        "bemelegites": "Bemelegítés",
        "cel1": "Cél 1",
        "cel2": "Cél 2",
        "cel3": "Cél 3"
    }.get(s, s)


############################################################
# 11. GYAKORLAT PONTOZÁSA / VÁLASZTÁSA
############################################################

def score_exercise(ex,
                   stage: str,
                   desired_fo: str,
                   tact: List[str],
                   tech: List[str],
                   kond: List[str],
                   age_group: str) -> int:
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
                  tech: List[str],
                  kond: List[str],
                  used_ids: Set[str],
                  age_group: str):

    candidates = []

    for ex in EX_DB:
        if ex.get("edzes_resze") != stage:
            continue
        if age_group not in ex.get("ajanlott_korosztalyok", []):
            continue
        if ex["file_name"] in used_ids:
            continue

        s = score_exercise(ex, stage, desired_fo, tact, tech, kond, age_group)
        candidates.append((s, ex))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score = candidates[0][0]
    best = [ex for s, ex in candidates if s == best_score]

    return random.choice(best)


############################################################
# 12. SESSIONS
############################################################

if "plan" not in st.session_state:
    st.session_state.plan = []

if "used_ids" not in st.session_state:
    st.session_state.used_ids = set()

if "match_override" not in st.session_state:
    st.session_state.match_override = False

STAGES = ["bemelegites", "cel1", "cel2", "cel3"]


def generate_plan(fo_taktikai,
                  tact_list,
                  tech_list,
                  kond_list,
                  age_group):

    plan = []
    used = set()

    for stg in STAGES:
        ex = pick_exercise(
            stg,
            fo_taktikai,
            tact_list,
            tech_list,
            kond_list,
            used,
            age_group
        )
        if ex:
            used.add(ex["file_name"])
            ex.setdefault("description", "")
            ex.setdefault("organisation", "")
            ex.setdefault("coaching_points", "")
            plan.append({"stage": stg, "exercise": ex})

    st.session_state.plan = plan
    st.session_state.used_ids = used


############################################################
# 13. UI — FELSŐ RÉSZ: CÍM + PERIODIZÁCIÓ
############################################################

st.title("⚽ Training Blueprint – Edzéstervező")

st.header("📊 Heti periodizációs fókusz")

week = st.sidebar.number_input("Periodizációs hét", 1, 4, 1)
period_targets = get_period_targets(week)

colA, colB, colC, colD = st.columns(4)
colA.metric("Taktikai fókusz", period_targets["taktikai"])
colB.metric("Technikai fókusz", period_targets["technikai"])
colC.metric("Kondicionális fókusz", period_targets["kondi"])
colD.metric("Intenzitási szorzó", period_targets["szorzo"])


############################################################
# 14. OLDALSÁV – EDZÉS PARAMÉTEREI
############################################################

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
# 15. EDZÉS GENERÁLÁS
############################################################

if st.button("🚀 Edzés generálása"):
    generate_plan(
        fo_taktikai,
        taktikai_valasztott,
        technikai_valasztott,
        kond_valasztott,
        age_group
    )

    workload = compute_workload(
        week,
        STAGES,
        technikai_valasztott,
        kond_valasztott
    )
    save_weekly_workload(coach_id, team_id, week, workload)
    st.success(f"Edzés elkészült! Workload erre az edzésre: {workload:.1f}")


############################################################
# 16. EDZÉS BLOKKOK MEGJELENÍTÉSE
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
        ex["description"] = st.text_area(
            "Leírás", ex.get("description", ""), key=f"desc_{i}"
        )
        ex["organisation"] = st.text_area(
            "Szervezés", ex.get("organisation", ""), key=f"org_{i}"
        )
        ex["coaching_points"] = st.text_area(
            "Coaching pontok", ex.get("coaching_points", ""), key=f"coach_{i}"
        )

        if st.button(f"🔄 Gyakorlat cseréje ({stage_label(stage)})", key=f"replace_{i}"):

            if stage == "cel3" and st.session_state.match_override:
                st.warning("Mérkőzésjáték módban nem cserélhető a gyakorlat.")
            else:
                new_ex = pick_exercise(
                    stage,
                    fo_taktikai,
                    taktikai_valasztott,
                    technikai_valasztott,
                    kond_valasztott,
                    st.session_state.used_ids,
                    age_group
                )

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
# 17. ACWR MEGJELÍTÉS + FIGYELMEZTETÉS
############################################################

st.header("📈 ACWR trend")

acute, chronic, acwr = compute_acwr(coach_id, team_id, week)

col1, col2, col3 = st.columns(3)
col1.metric("Akut terhelés", f"{acute:.1f}" if acute is not None else "N/A")
col2.metric("Krónikus terhelés (4 hét átlaga)", f"{chronic:.1f}" if chronic is not None else "N/A")
col3.metric("ACWR", f"{acwr:.2f}" if acwr is not None else "N/A")

# ACWR figyelmeztetés
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
# 18. PDF EXPORT
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
    pdf.multi_cell(0, 6, pdf_safe(f"Hét: {week}"))

    pdf.ln(4)
    pdf.set_font(base, "B", 12)
    pdf.cell(0, 8, pdf_safe("Heti periodizáció:"), ln=1)
    pdf.set_font(base, "", 12)
    pdf.multi_cell(0, 6, pdf_safe(f"Taktikai fókusz: {period_targets['taktikai']}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Technikai fókusz: {period_targets['technikai']}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Kondicionális fókusz: {period_targets['kondi']}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Intenzitási szorzó: {period_targets['szorzo']}"))

    pdf.ln(4)
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
