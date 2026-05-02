import re
import pycountry
from typing import Dict, Any, Optional


COUNTRY_LOOKUP = {}
for country in pycountry.countries:
    COUNTRY_LOOKUP[country.name.lower()] = country.alpha_2
    if hasattr(country, 'official_name'):
        COUNTRY_LOOKUP[country.official_name.lower()] = country.alpha_2


def parse_natural_language(query_str: str) -> Optional[Dict[str, Any]]:
    filters = {}
    q = query_str.lower()

    if re.search(r"\b(female|females)\b", q):
        filters["gender"] = "female"
    elif re.search(r"\b(male|males)\b", q):
        filters["gender"] = "male"


    if "young" in q:
        filters["min_age"] = 16
        filters["max_age"] = 24
    if "adult" in q: filters["age_group"] = "adult"
    if "senior" in q: filters["age_group"] = "senior"
    if "child" in q: filters["age_group"] = "child"
    if "teenager" in q: filters["age_group"] = "teenager"

    
    above_match = re.search(r"(?:above|over|after|>)\s*(\d+)", q)
    if above_match:
        filters["min_age"] = int(above_match.group(1))

    
    below_match = re.search(r"(?:below|under|before|<)\s*(\d+)", q)
    if below_match:
        filters["max_age"] = int(below_match.group(1))

   
    words = q.split()
    
    for word in words:
        if word in COUNTRY_LOOKUP:
            filters["country_id"] = COUNTRY_LOOKUP[word]
            break
    
    if "country_id" not in filters:
        for name, code in COUNTRY_LOOKUP.items():
            if len(name.split()) > 1 and name in q:
                filters["country_id"] = code
                break

    return filters if filters else None


