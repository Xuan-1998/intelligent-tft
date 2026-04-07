"""
TFT Set 17 Bot - Mecha Comp (Fast 8)
Strategy:
  1-1 to 3-7: ECON. Buy only cheap frontline to survive. Save to 50+ gold.
  4-1: Level to 8, roll down for Mecha core (AurelionSol, TahmKench, Karma, Urgot)
  4-1+: Fill board with best available units, place items on carries.
"""

COMP = {
    # Core Mecha carries - BUY THESE AT 4-1
    "AurelionSol": {
        "board_position": 14,  # back row center - main carry
        "items": ["JeweledGauntlet", "RabadonsDeathcap", "SpearofShojin"],
        "level": 2,
        "final_comp": True,
        "priority": 1,
    },
    "TahmKench": {
        "board_position": 24,  # front row - tank
        "items": ["WarmogsArmor", "DragonsClaw", "BrambleVest"],
        "level": 2,
        "final_comp": True,
        "priority": 1,
    },
    "Karma": {
        "board_position": 0,  # back corner - AP carry
        "items": ["BlueBuff", "JeweledGauntlet", "GiantSlayer"],
        "level": 2,
        "final_comp": True,
        "priority": 1,
    },
    "Urgot": {
        "board_position": 25,  # front row
        "items": ["SunfireCape", "Redemption", "GargoyleStoneplate"],
        "level": 2,
        "final_comp": True,
        "priority": 2,
    },
    "TheMightyMech": {
        "board_position": 26,  # front row
        "items": [],
        "level": 2,
        "final_comp": True,
        "priority": 2,
    },
    # Early game holders / frontline to survive until 4-1
    "Poppy": {
        "board_position": 23,
        "items": [],
        "level": 2,
        "final_comp": False,
        "priority": 3,
    },
    "Leona": {
        "board_position": 22,
        "items": [],
        "level": 2,
        "final_comp": False,
        "priority": 3,
    },
    "Mordekaiser": {
        "board_position": 27,
        "items": [],
        "level": 2,
        "final_comp": False,
        "priority": 3,
    },
    "Nasus": {
        "board_position": 21,
        "items": [],
        "level": 2,
        "final_comp": False,
        "priority": 3,
    },
    "ChoGath": {
        "board_position": 3,
        "items": [],
        "level": 2,
        "final_comp": False,
        "priority": 3,
    },
    "Caitlyn": {
        "board_position": 6,
        "items": [],
        "level": 2,
        "final_comp": False,
        "priority": 3,
    },
}

# Augments to look for (generic good ones)
AUGMENTS: list = [
    "Featherweight", "Combat Training", "Celestial Blessing",
    "Cybernetic Implants", "Stand United", "Electrocharge",
    "Cybernetic Uplink", "Cybernetic Shell", "Weakspot",
    "Tri Force", "Metabolic Accelerator", "Second Wind",
    "Last Stand", "Ascension", "Sunfire Board",
    "Wise Spending", "Preparation", "Blue Battery",
    "Hustler", "Verdant Veil", "First Aid Kit",
    "Rich Get Richer", "Meditation", "Component Grab Bag",
]


def champions_to_buy() -> list:
    champs = []
    for name, data in COMP.items():
        if data["level"] == 1:
            champs.append(name)
        elif data["level"] == 2:
            champs.extend([name] * 3)
        elif data["level"] == 3:
            champs.extend([name] * 9)
    return champs


def get_unknown_slots() -> list:
    used = [d["board_position"] for d in COMP.values()]
    return [n for n in range(27) if n not in used]


# Which champs to buy in early game (1-cost/2-cost frontline to survive)
EARLY_GAME_BUYS = {"Poppy", "Leona", "Mordekaiser", "Nasus", "ChoGath", "Caitlyn"}

# Which champs to buy at level 8 rolldown
ROLLDOWN_BUYS = {"AurelionSol", "TahmKench", "Karma", "Urgot", "TheMightyMech"}
