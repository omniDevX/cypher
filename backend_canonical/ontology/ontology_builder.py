"""直接使用Neo4j语法构建本体知识图谱"""
import sqlite3
import logging
from typing import Dict, List, Any
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text
from config.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

class DirectNeo4jOntologyBuilder:
    """直接使用Neo4j语法构建本体知识图谱"""
    
    def __init__(self):
        self.driver = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """连接Neo4j数据库"""
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info("成功连接到Neo4j数据库")
            return True
        except Exception as e:
            self.logger.error(f"连接Neo4j数据库失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
    
    def clear_database(self):
        """清空数据库中的所有数据"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            self.logger.info("已清空数据库")
    
    def create_ontology_schema(self):
        """创建本体模式"""
        with self.driver.session() as session:
            # 创建约束
            constraints = [
                "CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT team_id_unique IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE", 
                "CREATE CONSTRAINT developer_id_unique IF NOT EXISTS FOR (d:Developer) REQUIRE d.id IS UNIQUE",
                "CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE",
                "CREATE CONSTRAINT task_id_unique IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    self.logger.warning(f"创建约束失败: {e}")
            
            self.logger.info("本体模式创建完成")
    
    def build_ontology_from_sqlite(self, db_path: str):
        """从SQLite数据库构建本体知识图谱"""
        try:
            # 1. 清空现有数据
            self.clear_database()
            
            # 2. 创建本体模式
            self.create_ontology_schema()
            
            # 3. 连接SQLite数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 4. 创建项目节点
            self._create_project_nodes(cursor)
            
            # 5. 创建团队节点
            self._create_team_nodes(cursor)
            
            # 6. 创建开发者节点
            self._create_developer_nodes(cursor)
            
            # 7. 创建需求节点
            self._create_requirement_nodes(cursor)
            
            # 8. 创建任务节点
            self._create_task_nodes(cursor)
            
            # 9. 创建关系
            self._create_relationships(cursor)
            
            conn.close()
            self.logger.info("本体知识图谱构建完成")
            
        except Exception as e:
            self.logger.error(f"构建本体知识图谱失败: {e}")
            raise

    def build_ontology_from_postgres(self, database_url):
        """Build graph nodes and relationships from the PostgreSQL demo tables."""
        self.clear_database()
        self.create_ontology_schema()
        engine = create_engine(database_url)
        try:
            with engine.connect() as conn:
                rows = {
                    table: [dict(row) for row in conn.execute(text(f'SELECT * FROM "{table}"')).mappings()]
                    for table in ("projects", "teams", "developers", "requirements", "tasks")
                }
            # Preserve the existing node creation mapping while converting SQLAlchemy
            # mapping rows to the tuple order expected by the SQLite helpers.
            with self.driver.session() as session:
                for row in rows["projects"]:
                    session.run("CREATE (p:Project $props)", props=row)
                for row in rows["teams"]:
                    session.run("CREATE (n:Team $props)", props=row)
                for row in rows["developers"]:
                    session.run("CREATE (n:Developer $props)", props=row)
                for row in rows["requirements"]:
                    session.run("CREATE (n:Requirement $props)", props=row)
                for row in rows["tasks"]:
                    session.run("CREATE (n:Task $props)", props=row)
            self._create_relationships(None)
            self.logger.info("PostgreSQL ontology graph built")
        finally:
            engine.dispose()
    
    def _create_project_nodes(self, cursor):
        """创建项目节点"""
        cursor.execute("SELECT * FROM projects")
        projects = cursor.fetchall()
        
        with self.driver.session() as session:
            for project in projects:
                project_id, name, description, status, start_date, end_date, budget, created_at = project
                
                session.run("""
                    CREATE (p:Project {
                        id: $id,
                        name: $name,
                        description: $description,
                        status: $status,
                        start_date: $start_date,
                        end_date: $end_date,
                        budget: $budget,
                        created_at: $created_at
                    })
                """, 
                id=project_id, name=name, description=description, status=status,
                start_date=start_date, end_date=end_date, budget=budget, created_at=created_at)
        
        self.logger.info(f"创建了 {len(projects)} 个项目节点")
    
    def _create_team_nodes(self, cursor):
        """创建团队节点"""
        cursor.execute("SELECT * FROM teams")
        teams = cursor.fetchall()
        
        with self.driver.session() as session:
            for team in teams:
                team_id, name, project_id, leader_id, description, created_at = team
                
                session.run("""
                    CREATE (t:Team {
                        id: $id,
                        name: $name,
                        project_id: $project_id,
                        leader_id: $leader_id,
                        description: $description,
                        created_at: $created_at
                    })
                """,
                id=team_id, name=name, project_id=project_id, leader_id=leader_id,
                description=description, created_at=created_at)
        
        self.logger.info(f"创建了 {len(teams)} 个团队节点")
    
    def _create_developer_nodes(self, cursor):
        """创建开发者节点"""
        cursor.execute("SELECT * FROM developers")
        developers = cursor.fetchall()
        
        with self.driver.session() as session:
            for developer in developers:
                dev_id, name, email, role, team_id, experience_years, skills, created_at = developer
                
                session.run("""
                    CREATE (d:Developer {
                        id: $id,
                        name: $name,
                        email: $email,
                        role: $role,
                        team_id: $team_id,
                        experience_years: $experience_years,
                        skills: $skills,
                        created_at: $created_at
                    })
                """,
                id=dev_id, name=name, email=email, role=role, team_id=team_id,
                experience_years=experience_years, skills=skills, created_at=created_at)
        
        self.logger.info(f"创建了 {len(developers)} 个开发者节点")
    
    def _create_requirement_nodes(self, cursor):
        """创建需求节点"""
        cursor.execute("SELECT * FROM requirements")
        requirements = cursor.fetchall()
        
        with self.driver.session() as session:
            for req in requirements:
                req_id, title, description, project_id, priority, status, complexity, assigned_to, created_at = req
                
                session.run("""
                    CREATE (r:Requirement {
                        id: $id,
                        title: $title,
                        description: $description,
                        project_id: $project_id,
                        priority: $priority,
                        status: $status,
                        complexity: $complexity,
                        assigned_to: $assigned_to,
                        created_at: $created_at
                    })
                """,
                id=req_id, title=title, description=description, project_id=project_id,
                priority=priority, status=status, complexity=complexity, assigned_to=assigned_to,
                created_at=created_at)
        
        self.logger.info(f"创建了 {len(requirements)} 个需求节点")
    
    def _create_task_nodes(self, cursor):
        """创建任务节点"""
        cursor.execute("SELECT * FROM tasks")
        tasks = cursor.fetchall()
        
        with self.driver.session() as session:
            for task in tasks:
                task_id, title, description, requirement_id, assigned_to, status, priority, estimated_hours, actual_hours, created_at = task
                
                session.run("""
                    CREATE (t:Task {
                        id: $id,
                        title: $title,
                        description: $description,
                        requirement_id: $requirement_id,
                        assigned_to: $assigned_to,
                        status: $status,
                        priority: $priority,
                        estimated_hours: $estimated_hours,
                        actual_hours: $actual_hours,
                        created_at: $created_at
                    })
                """,
                id=task_id, title=title, description=description, requirement_id=requirement_id,
                assigned_to=assigned_to, status=status, priority=priority,
                estimated_hours=estimated_hours, actual_hours=actual_hours, created_at=created_at)
        
        self.logger.info(f"创建了 {len(tasks)} 个任务节点")
    
    def _create_relationships(self, cursor):
        """创建关系"""
        with self.driver.session() as session:
            # 项目-团队关系
            session.run("""
                MATCH (p:Project), (t:Team)
                WHERE p.id = t.project_id
                CREATE (t)-[:BELONGS_TO]->(p)
            """)
            
            # 团队-开发者关系
            session.run("""
                MATCH (t:Team), (d:Developer)
                WHERE t.id = d.team_id
                CREATE (d)-[:MEMBER_OF]->(t)
            """)
            
            # 项目-需求关系
            session.run("""
                MATCH (p:Project), (r:Requirement)
                WHERE p.id = r.project_id
                CREATE (r)-[:BELONGS_TO]->(p)
            """)
            
            # 需求-任务关系
            session.run("""
                MATCH (r:Requirement), (t:Task)
                WHERE r.id = t.requirement_id
                CREATE (t)-[:IMPLEMENTS]->(r)
            """)
            
            # 开发者-任务关系
            session.run("""
                MATCH (d:Developer), (t:Task)
                WHERE d.id = t.assigned_to
                CREATE (t)-[:ASSIGNED_TO]->(d)
            """)
            
            # 需求-开发者关系（分配关系）
            session.run("""
                MATCH (r:Requirement), (d:Developer)
                WHERE r.assigned_to = d.id
                CREATE (r)-[:ASSIGNED_TO]->(d)
            """)
            
            self.logger.info("关系创建完成")
    
    def verify_ontology(self):
        """验证本体知识图谱"""
        with self.driver.session() as session:
            # 统计节点数量
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
            print("\n=== 本体知识图谱验证 ===")
            print("节点统计:")
            for record in result:
                print(f"  {record['label']}: {record['count']}个")
            
            # 统计关系数量
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            print("\n关系统计:")
            for record in result:
                print(f"  {record['type']}: {record['count']}个")
            
            # 验证数据完整性
            print("\n数据完整性检查:")
            
            # 检查项目
            result = session.run("MATCH (p:Project) RETURN p.name, p.status ORDER BY p.id")
            print("项目:")
            for record in result:
                print(f"  - {record['p.name']} ({record['p.status']})")
            
            # 检查团队
            result = session.run("MATCH (t:Team) RETURN t.name, t.project_id ORDER BY t.id")
            print("团队:")
            for record in result:
                print(f"  - {record['t.name']} (项目ID: {record['t.project_id']})")
            
            # 检查开发者
            result = session.run("MATCH (d:Developer) RETURN d.name, d.role, d.team_id ORDER BY d.id")
            print("开发者:")
            for record in result:
                print(f"  - {record['d.name']} ({record['d.role']}, 团队ID: {record['d.team_id']})")

def main():
    """主函数"""
    # 设置日志级别
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    builder = DirectNeo4jOntologyBuilder()
    
    if not builder.connect():
        print("无法连接到Neo4j数据库")
        return
    
    try:
        print("开始构建直接Neo4j本体知识图谱...")
        builder.build_ontology_from_sqlite("software_engineering.db")
        builder.verify_ontology()
        print("\n本体知识图谱构建完成！")
        
    except Exception as e:
        print(f"构建失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        builder.close()

if __name__ == "__main__":
    main()
