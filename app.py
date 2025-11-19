import random
from io import BytesIO
from typing import List, Dict

import streamlit as st
from fpdf import FPDF

# ======================================================
# 1. MINTA ADATBÁZIS – BEÉGETETT GYAKORLATOK
# (később ezt lecseréljük a saját JSON-odra)
# ======================================================

SAMPLE_EXERCISES: List[Dict] = [
    {
        "id": "u7_u11_rondo_4v1",
        "age_group_code": "U7-U11",
        "tactical_code": "labdabirtoklas",
        "technical_code": "rovid_passz",
        "physical_goal": "alacsony",
        "period_week": 1,
        "title_hu": "Labdabirtoklás – 4v1 rondó (U7–U11)",
        "format": "4v1",
        "exercise_type": "rondó",
        "pitch_size": "12×12 m",
        "duration_minutes": 12,
        "intensity": "alacsony",
        "organisation_hu": "4 támadó játékos egy négyzet sarkaiban, 1 védő középen.",
        "description_hu": "A támadók 2 érintővel játszanak, cél a labda megtartása. A védő labdaszerzés után a hibázó támadó megy középre.",
        "coaching_points_hu": [
            "Folyamatos mozgás a labda körül.",
            "Első érintés a terület felé.",
            "Kommunikáció: ki kér labdát, ki támogat."
        ],
        "variations_hu": [
            "Max. 1 érintés, ha a gyerekek már magabiztosak.",
            "Két védő (4v2), nagyobb kihívás."
        ],
        "image_url": ""  # most nem használunk külső képet
    },
    {
        "id": "u7_u11_1v1_futas_kapu",
        "age_group_code": "U7-U11",
        "tactical_code": "befejezes",
        "technical_code": "vezetes_loves",
        "physical_goal": "kozepes",
        "period_week": 1,
        "title_hu": "1v1 futás kapura (U7–U11)",
        "format": "1v1",
        "exercise_type": "small-sided game",
        "pitch_size": "20×15 m",
        "duration_minutes": 15,
        "intensity": "közepes",
        "organisation_hu": "Két sor a félpályán, előttük egy-egy kapu kapussal.",
        "description_hu": "Edző indítja a labdát középre. A két támadó sprintel, aki előbb ér oda, támad, a másik védekezik. Támadás után gyors visszarendeződés.",
        "coaching_points_hu": [
            "Robbanékony indulás, első 3–4 lépés max sebesség.",
            "Támadásnál határozott befejezés, nem sodródni szögbe.",
            "Védekezésnél testhelyzet: féloldalas, irányítás kifelé."
        ],
        "variations_hu": [
            "Indulás fekvőtámasz-helyzetből, ülésből, háttal a kapunak.",
            "2v1 helyzet kialakítása a beindulások után."
        ],
        "image_url": ""
    },
    {
        "id": "u12_u15_build_up_6v4",
        "age_group_code": "U12-U15",
        "tactical_code": "labdakihozatal",
        "technical_code": "rovid_passz",
        "physical_goal": "kozepes",
        "period_week": 2,
        "title_hu": "Labdakihozatal – 6v4 a középső zónában (U12–U15)",
        "format": "6v4",
        "exercise_type": "positional game",
        "pitch_size": "40×30 m",
        "duration_minutes": 18,
        "intensity": "közepes",
        "organisation_hu": "3 zónára osztott pálya, hátul 2 védő + kapus, középen 3 középpályás, elöl 1 csatár. 4 védő próbálja megakadályozni a labdakihozatalt.",
        "description_hu": "A cél, hogy felépítsük a támadást hátulról, és átjussunk a középső zónán keresztül az utolsó harmadba. Minden sikeres átjuttatott labda pontot ér.",
        "coaching_points_hu": [
            "Szélesség és mélység tartása a labdakihozatalnál.",
            "Kapus bevonása harmadik emberként.",
            "Testhelyzet: nyitott, hogy előre is lásson a játékos."
        ],
        "variations_hu": [
            "Érintésszám-korlát a középpályán (pl. max. 2 érintés).",
            "Az ellenfél magasabb letámadást alkalmazhat."
        ],
        "image_url": ""
    },
    {
        "id": "u12_u15_press_5v5",
        "age_group_code": "U12-U15",
        "tactical_code": "presszing",
        "technical_code": "1v1_vedo",
        "physical_goal": "magas",
        "period_week": 3,
        "title_hu": "Presszing – 5v5 + kapusok (U12–U15)",
        "format": "5v5",
        "exercise_type": "game",
        "pitch_size": "40×30 m",
        "duration_minutes": 20,
        "intensity": "magas",
        "organisation_hu": "Két csapat 5–5 mezőnyjátékossal és kapusokkal félpályán.",
        "description_hu": "Cél a gyors labdaszerzés az ellenfél térfelén. Minden labdaszerzésből 10 másodpercen belüli lövés plusz pontot ér.",
        "coaching_points_hu": [
            "Presszing-indító jel: rossz átadás, háttal kapunak álló játékos.",
            "Távolság a játékosok között – ne legyenek lyukak a csapatban.",
            "Utópresszing: elvesztett labda után azonnali visszatámadás."
        ],
        "variations_hu": [
            "Korlátozott visszapassz a kapusnak.",
            "Az egyik csapat emberhátrányban játszik (5v4)."
        ],
        "image_url": ""
    },
    {
        "id": "u16_u19_finishing_box",
        "age_group_code": "U16-U19",
        "tactical_code": "befejezes",
        "technical_code": "loves_fej",
        "physical_goal": "magas",
        "period_week": 4,
        "title_hu": "Befejezés a tizenhatos körül – kombinációs játék (U16–U19)",
        "format": "3v2+GK",
        "exercise_type": "finishing",
        "pitch_size": "30×25 m",
        "duration_minutes": 18,
        "intensity": "magas",
        "organisation_hu": "Három támadó a tizenhatos előtt, két védő és kapus. Labda mindig a 10-esnél indul.",
        "description_hu": "Kombináció után beindulás a védők mögé, egyérintős befejezés. Váltott szerepek, hogy mindenki legyen befejező és előkészítő is.",
        "coaching_points_hu": [
            "Időzített beindulás, ne legyen les.",
            "Gyors döntés lövésnél, kevés érintés.",
            "Támadók háromszög-távolságban helyezkedjenek."
        ],
        "variations_hu": [
            "Plusz védő érkezik hátulról késve.",
            "Keresztlabda beadással kombinálva a szélről."
        ],
        "image_url": ""
    }
]

# ======================================================
# 2. SEGÉDFÜGGVÉNYEK – SZŰRÉS, STAGE SZCÓR
# ======================================================

def filter_exercises(
    db: List[Dict],
    age_group: str,
    tactical: str,
    technical: str,
    physical_goal: str,
    period_week: int,
) -> List[Dict]:
    """Egyszerű szűrés – ha valamelyik mező 'Mind', azt kihagyjuk a szűrésből."""
    result = []
    for ex in db:
        if age_group != "Mind" and ex["age_group_code"] != age_group:
            continue
        if tactical != "Mind" and ex["tactical_code"] != tactical:
            continue
        if technical != "Mind" and ex["technical_code"] != technical:
            continue
        if physical_goal != "Mind" and ex["physical_goal"] != physical_goal:
            continue
        if period_week != 0 and ex["period_week"] != period_week:
            continue
        result.append(ex)
    return result


def score_for_stage(ex: Dict, stage: str) -> int:
    """Nagyon egyszerű pontozás, hogy eltérő blokkokba más-más típusú feladat kerüljön."""
    score = 0
    fmt = ex.get("format", "")
    ex_type = ex.get("exercise_type", "").lower()
    intensity = ex.get("intensity", "").lower()

    if stage == "warmup":
        if "v1" in fmt or ex_type in ["rondó", "rondo"]:
            score += 3
        if intensity in ["alacsony", "alacsony–közepes"]:
            score += 2

    elif stage == "small":
        if "v1" in fmt or "v2" in fmt:
            score += 2
        if ex_type in ["small-sided game", "rondó", "rondo"]:
            score += 2

    elif stage == "large":
        if "v4" in fmt or "v5" in fmt or "v6" in fmt:
            score += 3
        if ex_type in ["positional game"]:
            score += 2

    elif stage == "main":
        if ex_type in ["game", "finishing"]:
            score += 3
        if intensity in ["magas"]:
            score += 2

    return score


def pick_for_stage(candidates: List[Dict], used_ids: set, stage: str):
    scored = []
    for ex in candidates:
        if ex["id"] in used_ids:
            continue
        s = score_for_stage(ex, stage)
        if s > 0:
            scored.append((s, ex))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score = scored[0][0]
    best = [ex for s, ex in scored if s == top_score]
    return random.choice(best)


# ======================================================
# 3. PDF – SEGÉDFÜGGVÉNYEK
# ======================================================

def safe_wrap(text: str, max_len: int = 110) -> str:
    """Ne legyen túl hosszú, egyben lévő sor (FPDF hibát dobna)."""
    if not text:
        return ""
    words = text.split()
    lines = []
    current = []
    length = 0
    for w in words:
        if length + len(w) + 1 > max_len:
            lines.append(" ".join(current))
            current = [w]
            length = len(w)
        else:
            current.append(w)
            length += len(w) + 1
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


class TrainingPDF(FPDF):
    def header(self):
        self.set_font("DejaVu", "", 10)
        self.cell(0, 6, "chatbotfootball – Training Blueprint", 0, 0, "L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "", 8)
        self.cell(0, 5, f"Oldal {self.page_no()}", 0, 0, "C")


def create_pdf(plan, plan_meta, coach_notes_for_pdf, exercise_notes_dict) -> bytes:
    pdf = TrainingPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    # Unicode betűtípus
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", "", 12)

    # ----- Címlap / összefoglaló -----
    pdf.add_page()
    pdf.set_font("DejaVu", "", 20)
    pdf.cell(0, 10, "Edzésterv", ln=1)

    pdf.set_font("DejaVu", "", 11)
    pdf.ln(4)
    pdf.multi_cell(0, 6, safe_wrap(
        f"Korosztály: {plan_meta['age_group']} | "
        f"Taktikai cél: {plan_meta['tactical']} | "
        f"Technikai fókusz: {plan_meta['technical']} | "
        f"Erőnléti cél: {plan_meta['physical']} | "
        f"Periodizációs hét: {plan_meta['period_week']}."
    ))
    pdf.ln(3)
    pdf.multi_cell(0, 6, safe_wrap(f"Edző ID: {plan_meta['coach_id']}"))

    if coach_notes_for_pdf:
        pdf.ln(4)
        pdf.set_font("DejaVu", "B", 11)
        pdf.cell(0, 7, "Edzői megjegyzés az edzéshez:", ln=1)
        pdf.set_font("DejaVu", "", 11)
        pdf.multi_cell(0, 6, safe_wrap(coach_notes_for_pdf))

    # ----- Blokkok -----
    for idx, (stage_title, ex) in enumerate(plan, start=1):
        pdf.add_page()
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
        pdf.set_font("DejaVu", "", 12)

        pdf.cell(0, 8, f"{idx}. {stage_title}", ln=1)

        pdf.set_font("DejaVu", "B", 11)
        pdf.multi_cell(0, 6, safe_wrap(ex.get("title_hu", "")))
        pdf.ln(2)

        pdf.set_font("DejaVu", "", 10)
        meta_line = (
            f"Formátum: {ex.get('format','')} | "
            f"Típus: {ex.get('exercise_type','')} | "
            f"Időtartam: {ex.get('duration_minutes','')} perc | "
            f"Pályaméret: {ex.get('pitch_size','')}"
        )
        pdf.multi_cell(0, 5, safe_wrap(meta_line))
        pdf.ln(2)

        org = ex.get("organisation_hu", "")
        if org:
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 6, "Szervezés:", ln=1)
            pdf.set_font("DejaVu", "", 10)
            pdf.multi_cell(0, 5, safe_wrap(org))
            pdf.ln(2)

        desc = ex.get("description_hu", "")
        if desc:
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 6, "Leírás / menete:", ln=1)
            pdf.set_font("DejaVu", "", 10)
            pdf.multi_cell(0, 5, safe_wrap(desc))
            pdf.ln(2)

        cpts = ex.get("coaching_points_hu", [])
        if cpts:
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 6, "Coaching pontok:", ln=1)
            pdf.set_font("DejaVu", "", 10)
            for c in cpts:
                pdf.multi_cell(0, 5, safe_wrap("• " + c))
            pdf.ln(1)

        vars_ = ex.get("variations_hu", [])
        if vars_:
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 6, "Variációk:", ln=1)
            pdf.set_font("DejaVu", "", 10)
            for v in vars_:
                pdf.multi_cell(0, 5, safe_wrap("• " + v))
            pdf.ln(1)

        # Egyedi jegyzet ehhez a feladathoz
        note = exercise_notes_dict.get(ex["id"])
        if note:
            pdf.ln(2)
            pdf.set_font("DejaVu", "B", 11)
            pdf.cell(0, 6, "Edzői jegyzet ehhez a gyakorlathoz:", ln=1)
            pdf.set_font("DejaVu", "", 10)
            pdf.multi_cell(0, 5, safe_wrap(note))

    out = pdf.output(dest="S")  # fpdf2-ben ez már bytes
    if isinstance(out, str):
        out = out.encode("latin-1", "ignore")
    return out


# ======================================================
# 4. STREAMLIT FELÜLET
# ======================================================

st.set_page_config(page_title="Training Blueprint – chatbotfootball", layout="wide")

st.title("⚽ Training Blueprint – chatbotfootball edzésterv generátor")

st.markdown(
    """
Ez a verzió egy **beépített minta-adatbázisból** dolgozik (5 gyakorlat),  
csak a folyamat és a logika kipróbálása miatt. Később ezt cseréljük majd a
saját, több száz gyakorlatot tartalmazó JSON-adatbázisodra.
"""
)

db = SAMPLE_EXERCISES

# -------- Oldalsáv: szűrők --------
st.sidebar.header("Alapbeállítások")

age_options = ["Mind"] + sorted({ex["age_group_code"] for ex in db})
tactical_options = ["Mind"] + sorted({ex["tactical_code"] for ex in db})
technical_options = ["Mind"] + sorted({ex["technical_code"] for ex in db})
physical_options = ["Mind"] + sorted({ex["physical_goal"] for ex in db})

age_sel = st.sidebar.selectbox("Korosztály", age_options, index=1)
tactical_sel = st.sidebar.selectbox("Taktikai cél", tactical_options, index=1)
technical_sel = st.sidebar.selectbox("Technikai fókusz", technical_options, index=1)
physical_sel = st.sidebar.selectbox("Erőnléti cél", physical_options, index=0)

period_week = st.sidebar.selectbox("Periodizációs hét (1–4 vagy Mind)", [0, 1, 2, 3, 4], index=1)

coach_id = st.sidebar.text_input("Edző ID", "coach_1")

st.sidebar.markdown("---")
coach_notes = st.sidebar.text_area(
    "Edzői megjegyzés az egész edzéshez",
    "",
    height=120,
    placeholder="Ide írhatod a teljes edzésre vonatkozó gondolataidat…"
)

generate_btn = st.sidebar.button("Edzésterv generálása")

# Session state: hogy a PDF-gomb külön is működjön, elmentjük a legutóbbi tervet
if "last_plan" not in st.session_state:
    st.session_state.last_plan = None
if "last_plan_meta" not in st.session_state:
    st.session_state.last_plan_meta = None

# -------- Fő logika: edzésterv generálása --------
if generate_btn:
    candidates = filter_exercises(
        db,
        age_group=age_sel,
        tactical=tactical_sel,
        technical=technical_sel,
        physical_goal=physical_sel,
        period_week=period_week,
    )

    if not candidates:
        st.error("Nincs olyan gyakorlat, amely megfelel a szűrőknek.")
    else:
        used_ids = set()
        plan = []

        stages = [
            ("Bemelegítés", "warmup"),
            ("Cél1 – kis létszámú játék", "small"),
            ("Cél2 – nagyobb taktikai játék", "large"),
            ("Cél3 – fő rész / meccsjáték jellegű", "main"),
        ]

        for title, code in stages:
            ex = pick_for_stage(candidates, used_ids, code)
            if ex:
                used_ids.add(ex["id"])
                plan.append((title, ex))

        if not plan:
            st.error("Nem sikerült gyakorlatsort összeállítani a szűrők alapján.")
        else:
            # Mentjük a session_state-be a PDF-hez
            st.session_state.last_plan = plan
            st.session_state.last_plan_meta = {
                "age_group": age_sel,
                "tactical": tactical_sel,
                "technical": technical_sel,
                "physical": physical_sel,
                "period_week": period_week,
                "coach_id": coach_id,
                "coach_notes": coach_notes,
            }
            st.success("✅ Edzésterv generálva a megadott paraméterek alapján.")

# -------- Ha van elmentett terv, megjelenítjük --------
plan = st.session_state.last_plan
plan_meta = st.session_state.last_plan_meta

if plan and plan_meta:
    st.subheader("📋 Edzésterv összefoglaló")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Korosztály:** {plan_meta['age_group']}")
        st.markdown(f"**Taktikai cél:** {plan_meta['tactical']}")
    with col2:
        st.markdown(f"**Technikai fókusz:** {plan_meta['technical']}")
        st.markdown(f"**Erőnléti cél:** {plan_meta['physical']}")
    with col3:
        st.markdown(f"**Periodizációs hét:** {plan_meta['period_week']}")
        st.markdown(f"**Edző ID:** `{plan_meta['coach_id']}`")

    if plan_meta["coach_notes"]:
        st.markdown("**Edzői megjegyzés az egész edzéshez:**")
        st.info(plan_meta["coach_notes"])

    st.markdown("---")

    # Egyedi jegyzetek a gyakorlatokhoz
    st.markdown("### Gyakorlatok részletesen")

    # exercise_notes: id -> szöveg
    exercise_notes: Dict[str, str] = {}

    for idx, (stage_title, ex) in enumerate(plan, start=1):
        st.markdown(f"#### {idx}. {stage_title}")
        c1, c2 = st.columns([1.1, 1.3])

        with c1:
            st.markdown(f"**{ex.get('title_hu','')}**")
            meta_txt = (
                f"Formátum: `{ex.get('format','')}`  \n"
                f"Típus: `{ex.get('exercise_type','')}`  \n"
                f"Pályaméret: `{ex.get('pitch_size','')}`  \n"
                f"Időtartam: `{ex.get('duration_minutes','')} perc`"
            )
            st.markdown(meta_txt)

        with c2:
            with st.expander("Szervezés (HU)"):
                st.write(ex.get("organisation_hu", ""))

            with st.expander("Leírás / menete (HU)"):
                st.write(ex.get("description_hu", ""))

            with st.expander("Coaching pontok (HU)"):
                for c in ex.get("coaching_points_hu", []):
                    st.write("• " + c)

            with st.expander("Variációk (HU)"):
                for v in ex.get("variations_hu", []):
                    st.write("• " + v)

        # Egyedi jegyzet textarea
        note_key = f"note_{ex['id']}"
        default_val = st.session_state.get(note_key, "")
        note_val = st.text_area(
            f"Edzői jegyzet ehhez a gyakorlathoz ({ex['id']})",
            value=default_val,
            key=note_key,
            height=80
        )
        exercise_notes[ex["id"]] = note_val

        st.markdown("---")

    # ACWR / terhelés – nagyon egyszerű demo
    st.subheader("📈 Terhelés / ACWR demo (heti összterhelés)")

    # Dummy load: minden gyakorlat terhelése = duration_minutes * (1/2/3)
    intensity_map = {"alacsony": 1, "alacsony–közepes": 1.5, "közepes": 2, "magas": 3}
    total_load = 0
    for _, ex in plan:
        factor = intensity_map.get(ex.get("intensity", "").lower(), 2)
        total_load += ex.get("duration_minutes", 15) * factor

    # Session history coachonként
    if "load_history" not in st.session_state:
        st.session_state.load_history = []
    st.session_state.load_history.append(float(total_load))
    if len(st.session_state.load_history) > 6:
        st.session_state.load_history = st.session_state.load_history[-6:]

    load_values = st.session_state.load_history
    weeks = list(range(1, len(load_values) + 1))
    acwr_values = []
    for i in range(len(load_values)):
        acute = load_values[i]
        chronic = sum(load_values[max(0, i-3):i+1]) / min(i+1, 4)
        acwr = acute / chronic if chronic > 0 else 1
        acwr_values.append(acwr)

    acwr_data = {
        "Hét": weeks,
        "Heti terhelés": load_values,
        "ACWR": acwr_values,
    }
    st.line_chart(acwr_data, x="Hét", y=["Heti terhelés", "ACWR"])

    st.caption("Megjegyzés: ez csak demo-számítás, később integráljuk a valódi terhelésadatokat.")

    # -------- PDF EXPORT --------
    st.subheader("📄 Magyar PDF export")

    try:
        pdf_bytes = create_pdf(
            plan=plan,
            plan_meta=plan_meta,
            coach_notes_for_pdf=plan_meta["coach_notes"],
            exercise_notes_dict=exercise_notes
        )

        st.download_button(
            label="📥 PDF generálása és letöltése",
            data=pdf_bytes,
            file_name="edzesterv_training_blueprint.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF generálási hiba: {e}")

else:
    st.info("Állítsd be a bal oldali szűrőket, majd kattints az **Edzésterv generálása** gombra.")
