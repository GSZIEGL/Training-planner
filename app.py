import json
import random
import textwrap
from typing import List, Dict, Any
from io import BytesIO
import tempfile

import requests
import streamlit as st

# ====== IDE ÍRD BE A SAJÁT MECCSJÁTÉK KÉPED URL-JÉT ======
# Pl. ha a GitHubon a repo gyökerébe feltöltöd "match_game.png" néven:
# MATCH_GAME_IMAGE_URL = "https://raw.githubusercontent.com/GSZIEGL/Training-planner/main/match_game.png"
MATCH_GAME_IMAGE_URL = ""https://raw.githubusercontent.com/GSZIEGL/Training-planner/main/match_game.png""  # <-- EZT CSERÉLD LE


# ====== Opcionális fordító EN -> HU ======
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR = GoogleTranslator(source="en", target="hu")
except Exception:
    TRANSLATOR = None


def en_to_hu(text: str):
    """
    Próbál angolról magyarra fordítani.
    Ha nem sikerül, vagy a fordítás kb. ugyanaz, mint az eredeti,
    akkor None-t ad vissza (ilyenkor nem jelenik meg külön HU blokk).
    """
    if not text:
        return None
    if not TRANSLATOR:
        return None
    try:
        t = TRANSLATOR.translate(text)
        if not t:
            return None
        if t.strip().lower() == text.strip().lower():
            return None
        return t
    except Exception:
        return None


def safe_wrap(text: str, width: int = 110) -> str:
    """Hosszú szavakra is felkészülő tördelés, hogy a PDF-ben ne fussanak szét a sorok."""
    if not text:
        return ""
    words = text.split()
    processed = []
    for w in words:
        if len(w) > width:
            chunks = [w[i:i + width] for i in range(0, len(w), width)]
            processed.extend(chunks)
        else:
            processed.append(w)
    wrapped = textwrap.wrap(" ".join(processed), width=width)
    return "\n".join(wrapped)


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
    1️⃣ Bemelegítés (Warm-up)  
    2️⃣ Cél1 – kis létszámú taktikai feladat (Small-sided)  
    3️⃣ Cél2 – nagyobb létszámú taktikai játék  
    4️⃣ Cél3 – fő rész, lehetőség szerint **mérkőzésjáték (match game)**  
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

# ====== EDDIG HASZNÁLT GYAKORLATOK TÁROLÁSA SESSION_STATE-BEN ======
if "used_urls_history" not in st.session_state:
    st.session_state["used_urls_history"] = []

st.sidebar.markdown("---")
if st.sidebar.button("🔁 Gyakorlat-história törlése (újrakezdés)"):
    st.session_state["used_urls_history"] = []
    st.sidebar.success("A korábban használt gyakorlatok törölve. Új generálásnál újra felhasználhatók.")


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
    """Összefűzzük a title + sections + meta értékeket egy hosszú szöveggé."""
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
    """Mérkőzésjáték jellegű gyakorlat felismerése."""
    game_words = [
        "game", "match", "game form", "small-sided game", "minigame",
        "7vs7", "7 vs 7", "8vs8", "8 vs 8",
        "9vs9", "9 vs 9", "10vs10", "10 vs 10",
        "11vs11", "11 vs 11",
        "players -", "players–", "players –",
        "team training", "game systems"
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
    is_main_like = any(w in blob for w in ["finishing", "goal", "half-field", "half field"])
    is_game_like = is_game_like_blob(blob)

    # meta-mezők külön kiemelve
    meta = ex.get("meta", {})
    meta_text = " ".join(str(v) for v in meta.values()).lower()

    if stage == "warmup":
        if is_warm_like:
            score += 8
        if is_main_like or is_game_like:
            score -= 6

    elif stage == "small":
        if any(w in blob for w in ["1vs1", "1 vs 1", "2vs2", "2 vs 2", "3vs3", "3 vs 3", "4vs4", "4 vs 4"]):
            score += 6
        if "small-sided" in blob or "small sided" in blob:
            score += 5
        if "aufwärmen" in blob or "warm" in blob:
            score += 2

    elif stage == "large":
        # támogatjuk a nagyobb létszámot
        has_large_tokens = ["5vs5", "5 vs 5", "6vs6", "6 vs 6", "7vs7", "7 vs 7", "8vs8", "8 vs 8", "9vs9", "9 vs 9"]
        if any(w in blob for w in has_large_tokens):
            score += 6
        for kw in goal2_format_tokens:
            if kw.lower() in blob:
                score += 4
        if any(w in blob for w in ["build-up", "build up", "possession", "keeping the ball",
                                   "game systems", "team training", "organization", "organised"]):
            score += 4
        if any(w in blob for w in ["circuit", "course"]):
            score -= 4
        if is_warm_like:
            score -= 4

    elif stage == "main":
        # Cél3 – legyen tényleg mérkőzésjáték
        if is_game_like:
            score += 20
        else:
            score -= 15

        # meta "Form of Training" + "Number of Players"
        if "game" in meta_text or "team training" in meta_text:
            score += 6
        if "players" in meta_text:
            score += 4

        for kw in goal3_format_tokens:
            if kw.lower() in blob:
                score += 6

        for kw in goal3_profile_keywords:
            if kw.lower() in blob:
                score += 5

        # "drill", "circuit" stb. – ne legyen Cél3
        if any(w in blob for w in ["drill", "circuit", "course", "pattern only", "coordinative"]):
            score -= 10
        if is_warm_like:
            score -= 10

    # kép-duplikáció büntetése
    img = get_image_url(ex)
    if img and img in used_images:
        score -= 50

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
    used_images: set,
    global_used_urls: set = None,
    require_match_game: bool = False
):
    """
    used_urls: az aktuális edzésterven belül már kiválasztott gyakorlatok
    global_used_urls: előző edzéstervekben már használt gyakorlatok (session_state)
    """
    if global_used_urls is None:
        global_used_urls = set()

    # 1) Próbáljunk olyan gyakorlatokat, amik se a mostani tervben, se globálisan nem szerepeltek
    candidates = [
        ex for ex in EX_DB
        if matches_age(ex, age_tokens)
        and ex.get("url") not in used_urls
        and ex.get("url") not in global_used_urls
    ]

    # 2) Ha így semmi, engedjük vissza a globálisan használtakat, csak az aktuális edzés duplikátjait tiltjuk
    if not candidates:
        candidates = [
            ex for ex in EX_DB
            if matches_age(ex, age_tokens)
            and ex.get("url") not in used_urls
        ]
        if not candidates:
            return None

    # ===== Cél3 – külön logika a formátum preferenciára + mérkőzésjátékra =====
    if stage == "main":
        blob_map = {id(ex): exercise_text_blob(ex) for ex in candidates}
        game_candidates = [ex for ex in candidates if is_game_like_blob(blob_map[id(ex)])]

        if require_match_game:
            preferred = []

            # Ha van formátum preferencia (pl. 6v6 / 7v7 / 11v11), először azt keressük
            if goal3_format_tokens:
                # 1) game-like + formátum-egyezés
                preferred = [
                    ex for ex in game_candidates
                    if any(tok.lower() in blob_map[id(ex)] for tok in goal3_format_tokens)
                ]

                # 2) ha ilyen nincs, akkor bármilyen, de a preferált létszámot tartalmazó gyakorlat
                if not preferred:
                    preferred = [
                        ex for ex in candidates
                        if any(tok.lower() in blob_map[id(ex)] for tok in goal3_format_tokens)
                    ]

            # 3) ha semmi sem passzol a formátumra, de vannak game-like gyakorlatok:
            if not preferred and game_candidates:
                preferred = game_candidates

            if preferred:
                candidates = preferred
            # ha preferred üres, marad az eredeti candidates (nagyon végső fallback)

        else:
            # Nem kötelező meccsjáték, de ha vannak game-like jellegűek, azokat preferáljuk
            if game_candidates:
                candidates = game_candidates

    # ===== PONTOSZÁM ALAPÚ VÁLASZTÁS =====
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

is_adult_group = any(a in ["Men", "Women's", "Adult"] for a in age_tokens)

# Ha a user konkrét formátumot választ (pl. 6v6), azt NEM írjuk felül.
# Csak akkor használjuk az életkori ajánlást, ha NINCS formátum preferencia (üres lista).
if want_match_game and not goal3_format_tokens:
    if is_adult_group:
        goal3_format_tokens = ["11vs11", "11 vs 11", "full pitch", "match"]
    else:
        tokens_age = age_based_game_tokens(age_tokens)
        if tokens_age:
            goal3_format_tokens = tokens_age

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
        used_images,
        global_used_urls=set(st.session_state["used_urls_history"]),
        require_match_game=(code == "main" and want_match_game)
    )
    if ex:
        plan.append((label, code, ex))
        used_urls.add(ex.get("url"))
        img = get_image_url(ex)
        if img:
            used_images.add(img)
    else:
        st.warning(f"Nem találtam gyakorlatot ehhez a szakaszhoz: {label}")

# Új gyakorlatok URL-jeinek hozzáadása a globális történethez
for _, _, ex in plan:
    url = ex.get("url")
    if url and url not in st.session_state["used_urls_history"]:
        st.session_state["used_urls_history"].append(url)

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
for idx, (stage_label, stage_code, ex) in enumerate(plan, start=1):
    st.markdown(f"### {idx}. {stage_label}")
    title = ex.get("title", "Névtelen gyakorlat")

    c1, c2 = st.columns([1.2, 2])

    with c1:
        # Cél3 + meccsjáték: MINDIG a fix kép
        if stage_code == "main" and want_match_game:
            img_url = MATCH_GAME_IMAGE_URL
        else:
            img_url = get_image_url(ex)

        if img_url:
            try:
                st.image(img_url, use_column_width=True)
            except Exception:
                st.info("Kép nem tölthető be (ellenőrizd az URL-t).")
        else:
            st.info("Ehhez a gyakorlathoz nincs kép-URL (placeholder).")

    with c2:
        st.markdown(f"**EN title:** {title}")
        hu_title = en_to_hu(title)
        if hu_title:
            st.markdown(f"**HU cím (gépi fordítás):** {hu_title}")

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
                    st.markdown("**Szervezés (HU – gépi fordítás):**")
                    st.write(hu_org)

        if proc:
            with st.expander("Process (EN) / Leírás (HU) + coaching pontok"):
                st.markdown("**Process (EN):**")
                st.write(proc)

                hu_proc = en_to_hu(proc)
                if hu_proc:
                    st.markdown("---")
                    st.markdown("**Leírás (HU – gépi fordítás):**")
                    st.write(hu_proc)

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
                    st.markdown("**Megjegyzés (HU – gépi fordítás):**")
                    st.write(hu_tip)

    st.markdown("---")

st.success("✅ Edzésterv generálva a fenti paraméterek alapján.")


# ====== PDF-GENERÁLÓ (EN+HU) ======
try:
    from fpdf import FPDF
    HAS_FPDF = True
except Exception:
    HAS_FPDF = False


def mc(pdf, text: str, h: float = 5, size: int = 10):
    """Segédfüggvény: bal margóról multi_cell, hogy ne csússzon el az X pozíció."""
    if not text:
        return
    pdf.set_x(pdf.l_margin)
    pdf.set_font("DejaVu", size=size)
    pdf.multi_cell(0, h, text, align="L")


if HAS_FPDF:

    class TrainingPDF(FPDF):
        def __init__(self):
            super().__init__(orientation="P", unit="mm", format="A4")
            self.set_auto_page_break(auto=True, margin=15)
            self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
            self.set_font("DejaVu", size=11)

        def header(self):
            self.set_fill_color(220, 210, 240)
            self.rect(0, 0, 210, 18, "F")
            self.set_xy(10, 5)
            self.set_font("DejaVu", size=10)
            self.cell(0, 5, "chatbotfootball training planner", ln=1)
            self.set_x(10)
            self.set_font("DejaVu", size=9)
            self.cell(0, 4, "Bilingual training session – Kéttannyelvű edzésterv", ln=1)
            self.ln(2)

        def footer(self):
            self.set_y(-15)
            self.set_font("DejaVu", size=8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 5, f"Page {self.page_no()}", align="C")


    def build_pdf(
        plan: List,
        age_label: str,
        players_raw: str,
        total_time: str,
        tact_label: str,
        tech_selection: List[str],
        phys_label: str,
        want_match_game: bool
    ) -> BytesIO:
        pdf = TrainingPDF()

        # ===== CÍMOLDAL =====
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        pdf.ln(15)

        mc(pdf, "Edzésterv / Training Plan", h=8, size=18)
        pdf.ln(4)

        mc(pdf, f"Korosztály / Age group: {age_label}", h=6, size=11)
        mc(pdf, f"Játékoslétszám / Number of players: {players_raw}", h=6, size=11)
        mc(pdf, f"Össz edzésidő / Total duration: {total_time}", h=6, size=11)
        pdf.ln(4)
        mc(pdf, f"Taktikai cél / Tactical goal: {tact_label}", h=6, size=11)
        mc(
            pdf,
            f"Technikai fókusz / Technical focus: {', '.join(tech_selection) if tech_selection else 'nincs megadva'}",
            h=6,
            size=11,
        )
        mc(pdf, f"Erőnléti fókusz / Physical focus: {phys_label}", h=6, size=11)
        mc(
            pdf,
            f"Cél3 mérkőzésjáték / Match game on main phase: {'Igen/Yes' if want_match_game else 'Nem/No'}",
            h=6,
            size=11,
        )

        pdf.ln(8)
        intro = (
            "Az edzésterv 4 blokkból áll: bemelegítés, kis létszámú játék, nagyobb létszámú taktikai játék "
            "és egy fő mérkőzésjáték jellegű feladat. "
            "A gyakorlatok angol leíráshoz – ha elérhető – gépi magyar fordítást is tartalmaznak."
        )
        mc(pdf, safe_wrap(intro), h=5, size=11)

        # ===== GYAKORLATOK =====
        for idx, (stage_label, stage_code, ex) in enumerate(plan, start=1):
            pdf.add_page()
            pdf.set_text_color(0, 0, 0)

            mc(pdf, f"{idx}. {stage_label}", h=8, size=14)
            pdf.ln(2)

            # Kép (ha van) – Cél3-nál MINDIG a fix match-game kép
            if stage_code == "main" and want_match_game:
                img_url = MATCH_GAME_IMAGE_URL
            else:
                img_url = get_image_url(ex)

            if img_url:
                try:
                    resp = requests.get(img_url, timeout=8)
                    if resp.ok:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                            tmp.write(resp.content)
                            tmp.flush()
                            x = pdf.l_margin
                            y = pdf.get_y()
                            pdf.image(tmp.name, x=x, y=y, w=80)
                            pdf.set_y(y + 60)
                            pdf.ln(2)
                except Exception:
                    pass

            title = ex.get("title", "Névtelen gyakorlat")
            mc(pdf, safe_wrap(f"EN: {title}"), h=6, size=12)
            hu_title = en_to_hu(title)
            if hu_title:
                mc(pdf, safe_wrap(f"HU: {hu_title}"), h=5, size=11)

            pdf.ln(3)

            sections = ex.get("sections", {})
            org = sections.get("Organisation") or sections.get("Organization")
            proc = sections.get("Process")
            tip = sections.get("Tip")

            # Organisation
            if org:
                pdf.set_text_color(60, 0, 90)
                mc(pdf, "Organisation / Szervezés", h=7, size=11)
                pdf.set_text_color(0, 0, 0)
                mc(pdf, "EN:", h=5, size=10)
                mc(pdf, safe_wrap(org), h=5, size=10)
                hu_org = en_to_hu(org)
                if hu_org:
                    pdf.ln(1)
                    mc(pdf, "HU:", h=5, size=10)
                    mc(pdf, safe_wrap(hu_org), h=5, size=10)
                pdf.ln(3)

            # Process
            if proc:
                pdf.set_text_color(60, 0, 90)
                mc(pdf, "Process / Leírás", h=7, size=11)
                pdf.set_text_color(0, 0, 0)
                mc(pdf, "EN:", h=5, size=10)
                mc(pdf, safe_wrap(proc), h=5, size=10)
                hu_proc = en_to_hu(proc)
                if hu_proc:
                    pdf.ln(1)
                    mc(pdf, "HU:", h=5, size=10)
                    mc(pdf, safe_wrap(hu_proc), h=5, size=10)
                pdf.ln(3)

                pdf.set_text_color(60, 0, 90)
                mc(pdf, "Coaching points (EN)", h=7, size=11)
                pdf.set_text_color(0, 0, 0)
                sentences = [s.strip() for s in proc.replace("\n", " ").split(".") if s.strip()]
                for s in sentences:
                    mc(pdf, "- " + safe_wrap(s), h=5, size=10)
                pdf.ln(2)

            # Tip
            if tip:
                pdf.set_text_color(60, 0, 90)
                mc(pdf, "Tip / Megjegyzés", h=7, size=11)
                pdf.set_text_color(0, 0, 0)
                mc(pdf, "EN:", h=5, size=10)
                mc(pdf, safe_wrap(tip), h=5, size=10)
                hu_tip = en_to_hu(tip)
                if hu_tip:
                    pdf.ln(1)
                    mc(pdf, "HU:", h=5, size=10)
                    mc(pdf, safe_wrap(hu_tip), h=5, size=10)
                pdf.ln(2)

        pdf_buffer = BytesIO()
        pdf_output = pdf.output(dest="S")  # fpdf2 -> bytearray
        pdf_buffer.write(bytes(pdf_output))
        pdf_buffer.seek(0)
        return pdf_buffer


# ====== PDF LETÖLTÉS GOMB ======
st.markdown("### 📄 PDF export")

if not HAS_FPDF:
    st.info(
        "A PDF export jelenleg nem elérhető, mert az 'fpdf2' csomag nincs telepítve. "
        "Streamlit Cloudon add hozzá a `fpdf2` csomagot a requirements.txt-be."
    )
else:
    try:
        pdf_bytes = build_pdf(
            plan=plan,
            age_label=age_label,
            players_raw=players_raw,
            total_time=total_time,
            tact_label=tact_label,
            tech_selection=tech_selection,
            phys_label=phys_label,
            want_match_game=want_match_game,
        )
        st.download_button(
            label="📥 Két nyelvű PDF edzésterv letöltése",
            data=pdf_bytes,
            file_name="edzesterv_ketnyelvu.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF generálási hiba: {e}")
