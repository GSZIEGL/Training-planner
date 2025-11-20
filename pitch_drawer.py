from typing import Dict, Any, List, Optional

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch


# ============================
# 1. PÁLYA RAJZOLÁSA
# ============================

def draw_pitch(ax=None):
    """
    Egyszerű, full-size pálya 0–100 x 0–100 koordinátarendszerben.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig = ax.figure

    # Zöld háttér
    ax.set_facecolor("#3a7d3a")

    # Külső vonal
    pitch = Rectangle((0, 0), 100, 100,
                      linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(pitch)

    # Középvonal
    ax.plot([50, 50], [0, 100], color="white", linewidth=2)

    # Középkör
    center_circle = Circle((50, 50), 10,
                           linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(center_circle)

    # Középpont
    ax.scatter([50], [50], color="white", s=20)

    # 16-osok
    left_box = Rectangle((0, 20), 16, 60,
                         linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(left_box)
    right_box = Rectangle((84, 20), 16, 60,
                          linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(right_box)

    # 5-ösök
    left_small = Rectangle((0, 34), 6, 32,
                           linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(left_small)
    right_small = Rectangle((94, 34), 6, 32,
                            linewidth=2, edgecolor="white", facecolor="none")
    ax.add_patch(right_small)

    # Tizenegyes pont
    ax.scatter([11], [50], color="white", s=20)
    ax.scatter([89], [50], color="white", s=20)

    # Kapuk (vonalas jelzés)
    ax.plot([0, 0], [44, 56], color="white", linewidth=4)
    ax.plot([100, 100], [44, 56], color="white", linewidth=4)

    # Beállítások
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")

    return fig, ax


# ============================
# 2. SEGÉDFÜGGVÉNYEK
# ============================

TEAM_COLORS = {
    "home": "#1f77b4",     # kék
    "away": "#d62728",     # piros
    "neutral": "#ffcf3c",  # sárga
    "keeper": "#2ca02c",   # zöld
}


def _get_player_by_id(players: List[Dict[str, Any]], pid: str) -> Optional[Dict[str, Any]]:
    for p in players:
        if p.get("id") == pid:
            return p
    return None


def _get_point(players: List[Dict[str, Any]], spec: Dict[str, Any], key: str):
    """
    Visszaad egy (x, y) pontot játékos ID-ból vagy explicit koordinátából.
    - "{key}_id": játékos azonosító (pl. from_id, to_id)
    - "{key}":   dict {"x": .., "y": ..}
    """
    id_key = f"{key}_id"
    if id_key in spec:
        pl = _get_player_by_id(players, spec[id_key])
        if pl:
            return {"x": pl["x"], "y": pl["y"]}

    if key in spec and isinstance(spec[key], dict):
        pt = spec[key]
        if "x" in pt and "y" in pt:
            return {"x": pt["x"], "y": pt["y"]}

    return None


# ============================
# 3. FŐ RAJZOLÓ FÜGGVÉNY
# ============================

def draw_drill(diagram: Dict[str, Any],
               figsize=(8, 5),
               show: bool = False,
               save_path: Optional[str] = None):
    """
    Megrajzolja a pályát + játékosokat + passzokat + futásokat + extra elemeket.

    diagram elvárt kulcsai (nem mind kötelező):
      - players:  [{id, label, x, y, team}]
      - cones:    [{x, y}]
      - passes:   [{from_id/to_id vagy from/to koordináta}]
      - runs:     [{from_id/to_id vagy from/to koordináta}]
      - ball:     {owner_id vagy x,y}
      - text_labels: [{x, y, text}]
      - area:     {x, y, w, h}        # kiemelt játéktér
      - mini_goals: [{x, y, w, h}]    # kis kapuk
    """
    fig, ax = plt.subplots(figsize=figsize)
    draw_pitch(ax)

    players = diagram.get("players", [])
    cones = diagram.get("cones", [])
    passes = diagram.get("passes", [])
    runs = diagram.get("runs", [])
    ball_spec = diagram.get("ball", {})
    texts = diagram.get("text_labels", [])
    area = diagram.get("area")
    mini_goals = diagram.get("mini_goals", [])

    # ---- Kiemelt játéktér (pl. kisjáték mező) ----
    if area:
        ax.add_patch(
            Rectangle(
                (area["x"], area["y"]),
                area["w"],
                area["h"],
                linewidth=1.5,
                edgecolor="white",
                linestyle="--",
                facecolor="none",
                zorder=1.5,
            )
        )

    # ---- Mini-kapuk ----
    for g in mini_goals:
        gx = g["x"]
        gy = g["y"]
        gw = g.get("w", 4)
        gh = g.get("h", 8)
        ax.add_patch(
            Rectangle(
                (gx - gw / 2, gy - gh / 2),
                gw,
                gh,
                linewidth=2,
                edgecolor="white",
                facecolor="#111827",
                zorder=4,
            )
        )

    # ---- Bóják ----
    for c in cones:
        x, y = c["x"], c["y"]
        cone = Rectangle((x - 0.8, y - 0.8), 1.6, 1.6,
                         facecolor="#ff7f0e", edgecolor="black",
                         linewidth=1, zorder=4)
        ax.add_patch(cone)

    # ---- Játékosok ----
    for p in players:
        x, y = p["x"], p["y"]
        label = p.get("label", "")
        color = TEAM_COLORS.get(p.get("team", "home"), "#1f77b4")

        circ = Circle((x, y), 3,
                      facecolor=color,
                      edgecolor="black",
                      linewidth=1.2,
                      zorder=5)
        ax.add_patch(circ)

        ax.text(x, y, label,
                ha="center", va="center",
                fontsize=7, color="black",
                zorder=6)

    # ---- Passzok (folyamatos fehér nyíl) ----
    for ps in passes:
        start = _get_point(players, ps, "from")
        end = _get_point(players, ps, "to")
        if not start or not end:
            continue

        arrow = FancyArrowPatch(
            (start["x"], start["y"]),
            (end["x"], end["y"]),
            arrowstyle="->",
            mutation_scale=10,
            linewidth=2,
            linestyle="-",
            color="white",
            zorder=3,
        )
        ax.add_patch(arrow)

    # ---- Futásvonalak (szaggatott fehér nyíl) ----
    for rn in runs:
        start = _get_point(players, rn, "from")
        end = _get_point(players, rn, "to")
        if not start or not end:
            continue

        arrow = FancyArrowPatch(
            (start["x"], start["y"]),
            (end["x"], end["y"]),
            arrowstyle="->",
            mutation_scale=10,
            linewidth=2,
            linestyle="--",
            color="white",
            zorder=2,
        )
        ax.add_patch(arrow)

    # ---- Labda ----
    ball_x = ball_spec.get("x")
    ball_y = ball_spec.get("y")
    if ball_spec.get("owner_id"):
        owner = _get_player_by_id(players, ball_spec["owner_id"])
        if owner:
            ball_x, ball_y = owner["x"], owner["y"]

    if ball_x is not None and ball_y is not None:
        ball = Circle((ball_x, ball_y), 1.5,
                      facecolor="white",
                      edgecolor="black",
                      linewidth=1.2,
                      zorder=7)
        ax.add_patch(ball)

    # ---- Szövegcímkék ----
    for t in texts:
        ax.text(t["x"], t["y"], t["text"],
                fontsize=8, color="white",
                ha="left", va="center", zorder=10)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return fig
