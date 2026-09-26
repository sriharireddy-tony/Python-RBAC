from fastapi import APIRouter

from app.api.v1 import tenants

api_router = APIRouter()
api_router.include_router(tenants.router)