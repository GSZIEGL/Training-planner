# ============================================================
# TRAINING BLUEPRINT – TELJES STREAMLIT APP
# Gyakorlat-generátor + PDF export + periodizáció + coach notes
# ============================================================

import streamlit as st
from fpdf import FPDF
import base64
import random
import os

# ------------------------------------------------------------
# SAMPLE GYAKORLATADATOK (amíg nem jön a nagy adatbázis)
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
        "description_hu": "A külső játékosok 1-2 érintéssel játszanak, cél a gyors döntéshozatal.",
        "coaching_points_hu": [
            "Testtartás a labda átvétele előtt",
            "Gyors irányváltás",
            "Letámadás szögei"
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
        "description_hu": "A gyakorlat gyors irányváltást és céltudatos befejezést fejleszt.",
        "coaching_points_hu": [
            "Határozott első érintés",
            "Csel tempóváltással",
            "Gyors befejezés"
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
        "organisation_hu": "A védekező négyes pressinget alkalmaz, a támadók építkeznek.",
        "description_hu": "A cél a 3. ember bevonása és pressing vonalak megtörése.",
        "coaching_points_hu": [
            "Pozíciók megtartása",
            "Gyors labdajáratás",
            "Passzok közötti szögek"
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
# PDF GENERÁTOR (unicode, stabil)
# ------------------------------------------------------------
class PDF(FPDF):
    pass


def generate_pdf(plan, meta, coach_notes, exercise_notes):
    pdf = PDF(format="A4")
    pdf.add_page()

    # ----- FONT -----
    if os.path.exists("DejaVuSans.ttf"):
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVu", size=12)
    else:
        pdf.set_font("Arial", size=12)

    # ----- CÍM -----
    pdf.set_font("DejaVu", "B", 20)
    pdf.multi_cell(0, 10, f"Training Blueprint – Edzésterv")
    pdf.ln(3)

    # ----- META -----
    pdf.set_font("DejaVu", size=12)
    pdf.multi_cell(0, 7, f"Korosztály: {meta['age_group']}")
    pdf.multi_cell(0, 7, f"Taktikai cél: {meta['tactical']}")
    pdf.multi_cell(0, 7, f"Technikai cél: {meta['technical']}")
    pdf.multi_cell(0, 7, f"Erőnléti cél: {meta['fitness']}")
    pdf.multi_cell(0, 7, f"Periodizációs hét: {meta['period']}")
    pdf.multi_cell(0, 7, f"Edző azonosító: {meta['coach']}")

    pdf.ln(4)

    # ----- EDZŐI MEGJEGYZÉS -----
    if coach_notes.strip():
        pdf.set_font("DejaVu", "B", 14)
        pdf.multi_cell(0, 8, "Edzői megjegyzés:")
        pdf.set_font("DejaVu", size=12)
        pdf.multi_cell(0, 6, coach_notes)
        pdf.ln(4)

    # ----- GYAKORLATOK -----
    for idx, ex in enumerate(plan, start=1):
        pdf.set_font("DejaVu", "B", 14)
        pdf.multi_cell(0, 8, f"{idx}. {ex['title_hu']}")
        pdf.set_font("DejaVu", size=11)
        pdf.multi_cell(0, 6, f"Formátum: {ex['format']} | Pályaméret: {ex['pitch_size']} | Időtartam: {ex['duration']} perc")
        pdf.ln(2)

        pdf.multi_cell(0, 6, "Szervezés:")
        pdf.multi_cell(0, 6, ex["organisation_hu"])
        pdf.ln(1)

        pdf.multi_cell(0, 6, "Leírás:")
        pdf.multi_cell(0, 6, ex["description_hu"])
        pdf.ln(1)

        pdf.multi_cell(0, 6, "Coaching pontok:")
        for cp in ex["coaching_points_hu"]:
            pdf.multi_cell(0, 6, f"• {cp}")

        # ----- Egyedi edzői jegyzet adott gyakorlathoz -----
        if exercise_notes.get(ex["id"], "").strip():
            pdf.ln(2)
            pdf.multi_cell(0, 6, "Edző jegyzete ehhez a gyakorlathoz:")
            pdf.multi_cell(0, 6, exercise_notes[ex["id"]])

        pdf.ln(4)

    return pdf.output(dest="S").encode("utf-8")



# ------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------
st.set_page_config(page_title="Training Blueprint", layout="wide")
st.title("⚽ Training Blueprint – Edzésterv generátor")

st.write("Töltsd ki a szűrőket, majd generálj egy teljes edzéstervet.")

# Szűrők
age = st.selectbox("Korosztály", ["u7-u11", "u12-u15", "u16-u19"])
tact = st.selectbox("Taktikai cél", ["labdabirtoklás", "1v1", "labdakihozatal"])
tech = st.selectbox("Technikai cél", ["passzjáték", "cselezés", "kombináció"])
fit = st.selectbox("Erőnléti cél", ["alacsony terhelés", "közepes terhelés", "magas terhelés"])
period = st.selectbox("Periodizációs hét (1–4)", [1, 2, 3, 4])
coach_id = st.text_input("Edző ID", "coach_1")

st.subheader("Edzői megjegyzés az egész edzéshez")
coach_notes = st.text_area("Ide írhatod a teljes edzéshez kapcsolódó gondolataidat…", height=120)

st.markdown("---")


# ------------------------------------------------------------
# GYAKORLATOK SZŰRÉSE
# ------------------------------------------------------------
def filter_exercises():
    result = []
    for ex in sample_exercises:
        cat = ex["category"]
        if cat["age_group"] != age:
            continue
        if cat["tactical"] != tact:
            continue
        if cat["technical"] != tech:
            continue
        if cat["fitness"] != fit:
            continue
        result.append(ex)
    return result


# ------------------------------------------------------------
# EDZÉSTERV GENERÁLÁSA
# ------------------------------------------------------------
if st.button("Edzésterv generálása"):
    possible = filter_exercises()

    if not possible:
        st.error("Nincs olyan gyakorlat, amely megfelel a szűrőknek.")
        st.stop()

    # Random 2–3 gyakorlat
    plan = random.sample(possible, k=min(3, len(possible)))

    st.success("Edzésterv elkészült!")

    st.header("📘 Edzésterv")

    exercise_notes = {}

    for ex in plan:
        st.subheader(ex["title_hu"])
        st.write(f"**Formátum:** {ex['format']} | **Időtartam:** {ex['duration']} perc")
        st.write(f"**Szervezés:** {ex['organisation_hu']}")
        st.write(f"**Leírás:** {ex['description_hu']}")

        st.write("**Coaching pontok:**")
        for c in ex["coaching_points_hu"]:
            st.write("• " + c)

        txt = st.text_area(f"Edző saját jegyzete ehhez a gyakorlathoz ({ex['id']}):", height=100)
        exercise_notes[ex["id"]] = txt

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
        }

        pdf_bytes = generate_pdf(plan, meta, coach_notes, exercise_notes)

        st.download_button(
            "📥 PDF letöltése",
            data=pdf_bytes,
            file_name="edzesterv.pdf",
            mime="application/pdf"
        )

