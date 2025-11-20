import random
from io import BytesIO
from typing import List, Dict

import streamlit as st
import pandas as pd
from fpdf import FPDF

from pitch_drawer import draw_drill  # <-- ÚJ: rajzoló modul importja


# =====================================================
# 0. DIAGRAM – 4v2 RONDÓ DEMO SPEC
# =====================================================

Rondo4v2_DIAGRAM = {
    "pitch": {
        "type": "full",
        "orientation": "horiz",
    },
    "players": [
        # támadók – négyzet sarkai
        {"id": "A1", "label": "1", "x": 35, "y": 40, "team": "home"},
        {"id": "A2", "label": "2", "x": 65, "y": 40, "team": "home"},
        {"id": "A3", "label": "3", "x": 35, "y": 60, "team": "home"},
        {"id": "A4", "label": "4", "x": 65, "y": 60, "team": "home"},
        # védők – középen
        {"id": "D1", "label": "X", "x": 48, "y": 50, "team": "away"},
        {"id": "D2", "label": "X", "x": 52, "y": 50, "team": "away"},
    ],
    "ball": {
        "owner_id": "A1"
    },
    "cones": [
        {"x": 35, "y": 40},
        {"x": 65, "y": 40},
        {"x": 35, "y": 60},
        {"x": 65, "y": 60},
    ],
    "passes": [
        {"from_id": "A1", "to_id": "A2"},
        {"from_id": "A2", "to_id": "A4"},
    ],
    "runs": [
        {"from_id": "D1", "to": {"x": 55, "y": 55}},
        {"from_id": "D2", "to": {"x": 45, "y": 45}},
    ],
    "text_labels": [
        {"x": 5, "y": 95, "text": "Bemelegítő rondó 4v2 – U12–U15"},
    ],
}


# =====================================================
# 0. DEMÓ ADATBÁZIS – KÉSŐBB CSERÉLHETŐ A VALÓDI JSON-RA
# =====================================================

DEMO_DB: List[Dict] = [
    # -------- Bemelegítés / rondó jelleg --------
    {
        "id": "warmup_u12_rondo",
        "age_group": "U12–U15",
        "tactical_goal": "labdabirtoklás",
        "technical_goal": "rövid passzjáték",
        "fitness_goal": "alacsony terhelés",
        "period_week": 1,
        "stage_tag": "warmup",
        "title_hu": "Bemelegítő rondó 4v2",
        "format": "4v2",
        "exercise_type": "rondó",
        "duration_min": 15,
        "intensity": "alacsony–közepes",
        "pitch_size": "18×18 m",
        "organisation_hu": (
            "Négy támadó a négyzet sarkaiban, két védő középen. "
            "Labdával rendelkező támadók két érintéssel játszanak."
        ),
        "description_hu": (
            "A támadók célja a labda megtartása, gyors passzokkal. "
            "A védők labdaszerzés után azonnal visszapasszolják kívülre."
        ),
        "coaching_points_hu": [
            "Testhelyzet a labda fogadásához.",
            "Kommunikáció – ki kér labdát?",
            "Első érintés iránya kifelé a nyomásból."
        ],
        "variations_hu": [
            "Max. 2 érintés.",
            "Labdaszerzés után 5 gyors passz = pont."
        ],
        "diagram_v1": Rondo4v2_DIAGRAM,  # <-- ÚJ: taktikai ábra
    },

    # -------- Kis létszámú taktikai játék --------
    {
        "id": "small_u12_pressing",
        "age_group": "U12–U15",
        "tactical_goal": "labdaszerzés / pressing",
        "technical_goal": "1v1 védekezés",
        "fitness_goal": "közepes terhelés",
        "period_week": 2,
        "stage_tag": "small",
        "title_hu": "3v3 + 2 neutrális – pressing játék",
        "format": "3v3+2",
        "exercise_type": "small-sided game",
        "duration_min": 20,
        "intensity": "közepes–magas",
        "pitch_size": "25×20 m",
        "organisation_hu": (
            "3v3 játék két neutrális támadóval, akik mindig labdát birtokló csapattal "
            "játszanak. Játék két kis kapura."
        ),
        "description_hu": (
            "A labdát vesztett csapat azonnal próbál visszatámadni (gegenpressing). "
            "Cél: 5 passz vagy gól a kis kapukra."
        ),
        "coaching_points_hu": [
            "Azonnali reakció labdavesztés után.",
            "Testtartás 1v1 párharcban.",
            "Neutrális játékosok helyezkedése passzsávokban."
        ],
        "variations_hu": [
            "Max. 3 érintés a neutrális játékosoknak.",
            "Labdaszerzés után 5 másodpercen belül kapura lövés."
        ],
    },

    # -------- Nagyobb létszámú taktikai játék --------
    {
        "id": "large_u16_build_up",
        "age_group": "U16–U19",
        "tactical_goal": "labdakihozatal / build-up",
        "technical_goal": "befejezés technika",
        "fitness_goal": "közepes terhelés",
        "period_week": 3,
        "stage_tag": "large",
        "title_hu": "7v5 labdakihozatal a középső zónában",
        "format": "7v5",
        "exercise_type": "positional game",
        "duration_min": 25,
        "intensity": "közepes",
        "pitch_size": "40×35 m",
        "organisation_hu": (
            "7 támadó a saját térfélen, 5 védő próbál labdát szerezni. "
            "A cél: kijátszani a pressinget és átjátszani a középső zónát."
        ),
        "description_hu": (
            "A támadó csapat felépíti a játékot hátulról, a labda kijuttatása a kijelölt "
            "kapukon vagy célzónákon keresztül. Labdavesztéskor azonnali visszatámadás."
        ),
        "coaching_points_hu": [
            "Hátsó lánc szélessége és mélysége.",
            "Határozott első passz a kapustól.",
            "Középpályások közti háromszögek kialakítása."
        ],
        "variations_hu": [
            "Időlimit a labdakihozatalra (pl. 10 másodperc).",
            "Extra pont, ha a 6-os pozícióban lévő játékos ér labdához."
        ],
    },

    # -------- Fő rész / mérkőzésjáték --------
    {
        "id": "main_u16_game_like",
        "age_group": "U16–U19",
        "tactical_goal": "befejezés, gólhelyzet-teremtés",
        "technical_goal": "1v1 támadás",
        "fitness_goal": "magas terhelés",
        "period_week": 4,
        "stage_tag": "main",
        "title_hu": "8v8 + kapusok – mérkőzésjáték",
        "format": "8v8+GK",
        "exercise_type": "game",
        "duration_min": 30,
        "intensity": "magas",
        "pitch_size": "60×45 m",
        "organisation_hu": (
            "Szabályos mérkőzésjáték lerövidített pályán. "
            "Mindkét csapat 8 mezőnyjátékossal és kapussal."
        ),
        "description_hu": (
            "A hangsúly a gyors támadásbefejezéseken, sok kapura lövéssel. "
            "Pontszám: gól + extra pont, ha 10 másodpercen belül befejezik a támadást."
        ),
        "coaching_points_hu": [
            "Gyors átmenet védekezésből támadásba.",
            "Bátor 1v1 vállalása az utolsó harmadban.",
            "Kapura lövések minősége, döntéshozatal."
        ],
        "variations_hu": [
            "Max. 3 érintés a középső zónában.",
            "Extra pont fejessel szerzett gólért."
        ],
    },
]


# =====================================================
# 1. SEGÉDFÜGGVÉNYEK – SZŰRÉS, VÁLASZTÁS, ACWR
# =====================================================

def smart_filter(
    db: List[Dict],
    age_group: str,
    tactical_goal: str,
    technical_goal: str,
    fitness_goal: str,
    period_week: int,
    stage: str,
) -> List[Dict]:
    """
    'Okos' szűrés: először megpróbál minden feltételt,
    ha üres, akkor fokozatosan lazít (hogy mindig legyen gyakorlat).
    """
    def matches(ex: Dict, strict: bool) -> bool:
        if stage and ex.get("stage_tag") != stage:
            return False
        if strict:
            if age_group and ex.get("age_group") != age_group:
                return False
            if tactical_goal and ex.get("tactical_goal") != tactical_goal:
                return False
            if technical_goal and ex.get("technical_goal") != technical_goal:
                return False
            if fitness_goal and ex.get("fitness_goal") != fitness_goal:
                return False
            if period_week and ex.get("period_week") != period_week:
                return False
        return True

    # 1) teljesen szigorú
    strict_res = [ex for ex in db if matches(ex, strict=True)]
    if strict_res:
        return strict_res

    # 2) csak korosztály + stage + erőnlét
    loose_res = [
        ex for ex in db
        if ex.get("stage_tag") == stage
        and (not age_group or ex.get("age_group") == age_group)
        and (not fitness_goal or ex.get("fitness_goal") == fitness_goal)
    ]
    if loose_res:
        return loose_res

    # 3) utolsó fallback: csak stage
    return [ex for ex in db if ex.get("stage_tag") == stage]


def pick_exercise_for_stage(
    db: List[Dict],
    age_group: str,
    tactical_goal: str,
    technical_goal: str,
    fitness_goal: str,
    period_week: int,
    stage: str,
) -> Dict:
    candidates = smart_filter(
        db, age_group, tactical_goal, technical_goal, fitness_goal, period_week, stage
    )
    if not candidates:
        return {}
    return random.choice(candidates)


def demo_acwr_series(current_session_load: int) -> pd.DataFrame:
    """
    Egyszerű demo ACWR: 3 korábbi hét + aktuális edzés.
    """
    # krónikus terhelés (elmúlt 3 hét összterhelés)
    past_weeks = [220, 260, 240]
    acute = current_session_load
    weeks = ["-3. hét", "-2. hét", "-1. hét", "Aktuális edzés"]

    loads = past_weeks + [acute]
    chronic_mean = sum(past_weeks) / len(past_weeks)
    acwr_values = [round(l / chronic_mean, 2) for l in loads]

    df = pd.DataFrame({"Hét": weeks, "Terhelés": loads, "ACWR": acwr_values})
    return df


# =====================================================
# 2. PDF – DEJAVU FONTOK, MAGYAR SZÖVEG
# =====================================================

class TrainingPDF(FPDF):
    def header(self):
        try:
            self.set_font("DejaVu", "B", 14)
        except:
            self.set_font("Arial", "B", 14)
        self.cell(0, 8, "Edzésterv – Training Blueprint", ln=1)

    def footer(self):
        self.set_y(-15)
        try:
            self.set_font("DejaVu", "", 9)
        except:
            self.set_font("Arial", "", 9)
        self.cell(0, 10, "Generálva Training Blueprint alkalmazással", 0, 0, "C")


def init_fonts(pdf: TrainingPDF):
    """DejaVu fontok biztonságos regisztrálása."""
    try:
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    except:
        pass
    try:
        pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    except:
        pass


def multiline(pdf: TrainingPDF, txt: str):
    """Biztonságos multi_cell, hogy ne dőljön el hosszú szavaknál sem."""
    if not txt:
        return
    safe = txt.replace("\r", " ").replace("\n", " ")
    try:
        pdf.multi_cell(0, 6, safe)
    except Exception:
        pdf.multi_cell(0, 6, safe[:500] + " ...")


def create_pdf(plan: List[Dict], plan_meta: Dict, coach_notes: str, exercise_notes: Dict[str, str]) -> BytesIO:
    pdf = TrainingPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    init_fonts(pdf)

    # ---------- Címlap ----------
    pdf.add_page()
    try:
        pdf.set_font("DejaVu", "B", 18)
    except:
        pdf.set_font("Arial", "B", 18)

    pdf.cell(0, 10, "Edzésterv összefoglaló", ln=1)
    try:
        pdf.set_font("DejaVu", "", 12)
    except:
        pdf.set_font("Arial", "", 12)

    pdf.ln(2)
    pdf.cell(0, 7, f"Korosztály: {plan_meta['age_group']}", ln=1)
    pdf.cell(0, 7, f"Taktikai cél: {plan_meta['tactical_goal']}", ln=1)
    pdf.cell(0, 7, f"Technikai cél: {plan_meta['technical_goal']}", ln=1)
    pdf.cell(0, 7, f"Erőnléti cél: {plan_meta['fitness_goal']}", ln=1)
    pdf.cell(0, 7, f"Periódizációs hét: {plan_meta['period_week']}", ln=1)
    pdf.cell(0, 7, f"Edző ID: {plan_meta['coach_id']}", ln=1)

    pdf.ln(4)
    pdf.cell(0, 7, "Edzői megjegyzés az edzéshez:", ln=1)
    multiline(pdf, coach_notes or "-")

    # ---------- Blokkok ----------
    for idx, block in enumerate(plan, start=1):
        stage_title = block["stage_title"]
        ex = block["exercise"]
        ex_id = ex["id"]

        pdf.add_page()
        try:
            pdf.set_font("DejaVu", "B", 14)
        except:
            pdf.set_font("Arial", "B", 14)

        pdf.cell(0, 8, f"{idx}. {stage_title}", ln=1)
        pdf.ln(2)

        try:
            pdf.set_font("DejaVu", "", 11)
        except:
            pdf.set_font("Arial", "", 11)

        pdf.cell(0, 6, f"Cím: {ex['title_hu']}", ln=1)
        pdf.cell(
            0, 6,
            f"Formátum: {ex['format']}   |   Típus: {ex['exercise_type']}   |   Időtartam: {ex['duration_min']} perc",
            ln=1,
        )
        pdf.cell(0, 6, f"Pályaméret: {ex['pitch_size']}   |   Intenzitás: {ex['intensity']}", ln=1)

        pdf.ln(3)
        pdf.cell(0, 6, "Szervezés:", ln=1)
        multiline(pdf, ex["organisation_hu"])

        pdf.ln(2)
        pdf.cell(0, 6, "Leírás / menet:", ln=1)
        multiline(pdf, ex["description_hu"])

        pdf.ln(2)
        pdf.cell(0, 6, "Coaching pontok:", ln=1)
        bullet_text = "\n".join([f"• {c}" for c in ex["coaching_points_hu"]])
        multiline(pdf, bullet_text)

        if ex["variations_hu"]:
            pdf.ln(2)
            pdf.cell(0, 6, "Variációk:", ln=1)
            var_text = "\n".join([f"• {v}" for v in ex["variations_hu"]])
            multiline(pdf, var_text)

        # Egyedi edzői megjegyzés ehhez a gyakorlathoz
        note = exercise_notes.get(ex_id, "")
        pdf.ln(3)
        pdf.cell(0, 6, "Edzői megjegyzés ehhez a gyakorlathoz:", ln=1)
        multiline(pdf, note or "-")

    # ---------- PDF -> BytesIO ----------
    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        raw = raw.encode("latin-1", "ignore")
    bio = BytesIO(raw)
    bio.seek(0)
    return bio


# =====================================================
# 3. STREAMLIT UI – TRAINING BLUEPRINT
# =====================================================

st.set_page_config(page_title="Training Blueprint – edzéstervező", layout="wide")

st.title("⚽ Training Blueprint – edzéstervező demó")

st.write(
    "Ez egy **demó verzió**, amely néhány példagyakorlatból generál edzéstervet "
    "a megadott szűrők alapján. Később ide kerül majd a teljes, 300+ gyakorlatos adatbázis."
)

# --- Szűrők / beállítások ---

st.sidebar.header("Szűrés és beállítások")

age_group = st.sidebar.selectbox(
    "Korosztály",
    ["U7–U11", "U12–U15", "U16–U19"],
    index=1,
)

tactical_goal = st.sidebar.selectbox(
    "Taktikai cél",
    [
        "",
        "labdabirtoklás",
        "labdaszerzés / pressing",
        "labdakihozatal / build-up",
        "befejezés, gólhelyzet-teremtés",
    ],
    index=1,
)

technical_goal = st.sidebar.selectbox(
    "Technikai cél",
    [
        "",
        "rövid passzjáték",
        "1v1 védekezés",
        "1v1 támadás",
        "befejezés technika",
    ],
    index=1,
)

fitness_goal = st.sidebar.selectbox(
    "Erőnléti cél",
    ["", "alacsony terhelés", "közepes terhelés", "magas terhelés"],
    index=2,
)

period_week = st.sidebar.slider("Periódizációs hét (1–4)", min_value=1, max_value=4, value=1)

coach_id = st.sidebar.text_input("Edző ID", value="coach_1")

coach_notes = st.text_area(
    "Edzői megjegyzés az egész edzéshez",
    placeholder="Ide írhatod a teljes edzéshez kapcsolódó gondolataidat…",
)

if "exercise_notes" not in st.session_state:
    st.session_state["exercise_notes"] = {}

generate = st.button("Edzésterv generálása")

plan = []
plan_meta = {
    "age_group": age_group,
    "tactical_goal": tactical_goal or "nincs megadva",
    "technical_goal": technical_goal or "nincs megadva",
    "fitness_goal": fitness_goal or "nincs megadva",
    "period_week": period_week,
    "coach_id": coach_id,
}

if generate:
    stages = [
        ("warmup", "Bemelegítés"),
        ("small", "Cél1 – kis létszámú taktikai játék"),
        ("large", "Cél2 – nagyobb létszámú taktikai játék"),
        ("main", "Cél3 – fő rész / mérkőzésjáték jellegű feladat"),
    ]

    for stage_tag, stage_title in stages:
        ex = pick_exercise_for_stage(
            DEMO_DB,
            age_group=age_group,
            tactical_goal=tactical_goal,
            technical_goal=technical_goal,
            fitness_goal=fitness_goal,
            period_week=period_week,
            stage=stage_tag,
        )
        if ex:
            plan.append({"stage_tag": stage_tag, "stage_title": stage_title, "exercise": ex})

    if not plan:
        st.error("Nem találtam egyetlen gyakorlatsort sem – próbáld lazítani a szűrőket.")
    else:
        st.success("✅ Edzésterv generálva a fenti paraméterek alapján.")
        st.session_state["plan"] = plan
        st.session_state["plan_meta"] = plan_meta
        st.session_state["coach_notes_for_pdf"] = coach_notes

# --------- Ha van mentett terv, megjelenítjük ---------

if "plan" in st.session_state and st.session_state["plan"]:
    plan = st.session_state["plan"]
    plan_meta = st.session_state["plan_meta"]

    st.header("📝 Edzésterv összefoglaló")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Korosztály", plan_meta["age_group"])
        st.metric("Periódizációs hét", plan_meta["period_week"])
    with col2:
        st.write("**Taktikai cél:**", plan_meta["tactical_goal"])
        st.write("**Technikai cél:**", plan_meta["technical_goal"])
    with col3:
        st.write("**Erőnléti cél:**", plan_meta["fitness_goal"])
        st.write("**Edző ID:**", plan_meta["coach_id"])

    # --- ACWR demo ---
    st.subheader("📊 Terhelés és ACWR (demó)")

    total_session_load = sum(ex["exercise"]["duration_min"] for ex in plan) * 10  # nagyon egyszerű becslés
    acwr_df = demo_acwr_series(total_session_load)
    st.caption("Az ACWR itt csak demo jellegű, később valós GPS / terhelésadatokra cseréljük.")
    st.line_chart(acwr_df.set_index("Hét")[["Terhelés", "ACWR"]])

    # --- Blokkok részletesen ---
    st.header("📚 Gyakorlatok blokkra bontva")

    for block in plan:
        stage_title = block["stage_title"]
        ex = block["exercise"]
        ex_id = ex["id"]

        st.subheader(stage_title)
        st.markdown(f"**{ex['title_hu']}**")

        # --- ÚJ: taktikai rajz, ha van diagram_v1 ---
        diagram_spec = ex.get("diagram_v1")
        if diagram_spec:
            fig = draw_drill(diagram_spec, show=False)
            st.pyplot(fig, use_container_width=True)

        st.write(
            f"*Formátum:* {ex['format']}  |  *Típus:* {ex['exercise_type']}  |  "
            f"*Időtartam:* {ex['duration_min']} perc  |  *Intenzitás:* {ex['intensity']}"
        )
        st.write(f"*Pályaméret:* {ex['pitch_size']}")

        with st.expander("Szervezés (HU)"):
            st.write(ex["organisation_hu"])

        with st.expander("Leírás / menet (HU)"):
            st.write(ex["description_hu"])

        with st.expander("Coaching pontok (HU)"):
            for c in ex["coaching_points_hu"]:
                st.write("- " + c)

        with st.expander("Variációk (HU)"):
            for v in ex["variations_hu"]:
                st.write("- " + v)

        # Egyedi edzői megjegyzés ehhez a gyakorlathoz
        note_key = f"note_{ex_id}"
        current_note = st.session_state["exercise_notes"].get(ex_id, "")
        new_note = st.text_area(
            f"Edzői megjegyzés ehhez a gyakorlathoz ({ex_id})",
            value=current_note,
            key=note_key,
        )
        st.session_state["exercise_notes"][ex_id] = new_note

    # --------- PDF export ---------
    st.header("📄 Magyar PDF export")

    if st.button("PDF generálása"):
        try:
            pdf_bytes = create_pdf(
                plan=plan,
                plan_meta=plan_meta,
                coach_notes=st.session_state.get("coach_notes_for_pdf", ""),
                exercise_notes=st.session_state["exercise_notes"],
            )
            st.download_button(
                "📥 PDF letöltése",
                data=pdf_bytes,
                file_name="edzesterv_demo.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"PDF generálási hiba: {e}")
else:
    st.info("Kattints az **Edzésterv generálása** gombra a kezdéshez.")
