import csv
import io
import pycountry
from datetime import datetime

def get_country_name(country_id: str) -> str:
    """Dynamically resolves ISO alpha-2 code to full country name."""
    try:
        country = pycountry.countries.get(alpha_2=country_id.upper())
        return country.name if country else country_id
    except Exception:
        return country_id

def generate_profile_csv(profiles):
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "id", "name", "gender", "gender_probability", "age", 
        "age_group", "country_id", "country_name", "country_probability", "created_at"
    ])
    
    for p in profiles:
        writer.writerow([
            str(p.id),
            p.name,
            p.gender,
            p.gender_probability,
            p.age,
            p.age_group,
            p.country_id,
            get_country_name(p.country_id), 
            p.country_probability,
            p.created_at.isoformat() if p.created_at else ""
        ])
    
    return output.getvalue()