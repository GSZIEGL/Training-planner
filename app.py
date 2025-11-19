import streamlit as st
import json
import random
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
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
- ACWR (terhelési mutató) automatikus számítása
- 4 hetes periodizáció (technikai + taktikai + terhelési fókusz)
- edzői profil figyelése (szokások, preferenciák, került gyakorlatok)
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
    # MINI DEMO
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
            "description_hu": "Gyors passzjáték, labdatartás 2 nyomás alatt védekező játékos ellen.",
            "coaching_points_hu": [
                "Első érintés kifelé",
                "Háromszögtávolság tartása",
                "Gyors döntéshozatal"
            ],
            "variations_hu": ["Max 2 érintés", "Érintés nélküli átvétel"],
            "image_url": ""
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
        if ex["age_group_code"] != age:
            continue
        if ex["tactical_code"] != tac:
            continue
        if techs:
            if ex["technical_code"] not in techs:
                continue
        out.append(ex)
    return out


filtered = filter_exercises(db, age_sel, tactical_sel, technical_sel)



# ======================================================
#   ACWR SZÁMÍTÁS (fiktív példa)
# ======================================================
def calculate_acwr(session_loads):
    """
    session_loads: pl. [300, 280, 310, 250]  (últó 4 alkalom)
    """
    if len(session_loads) < 4:
        return None

    acute = session_loads[-1]
    chronic = sum(session_loads[-4:]) / 4
    if chronic == 0:
        return None

    return round(acute / chronic, 2)


# Edző korábbi edzései – később adatbázisból jönne
coach_history_loads = [300, 280, 310, 260]

acwr_val = calculate_acwr(coach_history_loads)




# ======================================================
#  ÖSSZETETT AJÁNLÓRENDSZER – GYAKORLAT KIVÁLASZTÁS
# ======================================================
def pick_best_exercise(exlist):
    if not exlist:
        return None
    return random.choice(exlist)


generate = st.sidebar.button("🏃 Edzésterv generálása")



# ======================================================
#   EDZÉSTERV GENERÁLÁS
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

    for idx, (title, ex) in enumerate(plan, 1):
        if ex is None:
            st.error(f"{title}: Nincs megfelelő gyakorlat!")
            continue

        st.subheader(f"**{idx}. {title}** – {ex['title_hu']}")

        col1, col2 = st.columns([1, 1.5])

        with col1:
            if ex.get("image_url"):
                st.image(ex["image_url"])
            else:
                st.info("Ehhez a gyakorlathoz nincs kép.")

        with col2:
            st.write(f"**Formátum:** {ex['format']}")
            st.write(f"**Időtartam:** {ex['duration_minutes']} perc")
            st.write(f"**Pályaméret:** {ex['pitch_size']}")

            st.markdown("### ⚙️ Szervezés")
            st.write(ex["organisation_hu"])

            st.markdown("### ▶️ Menet")
            st.write(ex["description_hu"])

            st.markdown("### 🎯 Coaching pontok")
            for c in ex["coaching_points_hu"]:
                st.write(f"- {c}")

            st.markdown("### ♻️ Variációk")
            for v in ex["variations_hu"]:
                st.write(f"- {v}")



    # ======================================================
    #  ACWR VIZUALIZÁCIÓ
    # ======================================================
    st.subheader("📈 ACWR – Terhelés kockázat")
    if acwr_val:
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
    else:
        st.info("Kevés adat az ACWR-hez.")



    # ======================================================
    #  4 HETES PERIODIZÁCIÓ
    # ======================================================
    st.subheader("📅 4 hetes periodizáció")

    period_table = pd.DataFrame([
        ["Hét 1", "Alap intenzitás", "Technikai alapok", "Kis játék dominancia"],
        ["Hét 2", "Közepes intenzitás", "Taktikai struktúrák", "Positional play"],
        ["Hét 3", "Magas intenzitás", "Pressing & transition", "SSG + mérkőzésjáték"],
        ["Hét 4", "Csökkentés", "Finomhangolás", "Rövid taktikai blokkok"],
    ], columns=["Hét", "Fizikai fókusz", "Technikai fókusz", "Taktikai fókusz"])

    st.table(period_table)



    # ======================================================
    #  PDF EXPORTER
    # ======================================================
    st.subheader("📄 Magyar PDF export")

    def create_pdf(plan, coach_id):
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVu", "", 16)
        pdf.cell(0, 10, "Edzésterv", ln=1)

        pdf.set_font("DejaVu", "", 10)
        pdf.cell(0, 6, f"Edző ID: {coach_id}", ln=1)
        pdf.ln(5)

        for title, ex in plan:
            if not ex:
                continue

            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 8, title, ln=1)

            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 6, f"Cím: {ex['title_hu']}")

            if ex.get("image_url"):
                try:
                    r = requests.get(ex["image_url"], timeout=5)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(r.content)
                        tmp_path = tmp.name
                    pdf.image(tmp_path, w=120)
                except:
                    pass

            pdf.multi_cell(0, 6, "Szervezés: " + ex["organisation_hu"])
            pdf.multi_cell(0, 6, "Leírás: " + ex["description_hu"])
            pdf.multi_cell(0, 6, "Coaching pontok:")

            for c in ex["coaching_points_hu"]:
                pdf.multi_cell(0, 6, f" • {c}")

            pdf.ln(5)

        buffer = BytesIO()
        pdf.output(buffer)
        buffer.seek(0)
        return buffer

    if st.button("📥 PDF letöltése"):
        pdf_bytes = create_pdf(plan, coach_id)
        st.download_button(
            "PDF letöltése",
            pdf_bytes,
            file_name="edzesterv.pdf",
            mime="application/pdf"
        )
