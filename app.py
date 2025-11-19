# ============================================================
# TRAINING BLUEPRINT – STREAMLIT APP (v2 – mindig ad edzéstervet)
# ============================================================

import streamlit as st
from fpdf import FPDF
import random
import os

# ------------------------------------------------------------
# 1. MINTA GYAKORLATADATOK (amíg nincs nagy adatbázis)
# ------------------------------------------------------------
sample_exercises = [
    {
        "id": "ex1",
        "title_hu": "5v2 rondó – labdabirtoklás",
        "format": "5v2",
        "exercise_type": "rondó",
        "pitch_size": "12×12 m",
        "duration": 12,
        "organisation_hu": "A kék csapat 5 fővel tartja a labdát, a piros 2 játékos letámad.",
        "description_hu": "A külső játékosok 1-2 érintéssel játszanak, cél a gyors döntéshozatal és labdabirtoklás.",
        "coaching_points_hu": [
            "Testtartás a labda átvétele előtt",
            "Gyors irányváltás a labdától felfelé",
            "Letámadás szöge és sebessége"
        ],
        "category": {
            "age_group": "u12-u15",
            "tactical": "labdabirtoklás",
            "technical": "passzjáték",
            "fitness": "alacsony terhelés"
        }
    },
    {
        "id": "ex2",
        "title_hu": "1v1 csel + befejezés",
        "format": "1v1",
        "exercise_type": "technikás",
        "pitch_size": "15×10 m",
        "duration": 10,
        "organisation_hu": "Piros támad, kék védekezik. A támadó csel után kapura tör.",
        "description_hu": "A gyakorlat gyors irányváltást, cseleket és céltudatos befejezést fejleszt.",
        "coaching_points_hu": [
            "Határozott első érintés előre",
            "Csel tempóváltással, ne oldalra",
            "Gyors, pontos befejezés a kapu felé"
        ],
        "category": {
            "age_group": "u7-u11",
            "tactical": "1v1",
            "technical": "cselezés",
            "fitness": "közepes terhelés"
        }
    },
    {
        "id": "ex3",
        "title_hu": "6v4 labdakihozatal – pressing ellen",
        "format": "6v4",
        "exercise_type": "positional",
        "pitch_size": "40×30 m",
        "duration": 15,
        "organisation_hu": "A védekező négyes pressinget alkalmaz, a támadók építkeznek hátulról.",
        "description_hu": "A cél a 3. ember bevonása, pressing vonalak megtörése és labdakihozatal biztonságosan.",
        "coaching_points_hu": [
            "Pozíciók megtartása, szélesség és mélység",
            "Gyors labdajáratás kevés érintéssel",
            "Passzok szöge és a harmadik ember keresése"
        ],
        "category": {
            "age_group": "u16-u19",
            "tactical": "labdakihozatal",
            "technical": "kombináció",
            "fitness": "alacsony terhelés"
        }
    }
]


# ------------------------------------------------------------
# 2. PDF GENERÁTOR
# ------------------------------------------------------------
class PDF(FPDF):
    pass


def generate_pdf(plan, meta, coach_notes, exercise_notes):
    pdf = PDF(format="A4")
    pdf.add_page()

    # Font
    if os.path.exists("DejaVuSans.ttf"):
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVu", size=12)
        base_font = "DejaVu"
    else:
        pdf.set_font("Arial", size=12)
        base_font = "Arial"

    # Cím
    pdf.set_font(base_font, "B", 20)
    pdf.multi_cell(0, 10, "Training Blueprint – Edzésterv")
    pdf.ln(3)

    # Meta
    pdf.set_font(base_font, "", 12)
    pdf.multi_cell(0, 7, f"Korosztály: {meta['age_group']}")
    pdf.multi_cell(0, 7, f"Taktikai cél: {meta['tactical']}")
    pdf.multi_cell(0, 7, f"Technikai cél: {meta['technical']}")
    pdf.multi_cell(0, 7, f"Erőnléti cél: {meta['fitness']}")
    pdf.multi_cell(0, 7, f"Periodizációs hét: {meta['period']}")
    pdf.multi_cell(0, 7, f"Edző azonosító: {meta['coach']}")

    if meta.get("filter_info"):
        pdf.multi_cell(0, 7, f"Szűrés módja: {meta['filter_info']}")

    pdf.ln(4)

    # Edzői jegyzet
    if coach_notes.strip():
        pdf.set_font(base_font, "B", 14)
        pdf.multi_cell(0, 8, "Edzői megjegyzés:")
        pdf.set_font(base_font, "", 12)
        pdf.multi_cell(0, 6, coach_notes)
        pdf.ln(4)

    # Gyakorlatok
    for idx, ex in enumerate(plan, start=1):
        pdf.set_font(base_font, "B", 14)
        pdf.multi_cell(0, 8, f"{idx}. {ex['title_hu']}")
        pdf.set_font(base_font, "", 11)
        pdf.multi_cell(
            0,
            6,
            f"Formátum: {ex['format']} | Pályaméret: {ex['pitch_size']} | Időtartam: {ex['duration']} perc",
        )
        pdf.ln(1)

        pdf.multi_cell(0, 6, "Szervezés:")
        pdf.multi_cell(0, 6, ex["organisation_hu"])
        pdf.ln(1)

        pdf.multi_cell(0, 6, "Leírás:")
        pdf.multi_cell(0, 6, ex["description_hu"])
        pdf.ln(1)

        pdf.multi_cell(0, 6, "Coaching pontok:")
        for cp in ex["coaching_points_hu"]:
            pdf.multi_cell(0, 6, f"• {cp}")

        # Egyedi jegyzet ehhez a gyakorlathoz
        note = exercise_notes.get(ex["id"], "").strip()
        if note:
            pdf.ln(2)
            pdf.multi_cell(0, 6, "Edző jegyzete ehhez a gyakorlathoz:")
            pdf.multi_cell(0, 6, note)

        pdf.ln(4)

    # FPDF2 -> str, ezért latin1-re kódolunk
    return pdf.output(dest="S").encode("latin-1", "ignore")


# ------------------------------------------------------------
# 3. STREAMLIT UI
# ------------------------------------------------------------
st.set_page_config(page_title="Training Blueprint", layout="wide")
st.title("⚽ Training Blueprint – Edzésterv generátor")

st.write("Töltsd ki a szűrőket, majd generálj egy edzéstervet. Ha nincs pontos egyezés, a rendszer fokozatosan lazítja a szűrést, hogy mindig kapj javaslatot.")

# Szűrők
age = st.selectbox("Korosztály", ["u7-u11", "u12-u15", "u16-u19"])
tact = st.selectbox("Taktikai cél", ["labdabirtoklás", "1v1", "labdakihozatal"])
tech = st.selectbox("Technikai cél", ["passzjáték", "cselezés", "kombináció"])
fit = st.selectbox("Erőnléti cél", ["alacsony terhelés", "közepes terhelés", "magas terhelés"])
period = st.selectbox("Periodizációs hét (1–4)", [1, 2, 3, 4])
coach_id = st.text_input("Edző ID", "coach_1")

st.subheader("Edzői megjegyzés az egész edzéshez")
coach_notes = st.text_area(
    "Ide írhatod a teljes edzéshez kapcsolódó gondolataidat…", height=120
)

st.markdown("---")


# ------------------------------------------------------------
# 4. GYAKORLATOK SZŰRÉSE – FOKOZATOS LAZÍTÁS
# ------------------------------------------------------------
def smart_filter(db, age, tact, tech, fit):
    """
    Mindig visszaad legalább 1 gyakorlatot.
    Fokozatosan lazítjuk a szűrést, és visszaadunk egy magyarázó szöveget is.
    """
    def match(ex, age_ok=True, tact_ok=True, tech_ok=True, fit_ok=True):
        c = ex["category"]
        if age_ok and c["age_group"] != age:
            return False
        if tact_ok and c["tactical"] != tact:
            return False
        if tech_ok and c["technical"] != tech:
            return False
        if fit_ok and c["fitness"] != fit:
            return False
        return True

    # 1. Teljes egyezés
    lvl1 = [ex for ex in db if match(ex, True, True, True, True)]
    if lvl1:
        return lvl1, "Teljes egyezés a szűrőkkel."

    # 2. Fitness elengedése
    lvl2 = [ex for ex in db if match(ex, True, True, True, False)]
    if lvl2:
        return lvl2, "Erőnléti cél figyelmen kívül hagyva."

    # 3. Technikai elengedése
    lvl3 = [ex for ex in db if match(ex, True, True, False, False)]
    if lvl3:
        return lvl3, "Csak korosztály + taktikai cél alapján."

    # 4. Csak taktikai cél
    lvl4 = [ex for ex in db if match(ex, False, True, False, False)]
    if lvl4:
        return lvl4, "Csak taktikai cél alapján."

    # 5. Végső fallback: teljes adatbázis
    if db:
        return db, "Nem találtam egyezést, ezért a teljes adatbázisból választottam."
    else:
        return [], "Az adatbázis üres."


# ------------------------------------------------------------
# 5. EDZÉSTERV GENERÁLÁSA
# ------------------------------------------------------------
if st.button("Edzésterv generálása"):
    candidates, filter_info = smart_filter(sample_exercises, age, tact, tech, fit)

    if not candidates:
        st.error("Az adatbázis teljesen üres – ide majd a saját JSON-öd kerül.")
        st.stop()

    # Random 2–3 gyakorlat
    plan = random.sample(candidates, k=min(3, len(candidates)))

    st.success("Edzésterv elkészült!")
    st.info(f"Szűrési logika: {filter_info}")

    st.header("📘 Edzésterv")

    exercise_notes = {}

    for ex in plan:
        st.subheader(ex["title_hu"])
        st.write(f"**Formátum:** {ex['format']} | **Időtartam:** {ex['duration']} perc")
        st.write(f"**Pályaméret:** {ex['pitch_size']}")
        st.write(f"**Szervezés:** {ex['organisation_hu']}")
        st.write(f"**Leírás:** {ex['description_hu']}")

        st.write("**Coaching pontok:**")
        for c in ex["coaching_points_hu"]:
            st.write("• " + c)

        note = st.text_area(
            f"Edző saját jegyzete ehhez a gyakorlathoz ({ex['id']}):",
            height=80,
        )
        exercise_notes[ex["id"]] = note

        st.markdown("---")

    # PDF export
    st.subheader("📄 Magyar PDF export")

    if st.button("PDF generálása"):
        meta = {
            "age_group": age,
            "tactical": tact,
            "technical": tech,
            "fitness": fit,
            "period": period,
            "coach": coach_id,
            "filter_info": filter_info,
        }

        pdf_bytes = generate_pdf(plan, meta, coach_notes, exercise_notes)

        st.download_button(
            "📥 PDF letöltése",
            data=pdf_bytes,
            file_name="edzesterv.pdf",
            mime="application/pdf",
        )
