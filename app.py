############################################################
#  app.py — Training Blueprint Edzéstervező (MAGYAR UI)
#  TELJES VERZIÓ — RÉSZ 1/3
############################################################

import os
import json
import random
from io import BytesIO
from typing import Dict, Any, List, Optional, Set

import streamlit as st
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt

from pitch_drawer import draw_drill


############################################################
# 1. JSON BETÖLTÉSE
############################################################

JSON_PATH = "drill_metadata_with_u7u9.json"
DRILL_IMAGE_FOLDER = "."  # PNG fájlok ugyanabban a mappában vannak, ahol az app.py


@st.cache_data
def load_db() -> List[Dict[str, Any]]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


EX_DB = load_db()


############################################################
# 2. SZŰRŐLISTÁK A JSON-BŐL
############################################################

FO_TAKTIKAI_CELOK = sorted({ex["fo_taktikai_cel"] for ex in EX_DB})

# az összes taktikai címke egy listába összegyűjtve
TAKTIKAI_CIMKEK = sorted({
    cimke
    for ex in EX_DB
    for cimke in ex.get("taktikai_cel_cimkek", [])
})

TECHNIKAI_CIMKEK = sorted({
    cimke
    for ex in EX_DB
    for cimke in ex.get("technikai_cel_cimkek", [])
})

KONDICIONALIS_CIMKEK = sorted({
    cimke
    for ex in EX_DB
    for cimke in ex.get("kondicionalis_cel_cimkek", [])
})

KATEGORIÁK = sorted({ex["gyakorlat_kategoria"] for ex in EX_DB})


############################################################
# 3. PERIODIZÁCIÓ → ALAP CÉLOK
############################################################

def get_default_targets(age_group: str, week: int) -> Dict[str, Any]:
    """
    Periodizáció alapján előre beállított fókuszok.
    (Egyszerűsített mapping; igény szerint később bővíthető.)
    """

    if age_group.startswith("U7") or age_group.startswith("U10"):
        if week == 1:
            return {
                "fo_taktikai": "jatekszervezes",
                "taktikai": ["jatekszervezes"],
                "technikai": ["passz"],
                "kondicionalis": ["koordinacio"]
            }
        if week == 2:
            return {
                "fo_taktikai": "labdakihozatal",
                "taktikai": ["labdakihozatal"],
                "technikai": ["passz", "mozgás labdára"],
                "kondicionalis": ["gyors iranyvaltas"]
            }
        if week == 3:
            return {
                "fo_taktikai": "befejezes",
                "taktikai": ["befejezes"],
                "technikai": ["lövéstechnika"],
                "kondicionalis": ["gyorsasag"]
            }
        return {
            "fo_taktikai": "jatekszervezes",
            "taktikai": ["jatekszervezes"],
            "technikai": ["passz"],
            "kondicionalis": ["könnyű allokepesseg"]
        }

    # U13–U19 és felnőtt — alap séma:
    if week == 1:
        return {
            "fo_taktikai": "labdakihozatal",
            "taktikai": ["labdakihozatal", "jatekszervezes"],
            "technikai": ["passz", "mozgás passz után"],
            "kondicionalis": ["koordinacio"]
        }
    if week == 2:
        return {
            "fo_taktikai": "jatekszervezes",
            "taktikai": ["jatekszervezes"],
            "technikai": ["passzjatek"],
            "kondicionalis": ["allokepesseg"]
        }
    if week == 3:
        return {
            "fo_taktikai": "befejezes",
            "taktikai": ["befejezes"],
            "technikai": ["lövéstechnika"],
            "kondicionalis": ["robbanekonysag"]
        }
    return {
        "fo_taktikai": "atmenet",
        "taktikai": ["atmenet_tamadasba"],
        "technikai": ["passz"],
        "kondicionalis": ["koordinacio"]
    }


############################################################
# 4. STAGE + KATEGÓRIA ALAPÚ PONTOZÁS
############################################################

def score_exercise(ex: Dict[str, Any],
                   stage: str,
                   desired_fo: str,
                   desired_taktikai: List[str],
                   desired_technikai: List[str],
                   desired_kond: List[str]) -> int:
    score = 0

    # FŐ taktikai egyezés
    if ex.get("fo_taktikai_cel") == desired_fo:
        score += 5

    # Taktikai címkék
    ex_takt = ex.get("taktikai_cel_cimkek", [])
    for t in desired_taktikai:
        if t in ex_takt:
            score += 2

    # Technikai címkék
    ex_tech = ex.get("technikai_cel_cimkek", [])
    for t in desired_technikai:
        if t in ex_tech:
            score += 1

    # Kondicionális címkék
    ex_k = ex.get("kondicionalis_cel_cimkek", [])
    for c in desired_kond:
        if c in ex_k:
            score += 1

    # Kategória preferencia stage szerint
    kat = ex.get("gyakorlat_kategoria", "")

    if stage == "bemelegites":
        if kat in ["rondo", "technikazas"]:
            score += 4
        elif kat == "kisjatek":
            score += 1
        elif kat in ["merkozesjatek", "jatekszituacio"]:
            score -= 3

    elif stage == "cel1":
        if kat in ["kisjatek", "rondo"]:
            score += 4
        elif kat in ["jatekszituacio"]:
            score += 1
        elif kat in ["merkozesjatek"]:
            score -= 3

    elif stage == "cel2":
        if kat in ["jatekszituacio", "mezonyjatekszituacio"]:
            score += 4
        elif kat in ["kisjatek"]:
            score += 1
        elif kat in ["rondo", "technikazas"]:
            score -= 3

    elif stage == "cel3":
        if kat in ["merkozesjatek", "jatekszituacio"]:
            score += 5
        elif kat in ["mezonyjatekszituacio"]:
            score += 3
        elif kat in ["rondo", "kisjatek", "technikazas"]:
            score -= 4

    return score


############################################################
# 5. GYAKORLAT KIVÁLASZTÁSA
############################################################

def pick_exercise(stage: str,
                  desired_fo: str,
                  desired_taktikai: List[str],
                  desired_technikai: List[str],
                  desired_kond: List[str],
                  used_ids: Set[str]) -> Optional[Dict[str, Any]]:
    scored = []
    for ex in EX_DB:
        if ex.get("edzes_resze") != stage:
            continue
        if ex["file_name"] in used_ids:
            continue

        s = score_exercise(
            ex,
            stage,
            desired_fo,
            desired_taktikai,
            desired_technikai,
            desired_kond
        )
        scored.append((s, ex))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0]
    best = [ex for s, ex in scored if s == best_score]
    chosen = random.choice(best)

    return chosen


############################################################
# 6. KÉP + DIAGRAM A PDF-BE
############################################################

def render_diagram_to_png(diagram_spec: Dict[str, Any]) -> BytesIO:
    fig = draw_drill(diagram_spec, show=False)
    fig.set_size_inches(5, 3)
    bio = BytesIO()
    fig.savefig(bio, format="png", dpi=120, bbox_inches="tight")
    bio.seek(0)
    plt.close(fig)
    return bio


############################################################
# 7. PDF GENERÁLÁS
############################################################

class TrainingPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 8, "Edzésterv – Training Blueprint", ln=1)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "", 9)
        self.cell(0, 10, "Generálva a Training Blueprint alkalmazással", 0, 0, "C")


def create_pdf(plan: List[Dict[str, Any]]) -> BytesIO:
    pdf = TrainingPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for block in plan:
        ex = block["exercise"]
        pdf.add_page()

        # ---- KÉP / DIAGRAM FELÜL ----
        img_buffer = None

        if "diagram_v1" in ex and ex["diagram_v1"]:
            img_buffer = render_diagram_to_png(ex["diagram_v1"])
        else:
            fname = ex.get("file_name")
            if fname:
                path = os.path.join(DRILL_IMAGE_FOLDER, fname)
                if os.path.exists(path):
                    img_buffer = path

        if img_buffer:
            if isinstance(img_buffer, BytesIO):
                pdf.image(img_buffer, x=10, w=180)
            else:
                pdf.image(img_buffer, x=10, w=180)

        # ---- SZÖVEGEK ----
        pdf.set_font("Arial", "B", 12)
        pdf.ln(5)
        pdf.cell(0, 7, ex.get("title", "Gyakorlat"), ln=1)

        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, f"Szervezés:\n{ex.get('organisation', '-')}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, f"Leírás:\n{ex.get('description', '-')}")
        pdf.ln(1)

    bio = BytesIO()
    pdf.output(bio)
    bio.seek(0)
    return bio


############################################################
# ----------- RÉSZ 1/3 VÉGE --------------------------------
############################################################
############################################################
#  app.py — Training Blueprint Edzéstervező (MAGYAR UI)
#  TELJES VERZIÓ — RÉSZ 2/3
############################################################

st.set_page_config(page_title="Training Blueprint – Edzéstervező", layout="wide")

st.title("⚽ Edzéstervező – Training Blueprint")

############################################################
# OLDALSÁV – KOROSZTÁLY, HÉT, PERIODIZÁCIÓ
############################################################

st.sidebar.header("Edzés paraméterei")

korosztaly = st.sidebar.selectbox(
    "Korosztály",
    ["U7-U9", "U10-U12", "U13-U15", "U16-U19", "felnott"],
)

period_week = st.sidebar.number_input(
    "Periodizációs hét",
    min_value=1,
    max_value=4,
    value=1
)

# Periodizáció alapján automatikus célok
defaults = get_default_targets(korosztaly, period_week)

############################################################
# TAKTIKAI / TECHNIKAI / ERŐNLÉTI CÉLOK – JSON-BŐL
############################################################

st.sidebar.subheader("Edzés céljai")

# Fő taktikai cél
fo_taktikai = st.sidebar.selectbox(
    "Fő taktikai cél",
    [""] + FO_TAKTIKAI_CELOK,
    index=(1 + FO_TAKTIKAI_CELOK.index(defaults["fo_taktikai"])
           if defaults["fo_taktikai"] in FO_TAKTIKAI_CELOK else 0)
)

# Taktikai címkék (több választható)
taktikai_valasztott = st.sidebar.multiselect(
    "Taktikai címkék",
    TAKTIKAI_CIMKEK,
    default=[t for t in defaults["taktikai"] if t in TAKTIKAI_CIMKEK]
)

# Technikai címkék
technikai_valasztott = st.sidebar.multiselect(
    "Technikai címkék",
    TECHNIKAI_CIMKEK,
    default=[t for t in defaults["technikai"] if t in TECHNIKAI_CIMKEK]
)

# Erőnléti címkék
kond_valasztott = st.sidebar.multiselect(
    "Kondicionális címkék",
    KONDICIONALIS_CIMKEK,
    default=[t for t in defaults["kondicionalis"] if t in KONDICIONALIS_CIMKEK]
)

############################################################
# EDZÉS GENERÁLÁSA
############################################################

st.header("🧩 Edzés generálása")

if "plan" not in st.session_state:
    st.session_state.plan = []
if "used_ids" not in st.session_state:
    st.session_state.used_ids = set()

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
            used
        )
        if ex:
            used.add(ex["file_name"])
            plan.append({"stage": stage, "exercise": ex})

    st.session_state.plan = plan
    st.session_state.used_ids = used


if st.button("🚀 Edzés generálása"):
    generate_full_training()


############################################################
# GYAKORLAT BLOKK MEGJELENÍTÉSE (KÉP + SZERKESZTHETŐ SZÖVEG)
############################################################

st.header("📋 Generált edzés")

############################################################
#  app.py — Training Blueprint Edzéstervező (MAGYAR UI)
#  TELJES VERZIÓ — RÉSZ 1/3
############################################################

import os
import json
import random
from io import BytesIO
from typing import Dict, Any, List, Optional, Set

import streamlit as st
import pandas as pd
from fpdf import FPDF
import matplotlib.pyplot as plt

from pitch_drawer import draw_drill


############################################################
# 1. JSON BETÖLTÉSE
############################################################

JSON_PATH = "drill_metadata_with_u7u9.json"
DRILL_IMAGE_FOLDER = "."  # PNG fájlok ugyanabban a mappában vannak, ahol az app.py


@st.cache_data
def load_db() -> List[Dict[str, Any]]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


EX_DB = load_db()


############################################################
# 2. SZŰRŐLISTÁK A JSON-BŐL
############################################################

FO_TAKTIKAI_CELOK = sorted({ex["fo_taktikai_cel"] for ex in EX_DB})

# az összes taktikai címke egy listába összegyűjtve
TAKTIKAI_CIMKEK = sorted({
    cimke
    for ex in EX_DB
    for cimke in ex.get("taktikai_cel_cimkek", [])
})

TECHNIKAI_CIMKEK = sorted({
    cimke
    for ex in EX_DB
    for cimke in ex.get("technikai_cel_cimkek", [])
})

KONDICIONALIS_CIMKEK = sorted({
    cimke
    for ex in EX_DB
    for cimke in ex.get("kondicionalis_cel_cimkek", [])
})

KATEGORIÁK = sorted({ex["gyakorlat_kategoria"] for ex in EX_DB})


############################################################
# 3. PERIODIZÁCIÓ → ALAP CÉLOK
############################################################

def get_default_targets(age_group: str, week: int) -> Dict[str, Any]:
    """
    Periodizáció alapján előre beállított fókuszok.
    (Egyszerűsített mapping; igény szerint később bővíthető.)
    """

    if age_group.startswith("U7") or age_group.startswith("U10"):
        if week == 1:
            return {
                "fo_taktikai": "jatekszervezes",
                "taktikai": ["jatekszervezes"],
                "technikai": ["passz"],
                "kondicionalis": ["koordinacio"]
            }
        if week == 2:
            return {
                "fo_taktikai": "labdakihozatal",
                "taktikai": ["labdakihozatal"],
                "technikai": ["passz", "mozgás labdára"],
                "kondicionalis": ["gyors iranyvaltas"]
            }
        if week == 3:
            return {
                "fo_taktikai": "befejezes",
                "taktikai": ["befejezes"],
                "technikai": ["lövéstechnika"],
                "kondicionalis": ["gyorsasag"]
            }
        return {
            "fo_taktikai": "jatekszervezes",
            "taktikai": ["jatekszervezes"],
            "technikai": ["passz"],
            "kondicionalis": ["könnyű allokepesseg"]
        }

    # U13–U19 és felnőtt — alap séma:
    if week == 1:
        return {
            "fo_taktikai": "labdakihozatal",
            "taktikai": ["labdakihozatal", "jatekszervezes"],
            "technikai": ["passz", "mozgás passz után"],
            "kondicionalis": ["koordinacio"]
        }
    if week == 2:
        return {
            "fo_taktikai": "jatekszervezes",
            "taktikai": ["jatekszervezes"],
            "technikai": ["passzjatek"],
            "kondicionalis": ["allokepesseg"]
        }
    if week == 3:
        return {
            "fo_taktikai": "befejezes",
            "taktikai": ["befejezes"],
            "technikai": ["lövéstechnika"],
            "kondicionalis": ["robbanekonysag"]
        }
    return {
        "fo_taktikai": "atmenet",
        "taktikai": ["atmenet_tamadasba"],
        "technikai": ["passz"],
        "kondicionalis": ["koordinacio"]
    }


############################################################
# 4. STAGE + KATEGÓRIA ALAPÚ PONTOZÁS
############################################################

def score_exercise(ex: Dict[str, Any],
                   stage: str,
                   desired_fo: str,
                   desired_taktikai: List[str],
                   desired_technikai: List[str],
                   desired_kond: List[str]) -> int:
    score = 0

    # FŐ taktikai egyezés
    if ex.get("fo_taktikai_cel") == desired_fo:
        score += 5

    # Taktikai címkék
    ex_takt = ex.get("taktikai_cel_cimkek", [])
    for t in desired_taktikai:
        if t in ex_takt:
            score += 2

    # Technikai címkék
    ex_tech = ex.get("technikai_cel_cimkek", [])
    for t in desired_technikai:
        if t in ex_tech:
            score += 1

    # Kondicionális címkék
    ex_k = ex.get("kondicionalis_cel_cimkek", [])
    for c in desired_kond:
        if c in ex_k:
            score += 1

    # Kategória preferencia stage szerint
    kat = ex.get("gyakorlat_kategoria", "")

    if stage == "bemelegites":
        if kat in ["rondo", "technikazas"]:
            score += 4
        elif kat == "kisjatek":
            score += 1
        elif kat in ["merkozesjatek", "jatekszituacio"]:
            score -= 3

    elif stage == "cel1":
        if kat in ["kisjatek", "rondo"]:
            score += 4
        elif kat in ["jatekszituacio"]:
            score += 1
        elif kat in ["merkozesjatek"]:
            score -= 3

    elif stage == "cel2":
        if kat in ["jatekszituacio", "mezonyjatekszituacio"]:
            score += 4
        elif kat in ["kisjatek"]:
            score += 1
        elif kat in ["rondo", "technikazas"]:
            score -= 3

    elif stage == "cel3":
        if kat in ["merkozesjatek", "jatekszituacio"]:
            score += 5
        elif kat in ["mezonyjatekszituacio"]:
            score += 3
        elif kat in ["rondo", "kisjatek", "technikazas"]:
            score -= 4

    return score


############################################################
# 5. GYAKORLAT KIVÁLASZTÁSA
############################################################

def pick_exercise(stage: str,
                  desired_fo: str,
                  desired_taktikai: List[str],
                  desired_technikai: List[str],
                  desired_kond: List[str],
                  used_ids: Set[str]) -> Optional[Dict[str, Any]]:
    scored = []
    for ex in EX_DB:
        if ex.get("edzes_resze") != stage:
            continue
        if ex["file_name"] in used_ids:
            continue

        s = score_exercise(
            ex,
            stage,
            desired_fo,
            desired_taktikai,
            desired_technikai,
            desired_kond
        )
        scored.append((s, ex))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score = scored[0][0]
    best = [ex for s, ex in scored if s == best_score]
    chosen = random.choice(best)

    return chosen


############################################################
# 6. KÉP + DIAGRAM A PDF-BE
############################################################

def render_diagram_to_png(diagram_spec: Dict[str, Any]) -> BytesIO:
    fig = draw_drill(diagram_spec, show=False)
    fig.set_size_inches(5, 3)
    bio = BytesIO()
    fig.savefig(bio, format="png", dpi=120, bbox_inches="tight")
    bio.seek(0)
    plt.close(fig)
    return bio


############################################################
# 7. PDF GENERÁLÁS
############################################################

class TrainingPDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 8, "Edzésterv – Training Blueprint", ln=1)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "", 9)
        self.cell(0, 10, "Generálva a Training Blueprint alkalmazással", 0, 0, "C")


def create_pdf(plan: List[Dict[str, Any]]) -> BytesIO:
    pdf = TrainingPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for block in plan:
        ex = block["exercise"]
        pdf.add_page()

        # ---- KÉP / DIAGRAM FELÜL ----
        img_buffer = None

        if "diagram_v1" in ex and ex["diagram_v1"]:
            img_buffer = render_diagram_to_png(ex["diagram_v1"])
        else:
            fname = ex.get("file_name")
            if fname:
                path = os.path.join(DRILL_IMAGE_FOLDER, fname)
                if os.path.exists(path):
                    img_buffer = path

        if img_buffer:
            if isinstance(img_buffer, BytesIO):
                pdf.image(img_buffer, x=10, w=180)
            else:
                pdf.image(img_buffer, x=10, w=180)

        # ---- SZÖVEGEK ----
        pdf.set_font("Arial", "B", 12)
        pdf.ln(5)
        pdf.cell(0, 7, ex.get("title", "Gyakorlat"), ln=1)

        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, f"Szervezés:\n{ex.get('organisation', '-')}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, f"Leírás:\n{ex.get('description', '-')}")
        pdf.ln(1)

    bio = BytesIO()
    pdf.output(bio)
    bio.seek(0)
    return bio


############################################################
# ----------- RÉSZ 1/3 VÉGE --------------------------------
############################################################
############################################################
#  app.py — Training Blueprint Edzéstervező (MAGYAR UI)
#  TELJES VERZIÓ — RÉSZ 2/3
############################################################

st.set_page_config(page_title="Training Blueprint – Edzéstervező", layout="wide")

st.title("⚽ Edzéstervező – Training Blueprint")

############################################################
# OLDALSÁV – KOROSZTÁLY, HÉT, PERIODIZÁCIÓ
############################################################

st.sidebar.header("Edzés paraméterei")

korosztaly = st.sidebar.selectbox(
    "Korosztály",
    ["U7-U9", "U10-U12", "U13-U15", "U16-U19", "felnott"],
)

period_week = st.sidebar.number_input(
    "Periodizációs hét",
    min_value=1,
    max_value=4,
    value=1
)

# Periodizáció alapján automatikus célok
defaults = get_default_targets(korosztaly, period_week)

############################################################
# TAKTIKAI / TECHNIKAI / ERŐNLÉTI CÉLOK – JSON-BŐL
############################################################

st.sidebar.subheader("Edzés céljai")

# Fő taktikai cél
fo_taktikai = st.sidebar.selectbox(
    "Fő taktikai cél",
    [""] + FO_TAKTIKAI_CELOK,
    index=(1 + FO_TAKTIKAI_CELOK.index(defaults["fo_taktikai"])
           if defaults["fo_taktikai"] in FO_TAKTIKAI_CELOK else 0)
)

# Taktikai címkék (több választható)
taktikai_valasztott = st.sidebar.multiselect(
    "Taktikai címkék",
    TAKTIKAI_CIMKEK,
    default=[t for t in defaults["taktikai"] if t in TAKTIKAI_CIMKEK]
)

# Technikai címkék
technikai_valasztott = st.sidebar.multiselect(
    "Technikai címkék",
    TECHNIKAI_CIMKEK,
    default=[t for t in defaults["technikai"] if t in TECHNIKAI_CIMKEK]
)

# Erőnléti címkék
kond_valasztott = st.sidebar.multiselect(
    "Kondicionális címkék",
    KONDICIONALIS_CIMKEK,
    default=[t for t in defaults["kondicionalis"] if t in KONDICIONALIS_CIMKEK]
)

############################################################
# EDZÉS GENERÁLÁSA
############################################################

st.header("🧩 Edzés generálása")

if "plan" not in st.session_state:
    st.session_state.plan = []
if "used_ids" not in st.session_state:
    st.session_state.used_ids = set()

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
            used
        )
        if ex:
            used.add(ex["file_name"])
            plan.append({"stage": stage, "exercise": ex})

    st.session_state.plan = plan
    st.session_state.used_ids = used


if st.button("🚀 Edzés generálása"):
    generate_full_training()


############################################################
# GYAKORLAT BLOKK MEGJELENÍTÉSE (KÉP + SZERKESZTHETŐ SZÖVEG)
############################################################

st.header("📋 Generált edzés")

def show_exercise_block(block_index: int, block: Dict[str, Any]):
    stage = block["stage"]
    ex = block["exercise"]

    st.subheader(f"{stage.upper()} – {ex.get('file_name')}")

    cols = st.columns([1, 2])

    # ---- BAL: KÉP vagy DIAGRAM ----
    with cols[0]:
        if "diagram_v1" in ex and ex["diagram_v1"]:
            fig = draw_drill(ex["diagram_v1"], show=False)
            fig.set_size_inches(4, 2.5)
            st.pyplot(fig, use_container_width=False)
        else:
            fname = ex.get("file_name")
            if fname:
                path = os.path.join(DRILL_IMAGE_FOLDER, fname)
                if os.path.exists(path):
                    st.image(path, width=300)
                else:
                    st.warning("Nincs feltöltve a megfelelő kép.")

    # ---- JOBB: SZERKESZTHETŐ SZÖVEGEK ----
    with cols[1]:
        ex["organisation"] = st.text_area(
            "Szervezés",
            value=ex.get("organisation", "")
        )
        ex["description"] = st.text_area(
            "Leírás",
            value=ex.get("description", "")
        )

        if st.button(f"🔄 Gyakorlat cseréje ({stage})", key=f"replace_{block_index}"):
            new_ex = pick_exercise(
                stage,
                fo_taktikai,
                taktikai_valasztott,
                technikai_valasztott,
                kond_valasztott,
                st.session_state.used_ids
            )
            if new_ex:
                st.session_state.used_ids.add(new_ex["file_name"])
                st.session_state.plan[block_index]["exercise"] = new_ex
                st.rerun()
            else:
                st.error("Ehhez a szűréshez nincs több gyakorlat a kategóriában.")

# ---- Megjelenítés ----
for i, block in enumerate(st.session_state.plan):
    show_exercise_block(i, block)


############################################################
# RÉSZ 2/3 VÉGE
############################################################
############################################################
#  RÉSZ 3/3 — PDF EXPORT
############################################################

st.header("📄 PDF Export")

def create_training_pdf(plan):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Training Blueprint – Edzésterv", ln=1)

    pdf.set_font("Arial", "", 12)

    for block in plan:
        stage = block["stage"]
        ex = block["exercise"]

        pdf.ln(5)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, f"{stage.upper()}", ln=1)

        pdf.set_font("Arial", "", 12)

        # ---- Szövegek ----
        pdf.multi_cell(0, 6, f"Szervezés: {ex.get('organisation','')}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, f"Leírás: {ex.get('description','')}")
        pdf.ln(2)

        # ---- Kép / diagram ----
        pdf.set_font("Arial", "", 11)

        # Először PNG drill image
        fname = ex.get("file_name")
        img_path = os.path.join(DRILL_IMAGE_FOLDER, fname) if fname else ""

        if fname and os.path.exists(img_path):
            try:
                pdf.image(img_path, w=120)  # kisebb kép (70%)
                pdf.ln(8)
            except:
                pdf.multi_cell(0, 6, "[Kép beillesztése nem sikerült]")
        # Ha nincs PNG → diagram rajzolása
        elif "diagram_v1" in ex and ex["diagram_v1"]:
            try:
                fig = draw_drill(ex["diagram_v1"], show=False)
                tmp_diagram = "_temp_diagram.png"
                fig.savefig(tmp_diagram, dpi=120)
                pdf.image(tmp_diagram, w=120)
                pdf.ln(8)
                os.remove(tmp_diagram)
            except:
                pdf.multi_cell(0, 6, "[Diagram beillesztése nem sikerült]")

    # ---- PDF visszaadása memory bufferben ----
    pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
    return pdf_bytes


if st.button("📥 PDF generálása"):
    if not st.session_state.plan:
        st.error("Előbb generálj edzést!")
    else:
        pdf_bytes = create_training_pdf(st.session_state.plan)
        st.download_button(
            "📄 PDF letöltése",
            data=pdf_bytes,
            file_name="edzesterv.pdf",
            mime="application/pdf"
        )


############################################################
# --- APP VÉGE ---
############################################################


    # ---- JOBB: SZERKESZTHETŐ SZÖVEGEK ----
    with cols[1]:
        ex["organisation"] = st.text_area(
            "Szervezés",
            value=ex.get("organisation", "")
        )
        ex["description"] = st.text_area(
            "Leírás",
            value=ex.get("description", "")
        )

        if st.button(f"🔄 Gyakorlat cseréje ({stage})", key=f"replace_{block_index}"):
            new_ex = pick_exercise(
                stage,
                fo_taktikai,
                taktikai_valasztott,
                technikai_valasztott,
                kond_valasztott,
                st.session_state.used_ids
            )
            if new_ex:
                st.session_state.used_ids.add(new_ex["file_name"])
                st.session_state.plan[block_index]["exercise"] = new_ex
                st.rerun()
            else:
                st.error("Ehhez a szűréshez nincs több gyakorlat a kategóriában.")

# ---- Megjelenítés ----
for i, block in enumerate(st.session_state.plan):
    show_exercise_block(i, block)


############################################################
# RÉSZ 2/3 VÉGE
############################################################
############################################################
#  RÉSZ 3/3 — PDF EXPORT
############################################################

st.header("📄 PDF Export")

def create_training_pdf(plan):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Training Blueprint – Edzésterv", ln=1)

    pdf.set_font("Arial", "", 12)

    for block in plan:
        stage = block["stage"]
        ex = block["exercise"]

        pdf.ln(5)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, f"{stage.upper()}", ln=1)

        pdf.set_font("Arial", "", 12)

        # ---- Szövegek ----
        pdf.multi_cell(0, 6, f"Szervezés: {ex.get('organisation','')}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, f"Leírás: {ex.get('description','')}")
        pdf.ln(2)

        # ---- Kép / diagram ----
        pdf.set_font("Arial", "", 11)

        # Először PNG drill image
        fname = ex.get("file_name")
        img_path = os.path.join(DRILL_IMAGE_FOLDER, fname) if fname else ""

        if fname and os.path.exists(img_path):
            try:
                pdf.image(img_path, w=120)  # kisebb kép (70%)
                pdf.ln(8)
            except:
                pdf.multi_cell(0, 6, "[Kép beillesztése nem sikerült]")
        # Ha nincs PNG → diagram rajzolása
        elif "diagram_v1" in ex and ex["diagram_v1"]:
            try:
                fig = draw_drill(ex["diagram_v1"], show=False)
                tmp_diagram = "_temp_diagram.png"
                fig.savefig(tmp_diagram, dpi=120)
                pdf.image(tmp_diagram, w=120)
                pdf.ln(8)
                os.remove(tmp_diagram)
            except:
                pdf.multi_cell(0, 6, "[Diagram beillesztése nem sikerült]")

    # ---- PDF visszaadása memory bufferben ----
    pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
    return pdf_bytes


if st.button("📥 PDF generálása"):
    if not st.session_state.plan:
        st.error("Előbb generálj edzést!")
    else:
        pdf_bytes = create_training_pdf(st.session_state.plan)
        st.download_button(
            "📄 PDF letöltése",
            data=pdf_bytes,
            file_name="edzesterv.pdf",
            mime="application/pdf"
        )


############################################################
# --- APP VÉGE ---
############################################################
