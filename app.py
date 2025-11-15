


import json
import random
import textwrap
from typing import List, Dict, Any

import requests
import streamlit as st

# ====== Opciós fordító EN -> HU (ha nem megy, az app attól még működik) ======
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR = GoogleTranslator(source="en", target="hu")
except Exception:
    TRANSLATOR = None


def en_to_hu(text: str):
    """Próbál angolról magyarra fordítani. Ha nem sikerül, None."""
    if not TRANSLATOR or not text:
        return None
    try:
        return TRANSLATOR.translate(text)
    except Exception:
        return None


# ====== STREAMLIT ALAPBEÁLLÍTÁS ======
st.set_page_config(
    page_title="chatbotfootball training planner",
    layout="wide"
)

st.title("⚽ chatbotfootball training planner – Easy2Coach edzésterv generátor")
st.markdown(
    """
    Ez az app az **Easy2Coach** scrapelt adatbázisából választ ki gyakorlatokat a megadott
    **korosztály**, **taktikai cél**, **technikai és erőnléti fókusz** alapján.

    A kimenet:  
    - 1️⃣ Bemelegítés (Warm-up)  
    - 2️⃣ Cél1 – kis létszámú taktikai feladat (Small-sided)  
    - 3️⃣ Cél2 – nagyobb létszámú taktikai játék  
    - 4️⃣ Cél3 – fő rész, lehetőség szerint **mérkőzésjáték (match game)**  
    """
)

# ====== OLDALSÁV – JSON FELTÖLTÉS ======
st.sidebar.header("1. Adatbázis betöltése")

json_file = st.sidebar.file_uploader(
    "Easy2Coach JSON (pl. easy2coach_full_exercises.json)",
    type=["json"]
)

if json_file is None:
    st.warning("⬅️ Töltsd fel a JSON adatbázist a bal oldali sávban, majd válaszd ki a paramétereket.")
    st.stop()

try:
    EX_DB: List[Dict[str, Any]] = json.load(json_file)
except Exception as e:
    st.error(f"Nem sikerült beolvasni a JSON-t: {e}")
    st.stop()

st.sidebar.success(f"✅ Betöltött gyakorlatok száma: {len(EX_DB)}")


# ====== SEGÉDFÜGGVÉNYEK – SZŰRÉS / SCORING ======

def get_image_url(ex: Dict[str, Any]):
    if ex.get("image_url"):
        return ex["image_url"]
    if ex.get("image"):
        return ex["image"]
    if isinstance(ex.get("images"), list) and ex["images"]:
        return ex["images"][0]
    return None


def exercise_text_blob(ex: Dict[str, Any]) -> str:
    parts = []
    parts.append(ex.get("title", ""))
    secs = ex.get("sections", {})
    for v in secs.values():
        parts.append(v or "")
    meta = ex.get("meta", {})
    for v in meta.values():
        parts.append(v or "")
    return " ".join(parts).lower()


def matches_age(ex: Dict[str, Any], age_tokens: List[str]) -> bool:
    if not age_tokens:
        return True
    age_text = ""
    meta = ex.get("meta", {})
    for k, v in meta.items():
        if "age" in k.lower():
            age_text += " " + str(v)
    if not age_text:
        return True
    age_text = age_text.lower()
    return any(tok.lower() in age_text for tok in age_tokens)


def is_game_like_blob(blob: str) -> bool:
    game_words = [
        "game", "match", "small-sided", "possession game",
        "7vs7", "7 vs 7", "8vs8", "8 vs 8",
        "9vs9", "9 vs 9", "10vs10", "10 vs 10",
        "11vs11", "11 vs 11", "finishing game"
    ]
    return any(w in blob for w in game_words)


def age_based_game_tokens(age_tokens_list: List[str]) -> List[str]:
    """Korosztály szerinti meccslétszám preferencia – fallback Cél3-hoz."""
    if any(a in ["U7", "U8", "U9"] for a in age_tokens_list):
        return ["4vs4", "4 vs 4", "5vs5", "5 vs 5"]
    if any(a in ["U10", "U11"] for a in age_tokens_list):
        return ["6vs6", "6 vs 6", "7vs7", "7 vs 7"]
    if any(a in ["U12", "U13"] for a in age_tokens_list):
        return ["7vs7", "7 vs 7", "8vs8", "8 vs 8", "9vs9", "9 vs 9"]
    if any(a in ["U14", "U15", "U16", "U17", "U18", "U19"] for a in age_tokens_list):
        return ["10vs10", "10 vs 10", "11vs11", "11 vs 11"]
    if any(a in ["Men", "Women's", "Adult"] for a in age_tokens_list):
        return ["10vs10", "10 vs 10", "11vs11", "11 vs 11", "full pitch", "match"]
    return []


def score_exercise_for_stage(
    ex: Dict[str, Any],
    stage: str,
    tact_keywords: List[str],
    tech_keywords: List[str],
    phys_keywords: List[str],
    goal2_format_tokens: List[str],
    goal3_format_tokens: List[str],
    goal3_profile_keywords: List[str],
    used_images: set
) -> float:
    blob = exercise_text_blob(ex)
    score = 0.0

    # taktikai
    for kw in tact_keywords:
        if kw.lower() in blob:
            score += 3

    # technikai
    for kw in tech_keywords:
        if kw.lower() in blob:
            score += 2

    # erőnléti
    for kw in phys_keywords:
        if kw.lower() in blob:
            score += 2

    is_warm_like = any(w in blob for w in ["warm-up", "warm up", "aufwärmen", "coordination"])
    is_main_like = any(w in blob for w in ["finishing", "goal", "6vs6", "7vs7", "8vs8", "half-field", "game"])
    is_game_like = is_game_like_blob(blob)

    if stage == "warmup":
        if is_warm_like:
            score += 6
        if is_main_like:
            score -= 4

    elif stage == "small":
        if any(w in blob for w in ["1vs1", "1 vs 1", "2vs2", "2 vs 2", "3vs3", "3 vs 3", "4vs4", "4 vs 4"]):
            score += 5

    elif stage == "large":
        if any(w in blob for w in ["5vs5", "5 vs 5", "6vs6", "6 vs 6", "7vs7", "7 vs 7", "8vs8", "8 vs 8"]):
            score += 4
        for kw in goal2_format_tokens:
            if kw.lower() in blob:
                score += 4
        if any(w in blob for w in ["build-up", "build up", "possession", "keeping the ball",
                                   "game systems", "team training", "organization", "organised"]):
            score += 4
        if any(w in blob for w in ["circuit", "course", "pure coordination"]):
            score -= 3
        if is_warm_like:
            score -= 3

    elif stage == "main":
        # Cél3 – mérkőzésjáték preferencia
        if is_game_like:
            score += 10
        else:
            score -= 8

        for kw in goal3_format_tokens:
            if kw.lower() in blob:
                score += 5

        for kw in goal3_profile_keywords:
            if kw.lower() in blob:
                score += 4

        if any(w in blob for w in ["drill", "circuit", "course", "pattern only"]):
            score -= 4

    img = get_image_url(ex)
    if img and img in used_images:
        score -= 50  # ugyanaz a kép erősen büntetve

    score += random.uniform(0, 1)
    return score


def pick_exercise_for_stage(
    EX_DB: List[Dict[str, Any]],
    stage: str,
    age_tokens: List[str],
    tact_keywords: List[str],
    tech_keywords: List[str],
    phys_keywords: List[str],
    goal2_format_tokens: List[str],
    goal3_format_tokens: List[str],
    goal3_profile_keywords: List[str],
    used_urls: set,
    used_images: set
):
    candidates = [ex for ex in EX_DB if matches_age(ex, age_tokens) and ex.get("url") not in used_urls]
    if not candidates:
        return None

    if stage == "main":
        # először game-like szűrés
        game_candidates = []
        for ex in candidates:
            blob = exercise_text_blob(ex)
            if is_game_like_blob(blob):
                game_candidates.append(ex)

        if game_candidates:
            candidates = game_candidates
        else:
            # nincs game-like → korosztály-alapú meccs létszám
            fmt_tokens_age = age_based_game_tokens(age_tokens)
            if fmt_tokens_age:
                fmt_cands = []
                for ex in candidates:
                    blob = exercise_text_blob(ex)
                    if any(tok.lower() in blob for tok in fmt_tokens_age):
                        fmt_cands.append(ex)
                if fmt_cands:
                    candidates = fmt_cands

    scored = [
        (
            score_exercise_for_stage(
                ex, stage,
                tact_keywords, tech_keywords, phys_keywords,
                goal2_format_tokens, goal3_format_tokens, goal3_profile_keywords,
                used_images
            ),
            ex
        )
        for ex in candidates
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_ex = scored[0]
    if best_score <= 0:
        return candidates[0]
    return best_ex


# ====== OLDALSÁV – PARAMÉTEREK ======
st.sidebar.header("2. Edzésparaméterek")

players_raw = st.sidebar.text_input(
    "Hány játékosra tervezünk? (pl. 10, 14, 18, '7-9')",
    value="14"
)

age_options = {
    "U7-U9": ["U7", "U8", "U9"],
    "U10-U11": ["U10", "U11"],
    "U12-U13": ["U12", "U13"],
    "U14-U15": ["U14", "U15"],
    "U16-U19": ["U16", "U17", "U18", "U19"],
    "Adult amateur": ["Men", "Women's", "Adult"],
    "Adult pro": ["Men", "Women's", "Adult"],
    "Any": []
}
age_label = st.sidebar.selectbox("Korosztály:", list(age_options.keys()), index=4)
age_tokens = age_options[age_label]

st.sidebar.subheader("Fő taktikai cél")
tact_dict = {
    "Build-up play (labdakihozatal)": ["build-up", "build up", "building up", "4-3-3", "4-4-2", "opening the field"],
    "Pressing & ball winning": ["pressing", "win the ball", "counter-press", "pressure"],
    "Finishing & chance creation": ["finishing", "shot on goal", "goal", "scoring", "final third"],
    "Ball circulation & possession": ["keeping the ball", "possession", "passing game"]
}
tact_label = st.sidebar.selectbox("Taktikai cél:", list(tact_dict.keys()), index=0)
tact_keywords = tact_dict[tact_label]

st.sidebar.subheader("Technikai fókusz(ok)")
tech_dict = {
    "Short passing / combination": ["short pass", "combination", "passing", "one touch"],
    "Long passes / crosses": ["long pass", "cross", "switch play", "diagonal"],
    "Ball control & first touch": ["ball control", "trapping", "first touch", "receiving"],
    "1v1 attacking": ["1vs1", "1 vs 1", "dribbling", "feint"],
    "1v1 defending": ["1vs1", "1 vs 1", "defending", "tackle"]
}
tech_selection = st.sidebar.multiselect(
    "Válassz technikai elemeket:",
    list(tech_dict.keys()),
    default=["Short passing / combination", "Ball control & first touch"]
)
tech_keywords = []
for key in tech_selection:
    tech_keywords.extend(tech_dict[key])

st.sidebar.subheader("Erőnléti fókusz")
phys_dict = {
    "Speed – gyorsaság, rövid sprintek, reakció": ["sprint", "speed", "reaction"],
    "Endurance – állóképesség, folyamatos játék": ["endurance", "continuous", "high intensity"],
    "Strength / duels – párharcok, test-test elleni játék": ["duel", "1vs1", "1 vs 1", "physical", "contact"],
    "Explosiveness / quickness – robbanékonyság, irányváltások": ["explosive", "acceleration", "change of direction"]
}
phys_label = st.sidebar.selectbox(
    "Erőnléti prioritás:",
    list(phys_dict.keys()),
    index=0
)
phys_keywords = phys_dict[phys_label]

total_time = st.sidebar.text_input("Össz edzésidő (pl. 75 perc, 90 perc):", value="90 perc")

st.sidebar.markdown("---")
st.sidebar.subheader("Cél2 – nagyobb létszámú játék")

goal2_format_options = {
    "5v5 / 5 vs 5": ["5vs5", "5 vs 5"],
    "6v6 / 6 vs 6": ["6vs6", "6 vs 6"],
    "7v7 vagy több": ["7vs7", "7 vs 7", "8vs8", "8 vs 8", "9vs9", "9 vs 9"],
    "Nincs preferencia": []
}
goal2_format_label = st.sidebar.selectbox(
    "Cél2 formátum preferencia:",
    list(goal2_format_options.keys()),
    index=2
)
goal2_format_tokens = goal2_format_options[goal2_format_label]

st.sidebar.markdown("---")
st.sidebar.subheader("Cél3 – fő rész (mérkőzésjáték)")

goal3_profile_options = {
    "Finishing / gólhelyzet-teremtés": ["finishing game", "finishing", "shot on goal", "goal", "scoring"],
    "Build-up & possession game": ["build-up game", "possession game", "possession", "keeping the ball"],
    "Pressing & transition game": ["pressing game", "pressing", "transition game", "transition", "win the ball"],
    "Nincs extra preferencia": []
}
goal3_profile_label = st.sidebar.selectbox(
    "Cél3 játékprofil:",
    list(goal3_profile_options.keys()),
    index=0
)
goal3_profile_keywords = goal3_profile_options[goal3_profile_label]

goal3_format_options = {
    "6v6 körül (félpálya)": ["6vs6", "6 vs 6", "half-field", "half field"],
    "7v7–8v8 (rövidített pálya)": ["7vs7", "7 vs 7", "8vs8", "8 vs 8"],
    "10v10 / 11v11, meccsszerű": ["10vs10", "10 vs 10", "11vs11", "11 vs 11", "full pitch", "match"],
    "Nincs preferencia": []
}
goal3_format_label = st.sidebar.selectbox(
    "Cél3 formátum preferencia:",
    list(goal3_format_options.keys()),
    index=2
)
goal3_format_tokens = goal3_format_options[goal3_format_label]

want_match_game = st.sidebar.checkbox(
    "Legyen Cél3 kifejezetten mérkőzésjáték?",
    value=True
)

# ha igen, akkor korosztály alapján finomítjuk a formátum tokeneket
is_adult_group = any(a in ["Men", "Women's", "Adult"] for a in age_tokens)
if want_match_game:
    if is_adult_group:
        # felnőtt: 11v11 / full pitch
        goal3_format_tokens = ["11vs11", "11 vs 11", "full pitch", "match"]
    else:
        # korosztály szerinti meccsformátum
        goal3_format_tokens = age_based_game_tokens(age_tokens)

# ====== GOMB: EDZÉSTERV GENERÁLÁSA ======
generate = st.sidebar.button("Edzésterv generálása")

if not generate:
    st.info("⬅️ Állítsd be a paramétereket a bal oldalon, majd kattints az **Edzésterv generálása** gombra.")
    st.stop()

# ====== EDZÉSTERV ÖSSZERAKÁSA ======
used_urls = set()
used_images = set()
plan = []
stages = [
    ("Bemelegítés / Warm-up", "warmup"),
    ("Cél1 – kis létszámú játék / Small-sided", "small"),
    ("Cél2 – nagyobb létszámú taktikai játék / Larger tactical game", "large"),
    ("Cél3 – fő rész – mérkőzésjáték / Main phase – Match game", "main")
]

for label, code in stages:
    ex = pick_exercise_for_stage(
        EX_DB, code,
        age_tokens,
        tact_keywords,
        tech_keywords,
        phys_keywords,
        goal2_format_tokens,
        goal3_format_tokens,
        goal3_profile_keywords,
        used_urls,
        used_images
    )
    if ex:
        plan.append((label, ex))
        used_urls.add(ex.get("url"))
        img = get_image_url(ex)
        if img:
            used_images.add(img)
    else:
        st.warning(f"Nem találtam gyakorlatot ehhez a szakaszhoz: {label}")

st.subheader("📋 Edzésterv összefoglaló")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Korosztály / Age group:** {age_label}")
    st.markdown(f"**Játékoslétszám:** {players_raw}")
    st.markdown(f"**Edzésidő:** {total_time}")
with col2:
    st.markdown(f"**Taktikai cél:** {tact_label}")
    st.markdown(f"**Technikai fókusz:** {', '.join(tech_selection) if tech_selection else 'nincs megadva'}")
    st.markdown(f"**Erőnléti fókusz:** {phys_label}")
    st.markdown(f"**Cél3 mérkőzésjáték:** {'Igen' if want_match_game else 'Nem'}")

st.markdown("---")

if not plan:
    st.error("Nem sikerült gyakorlatokat találni a megadott paraméterekkel. Próbálj lazább szűrést (pl. korosztály: Any).")
    st.stop()

# ====== GYAKORLATOK MEGJELENÍTÉSE KÁRTYÁKBAN ======

for idx, (stage_label, ex) in enumerate(plan, start=1):
    st.markdown(f"### {idx}. {stage_label}")
    title = ex.get("title", "Névtelen gyakorlat")
    url = ex.get("url")

    c1, c2 = st.columns([1.2, 2])

    with c1:
        img_url = get_image_url(ex)
        if img_url:
            try:
                st.image(img_url, use_column_width=True)
            except Exception:
                st.info("Kép nem tölthető be, de az adatbázis tartalmaz hozzá URL-t.")
        else:
            st.info("Ehhez a gyakorlathoz nincs kép-URL (placeholder).")

    with c2:
        st.markdown(f"**EN title:** {title}")
        if url:
            st.markdown(f"[🔗 Megnyitás böngészőben]({url})")

        sections = ex.get("sections", {})
        org = sections.get("Organisation") or sections.get("Organization")
        proc = sections.get("Process")
        tip = sections.get("Tip")

        if org:
            with st.expander("Organisation (EN) / Szervezés (HU)"):
                st.markdown("**Organisation (EN):**")
                st.write(org)
                hu_org = en_to_hu(org)
                if hu_org:
                    st.markdown("---")
                    st.markdown("**Szervezés (HU) – gépi fordítás:**")
                    st.write(hu_org)

        if proc:
            with st.expander("Process (EN) / Leírás (HU) + coaching pontok"):
                st.markdown("**Process (EN):**")
                st.write(proc)

                hu_proc = en_to_hu(proc)
                if hu_proc:
                    st.markdown("---")
                    st.markdown("**Leírás (HU) – gépi fordítás:**")
                    st.write(hu_proc)

                # Coaching pontok – egyszerű mondatbontás
                st.markdown("---")
                st.markdown("**Coaching points (EN) – auto:**")
                sentences = [s.strip() for s in proc.replace("\n", " ").split(".") if s.strip()]
                if not sentences:
                    st.write("_Nem generálható coaching lista._")
                else:
                    for s in sentences:
                        wrapped_lines = textwrap.wrap(s, width=90, break_long_words=True)
                        st.markdown("- " + " ".join(wrapped_lines))

        if tip:
            with st.expander("Tip (EN) / Megjegyzés (HU)"):
                st.markdown("**Tip (EN):**")
                st.write(tip)
                hu_tip = en_to_hu(tip)
                if hu_tip:
                    st.markdown("---")
                    st.markdown("**Megjegyzés (HU) – gépi fordítás:**")
                    st.write(hu_tip)

    st.markdown("---")

st.success("✅ Edzésterv generálva a fenti paraméterek alapján.")
st.caption("Következő lépés: ha szeretnéd, ide be tudjuk építeni a PDF-generálót is, letölthető edzésterv formában.")
