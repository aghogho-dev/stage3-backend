import csv
import io 
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.dialects.postgresql import insert
from ..models import Profile


async def stream_csv_ingestion(file_content: bytes, db: AsyncSession):
    """
    Processes large CSV files using chunked streaming
    """
    stream =  io.StringIO(file_content.decode("utf-8"))
    reader = csv.DictReader(stream)

    stats = {
        "status": "success",
        "total_rows": 0,
        "inserted": 0,
        "skipped": 0,
        "reasons": {
            "duplicate_name": 0,
            "invalid_data": 0,
            "missing_fields": 0
        }
    }

    chunk_size = 1000

    current_chunk = []

    for row in reader:
        stats["total_rows"] += 1

        name = row.get("name")

        try:
            age = int(row.get("age",-1))
        except (ValueError, TypeError):
            age = -1
        
        if not name or not row.get("gender") or not row.get("country_id"):
            stats["reasons"]["missing_fields"] += 1
            continue 

        if age < 0:
            stats["reasons"]["invalid_data"] += 1
            continue 

        current_chunk.append({
            "name": name,
            "age": age,
            "gender": row["gender"].lower(),
            "country_id": row["country_id"].upper()
        })


        if len(current_chunk) >= chunk_size:
            inserted = await _execute_upsert(db, current_chunk, stats)
            stats["inserted"] += inserted 
            current_chunk = []

    if current_chunk:
        inserted = await _execute_upsert(db, current_chunk, stats)
        stats["inserted"] += inserted


    await db.commit()
    stats["skipped"] = stats["total_rows"] - stats["inserted"]
    return stats 


async def _execute_upsert(db: AsyncSession, chunk: list, stats: dict) -> int:
    stmt = insert(Profile).values(chunk)
    stmt = stmt.on_conflict_do_nothing(index_elements=["name"])

    res = await db.execute(stmt)
    actual_inserted = res.rowcount or 0

    duplicates = len(chunk) - actual_inserted
    stats["reasons"]["duplicate_name"] += duplicates

    return actual_inserted