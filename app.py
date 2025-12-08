############################################################
#  app.py — Training Blueprint Edzéstervező (MAGYAR UI)
############################################################

import os
import json
import random
from io import BytesIO
from typing import Dict, Any, List, Optional, Set

import streamlit as st
from fpdf import FPDF
import matplotlib.pyplot as plt

from pitch_drawer import draw_drill


############################################################
# 1. KONSTANSOK, JSON BETÖLTÉSE
############################################################

JSON_PATH = "drill_metadata_with_u7u9.json"
DRILL_IMAGE_FOLDER = "."       # PNG fájlok mappa
LOGO_PATH = "TBP_pdfsafe.png"  # Training Blueprint logó
MATCH_IMAGE = "match_game.png" # Minden korosztály mérkőzésjátéka
BACKGROUND = "pitch_background.png"

DEJAVU_REG = "DejaVuSans.ttf"
DEJAVU_BOLD = "DejaVuSans-Bold.ttf"


@st.cache_data
def load_db() -> List[Dict[str, Any]]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    # --- Taktikai duplikátumok tisztítása ---
    fix_map = {
        "jatek_szervezes": "jatekszervezes",
        "jatekszervezes": "jatekszervezes",
        "jatekszervezés": "jatekszervezes",
        "játékszervezés": "jatekszervezes",
        "jatekszervezet": "jatekszervezes",
    }

    for ex in db:
        main = ex.get("fo_taktikai_cel", "")
        ex["fo_taktikai_cel"] = fix_map.get(main, main)

        fixed_tags = []
        for t in ex.get("taktikai_cel_cimkek", []):
            fixed_tags.append(fix_map.get(t, t))
        ex["taktikai_cel_cimkek"] = fixed_tags

    return db


EX_DB = load_db()


############################################################
# 2. Egyszerű kategórialisták
############################################################

TAKTIKAI_CELOK = sorted(set([ex["fo_taktikai_cel"] for ex in EX_DB]))

TECHNIKAI_SIMPLE = [
    "passz",
    "átvétel",
    "labdavezetés",
    "lövések",
    "fejelés"
]

KONDIC_SIMPLE = [
    "gyorsaság",
    "állóképesség",
    "erő",
    "agilitás"
]


############################################################
# 3. PERIODIZÁCIÓ – Egyszerű rendszer
############################################################

def get_default_targets(age_group: str, week: int) -> Dict[str, Any]:

    base = {
        1: "jatekszervezes",
        2: "labdakihozatal",
        3: "befejezes",
        4: "atmenet"
    }
    return {
        "fo_taktikai": base.get(week, "jatekszervezes"),
        "taktikai": [base.get(week, "jatekszervezes")],
        "technikai": ["passz"],
        "kondicionalis": ["állóképesség"]
    }


############################################################
# 4. GYAKORLAT PONTOZÁSA (egyszerű)
############################################################

def score_exercise(ex, stage, desired_fo, tact, tech, kond, age_group):
    score = 0

    if ex.get("fo_taktikai_cel") == desired_fo:
        score += 5

    for t in tact:
        if t in ex.get("taktikai_cel_cimkek", []):
            score += 2

    return score


############################################################
# 5. GYAKORLAT KIVÁLASZTÁSA
############################################################

def pick_exercise(stage, desired_fo, tact, tech, kond, used_ids, age_group):

    candidates = []
    for ex in EX_DB:
        if ex.get("edzes_resze") != stage:
            continue

        # korosztály szűrés
        if age_group not in ex.get("ajanlott_korosztalyok", []):
            continue

        # duplikáció tiltása
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
# 6. PDF-SAFE
############################################################

def pdf_safe(text):
    if not text:
        return ""
    return str(text).replace("…", "...").replace("’", "'")


############################################################
# 7. STREAMLIT FELÜLET
############################################################

st.set_page_config(page_title="Training Blueprint", layout="wide")
st.title("⚽ Training Blueprint – Edzéstervező")


############################################################
# Oldalsáv — beállítások
############################################################

st.sidebar.header("Edzés paraméterei")

age_group = st.sidebar.selectbox(
    "Korosztály",
    ["U7-U9", "U10-U12", "U13-U15", "U16-U19", "felnott"]
)

week = st.sidebar.number_input("Periodizációs hét", 1, 4, 1)

defaults = get_default_targets(age_group, week)

fo_taktikai = st.sidebar.selectbox(
    "Fő taktikai cél",
    options=TAKTIKAI_CELOK,
    index=TAKTIKAI_CELOK.index(defaults["fo_taktikai"])
)

taktikai_valasztott = st.sidebar.multiselect(
    "Taktikai címkék",
    options=TAKTIKAI_CELOK,
    default=defaults["taktikai"]
)

technikai_valasztott = st.sidebar.multiselect(
    "Technikai fókusz",
    options=TECHNIKAI_SIMPLE,
    default=["passz"]
)

kond_valasztott = st.sidebar.multiselect(
    "Kondicionális fókusz",
    options=KONDIC_SIMPLE,
    default=["állóképesség"]
)


############################################################
# Edzői össz-megjegyzés
############################################################

coach_notes = st.text_area("🧠 Edzői össz-megjegyzés az edzéshez")


############################################################
# Edzés generálása
############################################################

if "plan" not in st.session_state:
    st.session_state.plan = []
if "used_ids" not in st.session_state:
    st.session_state.used_ids = set()
if "match_override" not in st.session_state:
    st.session_state.match_override = False


def generate_plan():
    plan = []
    used = set()

    stages = ["bemelegites", "cel1", "cel2", "cel3"]

    for stg in stages:
        ex = pick_exercise(
            stg,
            fo_taktikai,
            taktikai_valasztott,
            technikai_valasztott,
            kond_valasztott,
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


if st.button("🚀 Edzés generálása"):
    generate_plan()


############################################################
# Gyakorlatok megjelenítése
############################################################

def stage_label(s):
    return {
        "bemelegites": "Bemelegítés",
        "cel1": "Cél 1",
        "cel2": "Cél 2",
        "cel3": "Cél 3"
    }.get(s, s)


st.header("📋 Generált edzés")

for i, block in enumerate(st.session_state.plan):
    stage = block["stage"]
    ex = block["exercise"]

    st.subheader(stage_label(stage))

    cols = st.columns([1, 2])

    with cols[0]:
        # --- Mérkőzésjáték felülírás cél3-ban ---
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

    with cols[1]:
        ex["description"] = st.text_area(
            "Leírás", ex.get("description", ""), key=f"desc_{i}"
        )
        ex["organisation"] = st.text_area(
            "Szervezés", ex.get("organisation", ""), key=f"org_{i}"
        )
        ex["coaching_points"] = st.text_area(
            "Coaching pontok", ex.get("coaching_points", ""), key=f"coach_{i}"
        )
        # --- Gyakorlat cseréje gomb ---
        if st.button(f"🔄 Gyakorlat cseréje ({stage_label(stage)})", key=f"replace_{i}"):

            # Cél3-ban ha mérkőzésjáték be van kapcsolva → nincs csere
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
                    st.rerun()
                else:
                    st.error("Ehhez az edzésrészhez nincs több releváns gyakorlat.")


############################################################
# PDF Export – Automatikus háttér minden oldalon
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

    # betűtípus
    base = "Arial"
    try:
        pdf.add_font("DejaVu", "", DEJAVU_REG, uni=True)
        pdf.add_font("DejaVu", "B", DEJAVU_BOLD, uni=True)
        base = "DejaVu"
    except:
        pass

    # --- Címlap ---
    pdf.add_page()
    pdf.set_font(base, "B", 16)
    pdf.cell(0, 10, pdf_safe("Training Blueprint – Edzésterv"), ln=1)

    pdf.set_font(base, "", 12)
    pdf.multi_cell(0, 6, pdf_safe(f"Korosztály: {age_group}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Periodizációs hét: {week}"))
    pdf.multi_cell(0, 6, pdf_safe(f"Fő taktikai cél: {fo_taktikai}"))

    pdf.ln(4)
    pdf.set_font(base, "B", 12)
    pdf.cell(0, 8, "Edzői megjegyzés:", ln=1)
    pdf.set_font(base, "", 12)
    pdf.multi_cell(0, 6, pdf_safe(coach_notes))

    # --- Gyakorlatok ---
    for block in st.session_state.plan:
        pdf.add_page()

        stage = block["stage"]
        ex = block["exercise"]

        pdf.set_font(base, "B", 14)
        pdf.cell(0, 10, pdf_safe(stage_label(stage)), ln=1)

        pdf.ln(3)

        # kép
        if stage == "cel3" and st.session_state.match_override:
            img = MATCH_IMAGE
        else:
            img = ex["file_name"]

        if img and os.path.exists(img):
            try:
                pdf.image(img, w=150)
            except:
                pdf.multi_cell(0, 6, "Kép nem tölthető be.")

        pdf.ln(5)

        # Leírás
        pdf.set_font(base, "B", 12)
        pdf.cell(0, 6, "Leírás:", ln=1)
        pdf.set_font(base, "", 12)
        pdf.multi_cell(0, 6, pdf_safe(ex.get("description", "")))
        pdf.ln(2)

        # Szervezés
        pdf.set_font(base, "B", 12)
        pdf.cell(0, 6, "Szervezés:", ln=1)
        pdf.set_font(base, "", 12)
        pdf.multi_cell(0, 6, pdf_safe(ex.get("organisation", "")))
        pdf.ln(2)

        # Coaching pontok
        pdf.set_font(base, "B", 12)
        pdf.cell(0, 6, "Coaching pontok:", ln=1)
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
