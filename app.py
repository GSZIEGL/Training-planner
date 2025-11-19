import streamlit as st
import json
import random
import pandas as pd
from io import BytesIO
from datetime import datetime
from pathlib import Path
import requests
import tempfile
from fpdf import FPDF

# ======================================================
#   ALAP BEÁLLÍTÁSOK
# ======================================================
st.set_page_config(
    page_title="TrainingBlueprint – Edzéstervező",
    layout="wide",
    page_icon="⚽"
)

st.title("⚽ TrainingBlueprint – Profi edzéstervező rendszer")
st.markdown("""
Ez az alkalmazás professzionális edzésterveket generál saját vagy beépített adatbázisból.

**Fő funkciók:**
- Korosztály, taktikai, technikai **és erőnléti** fókusz szerinti szűrés  
- Periodizációs hét megadása (1–4), hogy a gyakorlatszelekció illeszkedjen a ciklushoz  
- Edző ID alapú profil  
- Minden gyakorlathoz **edzői megjegyzés** + globális megjegyzés az edzéshez  
- ACWR (terhelési arány) *demo* megjelenítés  
- 4 hetes periodizációs táblázat (technika + taktika + terhelés)  
- Magyar nyelvű **PDF export** edzői megjegyzésekkel
""")


# ======================================================
#   ADATBÁZIS BETÖLTÉS
# ======================================================
st.sidebar.header("📁 Gyakorlat-adatbázis")

db_source = st.sidebar.radio(
    "Válassz adatbázis-forrást:",
    [
        "Beépített adatbázis (training_database.json)",
        "Saját JSON feltöltése"
    ]
)


def load_builtin_db():
    """training_database.json betöltése, ha van; különben mini demo."""
    try:
        with open("training_database.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "exercises" in data:
            return data["exercises"]
        elif isinstance(data, list):
            return data
        else:
            st.warning("A training_database.json formátuma nem egyértelmű, demo adatbázist használok.")
    except Exception as e:
        st.warning(f"Nem sikerült betölteni a training_database.json fájlt ({e}), demo adatbázist használok.")

    # Fallback demo gyakorlatsor
    return [
        {
            "id": "rondo_4v2_demo",
            "title_hu": "Rondó 4v2 – labdabirtoklás",
            "age_group_code": "U12-U15",
            "tactical_code": "possession",
            "technical_code": "passing",
            "physical_code": "alacsony-közepes",
            "period_week": 1,
            "exercise_type": "rondo",
            "format": "4v2",
            "duration_minutes": 12,
            "intensity": "közepes",
            "pitch_size": "15x15 m",
            "organisation_hu": "4 támadó kívül rombuszban, 2 védő középen.",
            "description_hu": "Gyors passzjáték, labdatartás két, nyomást gyakorló védő ellen.",
            "coaching_points_hu": [
                "Első érintés kifelé, térnyerő irányba.",
                "Háromszögtávolságok tartása.",
                "Gyors döntéshozatal nyomás alatt."
            ],
            "variations_hu": [
                "Max 2 érintés",
                "Érintés nélküli átvétel (half-turn)"
            ],
            "image_url": ""
        }
    ]


if db_source == "Beépített adatbázis (training_database.json)":
    db = load_builtin_db()
    st.success(f"Beépített adatbázis betöltve. Gyakorlatok száma: {len(db)}")
else:
    uploaded = st.sidebar.file_uploader("JSON feltöltése", type="json")
    if uploaded:
        try:
            data = json.loads(uploaded.read().decode("utf-8"))
            if isinstance(data, dict) and "exercises" in data:
                db = data["exercises"]
            elif isinstance(data, list):
                db = data
            else:
                st.error("A feltöltött JSON struktúrája nem támogatott (lista vagy 'exercises' kulcs szükséges).")
                db = []
            if db:
                st.success(f"Saját adatbázis betöltve. Gyakorlatok száma: {len(db)}")
        except Exception as e:
            st.error(f"Hiba a JSON beolvasásakor: {e}")
            db = []
    else:
        db = []
        st.info("Tölts fel egy JSON fájlt az adatbázishoz.")

if not db:
    st.stop()


# ======================================================
#   SZŰRŐK (KOROSZTÁLY, TAKTIKA, TECHNIKA, ERŐNLÉT, HÉT)
# ======================================================
st.sidebar.header("🔍 Szűrés és paraméterek")

age_groups = sorted({ex.get("age_group_code", "") for ex in db if ex.get("age_group_code")})
tacticals = sorted({ex.get("tactical_code", "") for ex in db if ex.get("tactical_code")})
technicals = sorted({ex.get("technical_code", "") for ex in db if ex.get("technical_code")})
physicals = sorted({ex.get("physical_code", "") for ex in db if ex.get("physical_code")})

age_sel = st.sidebar.selectbox("Korosztály", age_groups)
tactical_sel = st.sidebar.selectbox("Taktikai cél", tacticals)
technical_sel = st.sidebar.multiselect("Technikai cél(ok)", technicals)
physical_sel = st.sidebar.multiselect("Erőnléti cél(ok)", physicals)

period_week_option = st.sidebar.selectbox(
    "Periodizációs hét",
    ["Bármelyik", "1. hét", "2. hét", "3. hét", "4. hét"],
    index=0
)
if period_week_option == "Bármelyik":
    period_week_sel = None
else:
    period_week_sel = int(period_week_option[0])  # "1. hét" -> 1

coach_id = st.sidebar.text_input("Edző ID", "coach_001")

generate_btn = st.sidebar.button("🏃 Edzésterv generálása")


# ======================================================
#   SESSION STATE ALAPÉRTELMEK
# ======================================================
if "plan" not in st.session_state:
    st.session_state["plan"] = []
if "exercise_notes" not in st.session_state:
    st.session_state["exercise_notes"] = {}
if "plan_meta" not in st.session_state:
    st.session_state["plan_meta"] = {}
if "coach_notes" not in st.session_state:
    st.session_state["coach_notes"] = ""


# ======================================================
#   SZŰRŐFÜGGVÉNY
# ======================================================
def filter_exercises(db, age, tac, techs, phys, week):
    result = []
    for ex in db:
        if age and ex.get("age_group_code") != age:
            continue
        if tac and ex.get("tactical_code") != tac:
            continue
        if techs:
            if ex.get("technical_code") not in techs:
                continue
        if phys:
            if ex.get("physical_code") not in phys:
                continue
        if week is not None:
            ex_week = ex.get("period_week")
            # Ha a gyakorlatnál meg van adva period_week és nem egyezik, kizárjuk.
            if ex_week is not None and ex_week != week:
                continue
        result.append(ex)
    return result


filtered = filter_exercises(db, age_sel, tactical_sel, technical_sel, physical_sel, period_week_sel)


def pick_best_exercise(exlist):
    if not exlist:
        return None
    return random.choice(exlist)


# ======================================================
#   EDZÉSTERV GENERÁLÁS
# ======================================================
if generate_btn:
    warmup = pick_best_exercise(filtered)
    small_game = pick_best_exercise(filtered)
    large_game = pick_best_exercise(filtered)
    main_game = pick_best_exercise(filtered)

    plan = [
        ("Bemelegítés", warmup),
        ("Cél 1 – kis létszámú játék", small_game),
        ("Cél 2 – nagyobb létszámú játék", large_game),
        ("Cél 3 – fő rész / mérkőzésjáték", main_game),
    ]

    st.session_state["plan"] = plan
    st.session_state["plan_meta"] = {
        "coach_id": coach_id,
        "age_sel": age_sel,
        "tactical_sel": tactical_sel,
        "technical_sel": technical_sel,
        "physical_sel": physical_sel,
        "period_week_sel": period_week_sel,
    }


# ======================================================
#   EDZÉSTERV MEGJELENÍTÉS + MEGJEGYZÉSEK
# ======================================================
plan = st.session_state.get("plan", [])
exercise_notes_state = st.session_state.get("exercise_notes", {})

if plan:
    st.header("📘 Generált edzésterv")

    # Globális edzői megjegyzés az edzéshez
    st.markdown("### 📝 Edző megjegyzései az edzéshez")
    coach_notes = st.text_area(
        "Írd ide az edzés fő fókuszát, csapatra / játékosokra vonatkozó extra instrukciókat:",
        value=st.session_state.get("coach_notes", ""),
        height=120,
        key="coach_notes"
    )

    new_exercise_notes = {}

    for idx, (title, ex) in enumerate(plan, 1):
        if ex is None:
            st.error(f"{title}: Nincs megfelelő gyakorlat a szűrt adatbázisban!")
            continue

        st.markdown("---")
        st.subheader(f"**{idx}. {title}** – {ex.get('title_hu', '')}")

        col1, col2 = st.columns([1, 1.6])

        with col1:
            img_url = ex.get("image_url")
            if img_url:
                try:
                    st.image(img_url, use_column_width=True)
                except Exception:
                    st.info("A kép URL jelenleg nem érhető el.")
            else:
                st.info("Ehhez a gyakorlathoz nincs kép az adatbázisban.")

        with col2:
            st.write(f"**Formátum:** {ex.get('format','')}  |  **Időtartam:** {ex.get('duration_minutes','')} perc")
            st.write(f"**Pályaméret:** {ex.get('pitch_size','')}  |  **Intenzitás:** {ex.get('intensity','')}")

            st.markdown("#### ⚙️ Szervezés (HU)")
            st.write(ex.get("organisation_hu", ""))

            st.markdown("#### ▶️ Menet / leírás (HU)")
            st.write(ex.get("description_hu", ""))

            cps = ex.get("coaching_points_hu", [])
            if cps:
                st.markdown("#### 🎯 Coaching pontok (HU)")
                for c in cps:
                    st.write(f"- {c}")

            vars_ = ex.get("variations_hu", [])
            if vars_:
                st.markdown("#### ♻️ Variációk (HU)")
                for v in vars_:
                    st.write(f"- {v}")

            # Edzői megjegyzés az adott gyakorlathoz
            ex_id = ex.get("id", f"ex_{idx}")
            note_key = f"note_{ex_id}"
            default_note = exercise_notes_state.get(ex_id, "")
            note_text = st.text_area(
                "Edző megjegyzése ehhez a gyakorlathoz:",
                value=default_note,
                key=note_key
            )
            new_exercise_notes[ex_id] = note_text

    # Frissítjük a session_state-ben a gyakorlatszintű megjegyzéseket
    st.session_state["exercise_notes"] = new_exercise_notes

    # ==================================================
    #   ACWR DEMÓ
    # ==================================================
    st.markdown("---")
    st.subheader("📈 ACWR – Terhelés kockázat (demo)")

    # Egyszerű demo adatok – később valós edzésterhelésből jöhet
    demo_loads = [300, 280, 310, 260]

    def calculate_acwr(loads):
        if len(loads) < 4:
            return None
        acute = loads[-1]
        chronic = sum(loads[-4:]) / 4
        if chronic == 0:
            return None
        return round(acute / chronic, 2)

    acwr_val = calculate_acwr(demo_loads)

    if acwr_val is not None:
        if acwr_val < 0.8:
            zone = "Alulterhelés"
        elif acwr_val <= 1.3:
            zone = "Optimális zóna"
        elif acwr_val <= 1.5:
            zone = "Emelkedett kockázat"
        else:
            zone = "Veszélyzóna"

        st.markdown(f"**ACWR:** `{acwr_val}` – **{zone}**")
        st.progress(min(acwr_val / 2, 1.0))
    else:
        st.info("Kevés adat az ACWR becsléshez (legalább 4 terhelési érték kell).")

    # ==================================================
    #   4 HETES PERIODIZÁCIÓ – U12–U15 DEMO
    # ==================================================
    st.markdown("---")
    st.subheader("📅 4 hetes periodizáció – példa (U12–U15)")

    st.caption("Jelenleg a periodizáció ajánlásként jelenik meg; a gyakorlatválasztás a megadott 'Periodizációs hét' alapján szűr (ha az gyakorlatnál is fel van töltve).")

    period_table = pd.DataFrame([
        ["Hét 1", "Alap intenzitás", "Technikai alapok", "Labdakezelés, passzjáték, rondók"],
        ["Hét 2", "Közepes intenzitás", "Taktikai struktúrák", "Labdakihozatal, felépítés, positional play"],
        ["Hét 3", "Magas intenzitás", "Pressing & transition", "Kisjátékok, pressing, átmenetek"],
        ["Hét 4", "Intenzitás csökkentés", "Finomhangolás", "Rövid taktikai blokkok, technikai frissítés"],
    ], columns=["Hét", "Fizikai fókusz", "Technikai fókusz", "Taktikai fókusz"])

    st.table(period_table)

    # ==================================================
    #   PDF EXPORT
    # ==================================================
    st.markdown("---")
    st.subheader("📄 Magyar PDF export")

    FONT_PATH = Path(__file__).parent / "DejaVuSans.ttf"

    class TrainingPDF(FPDF):
        def __init__(self):
            super().__init__()
            self.base_font = "helvetica"
            # Próbáljuk hozzáadni a DejaVu fontot (ha van)
            try:
                if FONT_PATH.exists():
                    self.add_font("DejaVu", "", str(FONT_PATH), uni=True)
                    self.base_font = "DejaVu"
            except Exception:
                self.base_font = "helvetica"

        def header(self):
            try:
                self.set_font(self.base_font, "", 10)
            except Exception:
                self.set_font("helvetica", "", 10)
            self.cell(0, 6, "TrainingBlueprint – Edzésterv", ln=1)
            self.ln(2)

        def footer(self):
            self.set_y(-15)
            try:
                self.set_font(self.base_font, "", 8)
            except Exception:
                self.set_font("helvetica", "", 8)
            self.cell(0, 5, f"Oldal {self.page_no()}", 0, 0, "C")

    def safe_text(text: str) -> str:
        if text is None:
            return ""
        return str(text)

    def create_pdf(plan, meta, coach_notes, exercise_notes):
        pdf = TrainingPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Címoldal
        pdf.add_page()
        pdf.set_font(pdf.base_font, "", 18)
        pdf.cell(0, 10, safe_text("Edzésterv"), ln=1)

        pdf.set_font(pdf.base_font, "", 11)
        pdf.cell(0, 6, safe_text(f"Dátum: {datetime.now().strftime('%Y-%m-%d')}"), ln=1)
        pdf.cell(0, 6, safe_text(f"Edző ID: {meta.get('coach_id','')}"), ln=1)
        pdf.cell(0, 6, safe_text(f"Korosztály: {meta.get('age_sel','')}"), ln=1)
        pdf.cell(0, 6, safe_text(f"Taktikai cél: {meta.get('tactical_sel','')}"), ln=1)

        tech = meta.get("technical_sel", [])
        if tech:
            pdf.cell(0, 6, safe_text(f"Technikai fókusz: {', '.join(tech)}"), ln=1)
        phys = meta.get("physical_sel", [])
        if phys:
            pdf.cell(0, 6, safe_text(f"Erőnléti fókusz: {', '.join(phys)}"), ln=1)
        week = meta.get("period_week_sel", None)
        if week is not None:
            pdf.cell(0, 6, safe_text(f"Periodizációs hét: {week}. hét"), ln=1)
        pdf.ln(4)

        if coach_notes:
            pdf.set_font(pdf.base_font, "", 12)
            pdf.cell(0, 7, safe_text("Edző megjegyzései az edzéshez:"), ln=1)
            pdf.set_font(pdf.base_font, "", 11)
            pdf.multi_cell(0, 6, safe_text(coach_notes))
            pdf.ln(4)

        # Gyakorlatok
        for title, ex in plan:
            if not ex:
                continue

            pdf.add_page()

            pdf.set_font(pdf.base_font, "", 14)
            pdf.cell(0, 8, safe_text(title), ln=1)

            pdf.set_font(pdf.base_font, "", 12)
            pdf.multi_cell(0, 6, safe_text(f"Cím: {ex.get('title_hu','')}"))
            pdf.ln(1)

            # Kép (ha van)
            img_url = ex.get("image_url")
            if img_url:
                try:
                    r = requests.get(img_url, timeout=5)
                    r.raise_for_status()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(r.content)
                        tmp_path = tmp.name
                    pdf.image(tmp_path, w=120)
                    pdf.ln(4)
                except Exception:
                    pass

            # Szervezés
            pdf.set_font(pdf.base_font, "", 12)
            pdf.cell(0, 6, safe_text("Szervezés:"), ln=1)
            pdf.set_font(pdf.base_font, "", 11)
            pdf.multi_cell(0, 6, safe_text(ex.get("organisation_hu", "")))
            pdf.ln(2)

            # Leírás
            pdf.set_font(pdf.base_font, "", 12)
            pdf.cell(0, 6, safe_text("Leírás / menet:"), ln=1)
            pdf.set_font(pdf.base_font, "", 11)
            pdf.multi_cell(0, 6, safe_text(ex.get("description_hu", "")))
            pdf.ln(2)

            # Coaching pontok
            cps = ex.get("coaching_points_hu", [])
            if cps:
                pdf.set_font(pdf.base_font, "", 12)
                pdf.cell(0, 6, safe_text("Coaching pontok:"), ln=1)
                pdf.set_font(pdf.base_font, "", 11)
                for c in cps:
                    pdf.multi_cell(0, 6, safe_text(f" • {c}"))
                pdf.ln(2)

            # Variációk
            vars_ = ex.get("variations_hu", [])
            if vars_:
                pdf.set_font(pdf.base_font, "", 12)
                pdf.cell(0, 6, safe_text("Variációk:"), ln=1)
                pdf.set_font(pdf.base_font, "", 11)
                for v in vars_:
                    pdf.multi_cell(0, 6, safe_text(f" • {v}"))
                pdf.ln(2)

            # Edző megjegyzése ehhez a gyakorlathoz
            ex_id = ex.get("id", "")
            ex_note = exercise_notes.get(ex_id, "")
            if ex_note:
                pdf.set_font(pdf.base_font, "", 12)
                pdf.cell(0, 6, safe_text("Edző megjegyzése ehhez a gyakorlathoz:"), ln=1)
                pdf.set_font(pdf.base_font, "", 11)
                pdf.multi_cell(0, 6, safe_text(ex_note))
                pdf.ln(2)

        pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
        buf = BytesIO()
        buf.write(pdf_bytes)
        buf.seek(0)
        return buf

    plan_meta = st.session_state.get("plan_meta", {})
    exercise_notes = st.session_state.get("exercise_notes", {})
    coach_notes_for_pdf = st.session_state.get("coach_notes", "")

    if any(ex is not None for _, ex in plan):
        pdf_bytes = create_pdf(plan, plan_meta, coach_notes_for_pdf, exercise_notes)
        st.download_button(
            "📥 PDF letöltése",
            data=pdf_bytes,
            file_name="edzesterv.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Nincs elegendő gyakorlat a PDF generálásához.")
else:
    st.info("⬅️ Állítsd be a szűrőket bal oldalt, majd kattints az **Edzésterv generálása** gombra.")
