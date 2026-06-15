from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime, timezone

from app.db.database import EnvironmentDB, AIProviderDB, AnalysisDB, RecommendationDB
from app.models.environment import EnvironmentCreate, EnvironmentUpdate
from app.models.ai_provider import AIProviderCreate
from app.models.analysis import AnalysisCreate, AnalysisStatus


class EnvironmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: EnvironmentCreate) -> EnvironmentDB:
        from app.core.security import encrypt_value
        obj = EnvironmentDB(
            name=data.name,
            url=str(data.url),
            env_type=data.env_type.value,
            token_encrypted=encrypt_value(data.token),
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, env_id: int) -> EnvironmentDB | None:
        result = await self.db.execute(select(EnvironmentDB).where(EnvironmentDB.id == env_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[EnvironmentDB]:
        result = await self.db.execute(select(EnvironmentDB))
        return list(result.scalars().all())

    async def delete(self, env_id: int) -> bool:
        result = await self.db.execute(delete(EnvironmentDB).where(EnvironmentDB.id == env_id))
        await self.db.commit()
        return result.rowcount > 0

    def get_token(self, env: EnvironmentDB) -> str:
        from app.core.security import decrypt_value
        return decrypt_value(env.token_encrypted)


class AIProviderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: AIProviderCreate) -> AIProviderDB:
        from app.core.security import encrypt_value
        obj = AIProviderDB(
            name=data.name,
            provider_type=data.provider_type.value,
            model=data.model,
            api_key_encrypted=encrypt_value(data.api_key) if data.api_key else None,
            endpoint=data.endpoint,
            extra_config=data.extra_config,
            is_default=data.is_default,
            fallback_order=data.fallback_order,
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, provider_id: int) -> AIProviderDB | None:
        result = await self.db.execute(select(AIProviderDB).where(AIProviderDB.id == provider_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[AIProviderDB]:
        result = await self.db.execute(
            select(AIProviderDB).order_by(AIProviderDB.fallback_order)
        )
        return list(result.scalars().all())

    async def get_default(self) -> AIProviderDB | None:
        result = await self.db.execute(
            select(AIProviderDB).where(AIProviderDB.is_default == True).limit(1)
        )
        return result.scalar_one_or_none()

    def get_api_key(self, provider: AIProviderDB) -> str | None:
        from app.core.security import decrypt_value
        if not provider.api_key_encrypted:
            return None
        return decrypt_value(provider.api_key_encrypted)

    async def get_fallback_chain(self, primary_id: int) -> list[AIProviderDB]:
        """Return all providers ordered by fallback_order, with primary first."""
        result = await self.db.execute(
            select(AIProviderDB).order_by(AIProviderDB.fallback_order)
        )
        providers = list(result.scalars().all())
        primary = next((p for p in providers if p.id == primary_id), None)
        if primary:
            providers.remove(primary)
            providers.insert(0, primary)
        return providers


class AnalysisRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: AnalysisCreate) -> AnalysisDB:
        obj = AnalysisDB(
            environment_id=data.environment_id,
            ai_provider_id=data.ai_provider_id,
            analysis_type=data.analysis_type.value,
            time_range_hours=data.time_range_hours,
            parameters=data.parameters,
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, analysis_id: int) -> AnalysisDB | None:
        result = await self.db.execute(
            select(AnalysisDB).where(AnalysisDB.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 50,
        status: str | None = None,
        analysis_type: str | None = None,
    ) -> list[AnalysisDB]:
        query = select(AnalysisDB).order_by(AnalysisDB.created_at.desc()).limit(limit)
        if status:
            query = query.where(AnalysisDB.status == status)
        if analysis_type:
            query = query.where(AnalysisDB.analysis_type == analysis_type)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete(self, analysis_id: int) -> bool:
        result = await self.db.execute(delete(AnalysisDB).where(AnalysisDB.id == analysis_id))
        await self.db.commit()
        return result.rowcount > 0

    async def update_status(
        self,
        analysis_id: int,
        status: AnalysisStatus,
        result: dict | None = None,
        reasoning_steps: list[dict] | None = None,
        error_message: str | None = None,
    ) -> None:
        values: dict = {"status": status.value}
        if result is not None:
            values["result"] = result
        if reasoning_steps is not None:
            values["reasoning_steps"] = reasoning_steps
        if error_message is not None:
            values["error_message"] = error_message
        if status in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
            values["completed_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(AnalysisDB).where(AnalysisDB.id == analysis_id).values(**values)
        )
        await self.db.commit()


class RecommendationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_by_analysis_id(self, analysis_id: int) -> int:
        """Delete all recommendations for a given analysis."""
        result = await self.db.execute(
            delete(RecommendationDB).where(RecommendationDB.analysis_id == analysis_id)
        )
        await self.db.commit()
        return result.rowcount
