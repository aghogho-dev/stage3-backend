import httpx
import asyncio

async def get_enriched_data(name: str):
    async with httpx.AsyncClient() as client:
        g_task = client.get(f"https://api.genderize.io?name={name}")
        a_task = client.get(f"https://api.agify.io?name={name}")
        n_task = client.get(f"https://api.nationalize.io?name={name}")
        
        g_res, a_res, n_res = await asyncio.gather(g_task, a_task, n_task)
        
    age = a_res.json().get("age", 0) or 0
    # Logic for age_group
    group = "adult"
    if age < 13: group = "child"
    elif age < 20: group = "teenager"
    elif age >= 65: group = "senior"

    country = n_res.json().get("country", [{}])[0]

    return {
        "gender": g_res.json().get("gender"),
        "gender_probability": g_res.json().get("probability"),
        "age": age,
        "age_group": group,
        "country_id": country.get("country_id"),
        "country_probability": country.get("probability")
    }