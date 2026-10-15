from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ResourceSample


async def save_samples(session: AsyncSession, points: list[dict]) -> None:
    if not points:
        return
    stamps = [datetime.fromisoformat(point["sampled_at"]) for point in points]
    existing = await session.execute(
        select(ResourceSample.sampled_at).where(
            ResourceSample.sampled_at >= min(stamps),
            ResourceSample.sampled_at <= max(stamps),
        )
    )
    seen = set(existing.scalars().all())
    for point, stamp in zip(points, stamps, strict=True):
        if stamp in seen:
            continue
        session.add(
            ResourceSample(
                sampled_at=stamp,
                cpu_percent=point["cpu_percent"],
                ram_used_bytes=point["ram_used_bytes"],
                ram_total_bytes=point["ram_total_bytes"],
                vram_used_bytes=point["vram_used_bytes"],
                vram_total_bytes=point["vram_total_bytes"],
                gpu_util_percent=point["gpu_util_percent"],
            )
        )
    await session.flush()
