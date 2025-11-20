# pitch_drawer.py
from typing import Dict, Any, List, Optional

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyArrowPatch


# ============================
# 1. PÁLYA RAJZOLÁSA
# ============================

def draw_pitch(ax=None):
    """
    Full-size pálya 0–100 x 0–100 koordináta-rendszerben.
    Csíkos füves háttérrel, vonalakkal, kapukkal.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 5))
    else:
        fig = ax.figure

    # Csíkos zöld háttér
    for i in range(7):
        stripe_color = "#63a15f" if i % 2 == 0 else "#5a9657"
        ax.add_patch(
            Rectangle((0, i * (100 / 7)), 100, 100 / 7,
                      facecolor=stripe_color, edgecolor="none", zorder=0)
        )

    # Külső vonal
    outline = Rectangle((0, 0), 100, 100,
                        linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    ax.add_patch(outline)

    # Középvonal
    ax.plot([50, 50], [0, 100], color="white", linewidth=2, zorder=1)

    # Középkör
    center_circle = Circle((50, 50), 10,
                           linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    ax.add_patch(center_circle)

    # Középpont
    ax.scatter([50], [50], color="white", s=20, zorder=2)

    # 16-osok
    left_box = Rectangle((0, 20), 18, 60,
                         linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    ax.add_patch(left_box)
    right_box = Rectangle((82, 20), 18, 60,
                          linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    ax.add_patch(right_box)

    # 5-ösök
    left_small = Rectangle((0, 36), 6, 28,
                           linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    ax.add_patch(left_small)
    right_small = Rectangle((94, 36), 6, 28,
                            linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    ax.add_patch(right_small)

    # Tizenegyes pont
    ax.scatter([12], [50], color="white", s=18, zorder=2)
    ax.scatter([88], [50], color="white", s=18, zorder=2)

    # 16-os előtti félkörök
    left_arc = Circle((18, 50), 8,
                      linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    right_arc = Circle((82, 50), 8,
                       linewidth=2, edgecolor="white", facecolor="none", zorder=1)
    # Csak a belső fele látszik, de ez így is ad egy jó érzetet
    ax.add_patch(left_arc)
    ax.add_patch(right_arc)

    # Kapuk (egyszerű L-alak, „3D” hatás)
    goal_width = 14
    goal_depth = 3

    # Bal kapu
    ax.add_patch(
        Rectangle((-goal_depth, 50 - goal_width / 2),
                  goal_depth, goal_width,
                  linewidth=2, edgecolor="white",
                  facecolor="#111827", zorder=2)
    )
    # Jobb kapu
    ax.add_patch(
        Rectangle((100, 50 - goal_width / 2),
                  goal_depth, goal_width,
                  linewidth=2, edgecolor="white",
                  facecolor="#111827", zorder=2)
    )

    # Beállítások
    ax.set_xlim(-5, 105)
    ax.set_ylim(0, 100)
    ax.set_aspect("equal")
    ax.axis("off")

    return fig, ax


# ============================
# 2. SEGÉDFÜGGVÉNYEK
# ============================

TEAM_COLORS = {
    "home": "#e11d48",     # piros
    "away": "#2563eb",     # kék
    "neutral": "#facc15",  # sárga
    "keeper": "#22c55e",   # zöld
}


def _get_player_by_id(players: List[Dict[str, Any]], pid: str) -> Optional[Dict[str, Any]]:
    for p in players:
        if p.get("id") == pid:
            return p
    return None


def _get_point(players: List[Dict[str, Any]], spec: Dict[str, Any], key: str):
    """
    Visszaad egy (x, y) pontot játékos ID-ból vagy explicit koordinátából.
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

    # ---- Kiemelt játéktér (zóna) ----
    if area:
        ax.add_patch(
            Rectangle(
                (area["x"], area["y"]),
                area["w"],
                area["h"],
                linewidth=1.8,
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
        cone = Circle((x, y), 1.2,
                      facecolor="#f97316", edgecolor="black",
                      linewidth=1, zorder=4)
        ax.add_patch(cone)

    # ---- Játékosok (kétgyűrűs marker) ----
    for p in players:
        x, y = p["x"], p["y"]
        label = p.get("label", "")
        team = p.get("team", "home")
        inner_color = TEAM_COLORS.get(team, "#e11d48")

        # külső kontúr
        outer = Circle((x, y), 3.4,
                       facecolor="black",
                       edgecolor="black",
                       linewidth=0.5,
                       zorder=5)
        ax.add_patch(outer)

        # belső színes kör
        inner = Circle((x, y), 2.8,
                       facecolor=inner_color,
                       edgecolor="white",
                       linewidth=1.4,
                       zorder=6)
        ax.add_patch(inner)

        ax.text(x, y, label,
                ha="center", va="center",
                fontsize=7, color="black",
                zorder=7)

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

    # ---- Labda (fehér-fekete „foci labda”) ----
    ball_x = ball_spec.get("x")
    ball_y = ball_spec.get("y")
    if ball_spec.get("owner_id"):
        owner = _get_player_by_id(players, ball_spec["owner_id"])
        if owner:
            ball_x, ball_y = owner["x"], owner["y"]

    if ball_x is not None and ball_y is not None:
        outer = Circle((ball_x, ball_y), 1.3,
                       facecolor="white",
                       edgecolor="black",
                       linewidth=1.1,
                       zorder=8)
        ax.add_patch(outer)
        inner = Circle((ball_x, ball_y), 0.6,
                       facecolor="black",
                       edgecolor="black",
                       linewidth=0.8,
                       zorder=9)
        ax.add_patch(inner)

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
