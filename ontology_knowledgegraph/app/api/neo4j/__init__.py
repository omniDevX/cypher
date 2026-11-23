from fastapi import APIRouter

from .neo4j_basic import neo4jRou
from .api_loan import loanRou

rouAI = APIRouter()

rouAI.include_router(loanRou, prefix="/loan", tags=["RDFLPG"])
rouAI.include_router(neo4jRou, prefix="/neo4j", tags=["Neo4j"])
