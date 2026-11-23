from fastapi import APIRouter

from .neo4j import rouAI
from .legacy_fibo_mapping import legacyFiboRouter
from .sql_lineage import sqlLineageRouter

rou = APIRouter()

rou.include_router(rouAI)
rou.include_router(legacyFiboRouter)
rou.include_router(sqlLineageRouter)
