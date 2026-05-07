import re

DISTRICT_FIX = {
    "praga polnoc": "praga-polnoc",
    "praga polnoc": "praga-polnoc",
    "praga poludnie": "praga-poludnie",
    "lagiewniki borek falecki": "lagiewniki-borek-falecki",
}

def normalize_district(d: str) -> str:
    """
    Standaryzuje nazwy dzielnic:
    - lower
    - usuwa nadmiar spacji
    """
    d = d.lower().strip()
    d = re.sub(r"\s+", " ", d)
    return d