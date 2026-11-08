from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AgentRegistry


class AgentRegistryService:
    """
    Manages registered AI agents authorized to interact with the governance bridge.
    """

    async def get_agent(self, agent_id: str, db: AsyncSession) -> Optional[AgentRegistry]:
        stmt = select(AgentRegistry).where(AgentRegistry.agent_id == agent_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_agents(self, db: AsyncSession) -> List[AgentRegistry]:
        stmt = select(AgentRegistry).order_by(AgentRegistry.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def initialize_default_agent(self, data: Dict[str, Any], db: AsyncSession) -> AgentRegistry:
        """
        Ensures a default agent exists on system boot.
        If the agent already exists, preserves all administrator-managed settings
        (such as inactive status or customized allowed_tools) without overwriting them.
        """
        agent_id = data["agent_id"]
        existing = await self.get_agent(agent_id, db)
        if existing:
            return existing

        new_agent = AgentRegistry(
            agent_id=agent_id,
            name=data["name"],
            description=data.get("description"),
            role=data.get("role", "shopping_assistant"),
            department=data.get("department", "Retail Commerce"),
            model_provider=data.get("model_provider", "Google Gemini"),
            model_version=data.get("model_version", "gemini-1.5-pro"),
            owner_tenant=data.get("owner_tenant", "KON Retail Org"),
            status=data.get("status", "active"),
            allowed_tools=data.get("allowed_tools", []),
        )
        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        return new_agent

    async def register_agent(self, data: Dict[str, Any], db: AsyncSession) -> AgentRegistry:
        agent_id = data["agent_id"]
        existing = await self.get_agent(agent_id, db)
        if existing:
            existing.name = data.get("name", existing.name)
            existing.description = data.get("description", existing.description)
            existing.role = data.get("role", existing.role)
            existing.department = data.get("department", existing.department)
            existing.model_provider = data.get("model_provider", existing.model_provider)
            existing.model_version = data.get("model_version", existing.model_version)
            existing.owner_tenant = data.get("owner_tenant", existing.owner_tenant)
            existing.status = data.get("status", existing.status)
            existing.allowed_tools = data.get("allowed_tools", existing.allowed_tools)
            await db.commit()
            await db.refresh(existing)
            return existing

        new_agent = AgentRegistry(
            agent_id=agent_id,
            name=data["name"],
            description=data.get("description"),
            role=data.get("role", "shopping_assistant"),
            department=data.get("department", "Retail Commerce"),
            model_provider=data.get("model_provider", "Google Gemini"),
            model_version=data.get("model_version", "gemini-1.5-pro"),
            owner_tenant=data.get("owner_tenant", "KON Retail Org"),
            status=data.get("status", "active"),
            allowed_tools=data.get("allowed_tools", []),
        )
        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        return new_agent

    async def update_agent(self, agent_id: str, updates: Dict[str, Any], db: AsyncSession) -> Optional[AgentRegistry]:
        agent = await self.get_agent(agent_id, db)
        if not agent:
            return None

        if "name" in updates and updates["name"] is not None:
            agent.name = updates["name"]
        if "description" in updates and updates["description"] is not None:
            agent.description = updates["description"]
        if "role" in updates and updates["role"] is not None:
            agent.role = updates["role"]
        if "department" in updates and updates["department"] is not None:
            agent.department = updates["department"]
        if "model_provider" in updates and updates["model_provider"] is not None:
            agent.model_provider = updates["model_provider"]
        if "model_version" in updates and updates["model_version"] is not None:
            agent.model_version = updates["model_version"]
        if "owner_tenant" in updates and updates["owner_tenant"] is not None:
            agent.owner_tenant = updates["owner_tenant"]
        if "status" in updates and updates["status"] is not None:
            agent.status = updates["status"]
        if "allowed_tools" in updates and updates["allowed_tools"] is not None:
            agent.allowed_tools = updates["allowed_tools"]

        await db.commit()
        await db.refresh(agent)
        return agent

    async def toggle_agent_status(self, agent_id: str, db: AsyncSession) -> Optional[AgentRegistry]:
        agent = await self.get_agent(agent_id, db)
        if not agent:
            return None
        agent.status = "inactive" if agent.status == "active" else "active"
        await db.commit()
        await db.refresh(agent)
        return agent


agent_registry_service = AgentRegistryService()
