"""
GOTv3 Mini App — FastAPI Backend
PostgreSQL dan ma'lumot olib, frontend uchun API taqdim etadi.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import os
from typing import List, Optional, Dict, Any

# Models import — GOTv3 proyektidagi models.py dan nusxa olinadi
from models import (
    House, User, War, Alliance, AllianceGroup, AllianceGroupMember,
    Chronicle, MarketPrice, IronBankLoan, IronBankDeposit,
    WarStatusEnum, RoleEnum, RegionEnum
)

# ──────────────────────────────────────────────────
# App va DB sozlash
# ──────────────────────────────────────────────────
app = FastAPI(title="GOTv3 Mini App API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/got_bot"
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# ──────────────────────────────────────────────────
# Region → koordinata mapping (Westeros xaritasi uchun)
# ──────────────────────────────────────────────────
REGION_COORDS = {
    "Shimol":              {"x": 42, "y": 8,  "label": "The North",     "color": "#aed6f1"},
    "Vodiy":               {"x": 58, "y": 32, "label": "The Vale",      "color": "#a9dfbf"},
    "Daryo yerlari":       {"x": 44, "y": 38, "label": "Riverlands",    "color": "#f9e79f"},
    "Temir orollar":       {"x": 24, "y": 30, "label": "Iron Islands",  "color": "#aab7b8"},
    "G'arbiy yerlar":      {"x": 28, "y": 45, "label": "Westerlands",   "color": "#f0b27a"},
    "Qirollik bandargohi": {"x": 56, "y": 55, "label": "King's Landing","color": "#c39bd3"},
    "Tyrellar vodiysi":    {"x": 38, "y": 62, "label": "The Reach",     "color": "#82e0aa"},
    "Bo'ronli yerlar":     {"x": 60, "y": 68, "label": "Stormlands",    "color": "#85c1e9"},
    "Dorn":                {"x": 50, "y": 82, "label": "Dorne",         "color": "#f1948a"},
}


# ──────────────────────────────────────────────────
# API endpoints
# ──────────────────────────────────────────────────

@app.get("/api/map")
async def get_map_data():
    """
    Xarita uchun barcha ma'lumotlar: xonadonlar, urushlar, ittifoqlar.
    Frontend bitta so'rovda hamma narsani oladi.
    """
    async with AsyncSessionLocal() as db:
        # Barcha xonadonlar
        result = await db.execute(
            select(House)
            .options(
                selectinload(House.lord),
                selectinload(House.high_lord),
                selectinload(House.members),
            )
        )
        houses = result.scalars().all()

        # Faol urushlar
        result = await db.execute(
            select(War)
            .options(
                selectinload(War.attacker),
                selectinload(War.defender),
            )
            .where(War.status.in_(["declared", "grace_period", "fighting"]))
        )
        active_wars = result.scalars().all()

        # Faol ittifoqlar
        result = await db.execute(
            select(AllianceGroup)
            .options(selectinload(AllianceGroup.members).selectinload(AllianceGroupMember.house))
            .where(AllianceGroup.is_active == True)
        )
        alliances = result.scalars().all()

        # ──── Xonadonlar data ────
        houses_data = []
        for h in houses:
            region_info = REGION_COORDS.get(h.region.value if hasattr(h.region, 'value') else str(h.region), {})
            member_count = len([m for m in h.members if m.is_active])

            houses_data.append({
                "id": h.id,
                "name": h.name,
                "region": h.region.value if hasattr(h.region, 'value') else str(h.region),
                "region_label": region_info.get("label", ""),
                "region_color": region_info.get("color", "#ccc"),
                "x": region_info.get("x", 50),
                "y": region_info.get("y", 50),
                "treasury": h.treasury,
                "total_soldiers": h.total_soldiers,
                "total_dragons": h.total_dragons,
                "total_scorpions": h.total_scorpions,
                "member_count": member_count,
                "lord_name": h.lord.full_name if h.lord else None,
                "high_lord_name": h.high_lord.full_name if h.high_lord else None,
                "is_under_occupation": h.is_under_occupation,
                "occupier_house_id": h.occupier_house_id,
                "tax_rate": h.permanent_tax_rate,
            })

        # ──── Urushlar data ────
        wars_data = []
        for w in active_wars:
            atk_region = REGION_COORDS.get(
                w.attacker.region.value if w.attacker and hasattr(w.attacker.region, 'value') else "", {}
            )
            def_region = REGION_COORDS.get(
                w.defender.region.value if w.defender and hasattr(w.defender.region, 'value') else "", {}
            )
            wars_data.append({
                "id": w.id,
                "attacker_house": w.attacker.name if w.attacker else "?",
                "attacker_house_id": w.attacker_house_id,
                "defender_house": w.defender.name if w.defender else "?",
                "defender_house_id": w.defender_house_id,
                "status": w.status.value if hasattr(w.status, 'value') else str(w.status),
                "war_type": w.war_type,
                "declared_at": w.declared_at.isoformat() if w.declared_at else None,
                "attacker_x": atk_region.get("x", 50),
                "attacker_y": atk_region.get("y", 50),
                "defender_x": def_region.get("x", 50),
                "defender_y": def_region.get("y", 50),
            })

        # ──── Ittifoqlar data ────
        alliances_data = []
        for ag in alliances:
            member_house_ids = [m.house_id for m in ag.members]
            alliances_data.append({
                "id": ag.id,
                "name": ag.name,
                "leader_house_id": ag.leader_house_id,
                "member_house_ids": member_house_ids,
                "member_count": len(member_house_ids),
            })

        # ──── Statistika ────
        result = await db.execute(select(func.count(User.id)).where(User.is_active == True))
        total_players = result.scalar_one()

        result = await db.execute(select(func.count(House.id)))
        total_houses = result.scalar_one()

        result = await db.execute(select(func.count(War.id)).where(
            War.status.in_(["declared", "grace_period", "fighting"])
        ))
        active_war_count = result.scalar_one()

        return {
            "houses": houses_data,
            "wars": wars_data,
            "alliances": alliances_data,
            "stats": {
                "total_players": total_players,
                "total_houses": total_houses,
                "active_wars": active_war_count,
                "total_alliances": len(alliances_data),
            },
            "regions": REGION_COORDS,
        }


@app.get("/api/house/{house_id}")
async def get_house_detail(house_id: int):
    """Bitta xonadon haqida to'liq ma'lumot."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(House)
            .options(
                selectinload(House.lord),
                selectinload(House.high_lord),
                selectinload(House.knight),
                selectinload(House.members),
            )
            .where(House.id == house_id)
        )
        house = result.scalar_one_or_none()
        if not house:
            raise HTTPException(status_code=404, detail="House not found")

        # Bu xonadonning urushlari
        result = await db.execute(
            select(War)
            .options(selectinload(War.attacker), selectinload(War.defender))
            .where(
                or_(War.attacker_house_id == house_id, War.defender_house_id == house_id)
            )
            .order_by(War.declared_at.desc())
            .limit(5)
        )
        wars = result.scalars().all()

        # A'zolar ro'yxati
        members = []
        for m in house.members:
            if m.is_active:
                members.append({
                    "id": m.id,
                    "name": m.full_name,
                    "username": m.username,
                    "role": m.role.value if hasattr(m.role, 'value') else str(m.role),
                    "soldiers": m.soldiers,
                    "dragons": m.dragons,
                    "scorpions": m.scorpions,
                })

        wars_list = []
        for w in wars:
            wars_list.append({
                "id": w.id,
                "attacker": w.attacker.name if w.attacker else "?",
                "defender": w.defender.name if w.defender else "?",
                "status": w.status.value if hasattr(w.status, 'value') else str(w.status),
                "declared_at": w.declared_at.isoformat() if w.declared_at else None,
                "winner_house_id": w.winner_house_id,
            })

        region_info = REGION_COORDS.get(
            house.region.value if hasattr(house.region, 'value') else str(house.region), {}
        )

        return {
            "id": house.id,
            "name": house.name,
            "region": house.region.value if hasattr(house.region, 'value') else str(house.region),
            "region_label": region_info.get("label", ""),
            "region_color": region_info.get("color", "#ccc"),
            "treasury": house.treasury,
            "total_soldiers": house.total_soldiers,
            "total_dragons": house.total_dragons,
            "total_scorpions": house.total_scorpions,
            "lord": house.lord.full_name if house.lord else None,
            "high_lord": house.high_lord.full_name if house.high_lord else None,
            "knight": house.knight.full_name if house.knight else None,
            "is_under_occupation": house.is_under_occupation,
            "tax_rate": house.permanent_tax_rate,
            "members": members,
            "recent_wars": wars_list,
            "created_at": house.created_at.isoformat() if house.created_at else None,
        }


@app.get("/api/chronicles")
async def get_chronicles(limit: int = 20):
    """So'nggi voqealar tarixini olish."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Chronicle)
            .order_by(Chronicle.created_at.desc())
            .limit(limit)
        )
        chronicles = result.scalars().all()
        return [
            {
                "id": c.id,
                "event_type": c.event_type,
                "description": c.description,
                "related_house_id": c.related_house_id,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in chronicles
        ]


@app.get("/api/leaderboard")
async def get_leaderboard():
    """Xonadonlar reytingi (askar + ajdar bo'yicha)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(House).order_by(
                (House.total_soldiers + House.total_dragons * 200).desc()
            ).limit(10)
        )
        houses = result.scalars().all()
        return [
            {
                "rank": i + 1,
                "id": h.id,
                "name": h.name,
                "region": h.region.value if hasattr(h.region, 'value') else str(h.region),
                "treasury": h.treasury,
                "total_soldiers": h.total_soldiers,
                "total_dragons": h.total_dragons,
                "power": h.total_soldiers + h.total_dragons * 200 + h.total_scorpions * 25,
            }
            for i, h in enumerate(houses)
        ]


@app.get("/health")
async def health():
    return {"status": "ok"}

# ── Frontend static fayllarni serve qilish ──
# index.html ni root "/" da ko'rsatish
@app.get("/")
async def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "GOTv3 Mini App API is running. Frontend not found."}

# Static fayllar papkasi (agar boshqa fayllar bo'lsa)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/debug")
async def debug():
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    files = os.listdir(base)
    return {"base_dir": base, "files": files}
