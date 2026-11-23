"""配置文件"""
import os
from dotenv import load_dotenv

load_dotenv()

# Neo4j数据库配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12345678")

# Embedder配置
EMBEDDER_API_KEY = os.getenv("EMBEDDER_API_KEY", "ollama")
EMBEDDER_MODEL = os.getenv("EMBEDDER_MODEL", "bge-m3:latest")
EMBEDDER_DIM = int(os.getenv("EMBEDDER_DIM", "1024"))
EMBEDDER_BASE_URL = os.getenv("EMBEDDER_BASE_URL", "http://localhost:11434")

# 应用配置
APP_NAME = "Ontology Knowledge Graph"
DEBUG = True

def get_embedder_config():
    """获取Embedder配置"""
    return {
        'api_key': EMBEDDER_API_KEY,
        'embedding_model': EMBEDDER_MODEL,
        'embedding_dim': EMBEDDER_DIM,
        'base_url': EMBEDDER_BASE_URL
    }
