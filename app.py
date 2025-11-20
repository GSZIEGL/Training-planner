import random
from io import BytesIO
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
from fpdf import FPDF

from pitch_drawer import draw_drill  # koordinátás rajzoló modul


# =====================================================
# STREAMLIT ALAP BEÁLLÍTÁS + EGY KIS DESIGN
# =====================================================

st.set_page_config(page_title="Training Blueprint – edzéstervező", layout="wide")

# Egyszerű, visszafogott „card” jellegű design
st.markdown(
    """
    <style>
    .main {
        background-color: #0f172a;
        color: #e5e7eb;
    }
    .block-card {
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        border-radius: 0.75rem;
        background-color: #111827;
        border: 1px solid #1f2937;
    }
    .block-card h3, .block-card h4 {
        margin-top: 0.2rem;
    }
    .stMetric {
        background-color: #111827 !important;
        border-radius: 0.75rem;
        padding: 0.2rem 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================
# 0. DIAGRAM – FIX DEMÓ 4v2 RONDÓ (MEGMARAD)
# =====================================================

Rondo4v2_DIAGRAM = {
    "pitch": {
        "type": "full",
        "orientation": "horiz",
    },
    "players": [
        {"id": "A1", "label": "1", "x": 35, "y": 40, "team": "home"},
        {"id": "A2", "label": "2", "x": 65, "y": 40, "team": "home"},
        {"id": "A3", "label": "3", "x": 35, "y": 60, "team": "home"},
        {"id": "A4", "label": "4", "x": 65, "y": 60, "team": "home"},
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
# 0/b DEMÓ ADATBÁZIS – KÉSŐBB CSERÉLHETŐ A VALÓDI JSON-RA
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
        "diagram_v1": Rondo4v2_DIAGRAM,
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

    strict_res = [ex for ex in db if matches(ex, strict=True)]
    if strict_res:
        return strict_res

    loose_res = [
        ex for ex in db
        if ex.get("stage_tag") == stage
        and (not age_group or ex.get("age_group") == age_group)
        and (not fitness_goal or ex.get("fitness_goal") == fitness_goal)
    ]
    if loose_res:
        return loose_res

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
    past_weeks = [220, 260, 240]
    acute = current_session_load
    weeks = ["-3. hét", "-2. hét", "-1. hét", "Aktuális edzés"]

    loads = past_weeks + [acute]
    chronic_mean = sum(past_weeks) / len(past_weeks)
    acwr_values = [round(l / chronic_mean, 2) for l in loads]

    df = pd.DataFrame({"Hét": weeks, "Terhelés": loads, "ACWR": acwr_values})
    return df


# =====================================================
# 1/b SAJÁT GYAKORLAT GENERÁLÓ – RONDÓ + KISJÁTÉK KAPURA
# =====================================================

def generate_rondo_diagram(
    attackers: int,
    defenders: int,
    size_units: int,
    show_cones: bool,
    title: str,
) -> Dict[str, Any]:
    """
    Rondó középen, kiemelt négyzettel, sarkoknál/vonalon támadók, középen védők.
    """
    center_x, center_y = 50, 50
    half = size_units / 2

    # kiemelt játékterület
    area = {
        "x": center_x - half - 4,
        "y": center_y - half - 4,
        "w": size_units + 8,
        "h": size_units + 8,
    }

    # támadók pozíciói – sarkok + 2 középhely (max 6)
    positions = [
        (center_x - half, center_y - half),
        (center_x + half, center_y - half),
        (center_x + half, center_y + half),
        (center_x - half, center_y + half),
        (center_x, center_y + half),
        (center_x, center_y - half),
    ]
    positions = positions[:attackers]

    players = []
    cones = []

    for i, (x, y) in enumerate(positions, start=1):
        players.append(
            {"id": f"A{i}", "label": str(i), "x": x, "y": y, "team": "home"}
        )
        if show_cones:
            cones.append({"x": x, "y": y})

    # védők – kis „X” alakban középen
    def_positions = [
        (center_x - 2, center_y),
        (center_x + 2, center_y),
        (center_x, center_y + 3),
    ]
    def_positions = def_positions[:defenders]
    for j, (x, y) in enumerate(def_positions, start=1):
        players.append(
            {"id": f"D{j}", "label": "X", "x": x, "y": y, "team": "away"}
        )

    ball = {"owner_id": "A1"}

    # passz-szekvencia: 1→2→3→...→1
    passes = []
    attacker_ids = [f"A{i}" for i in range(1, attackers + 1)]
    for i in range(len(attacker_ids)):
        from_id = attacker_ids[i]
        to_id = attacker_ids[(i + 1) % len(attacker_ids)]
        passes.append({"from_id": from_id, "to_id": to_id})

    # futások: védők a labdás irányába lépnek
    runs = []
    for j in range(1, defenders + 1):
        from_id = f"D{j}"
        base = next(p for p in players if p["id"] == from_id)
        runs.append(
            {"from_id": from_id, "to": {"x": base["x"] + 4, "y": base["y"] + 2}}
        )

    text_labels = [
        {"x": 5, "y": 95, "text": title},
    ]

    return {
        "pitch": {"type": "full", "orientation": "horiz"},
        "area": area,
        "players": players,
        "ball": ball,
        "cones": cones,
        "passes": passes,
        "runs": runs,
        "text_labels": text_labels,
        "mini_goals": [],
    }


def generate_ssg_diagram(
    attackers: int,
    defenders: int,
    has_keepers: bool,
    title: str,
) -> Dict[str, Any]:
    """
    Kisjáték kapura – kb. félpálya, kiemelt játéktérrel, minikapukkal.
    Támadás balról jobbra.
    """
    # játéktér a pálya jobb oldalán (kb. félpálya)
    area = {
        "x": 20,
        "y": 30,
        "w": 60,
        "h": 40,
    }

    players = []
    cones = []

    # a játéktér sarkain bóják
    cones.extend(
        [
            {"x": area["x"], "y": area["y"]},
            {"x": area["x"] + area["w"], "y": area["y"]},
            {"x": area["x"], "y": area["y"] + area["h"]},
            {"x": area["x"] + area["w"], "y": area["y"] + area["h"]},
        ]
    )

    # kapu – jobb oldalon mini-kapu
    mini_goals = [
        {
            "x": area["x"] + area["w"] + 3,
            "y": area["y"] + area["h"] / 2,
            "w": 4,
            "h": 10,
        }
    ]

    if has_keepers:
        players.append(
            {"id": "GK_A", "label": "GK", "x": area["x"] - 5, "y": area["y"] + area["h"] / 2, "team": "keeper"}
        )
        players.append(
            {"id": "GK_D", "label": "GK", "x": area["x"] + area["w"] + 8, "y": area["y"] + area["h"] / 2, "team": "keeper"}
        )

    # támadók – mélységben 2 sor, befelé szűkülve
    atk_rows_y = [area["y"] + area["h"] * 0.35, area["y"] + area["h"] * 0.65]
    atk_per_row = (attackers + 1) // 2
    idx = 1
    for row_y in atk_rows_y:
        xs = [
            area["x"] + area["w"] * 0.25,
            area["x"] + area["w"] * 0.4,
            area["x"] + area["w"] * 0.55,
            area["x"] + area["w"] * 0.7,
            area["x"] + area["w"] * 0.85,
        ][:atk_per_row]
        for x in xs:
            if idx > attackers:
                break
            players.append({"id": f"A{idx}", "label": str(idx), "x": x, "y": row_y, "team": "home"})
            idx += 1

    # védők – kicsit hátrébb, blokkszerűen
    def_rows_y = [area["y"] + area["h"] * 0.4, area["y"] + area["h"] * 0.6]
    def_per_row = (defenders + 1) // 2
    jdx = 1
    for row_y in def_rows_y:
        xs = [
            area["x"] + area["w"] * 0.55,
            area["x"] + area["w"] * 0.7,
            area["x"] + area["w"] * 0.85,
        ][:def_per_row]
        for x in xs:
            if jdx > defenders:
                break
            players.append({"id": f"D{jdx}", "label": "X", "x": x, "y": row_y, "team": "away"})
            jdx += 1

    # labda: mindig az első támadónál
    ball = {"owner_id": "A1"}

    # TAKTIKAI PASSZLÁNC: első 3–4 támadó
    passes = []
    attacker_objs = [p for p in players if p["id"].startswith("A")]
    attacker_objs.sort(key=lambda p: p["x"])  # hátsóból előre

    chain = attacker_objs[:4] if len(attacker_objs) >= 4 else attacker_objs

    for i in range(len(chain) - 1):
        passes.append({"from_id": chain[i]["id"], "to_id": chain[i + 1]["id"]})

    if has_keepers and chain:
        passes.append({"from_id": chain[-1]["id"], "to_id": "GK_D"})

    # futások: csatárok kapu felé, védők oldalra tolódnak
    runs = []
    for a in attacker_objs[-2:]:
        runs.append(
            {"from_id": a["id"], "to": {"x": a["x"] + 6, "y": a["y"]}}
        )
    for d in [p for p in players if p["id"].startswith("D")]:
        runs.append(
            {"from_id": d["id"], "to": {"x": d["x"] + 3, "y": d["y"]}}
        )

    text_labels = [
        {"x": 5, "y": 95, "text": title},
    ]

    return {
        "pitch": {"type": "full", "orientation": "horiz"},
        "area": area,
        "players": players,
        "ball": ball,
        "cones": cones,
        "passes": passes,
        "runs": runs,
        "text_labels": text_labels,
        "mini_goals": mini_goals,
    }


def create_custom_exercise(
    drill_type: str,
    title: str,
    age_group: str,
    fitness_goal: str,
    period_week: int,
    stage_tag: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    drill_type: "rondo" vagy "ssg"
    params:
      rondó: attackers, defenders, size_m, duration_min, intensity, show_cones
      ssg:   attackers, defenders, has_keepers, duration_min, intensity
    """
    if drill_type == "rondo":
        diagram = generate_rondo_diagram(
            attackers=params["attackers"],
            defenders=params["defenders"],
            size_units=params["size_m"],
            show_cones=params["show_cones"],
            title=title,
        )
        exercise_type = "rondó"
        format_txt = f"{params['attackers']}v{params['defenders']}"
        pitch_size = f"{params['size_m']}×{params['size_m']} m"
        organisation = (
            f"{params['attackers']} támadó a négyzet oldalain/sarkaiban, "
            f"{params['defenders']} védő középen. "
            "A támadók célja a labda megtartása."
        )

    elif drill_type == "ssg":
        diagram = generate_ssg_diagram(
            attackers=params["attackers"],
            defenders=params["defenders"],
            has_keepers=params["has_keepers"],
            title=title,
        )
        exercise_type = "small-sided game"
        format_txt = f"{params['attackers']}v{params['defenders']}" + (" + GK" if params["has_keepers"] else "")
        pitch_size = "kb. félpálya"
        organisation = (
            f"Kisjáték {params['attackers']} támadóval és {params['defenders']} védővel, "
            "irányított játékkal kapura."
        )

    else:
        # fallback – ne dőljön el az app
        diagram = generate_rondo_diagram(
            attackers=4, defenders=2, size_units=18, show_cones=True, title=title
        )
        exercise_type = "rondó"
        format_txt = "4v2"
        pitch_size = "18×18 m"
        organisation = "Demó rondó – fallback."

    exercise_id = f"custom_{drill_type}_{stage_tag}"

    ex = {
        "id": exercise_id,
        "age_group": age_group,
        "tactical_goal": "labdabirtoklás",
        "technical_goal": "rövid passzjáték" if drill_type == "rondo" else "passzjáték / befejezés",
        "fitness_goal": fitness_goal or "nincs megadva",
        "period_week": period_week,
        "stage_tag": stage_tag,
        "title_hu": title,
        "format": format_txt,
        "exercise_type": exercise_type,
        "duration_min": params["duration_min"],
        "intensity": params["intensity"],
        "pitch_size": pitch_size,
        "organisation_hu": organisation,
        "description_hu": (
            "Folyamatos játék időre. A labdát birtokló csapat gyors passzokkal "
            "próbálja játékban tartani a labdát, illetve helyzeteket kialakítani."
        ),
        "coaching_points_hu": [
            "Testhelyzet labdaátvételnél.",
            "Első érintés iránya a szabad terület felé.",
            "Kommunikáció, szabadulás a fedezőtől.",
        ],
        "variations_hu": [
            "Érintésszám korlátozása.",
            "Gól / 5 passz után csere a védők/támadók között.",
        ],
        "diagram_v1": diagram,
    }
    return ex


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
    try:
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    except:
        pass
    try:
        pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
    except:
        pass


def multiline(pdf: TrainingPDF, txt: str):
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

        note = exercise_notes.get(ex_id, "")
        pdf.ln(3)
        pdf.cell(0, 6, "Edzői megjegyzés ehhez a gyakorlathoz:", ln=1)
        multiline(pdf, note or "-")

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        raw = raw.encode("latin-1", "ignore")
    bio = BytesIO(raw)
    bio.seek(0)
    return bio


# =====================================================
# 3. STREAMLIT UI – TRAINING BLUEPRINT
# =====================================================

st.title("⚽ Training Blueprint – edzéstervező demó")

st.write(
    "Ez egy **demó verzió**, amely néhány példagyakorlatból generál edzéstervet "
    "a megadott szűrők alapján. A bal oldalon beállíthatod az edzés paramétereit, "
    "és akár egy **saját gyakorlatot** (rondót vagy kisjátékot kapura) is megtervezhetsz."
)

# --- Szűrők / beállítások ---

st.sidebar.header("🎯 Edzés paraméterek")

age_group = st.sidebar.selectbox(
    "Korosztály",
    ["U7–U11", "U12–U15", "U16–U19"],
    index=1,
)

tactical_goal = st.sidebar.selectbox(
    "Taktikai cél (fő fókusz)",
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

# --- SAJÁT GYAKORLAT VARÁZSLÓ ---

st.sidebar.markdown("---")
use_custom_drill = st.sidebar.checkbox("➕ Saját gyakorlat hozzáadása")

custom_drill_params = None
custom_drill_type_key = None

if use_custom_drill:
    st.sidebar.markdown("**Saját gyakorlat beállításai**")

    stage_label_to_tag = {
        "Bemelegítés": "warmup",
        "Cél1 – kis létszámú játék": "small",
        "Cél2 – nagyobb létszámú játék": "large",
        "Cél3 – fő rész / mérkőzésjáték": "main",
    }
    stage_label = st.sidebar.selectbox(
        "Melyik blokk legyen ez a gyakorlat?",
        list(stage_label_to_tag.keys()),
        index=0,
    )
    custom_stage_tag = stage_label_to_tag[stage_label]

    custom_title = st.sidebar.text_input("Gyakorlat neve", "Saját gyakorlat")

    custom_drill_type = st.sidebar.radio(
        "Gyakorlat típusa",
        ["Rondó", "Kisjáték kapura"],
        index=0,
    )

    if custom_drill_type == "Rondó":
        attackers = st.sidebar.slider("Támadók (külső játékosok)", 3, 6, 4)
        defenders = st.sidebar.slider("Védők száma középen", 1, 3, 2)
        size_m = st.sidebar.slider("Négyzet mérete (relatív)", 12, 30, 18)
        duration_custom = st.sidebar.slider("Időtartam (perc)", 8, 30, 15)
        intensity_custom = st.sidebar.selectbox(
            "Intenzitás",
            ["alacsony", "alacsony–közepes", "közepes", "közepes–magas", "magas"],
            index=1,
        )
        show_cones = st.sidebar.checkbox("Bóják a rondó sarkain", value=True)

        custom_drill_params = {
            "stage_tag": custom_stage_tag,
            "title": custom_title,
            "attackers": attackers,
            "defenders": defenders,
            "size_m": size_m,
            "duration_min": duration_custom,
            "intensity": intensity_custom,
            "show_cones": show_cones,
        }
        custom_drill_type_key = "rondo"

    else:  # Kisjáték kapura
        attackers = st.sidebar.slider("Támadók száma", 3, 7, 4)
        defenders = st.sidebar.slider("Védők száma", 2, 6, 3)
        has_keepers = st.sidebar.checkbox("Kapusok a kapuban", value=True)
        duration_custom = st.sidebar.slider("Időtartam (perc)", 10, 35, 20)
        intensity_custom = st.sidebar.selectbox(
            "Intenzitás",
            ["közepes", "közepes–magas", "magas"],
            index=1,
        )

        custom_drill_params = {
            "stage_tag": custom_stage_tag,
            "title": custom_title,
            "attackers": attackers,
            "defenders": defenders,
            "has_keepers": has_keepers,
            "duration_min": duration_custom,
            "intensity": intensity_custom,
        }
        custom_drill_type_key = "ssg"

coach_notes = st.text_area(
    "🧠 Edzői megjegyzés az egész edzéshez",
    placeholder="Ide írhatod a teljes edzéshez kapcsolódó gondolataidat…",
)

if "exercise_notes" not in st.session_state:
    st.session_state["exercise_notes"] = {}

generate = st.button("🛠️ Edzésterv generálása")

plan: List[Dict[str, Any]] = []
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
        if use_custom_drill and custom_drill_params and custom_drill_params["stage_tag"] == stage_tag:
            ex = create_custom_exercise(
                drill_type=custom_drill_type_key or "rondo",
                title=custom_drill_params["title"],
                age_group=age_group,
                fitness_goal=fitness_goal,
                period_week=period_week,
                stage_tag=stage_tag,
                params=custom_drill_params,
            )
        else:
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

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.subheader("📊 Terhelés és ACWR (demó)")
    total_session_load = sum(ex["exercise"]["duration_min"] for ex in plan) * 10
    acwr_df = demo_acwr_series(total_session_load)
    st.caption("Az ACWR itt csak demo jellegű, később valós GPS / terhelésadatokra cseréljük.")
    st.line_chart(acwr_df.set_index("Hét")[["Terhelés", "ACWR"]])
    st.markdown('</div>', unsafe_allow_html=True)

    st.header("📚 Gyakorlatok blokkra bontva")

    for block in plan:
        stage_title = block["stage_title"]
        ex = block["exercise"]
        ex_id = ex["id"]

        st.markdown('<div class="block-card">', unsafe_allow_html=True)
        st.subheader(stage_title)
        st.markdown(f"**{ex['title_hu']}**")

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

        note_key = f"note_{ex_id}"
        current_note = st.session_state["exercise_notes"].get(ex_id, "")
        new_note = st.text_area(
            f"Edzői megjegyzés ehhez a gyakorlathoz ({ex_id})",
            value=current_note,
            key=note_key,
        )
        st.session_state["exercise_notes"][ex_id] = new_note
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("Kattints az **Edzésterv generálása** gombra a kezdéshez.")
