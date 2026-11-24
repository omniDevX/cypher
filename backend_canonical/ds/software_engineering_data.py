"""Software engineering demo data stored in the Alembic-managed PostgreSQL database."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from .data_source_mapper import DataSourceMapper


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _database_url() -> URL:
    value = os.getenv("PG_URL") or os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("Set PG_URL (or DATABASE_URL) in ontology_knowledgegraph/.env")
    url = make_url(value)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


class SoftwareEngineeringDemo:
    """Create sample software engineering data and build its ontology."""

    TABLES = ["projects", "teams", "developers", "requirements", "tasks"]

    def __init__(self, db_path: str | None = None):
        # db_path is retained for call compatibility; PostgreSQL is configured via .env.
        self.db_url = _database_url()
        self.mapper = DataSourceMapper()

    def create_database(self) -> bool:
        """Apply migrations and insert the demo rows if the tables are empty."""
        try:
            alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
            alembic_cfg.set_main_option("sqlalchemy.url", self.db_url.render_as_string(hide_password=False).replace("%", "%%"))
            command.upgrade(alembic_cfg, "head")

            with create_engine(self.db_url).begin() as conn:
                if conn.execute(text("SELECT EXISTS (SELECT 1 FROM projects)")).scalar_one():
                    print("PostgreSQL demo tables already contain data")
                    return True
                self._insert_sample_data(conn)
            print("PostgreSQL demo data created successfully")
            return True
        except Exception as exc:
            print(f"Failed to create PostgreSQL demo data: {exc}")
            return False

    @staticmethod
    def _insert_sample_data(conn) -> None:
        conn.execute(text("""
            INSERT INTO projects (name, description, status, start_date, end_date, budget) VALUES
            ('电商平台项目', '在线购物和交易的综合平台', 'active', '2024-01-01', '2024-12-31', 500000.0),
            ('移动应用项目', '跨平台移动应用程序', 'planning', '2024-03-01', '2024-10-31', 300000.0),
            ('数据分析平台', '企业级数据分析工具', 'completed', '2023-06-01', '2023-12-31', 200000.0)
        """))
        conn.execute(text("""
            INSERT INTO teams (name, project_id, leader_id, description) VALUES
            ('前端开发团队', 1, 1, '负责用户界面开发'),
            ('后端开发团队', 1, 2, '负责服务器端开发'),
            ('移动开发团队', 2, 3, '负责移动应用开发'),
            ('数据团队', 3, 4, '负责数据处理和分析')
        """))
        conn.execute(text("""
            INSERT INTO developers (name, email, role, team_id, experience_years, skills) VALUES
            ('张三', 'zhangsan@company.com', 'frontend_developer', 1, 3, 'React,Vue,JavaScript'),
            ('李四', 'lisi@company.com', 'backend_developer', 2, 5, 'Python,Java,Spring'),
            ('王五', 'wangwu@company.com', 'mobile_developer', 3, 4, 'React Native,Flutter'),
            ('赵六', 'zhaoliu@company.com', 'data_scientist', 4, 6, 'Python,R,SQL'),
            ('钱七', 'qianqi@company.com', 'fullstack_developer', 1, 4, 'Node.js,React,Python'),
            ('孙八', 'sunba@company.com', 'devops_engineer', 2, 3, 'Docker,Kubernetes,AWS')
        """))
        conn.execute(text("""
            INSERT INTO requirements (title, description, project_id, priority, status, complexity, assigned_to) VALUES
            ('用户注册功能', '用户可以通过邮箱或手机号注册账户', 1, 'high', 'open', 'medium', 1),
            ('商品浏览功能', '用户可以浏览和搜索商品', 1, 'high', 'in_progress', 'medium', 2),
            ('购物车功能', '用户可以添加商品到购物车', 1, 'medium', 'open', 'low', 1),
            ('订单管理功能', '用户可以查看和管理订单', 1, 'medium', 'open', 'high', 2),
            ('移动端适配', '适配移动设备界面', 2, 'high', 'planning', 'medium', 3),
            ('数据分析仪表板', '提供数据可视化界面', 3, 'medium', 'completed', 'high', 4)
        """))
        conn.execute(text("""
            INSERT INTO tasks (title, description, requirement_id, assigned_to, status, priority, estimated_hours, actual_hours) VALUES
            ('设计注册页面', '设计用户注册界面', 1, 1, 'todo', 'high', 8.0, NULL),
            ('实现注册API', '开发用户注册后端接口', 1, 2, 'in_progress', 'high', 12.0, 6.0),
            ('商品列表页面', '开发商品展示页面', 2, 1, 'todo', 'medium', 16.0, NULL),
            ('搜索功能实现', '实现商品搜索功能', 2, 2, 'todo', 'medium', 10.0, NULL),
            ('购物车UI设计', '设计购物车界面', 3, 1, 'todo', 'medium', 6.0, NULL),
            ('移动端导航', '实现移动端导航组件', 5, 3, 'planning', 'medium', 8.0, NULL),
            ('数据图表组件', '开发数据可视化组件', 6, 4, 'completed', 'high', 20.0, 18.0)
        """))

    def build_ontology_from_database(self) -> dict[str, Any]:
        from .postgres_data_source import PostgreSQLDataSource

        return self.mapper.build_ontology_from_database(self.db_url, self.TABLES, PostgreSQLDataSource)

    def get_database_statistics(self) -> dict[str, Any]:
        try:
            with create_engine(self.db_url).connect() as conn:
                stats: dict[str, Any] = {}
                for table in self.TABLES:
                    stats[f"{table}_count"] = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
                for table, column, key in [
                    ("projects", "status", "project_status_distribution"),
                    ("tasks", "status", "task_status_distribution"),
                    ("developers", "role", "developer_role_distribution"),
                ]:
                    rows = conn.execute(text(f"SELECT {column}, COUNT(*) FROM {table} GROUP BY {column}"))
                    stats[key] = dict(rows.fetchall())
                return stats
        except Exception as exc:
            print(f"Failed to get database statistics: {exc}")
            return {"error": str(exc)}

    def demonstrate_relations(self) -> list[dict[str, Any]]:
        ontology_data = self.build_ontology_from_database()
        return [
            {
                "subject": instance.name,
                "relation_type": relation.get("type"),
                "relation_name": relation.get("relation_name"),
                "object": relation.get("object"),
                "confidence": relation.get("confidence"),
            }
            for instance in ontology_data.get("instances", [])
            for relation in instance.relations
        ]


def main() -> None:
    demo = SoftwareEngineeringDemo()
    print("Building the software engineering ontology from PostgreSQL...")
    if not demo.create_database():
        return
    stats = demo.get_database_statistics()
    print("\nDatabase statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    ontology_data = demo.build_ontology_from_database()
    if "error" in ontology_data:
        print(f"Ontology build failed: {ontology_data['error']}")
        return
    print(f"\nOntology built: {len(ontology_data['classes'])} classes, "
          f"{len(ontology_data['instances'])} instances, "
          f"{len(ontology_data['data_sources'])} data sources")
    print(f"Relations found: {len(demo.demonstrate_relations())}")


if __name__ == "__main__":
    main()
