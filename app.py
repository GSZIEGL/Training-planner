import json
import random
from io import BytesIO
from typing import List, Dict
import requests
import streamlit as st
import tempfile

from fpdf import FPDF


# -----------------------------------------------------
# Utility: Load Training Database
# -----------------------------------------------------
@st.cache_data
def load_training_database(path: str = "training_database.json") -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


# -----------------------------------------------------
# Selecting exercises based on structured metadata
# -----------------------------------------------------
def filter_db(
    db: List[Dict],
    age_group: str,
    tactical_code: str,
    technical_filters: List[str]
) -> List[Dict]:

    res = []
    for ex in db:
        # korosztály szűrés
        if age_group and ex.get("age_group_code") != age_group:
            continue

        # taktikai szűrés
        if tactical_code and ex.get("tactical_code") != tactical_code:
            continue

        # technikai szűrés (multi)
        if technical_filters:
            if ex.get("technical_code") not in technical_filters:
                continue

        res.append(ex)

    return res


# -----------------------------------------------------
# Stage suitability scoring (warmup / small / large / main)
# -----------------------------------------------------
def score_for_stage(ex: Dict, stage: str) -> int:
    score = 0
    fmt = ex.get("format", "")
    ex_type = ex.get("exercise_type", "")
    intensity = ex.get("intensity", "")

    if stage == "warmup":
        if "v" in fmt:
            try:
                left = int(fmt.split("v")[0])
                if left <= 4:
                    score += 4
            except:
                pass
        if intensity in ["alacsony", "alacsony–közepes", "közepes"]:
            score += 2
        if ex_type.lower() in ["rondó", "rondo", "positional game"]:
            score += 3

    elif stage == "small":
        if ex_type.lower() in ["small-sided game", "positional game"]:
            score += 4
        if "v" in fmt:
            try:
                left = int(fmt.split("v")[0])
                if 3 <= left <= 5:
                    score += 3
            except:
                pass

    elif stage == "large":
        if "v" in fmt:
            try:
                left = int(fmt.split("v")[0])
                if 5 <= left <= 7:
                    score += 4
            except:
                pass
        if ex_type.lower() in ["positional game", "pressing"]:
            score += 3

    elif stage == "main":
        if "v" in fmt:
            try:
                left = int(fmt.split("v")[0])
                if left >= 7:
                    score += 4
            except:
                pass
        if ex_type.lower() in ["game", "small-sided game"]:
            score += 3

    return score


def pick_exercise(db: List[Dict], used_ids: set, stage: str):
    scored = []
    for ex in db:
        if ex["id"] in used_ids:
            continue
        s = score_for_stage(ex, stage)
        if s > 0:
            scored.append((s, ex))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    top = [x[1] for x in scored if x[0] == top_score]
    return random.choice(top)


# -----------------------------------------------------
# Image selection
# -----------------------------------------------------
def get_image_url(ex: Dict) -> str:
    url = ex.get("image_url", "")
    if url and url.strip():
        return url
    return ""


# -----------------------------------------------------
# PDF builder (with Unicode support)
# -----------------------------------------------------
class PDF(FPDF):
    def header(self):
        self.set_font("DejaVu", "", 12)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 10)
        self.cell(0, 10, "Edzésterv generálva ChatbotFootball rendszerrel", 0, 0, "C")


def build_pdf(plan, coach_id, age_group, tactical_choice, technical_filters):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Register unicode font
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)

    # Title page
    pdf.add_page()
    pdf.set_font("DejaVu", "", 20)
    pdf.cell(0, 10, "Edzésterv", ln=1)

    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 8, f"Korosztály: {age_group}", ln=1)
    pdf.cell(0, 8, f"Taktikai cél: {tactical_choice}", ln=1)
    pdf.cell(0, 8, f"Technikai fókusz: {', '.join(technical_filters)}", ln=1)
    pdf.cell(0, 8, f"Edző azonosító: {coach_id}", ln=1)

    # Each block
    for idx, (title, ex) in enumerate(plan, 1):
        pdf.add_page()
        pdf.set_font("DejaVu", "B", 16)
        pdf.cell(0, 10, f"{idx}. {title}", ln=1)

        pdf.set_font("DejaVu", "", 12)
        pdf.multi_cell(0, 7, f"Cím: {ex.get('title_hu','')}")

        # Insert image only if real image_url exists
        img_url = get_image_url(ex)
        if img_url:
            try:
                resp = requests.get(img_url, timeout=5)
                resp.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                pdf.image(tmp_path, w=120)
                pdf.ln(5)
            except:
                pass

        org = ex.get("organisation_hu", "")
        if org:
            pdf.multi_cell(0, 7, f"Szervezés: {org}")

        desc = ex.get("description_hu", "")
        if desc:
            pdf.multi_cell(0, 7, f"Leírás / menete: {desc}")

        cpts = ex.get("coaching_points_hu", [])
        if cpts:
            pdf.multi_cell(0, 7, "Coaching pontok:")
            for c in cpts:
                pdf.multi_cell(0, 7, f" • {c}")

        var = ex.get("variations_hu", [])
        if var:
            pdf.multi_cell(0, 7, "Variációk:")
            for v in var:
                pdf.multi_cell(0, 7, f" • {v}")

    bio = BytesIO()
    pdf.output(bio)
    bio.seek(0)
    return bio


# -----------------------------------------------------
# Streamlit UI
# -----------------------------------------------------
st.set_page_config(page_title="ChatbotFootball – 300 gyakorlatos edzésterv", layout="wide")

st.title("⚽ chatbotfootball – 300 gyakorlatos edzésterv generátor")

st.write("""
Ez az app egy saját, ~300 gyakorlatból álló adatbázisból generál edzéstervet  
a megadott korosztály, taktikai cél és technikai fókusz alapján.
""")

db = load_training_database()

if not db:
    st.error("❌ Nem sikerült betölteni a `training_database.json` fájlt.")
    st.stop()

age_options = sorted(list({ex["age_group_code"] for ex in db}))
tactical_options = sorted(list({ex["tactical_code"] for ex in db}))
technical_options = sorted(list({ex["technical_code"] for ex in db}))

st.sidebar.header("Szűrés")
age_group = st.sidebar.selectbox("Korosztály", age_options)
tactical_choice = st.sidebar.selectbox("Taktikai cél", tactical_options)
technical_filters = st.sidebar.multiselect("Technikai fókusz", technical_options)
coach_id = st.sidebar.text_input("Edző azonosító", "coach_1")

generate = st.sidebar.button("Edzésterv generálása")

if generate:
    st.success("Edzésterv generálva a fenti paraméterek alapján.")

    filtered = filter_db(db, age_group, tactical_choice, technical_filters)

    plan = []
    used = set()

    for stage, title in [
        ("warmup", "Bemelegítés"),
        ("small", "Cél1 – kis létszámú játék"),
        ("large", "Cél2 – nagyobb taktikai játék"),
        ("main", "Cél3 – fő rész / mérkőzésjáték jellegű feladat")
    ]:
        ex = pick_exercise(filtered, used, stage)
        if not ex:
            st.warning(f"Nem találtam gyakorlato ehhez a szakaszhoz: {title}")
        else:
            used.add(ex["id"])
            plan.append((title, ex))

    st.header("📘 Edzésterv összefoglaló")
    st.write(f"Korosztály: {age_group}")
    st.write(f"Játékoslétszám: {len(plan)}")
    st.write(f"Edző: {coach_id}")

    for idx, (title, ex) in enumerate(plan, 1):
        st.subheader(f"{idx}. {title}")

        c1, c2 = st.columns([1, 1.2])

        with c1:
            img_url = get_image_url(ex)
            if img_url:
                try:
                    st.image(img_url, use_column_width=True)
                except:
                    st.info("Kép nem tölthető be.")
            else:
                st.info("Ehhez a gyakorlathoz nincs kép az adatbázisban.")

        with c2:
            st.write(f"**{ex.get('title_hu','')}**")
            st.write(f"*Formátum:* {ex.get('format','')}  |  *Típus:* {ex.get('exercise_type','')}")
            st.write(f"Pályaméret: {ex.get('pitch_size','')}  |  Időtartam: {ex.get('duration_minutes','')} perc")

            with st.expander("Szervezés (HU)"):
                st.write(ex.get("organisation_hu", ""))

            with st.expander("Leírás / menet (HU)"):
                st.write(ex.get("description_hu", ""))

            with st.expander("Coaching pontok (HU)"):
                for c in ex.get("coaching_points_hu", []):
                    st.write("- " + c)

            with st.expander("Variációk (HU)"):
                for v in ex.get("variations_hu", []):
                    st.write("- " + v)

    # PDF Export
    st.subheader("📄 PDF export")

    pdf_btn = st.button("🇭🇺 Magyar PDF edzésterv generálása")

    if pdf_btn:
        try:
            pdf_bytes = build_pdf(plan, coach_id, age_group, tactical_choice, technical_filters)
            st.download_button(
                label="📥 PDF letöltése",
                data=pdf_bytes,
                file_name="edzesterv.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF generálási hiba: {e}")
