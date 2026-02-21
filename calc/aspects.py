# calc/aspects.py
from typing import Dict, List
from .base import SIGN_INDEX

def parashara_aspects(sign_idx_from: int) -> Dict[str, List[int]]:
    # return house offsets for general and special aspects (1-based house numbers)
    # Special aspects by planet; generic 7th for others.
    special = {
        "Ma": [4,7,8],
        "Ju": [5,7,9],
        "Sa": [3,7,10],
    }
    return special
