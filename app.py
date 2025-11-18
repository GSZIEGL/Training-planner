import json
import random
from io import BytesIO
from typing import List, Dict, Any, Optional

import re
import requests
import streamlit as st

from fpdf import FPDF
import tempfile
import textwrap

# ============================================================
# STREAMLIT ALAPBEÁLLÍTÁS
# ============================================================
st.set_page_config(
    page_title="chatbotfootball – 300 gyakorlatos edzésterv generátor",
    layout="wide"
)

st.title("⚽ chatbotfootball – 300 gyakorlatos edzésterv generátor")
st.markdown(
    """
    Ez az app egy **saját, ~300 gyakorlatból álló adatbázisból** generál edzéstervet  
    a megadott **korosztály**, **taktikai cél** és **technikai fókusz** alapján.

    A kimenet 4 blokkból áll:
    1. **Bemelegítés**  
    2. **Cél1 – kis létszámú játék**  
    3. **Cél2 – nagyobb létszámú taktikai játék**  
    4. **Cél3 – fő rész, meccsjáték jellegű feladat**  

    Alul egy gombbal **PDF-et is letölthetsz** az edzéstervből (képpel együtt, ha elérhető).
    """
)

# ============================================================
# ADATBÁZIS BETÖLTÉSE
# ============================================================

st.sidebar.header("1. Adatbázis forrása")

use_builtin = st.sidebar.checkbox(
    "Beépített 300 gyakorlatos adatbázis használata (`training_database.json`)",
    value=True
)

EX_DB: List[Dict[str, Any]] = []

if use_builtin:
    try:
        with open("training_database.json", "r", encoding="utf-8") as f:
            EX_DB = json.load(f)
        st.sidebar.success(f"✅ Beépített adatbázis betöltve. Gyakorlatok száma: {len(EX_DB)}")
    except Exception as e:
        st.sidebar.error(f"❌ Nem sikerült beolvasni a training_database.json fájlt: {e}")
else:
    json_file = st.sidebar.file_uploader(
        "Vagy tölts fel egy saját JSON adatbázist",
        type=["json"]
    )
    if json_file is not None:
        try:
            EX_DB = json.load(json_file)
            st.sidebar.success(f"✅ Betöltött gyakorlatok száma: {len(EX_DB)}")
        except Exception as e:
            st.sidebar.error(f"❌ Nem sikerült beolvasni a JSON-t: {e}")

if not EX_DB:
    st.warning("⬅️ Tölts be egy adatbázist (beépített vagy saját JSON), hogy tudjunk dolgozni.")
    st.stop()

# ============================================================
# SEGÉDFÜGGVÉNYEK
# ============================================================

def filter_by_age(ex_list: List[Dict[str, Any]], age_code: Optional[str]) -> List[Dict[str, Any]]:
    if not age_code:
        return ex_list
    return [ex for ex in ex_list if ex.get("age_group_code") == age_code]


def filter_by_tact(ex_list: List[Dict[str, Any]], tact_code: Optional[str]) -> List[Dict[str, Any]]:
    if not tact_code:
        return ex_list
    return [ex for ex in ex_list if ex.get("tactical_code") == tact_code]


def filter_by_tech(ex_list: List[Dict[str, Any]], tech_codes: List[str]) -> List[Dict[str, Any]]:
    if not tech_codes:
        return ex_list
    return [ex for ex in ex_list if ex.get("technical_code") in tech_codes]


def get_image_url(ex: Dict[str, Any]) -> Optional[str]:
    url = ex.get("image_url")
    if url:
        return url
    return None


PLACEHOLDER_IMAGE = "https://raw.githubusercontent.com/GSZIEGL/Training-planner/main/match_game.png"


def normalized_key(ex: Dict[str, Any]) -> tuple:
    """
    Azonos gyakorlat külön variációi (pl. #1, #2) ugyanazt a kulcsot kapják.
    Levágjuk a cím végéről a zárójeles részt, pl. "(Felnőtt, #2)".
    """
    title = ex.get("title_hu", "") or ""
    fmt = ex.get("format", "") or ""
    # minden zárójelben lévő rész (a végéről) törölve
    title_clean = re.sub(r"\s*\([^)]*#\d+[^)]*\)\s*$", "", title).strip().lower()
    return (title_clean, fmt.strip().lower())

# ============================================================
# PONTSZÁMÍTÁS
# ============================================================

def format_size_score(fmt: str, target: str) -> int:
    fmt = (fmt or "").lower()
    score = 0
    nums = re.findall(r"\d+", fmt)
    total = 0
    if nums:
        total = sum(int(n) for n in nums[:2])

    if target == "small":
        if 3 <= total <= 8:
            score += 5
        elif total <= 12:
            score += 2
        else:
            score -= 3
    elif target == "medium":
        if 6 <= total <= 14:
            score += 5
        elif total <= 20:
            score += 2
        else:
            score -= 3
    elif target == "large":
        if 10 <= total <= 22:
            score += 5
        elif total <= 26:
            score += 2
        else:
            score -= 3

    return score


def intensity_score(ex_intensity: str, target: str) -> int:
    ei = (ex_intensity or "").lower()
    if target == "low":
        if "alacsony" in ei:
            return 4
        if "közepes" in ei:
            return 2
        return 0
    if target == "medium":
        if "közepes" in ei:
            return 4
        if "alacsony" in ei or "magas" in ei:
            return 2
        return 0
    if target == "high":
        if "magas" in ei:
            return 4
        if "közepes" in ei:
            return 2
        return 0
    return 0


def exercise_type_score(ex_type: str, stage: str) -> int:
    t = (ex_type or "").lower()
    score = 0

    if stage == "warmup":
        if "rondó" in t or "rondo" in t or "warm" in t or "positional" in t:
            score += 5
        if "finishing" in t or "game" in t:
            score -= 2

    elif stage == "small":
        if "rondó" in t or "rondo" in t or "small-sided" in t or "positional" in t:
            score += 5

    elif stage == "large":
        if "positional" in t or "pressing" in t or "small-sided" in t:
            score += 5

    elif stage == "main":
        if "game" in t or "pressing game" in t or "transition game" in t:
            score += 6
        if "rondó" in t or "rondo" in t:
            score -= 2

    return score


def score_exercise_for_stage(ex: Dict[str, Any], stage: str) -> float:
    fmt = ex.get("format", "")
    ex_type = ex.get("exercise_type", "")
    intensity = ex.get("intensity", "")

    score = 0.0

    if stage == "warmup":
        score += format_size_score(fmt, "small")
        score += intensity_score(intensity, "low")
    elif stage == "small":
        score += format_size_score(fmt, "small")
        score += intensity_score(intensity, "medium")
    elif stage == "large":
        score += format_size_score(fmt, "medium")
        score += intensity_score(intensity, "medium")
    elif stage == "main":
        score += format_size_score(fmt, "large")
        score += intensity_score(intensity, "high")

    score += exercise_type_score(ex_type, stage)
    score += random.uniform(0, 1)
    return score


def pick_exercise_for_stage(
    ex_list: List[Dict[str, Any]],
    stage: str,
    used_keys: set
) -> Optional[Dict[str, Any]]:
    """
    ex_list: jelöltek az adott szakaszra (korosztály/taktika/technika alapján).
    used_keys: már használt normalizált kulcsok (cím_clean, formátum).
    """
    candidates = []
    for ex in ex_list:
        key = normalized_key(ex)
        if key not in used_keys:
            candidates.append(ex)

    if not candidates:
        return None

    scored = [(score_exercise_for_stage(ex, stage), ex) for ex in candidates]
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_ex = scored[0]
    if best_score < 1 and len(scored) >= 3:
        return random.choice([ex for _, ex in scored[:3]])
    return best_ex

# ============================================================
# OLDALSÁV – PARAMÉTEREK
# ============================================================

st.sidebar.header("2. Edzésparaméterek")

# Korosztály
age_codes = sorted(set(ex.get("age_group_code") for ex in EX_DB if ex.get("age_group_code")))
age_labels_map = {
    ex["age_group_code"]: ex.get("age_group_label", ex["age_group_code"])
    for ex in EX_DB if ex.get("age_group_code")
}
age_options = ["Bármely"] + [age_labels_map[code] for code in age_codes]
age_choice = st.sidebar.selectbox("Korosztály:", age_options, index=1 if len(age_options) > 1 else 0)

selected_age_code = None
if age_choice != "Bármely":
    for code, label in age_labels_map.items():
        if label == age_choice:
            selected_age_code = code
            break

# Taktikai cél
tact_codes = []
tact_labels_map = {}
for ex in EX_DB:
    c = ex.get("tactical_code")
    l = ex.get("tactical_label")
    if c and c not in tact_codes:
        tact_codes.append(c)
        tact_labels_map[c] = l or c

tact_options = ["Bármely"] + [tact_labels_map[c] for c in tact_codes]
tact_choice = st.sidebar.selectbox("Taktikai cél:", tact_options, index=1 if len(tact_options) > 1 else 0)

selected_tact_code = None
if tact_choice != "Bármely":
    for c, l in tact_labels_map.items():
        if l == tact_choice:
            selected_tact_code = c
            break

# Technikai fókusz (multi)
tech_codes = []
tech_labels_map = {}
for ex in EX_DB:
    c = ex.get("technical_code")
    l = ex.get("technical_label")
    if c and c not in tech_codes:
        tech_codes.append(c)
        tech_labels_map[c] = l or c

tech_options = [tech_labels_map[c] for c in tech_codes]
tech_choice_labels = st.sidebar.multiselect(
    "Technikai fókusz(ok):",
    tech_options,
    default=tech_options[:1] if tech_options else []
)

selected_tech_codes = []
for label in tech_choice_labels:
    for c, l in tech_labels_map.items():
        if l == label:
            selected_tech_codes.append(c)

players_raw = st.sidebar.text_input("Hány játékosra tervezünk? (pl. 12–16)", value="14")
total_time = st.sidebar.text_input("Össz edzésidő (pl. 75 perc, 90 perc):", value="90 perc")

st.sidebar.markdown("---")
coach_id = st.sidebar.text_input("Edző azonosító (név / email – későbbi historyhoz):", value="coach_1")

generate = st.sidebar.button("🎯 Edzésterv generálása")

if not generate:
    st.info("⬅️ Állítsd be a paramétereket, majd kattints a **🎯 Edzésterv generálása** gombra.")
    st.stop()

# ============================================================
# EDZÉSTERV ÖSSZERAKÁSA – FOKOZATOSAN LAZÍTOTT SZŰRÉS + DUPLIKÁCIÓ TILTÁSA
# ============================================================

def candidates_for_stage(stage: str, used_keys: set) -> Optional[Dict[str, Any]]:
    """
    Fokozatosan lazítjuk a szűrést:
    1) age + tact + tech
    2) age + tact
    3) age only
    4) bármi az adatbázisból
    """
    # 1. age + tact + tech
    cand = EX_DB
    cand = filter_by_age(cand, selected_age_code)
    cand = filter_by_tact(cand, selected_tact_code)
    cand = filter_by_tech(cand, selected_tech_codes)
    ex = pick_exercise_for_stage(cand, stage, used_keys)
    if ex:
        return ex

    # 2. age + tact
    cand = EX_DB
    cand = filter_by_age(cand, selected_age_code)
    cand = filter_by_tact(cand, selected_tact_code)
    ex = pick_exercise_for_stage(cand, stage, used_keys)
    if ex:
        return ex

    # 3. csak age
    cand = filter_by_age(EX_DB, selected_age_code)
    ex = pick_exercise_for_stage(cand, stage, used_keys)
    if ex:
        return ex

    # 4. teljes adatbázis
    ex = pick_exercise_for_stage(EX_DB, stage, used_keys)
    return ex

used_keys = set()
plan: List[Dict[str, Any]] = []
stages = [
    ("Bemelegítés", "warmup"),
    ("Cél1 – kis létszámú játék", "small"),
    ("Cél2 – nagyobb taktikai játék", "large"),
    ("Cél3 – fő rész / meccsjáték jellegű", "main"),
]

for label, code in stages:
    ex = candidates_for_stage(code, used_keys)
    if ex:
        plan.append((label, code, ex))
        used_keys.add(normalized_key(ex))
    else:
        st.warning(f"Nem találtam gyakorlatot ehhez a szakaszhoz: {label}")

if not plan:
    st.error("Nem sikerült gyakorlatokat választani az edzéshez.")
    st.stop()

# ============================================================
# ÖSSZEFOGLALÓ
# ============================================================

st.subheader("📋 Edzésterv összefoglaló")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Korosztály:** {age_choice}")
    st.markdown(f"**Játékoslétszám:** {players_raw}")
    st.markdown(f"**Edzésidő:** {total_time}")
with col2:
    st.markdown(f"**Taktikai cél:** {tact_choice}")
    st.markdown(f"**Technikai fókusz:** {', '.join(tech_choice_labels) if tech_choice_labels else 'nincs megadva'}")
    st.markdown(f"**Edző azonosító:** {coach_id or 'nincs megadva'}")

st.markdown("---")

# ============================================================
# GYAKORLATOK MEGJELENÍTÉSE
# ============================================================

for idx, (stage_label, stage_code, ex) in enumerate(plan, start=1):
    st.markdown(f"### {idx}. {stage_label}")
    c1, c2 = st.columns([1.2, 2])

    with c1:
        img_url = get_image_url(ex)
        if img_url:
            try:
                st.image(img_url, use_column_width=True)
            except Exception:
                st.info("Kép nem tölthető be az image_url alapján, placeholder jelenik meg.")
                st.image(PLACEHOLDER_IMAGE, use_column_width=True)
        else:
            st.image(PLACEHOLDER_IMAGE, use_column_width=True)

    with c2:
        title = ex.get("title_hu", "Névtelen gyakorlat (HU)")
        st.markdown(f"**Cím:** {title}")
        st.markdown(
            f"**Formátum:** {ex.get('format', 'nincs megadva')} "
            f"&nbsp;&nbsp; | &nbsp;&nbsp; **Típus:** {ex.get('exercise_type', 'nincs megadva')}"
        )
        st.markdown(
            f"**Pályaméret:** {ex.get('pitch_size', 'nincs megadva')} "
            f"&nbsp;&nbsp; | &nbsp;&nbsp; **Időtartam:** {ex.get('duration_minutes', 'n/a')} perc "
            f"&nbsp;&nbsp; | &nbsp;&nbsp; **Intenzitás:** {ex.get('intensity', 'n/a')}"
        )

        org = ex.get("organisation_hu")
        desc = ex.get("description_hu")
        cps = ex.get("coaching_points_hu") or []
        vars_ = ex.get("variations_hu") or []
        prog = ex.get("progression_hu")

        if org:
            with st.expander("Szervezés (HU)"):
                st.write(org)

        if desc:
            with st.expander("Leírás / menete (HU)"):
                st.write(desc)

        if cps:
            with st.expander("Coaching pontok (HU)"):
                for p in cps:
                    st.markdown(f"- {p}")

        if vars_:
            with st.expander("Variációk (HU)"):
                for v in vars_:
                    st.markdown(f"- {v}")

        if prog:
            with st.expander("Progresszió / következő lépcső (HU)"):
                st.write(prog)

    st.markdown("---")

st.success("✅ Edzésterv generálva a fenti paraméterek alapján.")

# ============================================================
# PDF GENERÁLÁS – EGY LETÖLTŐGOMB, SAFE WRAP
# ============================================================

def safe_wrap(text: str, width: int = 110) -> str:
    if not text:
        return ""
    words = text.split()
    processed = []
    for w in words:
        if len(w) > width:
            chunks = [w[i:i + width] for i in range(0, len(w), width)]
            processed.extend(chunks)
        else:
            processed.append(w)
    wrapped = textwrap.wrap(" ".join(processed), width=width)
    return "\n".join(wrapped)


class TrainingPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        try:
            self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
            self.set_font("DejaVu", size=11)
        except Exception:
            self.set_font("Helvetica", size=11)

    def header(self):
        self.set_fill_color(220, 210, 240)
        self.rect(0, 0, 210, 18, "F")
        self.set_xy(10, 5)
        self.set_font("Helvetica", size=10)
        self.cell(0, 5, "chatbotfootball training planner", ln=1)
        self.set_x(10)
        self.set_font("Helvetica", size=9)
        self.cell(0, 4, "Edzésterv – magyar leírás", ln=1)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")


def build_pdf(
    plan: List,
    age_choice: str,
    players_raw: str,
    total_time: str,
    tact_choice: str,
    tech_choice_labels: List[str],
    coach_id: str
) -> bytes:
    pdf = TrainingPDF()

    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    pdf.ln(15)

    pdf.set_font("Helvetica", size=18)
    pdf.cell(0, 10, "Edzésterv – Training Plan", ln=1)
    pdf.ln(4)

    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 6, f"Korosztály: {age_choice}", ln=1)
    pdf.cell(0, 6, f"Játékoslétszám: {players_raw}", ln=1)
    pdf.cell(0, 6, f"Össz edzésidő: {total_time}", ln=1)
    pdf.ln(4)
    pdf.cell(0, 6, f"Taktikai cél: {tact_choice}", ln=1)
    pdf.cell(
        0, 6,
        f"Technikai fókusz: {', '.join(tech_choice_labels) if tech_choice_labels else 'nincs megadva'}",
        ln=1,
    )
    pdf.cell(0, 6, f"Edző: {coach_id or 'nincs megadva'}", ln=1)

    pdf.ln(8)
    intro = (
        "Az edzésterv 4 blokkból áll: bemelegítés, kis létszámú játék, nagyobb létszámú taktikai játék "
        "és egy meccsjáték jellegű fő rész. A gyakorlatok magyar leírást, coaching pontokat és variációkat tartalmaznak."
    )
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 5, safe_wrap(intro), align="L")

    for idx, (stage_label, stage_code, ex) in enumerate(plan, start=1):
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=14)
        pdf.cell(0, 8, f"{idx}. {stage_label}", ln=1)
        pdf.ln(2)

        title = ex.get("title_hu", "Névtelen gyakorlat")
        fmt = ex.get("format", "")
        ex_type = ex.get("exercise_type", "")
        pitch = ex.get("pitch_size", "")
        dur = ex.get("duration_minutes", "")
        intensity = ex.get("intensity", "")

        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 6, safe_wrap(f"Cím: {title}", width=110), align="L")
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 5, safe_wrap(f"Formátum: {fmt}   |   Típus: {ex_type}", width=110), align="L")
        pdf.multi_cell(0, 5, safe_wrap(f"Pályaméret: {pitch}   |   Időtartam: {dur} perc   |   Intenzitás: {intensity}", width=110), align="L")
        pdf.ln(3)

        img_url = get_image_url(ex)
        if img_url:
            try:
                resp = requests.get(img_url, timeout=5)
                resp.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                pdf.image(tmp_path, x=10, y=None, w=90)
                pdf.ln(5)
            except Exception:
                pass

        org = ex.get("organisation_hu")
        if org:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(60, 0, 90)
            pdf.cell(0, 7, "Szervezés", ln=1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, safe_wrap(org), align="L")
            pdf.ln(2)

        desc = ex.get("description_hu")
        if desc:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(60, 0, 90)
            pdf.cell(0, 7, "Leírás / menete", ln=1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, safe_wrap(desc), align="L")
            pdf.ln(2)

        cps = ex.get("coaching_points_hu") or []
        if cps:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(60, 0, 90)
            pdf.cell(0, 7, "Coaching pontok", ln=1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=10)
            for p in cps:
                pdf.multi_cell(0, 5, safe_wrap(f"• {p}"), align="L")
            pdf.ln(2)

        vars_ = ex.get("variations_hu") or []
        if vars_:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(60, 0, 90)
            pdf.cell(0, 7, "Variációk", ln=1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=10)
            for v in vars_:
                pdf.multi_cell(0, 5, safe_wrap(f"- {v}"), align="L")
            pdf.ln(2)

        prog = ex.get("progression_hu")
        if prog:
            pdf.set_font("Helvetica", size=11)
            pdf.set_text_color(60, 0, 90)
            pdf.cell(0, 7, "Progresszió", ln=1)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, safe_wrap(prog), align="L")
            pdf.ln(2)

    out = pdf.output(dest="S")
    if isinstance(out, bytes):
        return out
    return bytes(out)


st.markdown("### 📄 PDF export")

try:
    pdf_bytes = build_pdf(
        plan=plan,
        age_choice=age_choice,
        players_raw=players_raw,
        total_time=total_time,
        tact_choice=tact_choice,
        tech_choice_labels=tech_choice_labels,
        coach_id=coach_id,
    )
    st.download_button(
        label="📥 Magyar PDF edzésterv letöltése",
        data=pdf_bytes,
        file_name="edzesterv_magyar.pdf",
        mime="application/pdf"
    )
except Exception as e:
    st.error(f"PDF generálási hiba: {e}")
