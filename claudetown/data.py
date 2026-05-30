"""Static flavor data for ClaudeTown.

This module holds the vocabulary the simulation draws on: names, personality
traits, occupations, building types, and bits of narrative flavor. It contains
no logic -- just data -- so future sessions can safely expand the town's
character by adding entries here without touching the engine.
"""

# --- Names -----------------------------------------------------------------

GIVEN_NAMES_F = [
    "Ada", "Briony", "Cosima", "Delphine", "Elspeth", "Fenna", "Greta",
    "Halcyon", "Isolde", "Juniper", "Kestrel", "Linnea", "Maren", "Nessa",
    "Orla", "Petra", "Quilla", "Rowena", "Saffron", "Tamsin", "Una",
    "Verity", "Wren", "Xanthe", "Yara", "Zinnia", "Bramble", "Clove",
    "Marigold", "Sorrel", "Posy", "Hazel", "Ivy", "Maeve", "Sable",
]

GIVEN_NAMES_M = [
    "Aldous", "Barnaby", "Caspian", "Dorian", "Edmund", "Finnian", "Gideon",
    "Hollis", "Ignatius", "Jasper", "Knox", "Leopold", "Magnus", "Niall",
    "Osric", "Percival", "Quentin", "Rufus", "Silas", "Thaddeus", "Ulric",
    "Viktor", "Wendell", "Xavier", "Yorick", "Zephyr", "Ash", "Crispin",
    "Flint", "Hawthorn", "Linden", "Roman", "Bran", "Corwin", "Emrys",
]

GIVEN_NAMES_N = [
    "Ari", "Bay", "Cy", "Eden", "Frey", "Indigo", "Jules", "Lux",
    "Marsh", "Onyx", "Reed", "Sage", "Vale", "Wisp", "Ember", "North",
]

SURNAMES = [
    "Ashdown", "Briarwood", "Coppersmith", "Dunmore", "Elmsworth", "Fairweather",
    "Greenhollow", "Hartwell", "Ironwood", "Larkspur", "Meadowsweet", "Nightingale",
    "Oakhart", "Pennywhistle", "Quill", "Ravensworth", "Stonebrook", "Thistledown",
    "Underhill", "Vesper", "Whitlock", "Yarrow", "Bellwether", "Cinderhaugh",
    "Drumlin", "Fernsby", "Glimmer", "Holloway", "Marston", "Penhallow",
    "Rookwood", "Sallow", "Thorne", "Wexley", "Aldercott", "Brightwater",
]

# --- Personality -----------------------------------------------------------

TRAITS = [
    "kind", "stubborn", "curious", "shy", "ambitious", "lazy", "generous",
    "miserly", "brave", "anxious", "witty", "dour", "honest", "scheming",
    "patient", "hot-tempered", "dreamy", "practical", "loyal", "fickle",
    "gentle", "fierce", "humble", "proud", "industrious", "restless",
    "tender-hearted", "guarded", "merry", "melancholy", "inventive", "traditional",
]

# Traits that nudge particular behaviors (used by the engine for flavor weighting).
TRAIT_AMBITIOUS = {"ambitious", "industrious", "inventive", "proud", "restless"}
TRAIT_SOCIAL = {"kind", "generous", "merry", "witty", "tender-hearted", "gentle"}
TRAIT_PRICKLY = {"stubborn", "hot-tempered", "scheming", "fickle", "proud", "guarded"}

# --- Work & Buildings ------------------------------------------------------

# Each building type: jobs it provides, how many citizens it can employ, and
# the prerequisites (min population, treasury cost) for the town to build one.
BUILDING_TYPES = {
    "house": {
        "jobs": [], "employs": 0, "min_pop": 0, "cost": 20,
        "desc": "a modest dwelling", "icon": "house",
    },
    "farm": {
        "jobs": ["farmer", "shepherd", "orchardist"], "employs": 3,
        "min_pop": 0, "cost": 0, "desc": "tilled fields and pens", "icon": "farm",
    },
    "well": {
        "jobs": ["water-keeper"], "employs": 1, "min_pop": 0, "cost": 15,
        "desc": "the town's source of fresh water", "icon": "well",
    },
    "market": {
        "jobs": ["merchant", "grocer", "trader"], "employs": 3,
        "min_pop": 8, "cost": 60, "desc": "stalls of trade and gossip", "icon": "market",
    },
    "smithy": {
        "jobs": ["blacksmith", "farrier"], "employs": 2,
        "min_pop": 10, "cost": 70, "desc": "the ring of hammer on anvil", "icon": "smithy",
    },
    "tavern": {
        "jobs": ["innkeeper", "cook", "minstrel"], "employs": 3,
        "min_pop": 12, "cost": 80, "desc": "warmth, ale, and song", "icon": "tavern",
    },
    "mill": {
        "jobs": ["miller"], "employs": 1, "min_pop": 14, "cost": 90,
        "desc": "great turning stones", "icon": "mill",
    },
    "temple": {
        "jobs": ["priest", "acolyte"], "employs": 2, "min_pop": 16, "cost": 120,
        "desc": "quiet bells and candlelight", "icon": "temple",
    },
    "school": {
        "jobs": ["teacher", "tutor"], "employs": 2, "min_pop": 20, "cost": 130,
        "desc": "slates, chalk, and chatter", "icon": "school",
    },
    "library": {
        "jobs": ["librarian", "scribe"], "employs": 2, "min_pop": 24, "cost": 160,
        "desc": "shelves of patient knowledge", "icon": "library",
    },
    "town_hall": {
        "jobs": ["mayor", "clerk", "constable"], "employs": 3, "min_pop": 28, "cost": 200,
        "desc": "the seat of the town's affairs", "icon": "town_hall",
    },
    "observatory": {
        "jobs": ["astronomer", "cartographer"], "employs": 2, "min_pop": 34, "cost": 260,
        "desc": "a dome open to the stars", "icon": "observatory",
    },
    "theatre": {
        "jobs": ["playwright", "actor", "stagehand"], "employs": 3, "min_pop": 40, "cost": 300,
        "desc": "masks, velvet, and applause", "icon": "theatre",
    },
}

# Order in which the town prefers to construct civic buildings.
CIVIC_BUILD_ORDER = [
    "well", "market", "smithy", "tavern", "mill", "temple",
    "school", "library", "town_hall", "observatory", "theatre",
]

# --- Calendar --------------------------------------------------------------

MONTHS = [
    "Frostwane", "Thawmoon", "Seedfall", "Bloomtide", "Sunhigh", "Hayrest",
    "Goldmaize", "Emberfall", "Mistgather", "Leafdown", "Snowcome", "Yuleweald",
]

SEASON_OF_MONTH = (
    ["winter"] * 2 + ["spring"] * 3 + ["summer"] * 3 + ["autumn"] * 3 + ["winter"]
)

WEATHER_BY_SEASON = {
    "winter": ["bitter frost", "heavy snow", "clear cold", "grey sleet", "still chill"],
    "spring": ["soft rain", "bright thaw", "blustery showers", "first warmth", "green haze"],
    "summer": ["golden heat", "lazy sun", "thunderheads", "dry wind", "long dusk"],
    "autumn": ["crisp wind", "amber light", "early mist", "falling leaves", "harvest sun"],
}

# --- Naming helpers for buildings -----------------------------------------

BUILDING_NAME_ADJ = [
    "Old", "New", "Bright", "Quiet", "Crooked", "High", "Low", "Hidden",
    "Golden", "Silver", "Grey", "Red", "Whispering", "Merry", "Stout",
]

BUILDING_NAME_NOUN = [
    "Oak", "Stone", "Hollow", "Spring", "Hearth", "Crossing", "Hill",
    "Brook", "Garden", "Lantern", "Bell", "Anchor", "Fox", "Raven", "Rose",
]
