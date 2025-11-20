import random
from io import BytesIO
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
from fpdf import FPDF

from pitch_drawer import draw_drill   # profi pályarajzoló


# =====================================================
# 0. DEMÓ GYAKORLAT – RONDÓ
# =====================================================

DEMO_RONDO_DIAGRAM = {
    "pitch": {"type": "full", "orientation": "horiz"},
    "players": [
        {"id": "A1", "label": "1", "x": 40, "y": 40, "team": "home"},
        {"id": "A2", "label": "2", "x": 60, "y": 40, "team": "home"},
        {"id": "A3", "label": "3", "x": 40, "y": 60, "team": "home"},
        {"id": "A4", "label": "4", "x": 60, "y": 60, "team": "home"},
        {"id": "D1", "label": "X", "x": 49, "y": 50, "team": "away"},
        {"id": "D2", "label": "X", "x": 51, "y": 50, "team": "away"},
    ],
    "ball": {"owner_id": "A1"},
    "cones": [
        {"x": 35, "y": 35},
        {"x": 65, "y": 35},
        {"x": 35, "y": 65},
        {"x": 65, "y": 65},
    ],
    "area": {"x": 35, "y": 35, "w": 30, "h": 30},
    "passes": [
        {"from_id": "A1", "to_id": "A2"},
        {"from_id": "A2", "to_id": "A4"},
        {"from_id": "A4", "to_id": "A3"},
        {"from_id": "A3", "to_id": "A1"},
    ],
    "runs": [
        {"from_id": "D1", "to": {"x": 52, "y": 48}},
        {"from_id": "D2", "to": {"x": 48, "y": 52}},
    ],
    "text_labels": [
        {"x": 5, "y": 95, "text": "Bemelegítő rondó 4v2 – demó"},
    ],
    "mini_goals": [],
}

DEMO_DB: List[Dict[str, Any]] = [
    {
        "id": "warmup_u12_rondo",
        "age_group": "U12–U15",
        "tactical_goal": "labdabirtoklás",
        "technical_goal": "rövid passzjáték",
        "fitness_goal": "alacsony terhelés",
        "period_week": 1,
        "stage_tag": "warmup",
        "title_hu": "Bemelegítő rondó",
        "format": "4v2",
        "exercise_type": "rondó",
        "duration_min": 15,
        "intensity": "alacsony–közepes",
        "pitch_size": "18×18 m",
        "organisation_hu": "Demó bemelegítő rondó.",
        "description_hu": "Demó leírás.",
        "coaching_points_hu": ["Demó coaching pont 1", "Demó coaching pont 2"],
        "variations_hu": [],
        "diagram_v1": DEMO_RONDO_DIAGRAM,
    },
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
        "organisation_hu": "Demó pressing kisjáték.",
        "description_hu": "Demó leírás.",
        "coaching_points_hu": ["Demó coaching pont 1"],
        "variations_hu": [],
    },
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
        "organisation_hu": "Demó build-up játék.",
        "description_hu": "Demó leírás.",
        "coaching_points_hu": ["Demó coaching pont 1"],
        "variations_hu": [],
    },
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
        "organisation_hu": "Demó mérkőzésjáték.",
        "description_hu": "Demó leírás.",
        "coaching_points_hu": ["Demó coaching pont 1"],
        "variations_hu": [],
    },
]


# =====================================================
# 0/B. PERIODIZÁCIÓS PROFILOK – KOROSZTÁLY / FELNŐTT
# =====================================================

PERIODIZATION_PROFILES: Dict[str, List[Dict[str, str]]] = {
    "U7–U11": [
        {
            "Terület": "Technika",
            "Fókusz": "Elsődleges fókusz – labdavezetés, cselek, labdaérzékelés, mindez sok játékhelyzetben.",
        },
        {
            "Terület": "Taktika",
            "Fókusz": "Alap 1v1 helyzetek, egyszerű döntéshozatal, támadás–védekezés váltás játékosan.",
        },
        {
            "Terület": "Erőnlét",
            "Fókusz": "Koordináció, gyorsasági reakciók, sok kisjáték, strukturált terhelés nélkül.",
        },
        {
            "Terület": "Játékforma",
            "Fókusz": "1v1–4v4 kisjátékok, sok labda, élményközpontú edzés.",
        },
        {
            "Terület": "Mentális",
            "Fókusz": "Bátorság, önbizalom, labdával való kapcsolat megszerettetése.",
        },
    ],
    "U12–U15": [
        {
            "Terület": "Technika",
            "Fókusz": "Gyors passzjáték, irányváltások, labdakezelés nyomás alatt.",
        },
        {
            "Terület": "Taktika",
            "Fókusz": "1v1, 2v1, 3v2 alapelvek, pressing alapok, átmenetek alap szinten.",
        },
        {
            "Terület": "Erőnlét",
            "Fókusz": "Gyorsaság, agilitás, alacsony–közepes intenzitású állóképességi elemek.",
        },
        {
            "Terület": "Játékforma",
            "Fókusz": "4v4–8v8, rondók, kisjátékok, alap build-up / pressing szituációk.",
        },
        {
            "Terület": "Mentális",
            "Fókusz": "Tanulási attitűd, koncentráció, csapatjáték alapnormák.",
        },
    ],
    "U16–U19": [
        {
            "Terület": "Technika",
            "Fókusz": "Technika tempóban – passz, átvétel, 1v1 megoldások meccsintenzitáson.",
        },
        {
            "Terület": "Taktika",
            "Fókusz": "Pressing rendszerek, build-up struktúrák, csapatrészek együttműködése.",
        },
        {
            "Terület": "Erőnlét",
            "Fókusz": "Gyorsaság-állóképesség, iramváltások, sprintek, alap ACWR szemlélet.",
        },
        {
            "Terület": "Játékforma",
            "Fókusz": "8v8–11v11 fázisjáték, taktikai edzés szélességben és mélységben.",
        },
        {
            "Terület": "Mentális",
            "Fókusz": "Versenyhelyzet kezelése, szerepek elfogadása, felelősség.",
        },
    ],
    "Felnőtt amatőr": [
        {
            "Terület": "Technika",
            "Fókusz": "Stabil alaptechnika szinten tartása, gyenge láb, első érintés fejlesztése.",
        },
        {
            "Terület": "Taktika",
            "Fókusz": "Alapelvű szervezettség (védekezési blokk, átmenetek), egyszerű, jól érthető struktúrák.",
        },
        {
            "Terület": "Erőnlét",
            "Fókusz": "Általános állóképesség, sérülésmegelőzés, terhelés óvatos emelése heti 2–3 edzés mellett.",
        },
        {
            "Terület": "Játékforma",
            "Fókusz": "Nagyobb területű játékok (7v7–11v11), meccsszituációk gyakorlása.",
        },
        {
            "Terület": "Mentális",
            "Fókusz": "Motiváció fenntartása, csapategység, munka–foci balansz.",
        },
    ],
    "Felnőtt félprofi": [
        {
            "Terület": "Technika",
            "Fókusz": "Technikai precizitás meccsintenzitáson, egyérintős játék, döntéshozatal gyorsítása.",
        },
        {
            "Terület": "Taktika",
            "Fókusz": "Strukturált pressing, build-up koncepciók, ellenfélre szabott taktikai terv.",
        },
        {
            "Terület": "Erőnlét",
            "Fókusz": "Iramváltás, ismétléses sprintek, periodizált terhelés heti 3–4 edzéssel.",
        },
        {
            "Terület": "Játékforma",
            "Fókusz": "11v11 taktikai edzések, speciális fázisok (pl. labdakihozatal, rögzített szituációk).",
        },
        {
            "Terület": "Mentális",
            "Fókusz": "Versenyközpontú gondolkodás, meccsre fókuszált hétközi munka.",
        },
    ],
    "Felnőtt profi": [
        {
            "Terület": "Technika",
            "Fókusz": "Top szintű végrehajtás nyomás alatt, első érintés, tempóváltás labdával.",
        },
        {
            "Terület": "Taktika",
            "Fókusz": "Komplex csapatszintű modellek (pressing, build-up, átmenetek, pozíciós játék).",
        },
        {
            "Terület": "Erőnlét",
            "Fókusz": "Meccsintenzitás replikálása, ACWR, GPS alapú terhelésmenedzsment, mikro/mezociklusok.",
        },
        {
            "Terület": "Játékforma",
            "Fókusz": "Matchday-hez igazított fázisedzések, specifikus szituációk magas minőségben.",
        },
        {
            "Terület": "Mentális",
            "Fókusz": "Nyomáskezelés, fókusz, profi életmód és regeneráció.",
        },
    ],
}


def get_periodization_table(age_group: str) -> pd.DataFrame | None:
    rows = PERIODIZATION_PROFILES.get(age_group)
    if not rows:
        return None
    return pd.DataFrame(rows)


# =====================================================
# 1. SEGÉDFÜGGVÉNYEK – SZŰRÉS, VÁLASZTÁS, ACWR
# =====================================================

def smart_filter(
    db: List[Dict[str, Any]],
    age_group: str,
    tactical_goal: str,
    technical_goal: str,
    fitness_goal: str,
    period_week: int,
    stage: str,
) -> List[Dict[str, Any]]:
    def matches(ex: Dict[str, Any], strict: bool) -> bool:
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
    db: List[Dict[str, Any]],
    age_group: str,
    tactical_goal: str,
    technical_goal: str,
    fitness_goal: str,
    period_week: int,
    stage: str,
) -> Dict[str, Any]:
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
# 2. RAJZ GENERÁLÓ – RONDÓ
# =====================================================

def build_custom_rondo_diagram(
    attackers: int,
    defenders: int,
    size_rel: int,
    theme: str,
) -> Dict[str, Any]:
    """
    Körülbelüli 0–100-as koordinátarendszerben rajzol rondót.
    """
    center_x, center_y = 50, 50
    half = size_rel / 2

    area = {
        "x": center_x - half,
        "y": center_y - half,
        "w": size_rel,
        "h": size_rel,
    }

    players = []
    cones = []

    # támadók – sarkok + oldal-középsők
    base_positions = [
        (center_x - half, center_y - half),
        (center_x + half, center_y - half),
        (center_x + half, center_y + half),
        (center_x - half, center_y + half),
        (center_x, center_y - half),
        (center_x, center_y + half),
        (center_x - half, center_y),
        (center_x + half, center_y),
    ]
    for i in range(attackers):
        x, y = base_positions[i]
        players.append({"id": f"A{i+1}", "label": str(i+1), "x": x, "y": y, "team": "home"})
        cones.append({"x": x, "y": y})

    # védők – középen kis „X” alakban
    def_positions = [
        (center_x - 3, center_y),
        (center_x + 3, center_y),
        (center_x, center_y + 3),
        (center_x, center_y - 3),
    ]
    for j in range(defenders):
        x, y = def_positions[j]
        players.append({"id": f"D{j+1}", "label": "X", "x": x, "y": y, "team": "away"})

    # labda
    ball = {"owner_id": "A1"}

    # passz-lánc
    passes = []
    attacker_ids = [f"A{i+1}" for i in range(attackers)]
    for i in range(len(attacker_ids)):
        from_id = attacker_ids[i]
        to_id = attacker_ids[(i + 1) % len(attacker_ids)]
        passes.append({"from_id": from_id, "to_id": to_id})

    # futások – téma szerint
    runs = []
    if theme == "pressing":
        for j in range(defenders):
            runs.append({"from_id": f"D{j+1}", "to": {"x": center_x, "y": center_y}})
    else:  # labdabirtoklás / possession
        for i in range(min(3, attackers)):
            pl = players[i]
            runs.append({"from_id": pl["id"], "to": {"x": pl["x"] + 3, "y": pl["y"]}})

    text_labels = [
        {"x": 5, "y": 95, "text": f"Rondó {attackers}v{defenders} – {theme}"},
    ]

    return {
        "pitch": {"type": "full", "orientation": "horiz"},
        "players": players,
        "cones": cones,
        "ball": ball,
        "area": area,
        "passes": passes,
        "runs": runs,
        "text_labels": text_labels,
        "mini_goals": [],
    }


# =====================================================
# 3. RAJZ GENERÁLÓ – FÉLPÁLYÁS JÁTÉK / FELÁLLÁS
# =====================================================

def _line_positions(x: float, n: int, y_min: float = 30, y_max: float = 70):
    if n == 1:
        return [(x, 50)]
    step = (y_max - y_min) / (n - 1)
    return [(x, y_min + i * step) for i in range(n)]


def build_custom_halfpitch_game_diagram(
    formation: str,
    theme: str,
) -> Dict[str, Any]:
    """
    Félpályás játék két csapattal – a formation string alapján (pl. '1-2-3-1').
    1 kapus + sorok.
    """
    # egyszerűsített: 1 GK + N sor
    try:
        lines = [int(x) for x in formation.split("-")[1:]]  # GK után
    except Exception:
        lines = [2, 3, 1]  # fallback 1-2-3-1

    # RED (home) balról támad jobbra
    players = []

    # Kapusok
    players.append({"id": "R_GK", "label": "GK", "x": 10, "y": 50, "team": "keeper"})
    players.append({"id": "B_GK", "label": "GK", "x": 90, "y": 50, "team": "keeper"})

    # x-pozíciók sorokra (védők, kp, csatár)
    line_x = [25, 45, 65, 80]  # annyit használunk, ahány sor van

    # vörös csapat
    red_ids = []
    for idx, num in enumerate(lines):
        x = line_x[idx]
        for i, (px, py) in enumerate(_line_positions(x, num)):
            pid = f"R_{idx}_{i}"
            label = str(i + 2)  # csak hogy ne GK legyen
            players.append({"id": pid, "label": label, "x": px, "y": py, "team": "home"})
            red_ids.append(pid)

    # kék csapat – tükrözés
    blue_ids = []
    for idx, num in enumerate(lines):
        x = 100 - line_x[idx]
        for i, (px, py) in enumerate(_line_positions(x, num)):
            pid = f"B_{idx}_{i}"
            label = str(i + 2)
            players.append({"id": pid, "label": label, "x": px, "y": py, "team": "away"})
            blue_ids.append(pid)

    # labda + passz / futás téma szerint
    passes = []
    runs = []
    ball = {}

    if theme == "labdakihozatal / build-up":
        ball = {"owner_id": "R_GK"}
        # GK -> legközelebbi védő -> középpályás -> csatár
        if red_ids:
            first_line = [pid for pid in red_ids if pid.startswith("R_0_")]
            second_line = [pid for pid in red_ids if pid.startswith("R_1_")]
            third_line = [pid for pid in red_ids if pid.startswith("R_2_")]
            chain = ["R_GK"]
            if first_line:
                chain.append(first_line[0])
            if second_line:
                chain.append(second_line[0])
            if third_line:
                chain.append(third_line[0])
            for i in range(len(chain) - 1):
                passes.append({"from_id": chain[i], "to_id": chain[i+1]})
        # futások: szélsők felfutnak
        for pid in red_ids[-2:]:
            runs.append({"from_id": pid, "to": {"x": 72, "y": 55}})
    elif theme == "pressing":
        # labda a kék védőnél
        ball = {"owner_id": blue_ids[0]} if blue_ids else {}
        # pressing futások vörös csatártól / kp-tól
        for pid in red_ids[-3:]:
            runs.append({"from_id": pid, "to": {"x": 60, "y": 50}})
    else:  # befejezés / általános
        ball = {"owner_id": red_ids[-1]} if red_ids else {}
        if red_ids:
            passes.append({"from_id": red_ids[-1], "to_id": "R_GK"})
            runs.append({"from_id": red_ids[-1], "to": {"x": 85, "y": 50}})

    text_labels = [
        {"x": 5, "y": 95, "text": f"Félpályás játék – {formation}, téma: {theme}"},
    ]

    return {
        "pitch": {"type": "full", "orientation": "horiz"},
        "players": players,
        "cones": [],
        "ball": ball,
        "area": None,
        "passes": passes,
        "runs": runs,
        "text_labels": text_labels,
        "mini_goals": [],
    }


# =====================================================
# 4. PDF – MAGYAR EXPORT
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


def create_pdf(plan: List[Dict[str, Any]], plan_meta: Dict[str, Any],
               coach_notes: str, exercise_notes: Dict[str, str]) -> BytesIO:
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
            f"Formátum: {ex.get('format','')}   |   Típus: {ex['exercise_type']}   |   Időtartam: {ex['duration_min']} perc",
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
# 5. STREAMLIT UI – EDZÉSTERV + INTERAKTÍV RAJZ KÉRDEZŐ
# =====================================================

st.set_page_config(page_title="Training Blueprint – edzéstervező", layout="wide")

st.title("⚽ Training Blueprint – edzéstervező demó")

st.write(
    "A bal oldali szűrők alapján generálunk egy 4 blokkból álló edzéstervet. "
    "Ezután megadhatod, **melyik gyakorlathoz szeretnél saját rajzot**, és "
    "néhány kérdésre válaszolva az ábra ehhez igazodik. "
    "A kiválasztott korosztályhoz tartozó **periodizációs fókusz** is megjelenik."
)

# ---- Oldalsáv: általános edzés paraméterek ----

st.sidebar.header("🎯 Edzés paraméterek")

age_group = st.sidebar.selectbox(
    "Korosztály / szint",
    [
        "U7–U11",
        "U12–U15",
        "U16–U19",
        "Felnőtt amatőr",
        "Felnőtt félprofi",
        "Felnőtt profi",
    ],
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

period_week = st.sidebar.slider(
    "Periódizációs hét (1–4)", min_value=1, max_value=4, value=1
)

coach_id = st.sidebar.text_input("Edző ID", value="coach_1")

st.sidebar.markdown("---")
st.sidebar.header("🖼 Saját rajz beállításai")

use_custom_diagram = st.sidebar.checkbox("Saját rajz egy kiválasztott gyakorlathoz")

custom_config = None
selected_stage_tag = None

if use_custom_diagram:
    stage_label_to_tag = {
        "Bemelegítés": "warmup",
        "Cél1 – kis játék": "small",
        "Cél2 – nagyobb játék": "large",
        "Cél3 – fő rész / meccsjáték": "main",
    }
    stage_label = st.sidebar.selectbox(
        "Melyik gyakorlathoz rajzoljunk?",
        list(stage_label_to_tag.keys()),
        index=0,
    )
    selected_stage_tag = stage_label_to_tag[stage_label]

    drill_type = st.sidebar.radio(
        "Gyakorlat típusa",
        ["Rondó", "Játék / mérkőzés"],
        index=0,
    )

    if drill_type == "Rondó":
        attackers = st.sidebar.slider("Támadók száma", 3, 8, 4)
        defenders = st.sidebar.slider("Védők száma", 1, 4, 2)
        size_rel = st.sidebar.slider("Négyzet mérete (relatív)", 12, 30, 18)
        theme_rondo = st.sidebar.selectbox(
            "Fő téma",
            ["labdabirtoklás", "pressing"],
            index=0,
        )
        custom_config = {
            "type": "rondo",
            "attackers": attackers,
            "defenders": defenders,
            "size_rel": size_rel,
            "theme": theme_rondo,
        }
    else:
        formation = st.sidebar.selectbox(
            "Felállási forma (1 + sorok)",
            ["1-2-3-1", "1-3-2-1", "1-2-2-2"],
            index=0,
        )
        theme_game = st.sidebar.selectbox(
            "Téma",
            ["labdakihozatal / build-up", "pressing", "befejezés"],
            index=0,
        )
        custom_config = {
            "type": "game",
            "formation": formation,
            "theme": theme_game,
        }

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
        ex = pick_exercise_for_stage(
            DEMO_DB,
            age_group=age_group if age_group in ["U12–U15", "U16–U19"] else "",
            tactical_goal=tactical_goal,
            technical_goal=technical_goal,
            fitness_goal=fitness_goal,
            period_week=period_week,
            stage=stage_tag,
        )

        # Ha ez az a blokk, amihez saját rajzot kérsz, akkor felülírjuk a diagramot
        if use_custom_diagram and custom_config and stage_tag == selected_stage_tag:
            if custom_config["type"] == "rondo":
                diag = build_custom_rondo_diagram(
                    attackers=custom_config["attackers"],
                    defenders=custom_config["defenders"],
                    size_rel=custom_config["size_rel"],
                    theme=custom_config["theme"],
                )
                ex["diagram_v1"] = diag
                ex["exercise_type"] = "rondó"
                ex["format"] = f"{custom_config['attackers']}v{custom_config['defenders']}"
                ex["title_hu"] = f"Saját rondó {ex['format']}"
            else:
                diag = build_custom_halfpitch_game_diagram(
                    formation=custom_config["formation"],
                    theme=custom_config["theme"],
                )
                ex["diagram_v1"] = diag
                ex["exercise_type"] = "game"
                ex["format"] = custom_config["formation"]
                ex["title_hu"] = f"Saját játék – {custom_config['formation']}"

        if ex:
            plan.append({"stage_tag": stage_tag, "stage_title": stage_title, "exercise": ex})

    if not plan:
        st.error("Nem találtam egyetlen gyakorlatsort sem – próbáld lazítani a szűrőket.")
    else:
        st.success("✅ Edzésterv generálva a fenti paraméterek alapján.")
        st.session_state["plan"] = plan
        st.session_state["plan_meta"] = plan_meta
        st.session_state["coach_notes_for_pdf"] = coach_notes

# ---- Terv megjelenítése ----

if "plan" in st.session_state and st.session_state["plan"]:
    plan = st.session_state["plan"]
    plan_meta = st.session_state["plan_meta"]

    st.header("📝 Edzésterv összefoglaló")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Korosztály / szint", plan_meta["age_group"])
        st.metric("Periódizációs hét", plan_meta["period_week"])
    with col2:
        st.write("**Taktikai cél:**", plan_meta["tactical_goal"])
        st.write("**Technikai cél:**", plan_meta["technical_goal"])
    with col3:
        st.write("**Erőnléti cél:**", plan_meta["fitness_goal"])
        st.write("**Edző ID:**", plan_meta["coach_id"])

    # 🔹 Periodizációs táblázat
    st.subheader("📋 Periodizációs fókusz a kiválasztott korosztályra / szintre")
    period_df = get_periodization_table(plan_meta["age_group"])
    if period_df is not None:
        st.table(period_df)
    else:
        st.info("Ehhez a korosztályhoz / szinthez még nincs periodizációs profil definiálva.")

    st.subheader("📊 Terhelés és ACWR (demó)")
    total_session_load = sum(ex["exercise"]["duration_min"] for ex in plan) * 10
    acwr_df = demo_acwr_series(total_session_load)
    st.caption("Az ACWR itt csak demo jellegű, később valós GPS / terhelésadatokra cseréljük.")
    st.line_chart(acwr_df.set_index("Hét")[["Terhelés", "ACWR"]])

    st.header("📚 Gyakorlatok blokkra bontva")

    for block in plan:
        stage_title = block["stage_title"]
        ex = block["exercise"]
        ex_id = ex["id"]

        st.subheader(stage_title)
        st.markdown(f"**{ex['title_hu']}**")

        diagram_spec = ex.get("diagram_v1")
        if diagram_spec:
            fig = draw_drill(diagram_spec, show=False)
            st.pyplot(fig, use_container_width=True)

        st.write(
            f"*Formátum:* {ex.get('format','')}  |  *Típus:* {ex['exercise_type']}  |  "
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
