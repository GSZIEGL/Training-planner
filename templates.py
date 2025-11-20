# templates.py

TEMPLATES = {
    "half_pitch_1231_u12_15": {
        "meta": {
            "label": "1–2–3–1 félpályás játék (U12–U15)",
            "recommended_stage": "main",
            "age_group": "U12–U15",
        },
        "diagram": {
            "pitch": {"type": "full", "orientation": "horiz"},

            # 1 kapus, 2 védő egy vonalban, 3 középpályás egy vonalban, 1 csatár
            # VÖRÖS csapat (home) – balról támad jobbra
            "players": [
                # Kapus
                {"id": "R_GK", "label": "GK", "x": 8, "y": 50, "team": "keeper"},

                # 2 védő egy vonalban
                {"id": "R_D1", "label": "2", "x": 25, "y": 35, "team": "home"},
                {"id": "R_D2", "label": "3", "x": 25, "y": 65, "team": "home"},

                # 3 középpályás egy vonalban
                {"id": "R_M1", "label": "4", "x": 45, "y": 30, "team": "home"},
                {"id": "R_M2", "label": "6", "x": 45, "y": 50, "team": "home"},
                {"id": "R_M3", "label": "8", "x": 45, "y": 70, "team": "home"},

                # 1 csatár
                {"id": "R_F1", "label": "9", "x": 65, "y": 50, "team": "home"},

                # KÉK csapat (ellenfél) – tükrösen, szintén 1–2–3–1
                {"id": "B_GK", "label": "GK", "x": 92, "y": 50, "team": "keeper"},

                {"id": "B_D1", "label": "2", "x": 75, "y": 35, "team": "away"},
                {"id": "B_D2", "label": "3", "x": 75, "y": 65, "team": "away"},

                {"id": "B_M1", "label": "4", "x": 55, "y": 30, "team": "away"},
                {"id": "B_M2", "label": "6", "x": 55, "y": 50, "team": "away"},
                {"id": "B_M3", "label": "8", "x": 55, "y": 70, "team": "away"},

                {"id": "B_F1", "label": "9", "x": 35, "y": 50, "team": "away"},
            ],

            # Labda: a bal oldali csatárnál
            "ball": {"owner_id": "R_F1"},

            # Példa bójasor az ellenfél térfelének határára
            "cones": [
                {"x": 50, "y": 15},
                {"x": 50, "y": 25},
                {"x": 50, "y": 75},
                {"x": 50, "y": 85},
            ],

            # Nincs külön zóna és minikapu ennél a sablonnál
            "area": None,
            "mini_goals": [],

            # Alap passz- és futásvonalak (opcionális taktikai minta)
            "passes": [
                {"from_id": "R_D1", "to_id": "R_M1"},
                {"from_id": "R_M1", "to_id": "R_M2"},
                {"from_id": "R_M2", "to_id": "R_F1"},
            ],
            "runs": [
                {"from_id": "R_F1", "to": {"x": 72, "y": 55}},
                {"from_id": "R_M3", "to": {"x": 55, "y": 75}},
            ],

            "text_labels": [
                {"x": 5, "y": 95, "text": "1–2–3–1 felállás – U12–U15 sablon"},
            ],
        },
    },
}
