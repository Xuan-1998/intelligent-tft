"""
Contains static item & champion data - Updated for TFT Set 17: Space Gods
"""

COMBINED_ITEMS: set = {"BFSword", "ChainVest", "GiantsBelt", "NeedlesslyLargeRod",
                       "NegatronCloak", "SparringGloves", "Spatula", "TearoftheGoddess",
                       "RecurveBow", "ArchangelsStaff", "Bloodthirster", "BlueBuff",
                       "BrambleVest", "ChaliceofPower", "Deathblade", "DragonsClaw",
                       "EdgeofNight", "FrozenHeart", "GargoyleStoneplate", "GiantSlayer",
                       "GuinsoosRageblade", "HandofJustice", "HextechGunblade",
                       "InfinityEdge", "IonicSpark", "JeweledGauntlet", "LastWhisper",
                       "LocketoftheIronSolari", "Morellonomicon", "Quicksilver",
                       "RabadonsDeathcap", "RapidFirecannon", "Redemption",
                       "RunaansHurricane", "ShroudofStillness", "SpearofShojin",
                       "StatikkShiv", "SunfireCape", "TacticiansCrown", "ThiefsGloves",
                       "TitansResolve", "WarmogsArmor", "ZekesHerald", "Zephyr", "ZzRotPortal"}

ITEMS: set = COMBINED_ITEMS

# Set 17: Space Gods champion pool
CHAMPIONS: dict = {
    # 1-cost
    "Aatrox": {"Gold": 1, "Board Size": 1},
    "Briar": {"Gold": 1, "Board Size": 1},
    "Caitlyn": {"Gold": 1, "Board Size": 1},
    "ChoGath": {"Gold": 1, "Board Size": 1},
    "Ezreal": {"Gold": 1, "Board Size": 1},
    "Leona": {"Gold": 1, "Board Size": 1},
    "Lissandra": {"Gold": 1, "Board Size": 1},
    "Nasus": {"Gold": 1, "Board Size": 1},
    "Poppy": {"Gold": 1, "Board Size": 1},
    "RekSai": {"Gold": 1, "Board Size": 1},
    "Talon": {"Gold": 1, "Board Size": 1},
    "Teemo": {"Gold": 1, "Board Size": 1},
    "TwistedFate": {"Gold": 1, "Board Size": 1},
    "Veigar": {"Gold": 1, "Board Size": 1},
    # 2-cost
    "Akali": {"Gold": 2, "Board Size": 1},
    "BelVeth": {"Gold": 2, "Board Size": 1},
    "Gnar": {"Gold": 2, "Board Size": 1},
    "Gragas": {"Gold": 2, "Board Size": 1},
    "Gwen": {"Gold": 2, "Board Size": 1},
    "Jax": {"Gold": 2, "Board Size": 1},
    "Jinx": {"Gold": 2, "Board Size": 1},
    "Meepsie": {"Gold": 2, "Board Size": 1},
    "Milio": {"Gold": 2, "Board Size": 1},
    "Mordekaiser": {"Gold": 2, "Board Size": 1},
    "Pantheon": {"Gold": 2, "Board Size": 1},
    "Pyke": {"Gold": 2, "Board Size": 1},
    "Zoe": {"Gold": 2, "Board Size": 1},
    # 3-cost
    "Aurora": {"Gold": 3, "Board Size": 1},
    "Diana": {"Gold": 3, "Board Size": 1},
    "Fizz": {"Gold": 3, "Board Size": 1},
    "Illaoi": {"Gold": 3, "Board Size": 1},
    "KaiSa": {"Gold": 3, "Board Size": 1},
    "Lulu": {"Gold": 3, "Board Size": 1},
    "Maokai": {"Gold": 3, "Board Size": 1},
    "MissFortune": {"Gold": 3, "Board Size": 1},
    "Ornn": {"Gold": 3, "Board Size": 1},
    "Rhaast": {"Gold": 3, "Board Size": 1},
    "Samira": {"Gold": 3, "Board Size": 1},
    "Urgot": {"Gold": 3, "Board Size": 1},
    "Viktor": {"Gold": 3, "Board Size": 1},
    # 4-cost
    "AurelionSol": {"Gold": 4, "Board Size": 1},
    "Corki": {"Gold": 4, "Board Size": 1},
    "Karma": {"Gold": 4, "Board Size": 1},
    "Kindred": {"Gold": 4, "Board Size": 1},
    "LeBlanc": {"Gold": 4, "Board Size": 1},
    "MasterYi": {"Gold": 4, "Board Size": 1},
    "Nami": {"Gold": 4, "Board Size": 1},
    "Nunu": {"Gold": 4, "Board Size": 1},
    "Rammus": {"Gold": 4, "Board Size": 1},
    "Riven": {"Gold": 4, "Board Size": 1},
    "TahmKench": {"Gold": 4, "Board Size": 1},
    "TheMightyMech": {"Gold": 4, "Board Size": 1},
    "Xayah": {"Gold": 4, "Board Size": 1},
    # 5-cost
    "Bard": {"Gold": 5, "Board Size": 1},
    "Blitzcrank": {"Gold": 5, "Board Size": 1},
    "Fiora": {"Gold": 5, "Board Size": 1},
    "Graves": {"Gold": 5, "Board Size": 1},
    "Jhin": {"Gold": 5, "Board Size": 1},
    "Morgana": {"Gold": 5, "Board Size": 1},
    "Shen": {"Gold": 5, "Board Size": 1},
    "Sona": {"Gold": 5, "Board Size": 1},
    "Vex": {"Gold": 5, "Board Size": 1},
    "Zed": {"Gold": 5, "Board Size": 1},
}

ROUNDS: set = {"1-1", "1-2", "1-3", "1-4",
               "2-1", "2-2", "2-3", "2-4", "2-5", "2-6", "2-7",
               "3-1", "3-2", "3-3", "3-4", "3-5", "3-6", "3-7",
               "4-1", "4-2", "4-3", "4-4", "4-5", "4-6", "4-7",
               "5-1", "5-2", "5-3", "5-4", "5-5", "5-6", "5-7",
               "6-1", "6-2", "6-3", "6-4", "6-5", "6-6", "6-7",
               "7-1", "7-2", "7-3", "7-4", "7-5", "7-6", "7-7"}

CAROUSEL_ROUND: set = {"1-1", "2-4", "3-4", "4-4", "5-4", "6-4", "7-4"}
PVE_ROUND: set = {"1-2", "1-3", "1-4", "2-7", "3-7", "4-7", "5-7", "6-7", "7-7"}
PVP_ROUND: set = {"2-1", "2-2", "2-3", "2-5", "2-6",
                  "3-1", "3-2", "3-3", "3-5", "3-6",
                  "4-1", "4-2", "4-3", "4-5", "4-6",
                  "5-1", "5-2", "5-3", "5-5", "5-6",
                  "6-1", "6-2", "6-3", "6-5", "6-6",
                  "7-1", "7-2", "7-3", "7-5", "7-6"}

PICKUP_ROUNDS: set = {"2-1", "3-1", "4-1", "5-1", "6-1", "7-1"}
ANVIL_ROUNDS: set = {"5-1", "6-1", "7-1"}
AUGMENT_ROUNDS: set = {"2-1", "3-2", "4-2"}
ITEM_PLACEMENT_ROUNDS: set = {"2-2", "3-2", "4-2", "5-2", "6-2", "7-2",
                              "2-5", "3-5", "4-5", "5-5", "6-5", "7-5"}
FINAL_COMP_ROUND = "4-5"

FULL_ITEMS = {
    "ArchangelsStaff": ("NeedlesslyLargeRod", "TearoftheGoddess"),
    "Bloodthirster": ("BFSword", "NegatronCloak"),
    "BlueBuff": ("TearoftheGoddess", "TearoftheGoddess"),
    "BrambleVest": ("ChainVest", "ChainVest"),
    "ChaliceofPower": ("NegatronCloak", "TearoftheGoddess"),
    "Deathblade": ("BFSword", "BFSword"),
    "DragonsClaw": ("NegatronCloak", "NegatronCloak"),
    "EdgeofNight": ("BFSword", "ChainVest"),
    "FrozenHeart": ("ChainVest", "TearoftheGoddess"),
    "GargoyleStoneplate": ("ChainVest", "NegatronCloak"),
    "GiantSlayer": ("BFSword", "RecurveBow"),
    "GuinsoosRageblade": ("NeedlesslyLargeRod", "RecurveBow"),
    "HandofJustice": ("SparringGloves", "TearoftheGoddess"),
    "HextechGunblade": ("BFSword", "NeedlesslyLargeRod"),
    "InfinityEdge": ("BFSword", "SparringGloves"),
    "IonicSpark": ("NeedlesslyLargeRod", "NegatronCloak"),
    "JeweledGauntlet": ("NeedlesslyLargeRod", "SparringGloves"),
    "LastWhisper": ("RecurveBow", "SparringGloves"),
    "LocketoftheIronSolari": ("ChainVest", "NeedlesslyLargeRod"),
    "Morellonomicon": ("GiantsBelt", "NeedlesslyLargeRod"),
    "Quicksilver": ("NegatronCloak", "SparringGloves"),
    "RabadonsDeathcap": ("NeedlesslyLargeRod", "NeedlesslyLargeRod"),
    "RapidFirecannon": ("RecurveBow", "RecurveBow"),
    "Redemption": ("GiantsBelt", "TearoftheGoddess"),
    "RunaansHurricane": ("NegatronCloak", "RecurveBow"),
    "ShroudofStillness": ("ChainVest", "SparringGloves"),
    "SpearofShojin": ("BFSword", "TearoftheGoddess"),
    "StatikkShiv": ("RecurveBow", "TearoftheGoddess"),
    "SunfireCape": ("ChainVest", "GiantsBelt"),
    "TacticiansCrown": ("Spatula", "Spatula"),
    "ThiefsGloves": ("SparringGloves", "SparringGloves"),
    "TitansResolve": ("ChainVest", "RecurveBow"),
    "WarmogsArmor": ("GiantsBelt", "GiantsBelt"),
    "ZekesHerald": ("BFSword", "GiantsBelt"),
    "Zephyr": ("GiantsBelt", "NegatronCloak"),
    "ZzRotPortal": ("GiantsBelt", "RecurveBow"),
}


def champion_board_size(champion: str) -> int:
    return CHAMPIONS[champion]["Board Size"]


def champion_gold_cost(champion: str) -> int:
    return CHAMPIONS[champion]["Gold"]
