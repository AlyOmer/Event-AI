import httpx
from fastapi import Request
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings, get_settings as _get_settings


async def get_session(request: Request):
    """Yield an AsyncSession from the app-level session factory."""
    async with request.app.state.session_factory() as session:
        yield session


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the shared httpx.AsyncClient from app state."""
    return request.app.state.http_client


async def get_llm_client(request: Request) -> AsyncOpenAI:
    """Return the shared AsyncOpenAI (Gemini-compatible) client from app state."""
    return request.app.state.llm_client


async def get_run_config(request: Request):
    """Return the shared RunConfig from app state."""
    return request.app.state.run_config


async def get_settings_dep() -> Settings:
    """Return the cached Settings instance."""
    return _get_settings()
