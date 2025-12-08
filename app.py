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
DRILL_IMAGE_FOLDER = "."            # PNG fájlok mappa
LOGO_PATH = "TBP_pdfsafe.png"       # logó
BACKGROUND_PATH = "pitch_background.png"  # háttérkép (8%-os)
DEJAVU_REG = "DejaVuSans.ttf"
DEJAVU_BOLD = "DejaVuSans-Bold.ttf"

@st.cache_data
def load_db() -> List[Dict[str, Any]]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- Egységesítés: jatekszervezes / jatek_szervezes → jatekszervezes ---
    for ex in data:
        if ex.get("fo_taktikai_cel", "").lower().replace("_", "") == "jatekszervezes":
            ex["fo_taktikai_cel"] = "jatekszervezes"

        fixed = []
        for c in ex.get("taktikai_cel_cimkek", []):
            if c.lower().replace("_", "") == "jatekszervezes":
                fixed.append("jatekszervezes")
            else:
                fixed.append(c)
        ex["taktikai_cel_cimkek"] = fixed

    return data

EX_DB = load_db()


############################################################
# 2. SEGÉD: DUPLIKÁCIÓK ELTÁVOLÍTÁSA
############################################################

def unique_normalized(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for v in values:
        if not v:
            continue
        key = str(v).strip().lower()
        if key not in seen:
            seen.add(key)
            out.append(str(v).strip())
    return out


############################################################
# 3. SZŰRŐLISTÁK A JSON-BŐL (TAKTIKAI)
############################################################

FO_TAKTIKAI_CELOK = sorted(
    unique_normalized([ex.get("fo_taktikai_cel", "") for ex in EX_DB])
)

TAKTIKAI_CIMKEK = sorted(
    unique_normalized([c for ex in EX_DB for c in ex.get("taktikai_cel_cimkek", [])])
)


############################################################
# 4. ÚJ FIX TECHNIKAI KATEGÓRIÁK
############################################################

TECHNIKAI_FIX = [
    "Passzjáték",
    "Labdavezetés",
    "Lövés / Befejezés",
    "Átvétel",
    "Csel / 1v1",
    "Fejelés",
    "Átvétel–továbbítás",
]

# Gyakorlat eredeti technikai címkéit erre projektáljuk rá
def map_tech_label(ex: Dict[str, Any]) -> List[str]:
    """
    Eredeti JSON technikai címkéinek szövegéből becsüljük meg,
    melyik FIX technikai kategóriába tartozik.
    """
    src = " ".join(ex.get("technikai_cel_cimkek", [])).lower()

    out = []

    if any(k in src for k in ["passz", "passzol"]):
        out.append("Passzjáték")

    if any(k in src for k in ["vezetes", "labdavezet"]):
        out.append("Labdavezetés")

    if any(k in src for k in ["löv", "bevez", "befeje"]):
        out.append("Lövés / Befejezés")

    if any(k in src for k in ["atvet", "átvét"]):
        out.append("Átvétel")

    if any(k in src for k in ["csel", "1v1"]):
        out.append("Csel / 1v1")

    if any(k in src for k in ["fej", "fejel"]):
        out.append("Fejelés")

    if any(k in src for k in ["továbbítás", "tovabbit"]):
        out.append("Átvétel–továbbítás")

    return out or ["Passzjáték"]   # default fallback


############################################################
# 5. ÚJ FIX KONDICIONÁLIS KATEGÓRIÁK
############################################################

KONDICIONALIS_FIX = [
    "Gyorsaság",
    "Irányváltás",
    "Állóképesség",
    "Koordináció",
    "Robbanékonyság",
]
############################################################
# 6. PERIODIZÁCIÓ → ALAP CÉLOK
############################################################

def get_default_targets(age_group: str, week: int) -> Dict[str, Any]:

    # U7–U12 egyszerűsített modell
    if age_group in ["U7-U9", "U10-U12"]:
        if week == 1:
            return {
                "fo_taktikai": "jatekszervezes",
                "taktikai": ["jatekszervezes"],
                "technikai": ["Passzjáték"],
                "kondicionalis": ["Koordináció"],
            }
        if week == 2:
            return {
                "fo_taktikai": "labdakihozatal",
                "taktikai": ["labdakihozatal"],
                "technikai": ["Passzjáték"],
                "kondicionalis": ["Irányváltás"],
            }
        if week == 3:
            return {
                "fo_taktikai": "befejezes",
                "taktikai": ["befejezes"],
                "technikai": ["Lövés / Befejezés"],
                "kondicionalis": ["Gyorsaság"],
            }
        return {
            "fo_taktikai": "jatekszervezes",
            "taktikai": ["jatekszervezes"],
            "technikai": ["Passzjáték"],
            "kondicionalis": ["Állóképesség"],
        }

    # U13+ modell
    if week == 1:
        return {
            "fo_taktikai": "labdakihozatal",
            "taktikai": ["labdakihozatal"],
            "technikai": ["Passzjáték"],
            "kondicionalis": ["Koordináció"],
        }
    if week == 2:
        return {
            "fo_taktikai": "jatekszervezes",
            "taktikai": ["jatekszervezes"],
            "technikai": ["Passzjáték"],
            "kondicionalis": ["Állóképesség"],
        }
    if week == 3:
        return {
            "fo_taktikai": "befejezes",
            "taktikai": ["befejezes"],
            "technikai": ["Lövés / Befejezés"],
            "kondicionalis": ["Robbanékonyság"],
        }
    return {
        "fo_taktikai": "atmenet",
        "taktikai": ["atmenet_tamadasba"],
        "technikai": ["Passzjáték"],
        "kondicionalis": ["Koordináció"],
    }


############################################################
# 7. PONTOZÁS — frissítve az új FIX technikai és kondicionális rendszerhez
############################################################

def score_exercise(
    ex: Dict[str, Any],
    stage: str,
    desired_fo: str,
    desired_taktikai: List[str],
    desired_tech: List[str],
    desired_kond: List[str],
    age_group: str,
) -> int:

    score = 0

    # Fő taktikai
    if ex.get("fo_taktikai_cel") == desired_fo:
        score += 5

    # Taktikai címkék
    ex_takt = ex.get("taktikai_cel_cimkek", [])
    for t in desired_taktikai:
        if t in ex_takt:
            score += 2

    # FIX technikai kategóriák
    ex_fixed_tech = map_tech_label(ex)
    for t in desired_tech:
        if t in ex_fixed_tech:
            score += 1

    # Kondicionális FIX
    ex_fixed_kond = []
    kc = " ".join(ex.get("kondicionalis_cel_cimkek", [])).lower()
    if "gyors" in kc:
        ex_fixed_kond.append("Gyorsaság")
    if "irany" in kc:
        ex_fixed_kond.append("Irányváltás")
    if "allo" in kc:
        ex_fixed_kond.append("Állóképesség")
    if "koordin" in kc:
        ex_fixed_kond.append("Koordináció")
    if "robb" in kc:
        ex_fixed_kond.append("Robbanékonyság")

    for c in desired_kond:
        if c in ex_fixed_kond:
            score += 1

    # Stage preferenciák
    kat = ex.get("gyakorlat_kategoria", "")

    if stage == "bemelegites":
        if kat in ["rondo", "technikazas"]:
            score += 4
        if kat == "kisjatek":
            score += 1

    if stage == "cel1":
        if kat in ["kisjatek", "rondo"]:
            score += 4
        if kat == "jatekszituacio":
            score += 1

    if stage == "cel2":
        if kat in ["jatekszituacio"]:
            score += 4
        if kat == "kisjatek":
            score += 1

    if stage == "cel3":
        if kat in ["jatekszituacio", "merkozesjatek"]:
            score += 5

    # Kiskorosztály tiltások
    if age_group in ["U7-U9", "U10-U12"] and stage in ["cel2", "cel3"]:
        if kat == "merkozesjatek":
            score -= 999

    return score


############################################################
# 8. GYAKORLAT KIVÁLASZTÁSA (MÉRKŐZÉSJÁTÉK OPCIÓVAL)
############################################################

MATCH_IMAGES = {
    "U7-U9": "match_small.png",
    "U10-U12": "match_small.png",
    "U13-U15": "match_7v7.png",
    "U16-U19": "match_11v11.png",
    "felnott": "match_11v11.png",
}

def pick_exercise(
    stage: str,
    desired_fo: str,
    takt: List[str],
    tech: List[str],
    kond: List[str],
    used_ids: Set[str],
    age_group: str,
    force_match=False,
) -> Optional[Dict[str, Any]]:

    # --- ha mérkőzésjáték be van pipálva Cél3-ban ---
    if stage == "cel3" and force_match:
        return {
            "file_name": MATCH_IMAGES.get(age_group, "match_11v11.png"),
            "gyakorlat_kategoria": "merkozesjatek",
            "diagram_v1": None,
            "organisation": "",
            "description": "",
            "coaching_points": "",
            "edzes_resze": "cel3",
        }

    # Normál gyakorlatok
    scored = []
    for ex in EX_DB:
        if ex.get("edzes_resze") != stage:
            continue

        # korosztály
        if age_group not in ex.get("ajanlott_korosztalyok", []):
            continue

        # duplikáció tiltása
        if ex.get("file_name") in used_ids:
            continue

        s = score_exercise(ex, stage, desired_fo, takt, tech, kond, age_group)
        scored.append((s, ex))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0]
    best = [ex for s, ex in scored if s == best_score]

    return random.choice(best)
############################################################
# 9. STREAMLIT UI
############################################################

st.set_page_config(page_title="Training Blueprint – Edzéstervező", layout="wide")
st.title("⚽ Edzéstervező – Training Blueprint")

############################################################
# OLDALSÁV – KOROSZTÁLY, HÉT, CÉLOK
############################################################

st.sidebar.header("Edzés paraméterei")

korosztaly = st.sidebar.selectbox(
    "Korosztály",
    ["U7-U9", "U10-U12", "U13-U15", "U16-U19", "felnott"],
)

period_week = st.sidebar.number_input("Periódizációs hét", 1, 4, 1)

defaults = get_default_targets(korosztaly, period_week)

############################################################
# CÉLOK – Taktikai / Technikai / Kondicionális
############################################################

st.sidebar.subheader("Edzés céljai")

# Fő taktikai
fo_index = (
    1 + FO_TAKTIKAI_CELOK.index(defaults["fo_taktikai"])
    if defaults["fo_taktikai"] in FO_TAKTIKAI_CELOK else 0
)

fo_taktikai = st.sidebar.selectbox(
    "Fő taktikai cél",
    [""] + FO_TAKTIKAI_CELOK,
    index=fo_index,
)

# Taktikai címkék
taktikai_valasztott = st.sidebar.multiselect(
    "Taktikai címkék",
    TAKTIKAI_CIMKEK,
    default=[t for t in defaults["taktikai"] if t in TAKTIKAI_CIMKEK],
)

# Technikai – FIX kategóriák
technikai_valasztott = st.sidebar.multiselect(
    "Technikai kategóriák",
    TECHNIKAI_FIX,
    default=[t for t in defaults["technikai"] if t in TECHNIKAI_FIX],
)

# Kondicionális – FIX kategóriák
kond_valasztott = st.sidebar.multiselect(
    "Kondicionális célok",
    KONDICIONALIS_FIX,
    default=[t for t in defaults["kondicionalis"] if t in KONDICIONALIS_FIX],
)

############################################################
# EDZÉS GENERÁLÁSA + EDZŐI MEGJEGYZÉS
############################################################

st.header("🧩 Edzés generálása")

if "coach_notes" not in st.session_state:
    st.session_state.coach_notes = ""

st.session_state.coach_notes = st.text_area(
    "🧠 Általános edzői megjegyzés az egész edzéshez",
    value=st.session_state.coach_notes,
)

if "plan" not in st.session_state:
    st.session_state.plan = []
if "used_ids" not in st.session_state:
    st.session_state.used_ids = set()

# --- Mérkőzésjáték opció Cél3-hoz ---
force_match = st.checkbox("Cél 3: Mérkőzésjáték (automatikus meccskép)")

def generate_full_training():
    plan = []
    used = set()

    for stage in ["bemelegites", "cel1", "cel2", "cel3"]:
        ex = pick_exercise(
            stage,
            fo_taktikai,
            taktikai_valasztott,
            technikai_valasztott,
            kond_valasztott,
            used,
            korosztaly,
            force_match = (stage == "cel3" and force_match)
        )
        if ex:
            fid = ex.get("file_name")
            if fid:
                used.add(fid)
            ex.setdefault("organisation", "")
            ex.setdefault("description", "")
            ex.setdefault("coaching_points", "")
            plan.append({"stage": stage, "exercise": ex})

    st.session_state.plan = plan
    st.session_state.used_ids = used


if st.button("🚀 Edzés generálása"):
    generate_full_training()


############################################################
# GYAKORLAT BLOKKOK MEGJELENÍTÉSE
############################################################

st.header("📋 Generált edzés")

def stage_label(stage):
    return {
        "bemelegites": "Bemelegítés",
        "cel1": "Cél 1",
        "cel2": "Cél 2",
        "cel3": "Cél 3",
    }.get(stage, stage)

def show_exercise_block(i, block):
    stage = block["stage"]
    ex = block["exercise"]

    st.subheader(stage_label(stage))
    cols = st.columns([1, 2])

    # ---- BAL oldali kép ----
    with cols[0]:
        fname = ex.get("file_name")
        if fname:
            path = os.path.join(DRILL_IMAGE_FOLDER, fname)
            if os.path.exists(path):
                st.image(path, width=300)
            else:
                st.warning("Kép nem található.")

    # ---- JOBB oldali szerkeszthető mezők ----
    with cols[1]:
        ex["description"] = st.text_area("Leírás", ex.get("description", ""), key=f"desc_{i}")
        ex["organisation"] = st.text_area("Szervezés", ex.get("organisation", ""), key=f"org_{i}")
        ex["coaching_points"] = st.text_area("Coaching pontok", ex.get("coaching_points", ""), key=f"cp_{i}")

        if st.button(f"🔄 Gyakorlat cseréje ({stage_label(stage)})", key=f"rep_{i}"):
            new_ex = pick_exercise(
                stage,
                fo_taktikai,
                taktikai_valasztott,
                technikai_valasztott,
                kond_valasztott,
                st.session_state.used_ids,
                korosztaly,
                force_match = (stage == "cel3" and force_match)
            )
            if new_ex:
                fid = new_ex.get("file_name")
                if fid:
                    st.session_state.used_ids.add(fid)
                new_ex.setdefault("organisation", "")
                new_ex.setdefault("description", "")
                new_ex.setdefault("coaching_points", "")
                st.session_state.plan[i]["exercise"] = new_ex
                st.rerun()
            else:
                st.error("Nincs több ilyen szűrésnek megfelelő gyakorlat.")

for i, block in enumerate(st.session_state.plan):
    show_exercise_block(i, block)


############################################################
# 10. PDF EXPORT (háttér minden oldalon)
############################################################

st.header("📄 PDF Export")

class TBPDF(FPDF):
    def header(self):
        try:
            self.image(BACKGROUND_PATH, x=0, y=0, w=210, h=297)
        except:
            pass
        try:
            self.image(LOGO_PATH, x=165, y=10, w=28)
        except:
            pass
        self.set_y(28)

def create_training_pdf():
    pdf = TBPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # fonts
    base = "Arial"
    try:
        if os.path.exists(DEJAVU_REG):
            pdf.add_font("DejaVu", "", DEJAVU_REG, uni=True)
            pdf.add_font("DejaVu", "B", DEJAVU_BOLD, uni=True)
            base = "DejaVu"
    except:
        pass

    pdf.add_page()
    pdf.set_font(base, "B", 16)
    pdf.cell(0, 10, "Training Blueprint – Edzésterv", ln=1)

    pdf.set_font(base, "", 12)
    pdf.multi_cell(0, 6, f"Korosztály: {korosztaly}")
    pdf.multi_cell(0, 6, f"Periódizációs hét: {period_week}")
    pdf.multi_cell(0, 6, f"Fő taktikai cél: {fo_taktikai or '-'}")

    pdf.ln(3)
    pdf.set_font(base, "B", 12)
    pdf.cell(0, 7, "Általános edzői megjegyzés:", ln=1)
    pdf.set_font(base, "", 12)
    pdf.multi_cell(0, 6, st.session_state.coach_notes or "-")

    # --- drills ---
    for block in st.session_state.plan:
        stage = block["stage"]
        ex = block["exercise"]

        pdf.add_page()
        pdf.set_font(base, "B", 14)
        pdf.cell(0, 8, stage_label(stage), ln=1)

        fname = ex.get("file_name")
        if fname:
            p = os.path.join(DRILL_IMAGE_FOLDER, fname)
            if os.path.exists(p):
                pdf.image(p, w=150)
                pdf.ln(5)

        def section(title, text):
            pdf.set_font(base, "B", 12)
            pdf.cell(0, 6, title, ln=1)
            pdf.set_font(base, "", 12)
            pdf.multi_cell(0, 6, text or "-")
            pdf.ln(2)

        section("Leírás:", ex.get("description", ""))
        section("Szervezés:", ex.get("organisation", ""))
        section("Coaching pontok:", ex.get("coaching_points", ""))

    out = pdf.output(dest="S")
    return out if isinstance(out, bytes) else out.encode("latin-1", "ignore")

if st.session_state.plan:
    pdf_bytes = create_training_pdf()
    st.download_button(
        "📄 PDF letöltése",
        data=pdf_bytes,
        file_name="edzesterv.pdf",
        mime="application/pdf",
    )
else:
    st.info("Előbb generálj edzést.")
