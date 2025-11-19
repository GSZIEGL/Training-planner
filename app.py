import streamlit as st
import json
import random
import pandas as pd
from io import BytesIO
from datetime import datetime
from fpdf import FPDF
import requests
import tempfile


# ======================================================
#    APP BEÁLLÍTÁS
# ======================================================
st.set_page_config(
    page_title="TrainingBlueprint",
    layout="wide",
    page_icon="⚽"
)

st.title("⚽ **TrainingBlueprint – Profi edzéstervező rendszer**")
st.markdown("""
Ez az alkalmazás professzionális edzésterveket generál:
- több száz gyakorlatból (saját adatbázis vagy feltöltött JSON)
- ACWR (terhelési mutató) becsült megjelenítése
- 4 hetes periodizáció (technikai + taktikai + terhelési fókusz)
- edzői profil (Edző ID alapján)
- PDF export (magyar nyelvű edzésterv)
""")


# ======================================================
#    ADATBÁZIS BETÖLTÉS / FELTÖLTÉS
# ======================================================
st.sidebar.header("📁 Gyakorlat-adatbázis")

db_source = st.sidebar.radio(
    "Válassz adatbázis forrást:",
    ["Beépített példa-adatbázis", "Saját JSON feltöltése"]
)

if db_source == "Beépített példa-adatbázis":
    # MINI DEMO – helyére kerül majd a 300+ gyaxis DB
    demo_db = [
        {
            "id": "rondo_4v2_demo",
            "title_hu": "Rondó 4v2 – labdabirtoklás",
            "age_group_code": "U12-U15",
            "tactical_code": "possession",
            "technical_code": "passing",
            "exercise_type": "rondo",
            "format": "4v2",
            "duration_minutes": 12,
            "intensity": "közepes",
            "pitch_size": "15x15 m",
            "organisation_hu": "4 támadó kívül rombuszban, 2 védő középen.",
            "description_hu": "Gyors passzjáték, labdatartás két nyomás alatt védekező játékos ellen.",
            "coaching_points_hu": [
                "Első érintés kifelé.",
                "Háromszögtávolság tartása.",
                "Gyors döntéshozatal nyomás alatt."
            ],
            "variations_hu": ["Max 2 érintés", "Érintés nélküli átvétel"],
            "image_url": ""  # ide jöhet később AI vagy saját kép
        }
    ]

    db = demo_db
    st.success("Beépített mini adatbázis betöltve.")

else:
    uploaded = st.sidebar.file_uploader("JSON feltöltése", type="json")
    if uploaded:
        db = json.loads(uploaded.read().decode("utf-8"))
        st.success("Saját adatbázis betöltve.")
    else:
        db = []
        st.info("Tölts fel egy JSON fájlt az adatbázishoz.")

if not db:
    st.stop()


# ======================================================
#   SZŰRŐK
# ======================================================
st.sidebar.header("🔍 Szűrés")

age_groups = sorted(list({ex["age_group_code"] for ex in db}))
tacticals = sorted(list({ex["tactical_code"] for ex in db}))
technicals = sorted(list({ex["technical_code"] for ex in db}))

age_sel = st.sidebar.selectbox("Korosztály", age_groups)
tactical_sel = st.sidebar.selectbox("Taktikai cél", tacticals)
technical_sel = st.sidebar.multiselect("Technikai célok", technicals)

coach_id = st.sidebar.text_input("Edző ID", "coach_001")


# ======================================================
#   SZŰRT ADATBÁZIS
# ======================================================
def filter_exercises(db, age, tac, techs):
    out = []
    for ex in db:
        if ex.get("age_group_code") != age:
            continue
        if ex.get("tactical_code") != tac:
            continue
        if techs:
            if ex.get("technical_code") not in techs:
                continue
        out.append(ex)
    return out


filtered = filter_exercises(db, age_sel, tactical_sel, technical_sel)


# ======================================================
#   ACWR SZÁMÍTÁS (egyszerű demo modell)
# ======================================================
def calculate_acwr(session_loads):
    """
    session_loads: pl. [300, 280, 310, 250]  (utolsó 4 edzés/heti load)
    """
    if len(session_loads) < 4:
        return None

    acute = session_loads[-1]
    chronic = sum(session_loads[-4:]) / 4
    if chronic == 0:
        return None

    return round(acute / chronic, 2)


# Dummy edző-történet – később coach_ID-hez valódi adat jön
coach_history_loads = [300, 280, 310, 260]
acwr_val = calculate_acwr(coach_history_loads)


# ======================================================
#  GYAKORLAT VÁLASZTÓ (egyszerű – később okosabb recommender)
# ======================================================
def pick_best_exercise(exlist):
    if not exlist:
        return None
    return random.choice(exlist)


generate = st.sidebar.button("🏃 Edzésterv generálása")


plan = []  # hogy a PDF rész is tudja használni
coach_notes = ""  # alapértelmezés


# ======================================================
#   EDZÉSTERV GENERÁLÁS + MEGJELENÍTÉS
# ======================================================
if generate:
    st.header("📘 Generált edzésterv")

    warmup = pick_best_exercise(filtered)
    small_game = pick_best_exercise(filtered)
    large_game = pick_best_exercise(filtered)
    main_game = pick_best_exercise(filtered)

    plan = [
        ("Bemelegítés", warmup),
        ("Cél 1 – kis játék", small_game),
        ("Cél 2 – nagyobb játék", large_game),
        ("Cél 3 – fő rész", main_game)
    ]

    # Edző saját szövege az edzéshez
    st.markdown("### 📝 Edző megjegyzései az edzéshez")
    coach_notes = st.text_area(
        "Írj ide bármilyen megjegyzést, fókuszpontot, egyéni instrukciót az edzéshez:",
        height=120
    )

    for idx, (title, ex) in enumerate(plan, 1):
        if ex is None:
            st.error(f"{title}: Nincs megfelelő gyakorlat a szűrt adatbázisban!")
            continue

        st.markdown("---")
        st.subheader(f"**{idx}. {title}** – {ex.get('title_hu', '')}")

        col1, col2 = st.columns([1, 1.5])

        with col1:
            img_url = ex.get("image_url")
            if img_url:
                try:
                    st.image(img_url, use_column_width=True)
                except Exception:
                    st.info("A kép URL nem érhető el.")
            else:
                st.info("Ehhez a gyakorlathoz nincs kép az adatbázisban.")

        with col2:
            st.write(f"**Formátum:** {ex.get('format','')}")
            st.write(f"**Időtartam:** {ex.get('duration_minutes','')} perc")
            st.write(f"**Pályaméret:** {ex.get('pitch_size','')}")

            st.markdown("### ⚙️ Szervezés")
            st.write(ex.get("organisation_hu", ""))

            st.markdown("### ▶️ Menet / leírás")
            st.write(ex.get("description_hu", ""))

            cps = ex.get("coaching_points_hu", [])
            if cps:
                st.markdown("### 🎯 Coaching pontok")
                for c in cps:
                    st.write(f"- {c}")

            vars_ = ex.get("variations_hu", [])
            if vars_:
                st.markdown("### ♻️ Variációk")
                for v in vars_:
                    st.write(f"- {v}")

    # ==================================================
    #   ACWR VIZUALIZÁCIÓ
    # ==================================================
    st.markdown("---")
    st.subheader("📈 ACWR – Terhelés kockázat (demo érték)")

    if acwr_val is not None:
        if acwr_val < 0.8:
            zone = "Alulterhelés"
            color = "blue"
        elif acwr_val <= 1.3:
            zone = "Optimális zóna"
            color = "green"
        elif acwr_val <= 1.5:
            zone = "Emelkedett kockázat"
            color = "orange"
        else:
            zone = "Veszélyzóna"
            color = "red"

        st.markdown(f"**ACWR:** `{acwr_val}` – **{zone}**")
        st.progress(min(acwr_val / 2, 1.0))
    else:
        st.info("Kevés adat az ACWR becsléshez (legalább 4 terhelési érték kell).")

    # ==================================================
    #  4 HETES PERIODIZÁCIÓ – U12–U15 (demo)
    # ==================================================
    st.markdown("---")
    st.subheader("📅 U12–U15 – 4 hetes periodizáció (demo)")

    period_table = pd.DataFrame([
        ["Hét 1", "Alap intenzitás", "Technikai alapok", "Kis játék dominancia (rondó)"],
        ["Hét 2", "Közepes intenzitás", "Taktikai struktúrák", "Positional play, build-up"],
        ["Hét 3", "Magas intenzitás", "Pressing & transition", "SSG + mérkőzésjáték"],
        ["Hét 4", "Intenzitás csökkentés", "Finomhangolás", "Rövid taktikai blokkok, technikai frissítés"],
    ], columns=["Hét", "Fizikai fókusz", "Technikai fókusz", "Taktikai fókusz"])

    st.table(period_table)

    # ==================================================
    #  PDF EXPORTER
    # ==================================================
    st.markdown("---")
    st.subheader("📄 Magyar PDF export")

    class TrainingPDF(FPDF):
        def header(self):
            # Fejléc
            self.set_font("DejaVu", "", 10)
            self.cell(0, 6, "TrainingBlueprint – Edzésterv", ln=1)
            self.ln(2)

        def footer(self):
            self.set_y(-15)
            self.set_font("DejaVu", "", 8)
            self.cell(0, 5, f"Oldal {self.page_no()}", 0, 0, "C")

    def create_pdf(plan, coach_id, age_sel, tactical_sel, technical_sel, coach_notes):
        pdf = TrainingPDF()
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.set_auto_page_break(auto=True, margin=15)

        # Címoldal
        pdf.add_page()
        pdf.set_font("DejaVu", "", 18)
        pdf.cell(0, 10, "Edzésterv", ln=1)

        pdf.set_font("DejaVu", "", 11)
        pdf.cell(0, 6, f"Dátum: {datetime.now().strftime('%Y-%m-%d')}", ln=1)
        pdf.cell(0, 6, f"Edző ID: {coach_id}", ln=1)
        pdf.cell(0, 6, f"Korosztály: {age_sel}", ln=1)
        pdf.cell(0, 6, f"Taktikai cél: {tactical_sel}", ln=1)
        if technical_sel:
            pdf.cell(0, 6, f"Technikai fókusz: {', '.join(technical_sel)}", ln=1)
        pdf.ln(4)

        if coach_notes:
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 7, "Edző megjegyzései:", ln=1)
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 6, coach_notes)
            pdf.ln(4)

        # Gyakorlatok
        for title, ex in plan:
            if not ex:
                continue

            pdf.add_page()

            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 8, title, ln=1)

            pdf.set_font("DejaVu", "", 12)
            pdf.multi_cell(0, 6, f"Cím: {ex.get('title_hu','')}")

            # Kép (ha van)
            img_url = ex.get("image_url")
            if img_url:
                try:
                    r = requests.get(img_url, timeout=5)
                    r.raise_for_status()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(r.content)
                        tmp_path = tmp.name
                    # nagy kép felül (kb. 120 mm széles)
                    pdf.ln(2)
                    pdf.image(tmp_path, w=120)
                    pdf.ln(4)
                except Exception:
                    pass

            # Szövegek
            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 6, "Szervezés:", ln=1)
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 6, ex.get("organisation_hu", ""))
            pdf.ln(2)

            pdf.set_font("DejaVu", "B", 12)
            pdf.cell(0, 6, "Leírás / menet:", ln=1)
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 6, ex.get("description_hu", ""))
            pdf.ln(2)

            cps = ex.get("coaching_points_hu", [])
            if cps:
                pdf.set_font("DejaVu", "B", 12)
                pdf.cell(0, 6, "Coaching pontok:", ln=1)
                pdf.set_font("DejaVu", "", 11)
                for c in cps:
                    pdf.multi_cell(0, 6, f" • {c}")
                pdf.ln(2)

            vars_ = ex.get("variations_hu", [])
            if vars_:
                pdf.set_font("DejaVu", "B", 12)
                pdf.cell(0, 6, "Variációk:", ln=1)
                pdf.set_font("DejaVu", "", 11)
                for v in vars_:
                    pdf.multi_cell(0, 6, f" • {v}")
                pdf.ln(2)

        # PDF visszaadása BytesIO-ként
        pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
        buffer = BytesIO()
        buffer.write(pdf_bytes)
        buffer.seek(0)
        return buffer

    # PDF letöltő gomb (nincs külön "button", egyből letölthető)
    if plan and any(ex is not None for _, ex in plan):
        pdf_bytes = create_pdf(plan, coach_id, age_sel, tactical_sel, technical_sel, coach_notes)
        st.download_button(
            "📥 PDF letöltése",
            data=pdf_bytes,
            file_name="edzesterv.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Nincs elegendő gyakorlat a PDF generálásához.")
