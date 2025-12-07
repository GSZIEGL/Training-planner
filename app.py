import random
import json
import copy
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
# 0/B. PERIODIZÁCIÓS PROFILOK – KOROSZTÁLY / FELNŐTT + HÉT
# =====================================================

PERIODIZATION_PROFILES: Dict[str, Dict[int, List[Dict[str, str]]]] = {
    # ... (VÁLTOZATLAN: a nagy PERIODIZATION_PROFILES blokk marad, ahogy nálad volt)
    # Itt hagyd érintetlenül az egész PERIODIZATION_PROFILES dictet
    # (nem írom újra végig, csak másold át az eredetit a kódodban).
    # --- IDE ILLesZD BE AZ EREDETI PERIODIZATION_PROFILES TARTALMÁT ---
}


def get_week_focus(age_group: str, week: int) -> str:
    # Alapértelmezett szöveg
    default = "Általános edzésfókusz a korosztály / szint szintjén."

    # Utánpótlás
    if age_group in ["U7–U11", "U12–U15", "U16–U19"]:
        youth_map = {
            1: "1. hét: alap technikai és játékfókusz, kisebb intenzitással.",
            2: "2. hét: taktikai elvek erősítése, több szervezett kis- és nagypályás játék.",
            3: "3. hét: intenzívebb terhelés, nagyobb létszámú játékok, pressing / átmenetek.",
            4: "4. hét: mérkőzésfókusz, ismétlés, stabilitás, regeneráció figyelembevételével.",
        }
        return youth_map.get(week, default)

    # Felnőtt amatőr
    if age_group == "Felnőtt amatőr":
        amatőr_map = {
            1: "1. hét: általános állóképesség és alap taktikai szervezettség.",
            2: "2. hét: intenzívebb játékok, több pressing / átmenet.",
            3: "3. hét: csúcsterhelés a rendelkezésre álló időkeret mellett.",
            4: "4. hét: terhelés kismértékű csökkentése, meccsre hangolás.",
        }
        return amatőr_map.get(week, default)

    # Felnőtt félprofi
    if age_group == "Felnőtt félprofi":
        félprofi_map = {
            1: "1. hét: terhelés felépítése, alap taktikai fókusz (védekezési elvek).",
            2: "2. hét: nagyobb intenzitás, pressing és build-up hangsúllyal.",
            3: "3. hét: csúcsterhelés, meccsintenzitás modellezése edzésen.",
            4: "4. hét: visszaterhelés, frissítés, ellenfélre szabott taktikai finomhangolás.",
        }
        return félprofi_map.get(week, default)

    # Felnőtt profi
    if age_group == "Felnőtt profi":
        profi_map = {
            1: "1. hét: alap ritmus felvétele, csapatszintű alapelvek frissítése.",
            2: "2. hét: taktikai részletek, specifikus pressing / build-up fázisok magas intenzitáson.",
            3: "3. hét: csúcsintenzitás, meccsprofil szimulálása, ACWR figyelembevételével.",
            4: "4. hét: tapering, frissítés, mérkőzésfókuszú edzésstruktúra.",
        }
        return profi_map.get(week, default)

    return default


def get_periodization_table(age_group: str, week: int):
    """
    Visszaadja a korosztály / szint + hét alapján a teljes periodizációs táblát.
    Minden hétre külön sorok vannak felvéve a PERIODIZATION_PROFILES-ben.
    """
    group = PERIODIZATION_PROFILES.get(age_group)
    if not group:
        return None

    rows = group.get(week)
    if not rows:
        rows = group.get(1, [])

    if not rows:
        return None

    return pd.DataFrame(rows)


# =====================================================
# 0/C. JSON GYAKORLATOK BETÖLTÉSE + NORMALIZÁLÁS
# =====================================================

DRILLS_JSON_PATH = "drill_metadata_with_u7u9.json"
USAGE_LOG_PATH = "drill_usage_log.json"


def _map_edzes_resze_to_stage_tag(value: str) -> str:
    mapping = {
        "bemelegites": "warmup",
        "cel1": "small",
        "cel2": "large",
        "cel3": "main",
    }
    return mapping.get(value, "")


def _normalize_fo_taktikai_cel(value: str) -> str:
    mapping = {
        "jatek_szervezes": "jatekszervezes",
        "jateksszervezes": "jatekszervezes",
    }
    return mapping.get(value, value)


def _map_age_buckets_to_ui(age_raw_list: List[str]) -> List[str]:
    """
    JSON: ['U7-U9', 'U10-U12', 'U13-U15', 'U16-U19', 'felnott']
    UI:   'U7–U11', 'U12–U15', 'U16–U19', 'Felnőtt amatőr', 'Felnőtt félprofi', 'Felnőtt profi'
    """
    ui_groups = set()
    for bucket in age_raw_list:
        if bucket in ("U7-U9", "U10-U12"):
            ui_groups.add("U7–U11")
        if bucket in ("U10-U12", "U13-U15"):
            ui_groups.add("U12–U15")
        if bucket == "U16-U19":
            ui_groups.add("U16–U19")
        if bucket == "felnott":
            ui_groups.update(["Felnőtt amatőr", "Felnőtt félprofi", "Felnőtt profi"])
    return sorted(ui_groups)


def normalize_demo_exercises(demo_db: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for ex in demo_db:
        ex_copy = copy.deepcopy(ex)
        ex_copy["source"] = "demo"
        ex_copy.setdefault("stage_tag", ex.get("stage_tag"))
        ex_copy["age_groups_ui"] = [ex.get("age_group")] if ex.get("age_group") else []
        ex_copy["main_tactical_goal"] = ex.get("tactical_goal")
        ex_copy["tactical_tags"] = []
        ex_copy["technical_tags"] = [ex.get("technical_goal")] if ex.get("technical_goal") else []
        ex_copy["physical_tags"] = [ex.get("fitness_goal")] if ex.get("fitness_goal") else []
        ex_copy["duration_min"] = ex.get("duration_min", 15)
        ex_copy.setdefault("organisation_hu", "-")
        ex_copy.setdefault("description_hu", "-")
        ex_copy.setdefault("coaching_points_hu", [])
        ex_copy.setdefault("variations_hu", [])
        normalized.append(ex_copy)
    return normalized


def normalize_json_exercises(raw_drills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for idx, d in enumerate(raw_drills):
        stage_tag = _map_edzes_resze_to_stage_tag(d.get("edzes_resze", ""))
        if not stage_tag:
            continue

        main_tact = _normalize_fo_taktikai_cel(d.get("fo_taktikai_cel", ""))
        age_raw = d.get("ajanlott_korosztalyok", [])
        age_ui = _map_age_buckets_to_ui(age_raw)

        title = f"{main_tact.replace('_', ' ').capitalize()} – {d.get('gyakorlat_kategoria', '')}"
        description = (
            "Automatikusan generált leírás az adatbázis metaadatai alapján. "
            f"Fő taktikai cél: {main_tact.replace('_', ' ')}. "
            f"Taktikai címkék: {', '.join(d.get('taktikai_cel_cimkek', []))}. "
            f"Technikai címkék: {', '.join(d.get('technikai_cel_cimkek', []))}. "
            f"Kondicionális címkék: {', '.join(d.get('kondicionalis_cel_cimkek', []))}."
        )

        ex = {
            "id": f"json_{idx}",
            "source": "json",
            "stage_tag": stage_tag,
            "age_groups_ui": age_ui,
            "age_groups_raw": age_raw,
            "main_tactical_goal": main_tact,
            "tactical_tags": d.get("taktikai_cel_cimkek", []),
            "technical_tags": d.get("technikai_cel_cimkek", []),
            "physical_tags": d.get("kondicionalis_cel_cimkek", []),
            "category": d.get("gyakorlat_kategoria", ""),
            "duration_min": d.get("ido_perc", 15),
            "title_hu": title,
            "format": "",
            "exercise_type": d.get("gyakorlat_kategoria", ""),
            "pitch_size": "",
            "intensity": "",
            "organisation_hu": "-",
            "description_hu": description,
            "coaching_points_hu": [],
            "variations_hu": [],
            "diagram_v1": None,
            "file_name": d.get("file_name"),
        }
        normalized.append(ex)
    return normalized


@st.cache_data
def load_all_exercises() -> List[Dict[str, Any]]:
    """
    Betölti és normalizálja az összes gyakorlatot:
    - DEMO_DB (kézzel felvitt, részletes leírással)
    - drill_metadata_with_u7u9.json (829 gyakorlat)
    """
    normalized = normalize_demo_exercises(DEMO_DB)

    try:
        with open(DRILLS_JSON_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        normalized.extend(normalize_json_exercises(raw))
    except FileNotFoundError:
        st.warning(
            "A 'drill_metadata_with_u7u9.json' fájl nem található. "
            "Jelenleg csak a demó gyakorlatok érhetők el."
        )
    except Exception as e:
        st.error(f"Hiba a JSON gyakorlatok betöltésekor: {e}")

    return normalized


def load_usage_counts() -> Dict[str, int]:
    try:
        with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k): int(v) for k, v in data.items()}
            return {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def save_usage_counts(counts: Dict[str, int]) -> None:
    try:
        with open(USAGE_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(counts, f, ensure_ascii=False, indent=2)
    except Exception:
        # nem kritikus, ha nem sikerül menteni
        pass


def mark_drills_used(drill_ids: List[str]) -> None:
    """
    PDF generáláskor hívjuk: ezek a gyakorlatok ténylegesen "elhasználtak".
    Így az app a jövőben inkább a ritkábban használt gyakorlatokat preferálja.
    """
    counts = load_usage_counts()
    for did in drill_ids:
        counts[did] = counts.get(did, 0) + 1
    save_usage_counts(counts)


# =====================================================
# 1. SEGÉDFÜGGVÉNYEK – SZŰRÉS, VÁLASZTÁS, ACWR
# =====================================================

TACTICAL_UI_TO_JSON = {
    "labdabirtoklás": {
        "jatekszervezes",
        "jatek_szervezes",
        "jateksszervezes",
        "labdakihozatal",
    },
    "labdaszerzés / pressing": {
        "vedekezes_labdaszerzes",
        "atmenet_vedekezesbe",
    },
    "labdakihozatal / build-up": {"labdakihozatal"},
    "befejezés, gólhelyzet-teremtés": {
        "befejezes",
        "atmenet_tamadasba",
    },
}


def _tactical_match_ui_json(ui_value: str, json_main: str) -> bool:
    if not ui_value or not json_main:
        return False
    allowed = TACTICAL_UI_TO_JSON.get(ui_value, set())
    return json_main in allowed


def _score_exercise(
    ex: Dict[str, Any],
    age_group: str,
    tactical_goal: str,
    technical_goal: str,
    fitness_goal: str,
) -> int:
    """
    Egyszerű pontozásos logika.
    - stage_tag-et előtte már ellenőrizzük
    - itt age_group + taktikai cél alapján adunk pontokat
    - technikai / fitness most minimálisan vagy egyáltalán nem szűr
    """
    score = 0
    source = ex.get("source", "json")

    # Korosztály / szint
    if age_group:
        if source == "demo":
            if ex.get("age_group") == age_group:
                score += 3
        else:
            if age_group in ex.get("age_groups_ui", []):
                score += 3

    # Taktikai cél
    if tactical_goal:
        if source == "demo":
            if ex.get("tactical_goal") == tactical_goal:
                score += 3
        else:
            if _tactical_match_ui_json(
                tactical_goal, ex.get("main_tactical_goal", "")
            ):
                score += 3

    # Technikai cél – most csak demóban van értelme
    if technical_goal:
        if source == "demo" and ex.get("technical_goal") == technical_goal:
            score += 1

    # Erőnléti cél – demóban használjuk, JSON-nál később lehet okosítani
    if fitness_goal:
        if source == "demo" and ex.get("fitness_goal") == fitness_goal:
            score += 1

    return score


def smart_filter(
    db: List[Dict[str, Any]],
    age_group: str,
    tactical_goal: str,
    technical_goal: str,
    fitness_goal: str,
    period_week: int,  # későbbre: periodizációs súlyozáshoz használható
    stage: str,
    used_ids: set | None = None,
) -> List[Dict[str, Any]]:
    """
    Pontozásos szűrés:
    - mindig egyeznie kell a stage_tag-nek
    - elkerüljük az aktuális edzésben már használt gyakorlatokat (used_ids)
    - pont a korosztály + taktikai cél egyezéséért
    """
    if used_ids is None:
        used_ids = set()

    usage_counts = load_usage_counts()

    candidates = []
    for ex in db:
        if ex.get("stage_tag") != stage:
            continue
        if ex.get("id") in used_ids:
            continue

        base_score = _score_exercise(ex, age_group, tactical_goal, technical_goal, fitness_goal)
        candidates.append((ex, base_score))

    if not candidates:
        return []

    # Max pontszám
    max_score = max(score for _, score in candidates)

    # Először a legmagasabb pontszámúakat vesszük
    best = [ex for ex, score in candidates if score == max_score]

    # Köztük preferáljuk a ritkábban használtakat
    if best:
        min_usage = min(usage_counts.get(ex["id"], 0) for ex in best)
        best = [ex for ex in best if usage_counts.get(ex["id"], 0) == min_usage]

    return best


def pick_exercise_for_stage(
    db: List[Dict[str, Any]],
    age_group: str,
    tactical_goal: str,
    technical_goal: str,
    fitness_goal: str,
    period_week: int,
    stage: str,
    used_ids: set | None = None,
) -> Dict[str, Any]:
    candidates = smart_filter(
        db,
        age_group,
        tactical_goal,
        technical_goal,
        fitness_goal,
        period_week,
        stage,
        used_ids=used_ids,
    )
    if not candidates:
        return {}
    chosen = random.choice(candidates)
    # Ne a globális adatbázist módosítsuk – mindig másolatot adunk vissza
    return copy.deepcopy(chosen)


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

    def_positions = [
        (center_x - 3, center_y),
        (center_x + 3, center_y),
        (center_x, center_y + 3),
        (center_x, center_y - 3),
    ]
    for j in range(defenders):
        x, y = def_positions[j]
        players.append({"id": f"D{j+1}", "label": "X", "x": x, "y": y, "team": "away"})

    ball = {"owner_id": "A1"}

    passes = []
    attacker_ids = [f"A{i+1}" for i in range(attackers)]
    for i in range(len(attacker_ids)):
        from_id = attacker_ids[i]
        to_id = attacker_ids[(i + 1) % len(attacker_ids)]
        passes.append({"from_id": from_id, "to_id": to_id})

    runs = []
    if theme == "pressing":
        for j in range(defenders):
            runs.append({"from_id": f"D{j+1}", "to": {"x": center_x, "y": center_y}})
    else:  # labdabirtoklás
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
    try:
        lines = [int(x) for x in formation.split("-")[1:]]  # GK után
    except Exception:
        lines = [2, 3, 1]  # fallback 1-2-3-1

    players = []
    players.append({"id": "R_GK", "label": "GK", "x": 10, "y": 50, "team": "keeper"})
    players.append({"id": "B_GK", "label": "GK", "x": 90, "y": 50, "team": "keeper"})

    line_x = [25, 45, 65, 80]

    red_ids = []
    for idx, num in enumerate(lines):
        x = line_x[idx]
        for i, (px, py) in enumerate(_line_positions(x, num)):
            pid = f"R_{idx}_{i}"
            label = str(i + 2)
            players.append({"id": pid, "label": label, "x": px, "y": py, "team": "home"})
            red_ids.append(pid)

    blue_ids = []
    for idx, num in enumerate(lines):
        x = 100 - line_x[idx]
        for i, (px, py) in enumerate(_line_positions(x, num)):
            pid = f"B_{idx}_{i}"
            label = str(i + 2)
            players.append({"id": pid, "label": label, "x": px, "y": py, "team": "away"})
            blue_ids.append(pid)

    passes = []
    runs = []
    ball = {}

    if theme == "labdakihozatal / build-up":
        ball = {"owner_id": "R_GK"}
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
        for pid in red_ids[-2:]:
            runs.append({"from_id": pid, "to": {"x": 72, "y": 55}})
    elif theme == "pressing":
        ball = {"owner_id": blue_ids[0]} if blue_ids else {}
        for pid in red_ids[-3:]:
            runs.append({"from_id": pid, "to": {"x": 60, "y": 50}})
    else:
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


def create_pdf(
    plan: List[Dict[str, Any]],
    plan_meta: Dict[str, Any],
    coach_notes: str,
    exercise_notes: Dict[str, str],
) -> BytesIO:
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

        pdf.cell(0, 6, f"Cím: {ex.get('title_hu', ex_id)}", ln=1)
        pdf.cell(
            0,
            6,
            f"Formátum: {ex.get('format','')}   |   Típus: {ex.get('exercise_type','')}   |   "
            f"Időtartam: {ex.get('duration_min','?')} perc",
            ln=1,
        )
        pdf.cell(
            0,
            6,
            f"Pályaméret: {ex.get('pitch_size','')}   |   Intenzitás: {ex.get('intensity','')}",
            ln=1,
        )

        pdf.ln(3)
        pdf.cell(0, 6, "Szervezés:", ln=1)
        multiline(pdf, ex.get("organisation_hu", "-"))

        pdf.ln(2)
        pdf.cell(0, 6, "Leírás / menet:", ln=1)
        multiline(pdf, ex.get("description_hu", "-"))

        pdf.ln(2)
        pdf.cell(0, 6, "Coaching pontok:", ln=1)
        coaching_points = ex.get("coaching_points_hu", []) or []
        bullet_text = "\n".join([f"• {c}" for c in coaching_points])
        multiline(pdf, bullet_text or "-")

        variations = ex.get("variations_hu", []) or []
        if variations:
            pdf.ln(2)
            pdf.cell(0, 6, "Variációk:", ln=1)
            var_text = "\n".join([f"• {v}" for v in variations])
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
    "A bal oldali szűrők alapján generálunk egy 4 blokkból álló edzéstervet "
    "(bemelegítés + 3 fő rész, **minden edzésrészben 1 gyakorlat**). "
    "Ezután megadhatod, **melyik gyakorlathoz szeretnél saját rajzot**, és "
    "néhány kérdésre válaszolva az ábra ehhez igazodik. "
    "A kiválasztott korosztályhoz tartozó **periodizációs fókusz** is megjelenik."
)

EXERCISE_DB = load_all_exercises()

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

    used_ids_in_plan = set()

    for stage_tag, stage_title in stages:
        ex = pick_exercise_for_stage(
            EXERCISE_DB,
            age_group=age_group,
            tactical_goal=tactical_goal,
            technical_goal=technical_goal,
            fitness_goal=fitness_goal,
            period_week=period_week,
            stage=stage_tag,
            used_ids=used_ids_in_plan,
        )

        if not ex:
            continue

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

        used_ids_in_plan.add(ex["id"])
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
    period_df = get_periodization_table(
        plan_meta["age_group"],
        plan_meta["period_week"],
    )

    if period_df is not None:
        st.table(period_df)
    else:
        st.info("Ehhez a korosztályhoz / szinthez még nincs periodizációs profil definiálva.")

    st.subheader("📊 Terhelés és ACWR (demó)")
    total_session_load = sum(ex["exercise"].get("duration_min", 0) for ex in plan) * 10
    acwr_df = demo_acwr_series(total_session_load)
    st.caption("Az ACWR itt csak demo jellegű, később valós GPS / terhelésadatokra cseréljük.")
    st.line_chart(acwr_df.set_index("Hét")[["Terhelés", "ACWR"]])

    st.header("📚 Gyakorlatok blokkra bontva")

    for block in plan:
        stage_title = block["stage_title"]
        stage_tag = block["stage_tag"]
        ex = block["exercise"]
        ex_id = ex["id"]

        st.subheader(stage_title)
        st.markdown(f"**{ex.get('title_hu', ex_id)}**")

        # 🔄 Gyakorlat csere gomb – adott edzésrészhez
        reroll_key = f"reroll_{stage_tag}"
        if st.button("🔄 Gyakorlat cseréje ebben a blokkban", key=reroll_key):
            # jelenlegi terv többi gyakorlata, hogy ne legyen duplikáció edzésen belül
            used_ids_other = {b["exercise"]["id"] for b in plan if b is not block}

            new_ex = pick_exercise_for_stage(
                EXERCISE_DB,
                age_group=plan_meta["age_group"],
                tactical_goal=plan_meta["tactical_goal"] if plan_meta["tactical_goal"] != "nincs megadva" else "",
                technical_goal=plan_meta["technical_goal"] if plan_meta["technical_goal"] != "nincs megadva" else "",
                fitness_goal=plan_meta["fitness_goal"] if plan_meta["fitness_goal"] != "nincs megadva" else "",
                period_week=plan_meta["period_week"],
                stage=stage_tag,
                used_ids=used_ids_other,
            )

            if new_ex:
                # ha ez a blokk a custom diagram célpontja, itt is alkalmazzuk
                if use_custom_diagram and custom_config and stage_tag == selected_stage_tag:
                    if custom_config["type"] == "rondo":
                        diag = build_custom_rondo_diagram(
                            attackers=custom_config["attackers"],
                            defenders=custom_config["defenders"],
                            size_rel=custom_config["size_rel"],
                            theme=custom_config["theme"],
                        )
                        new_ex["diagram_v1"] = diag
                        new_ex["exercise_type"] = "rondó"
                        new_ex["format"] = f"{custom_config['attackers']}v{custom_config['defenders']}"
                        new_ex["title_hu"] = f"Saját rondó {new_ex['format']}"
                    else:
                        diag = build_custom_halfpitch_game_diagram(
                            formation=custom_config["formation"],
                            theme=custom_config["theme"],
                        )
                        new_ex["diagram_v1"] = diag
                        new_ex["exercise_type"] = "game"
                        new_ex["format"] = custom_config["formation"]
                        new_ex["title_hu"] = f"Saját játék – {custom_config['formation']}"

                block["exercise"] = new_ex
                st.session_state["plan"] = plan
                st.experimental_rerun()
            else:
                st.warning("Ehhez az edzésrészhez nem találtam új gyakorlatot a megadott szűrőkkel.")

        # Diagram (ha van)
        diagram_spec = ex.get("diagram_v1")
        if diagram_spec:
            fig = draw_drill(diagram_spec, show=False)
            st.pyplot(fig, use_container_width=True)

        st.write(
            f"*Formátum:* {ex.get('format','')}  |  *Típus:* {ex.get('exercise_type','')}  |  "
            f"*Időtartam:* {ex.get('duration_min','?')} perc  |  *Intenzitás:* {ex.get('intensity','')}"
        )
        st.write(f"*Pályaméret:* {ex.get('pitch_size','')}")

        with st.expander("Szervezés (HU)"):
            st.write(ex.get("organisation_hu", "-"))

        with st.expander("Leírás / menet (HU)"):
            st.write(ex.get("description_hu", "-"))

        with st.expander("Coaching pontok (HU)"):
            for c in ex.get("coaching_points_hu", []) or []:
                st.write("- " + c)

        with st.expander("Variációk (HU)"):
            for v in ex.get("variations_hu", []) or []:
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
            # itt tekintjük ténylegesen "elhasználtnak" az aktuális edzésterv gyakorlatait
            used_for_pdf = [block["exercise"]["id"] for block in plan]
            mark_drills_used(used_for_pdf)

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
