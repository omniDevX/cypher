"""基于数据库的本体知识图谱查询演示程序 - 基于直接Neo4j实现"""
import logging
import sys
from typing import Optional
from neo4j import GraphDatabase

from config.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from config.neo4j_connector import Neo4jConnector
from ontology.ontology_query_engine import OntologyQueryEngine
from ontology.ontology_models import ConceptType, RelationType, DataSourceType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OntologyKnowledgeGraphSearcher:
    """基于数据库的本体知识图谱查询演示器 - 基于直接Neo4j实现"""
    
    def __init__(self):
        self.neo4j_connector: Optional[Neo4jConnector] = None
        self.query_engine: Optional[OntologyQueryEngine] = None
        self.driver: Optional[GraphDatabase] = None
    
    def initialize(self) -> bool:
        """初始化搜索演示器"""
        try:
            logger.info("初始化基于数据库的本体知识图谱查询演示器...")
            
            # 初始化Neo4j连接器
            self.neo4j_connector = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            
            if not self.neo4j_connector.connect():
                logger.error("无法连接到Neo4j数据库")
                return False
            
            # 初始化查询引擎
            self.query_engine = OntologyQueryEngine(self.neo4j_connector)
            
            # 初始化直接Neo4j驱动
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            
            logger.info("基于数据库的本体知识图谱查询演示器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"搜索演示器初始化失败: {e}")
            return False
    
    def demonstrate_search_capabilities(self):
        """演示基于数据库的本体查询功能"""
        print("\n" + "="*60)
        print("基于数据库的本体知识图谱查询演示")
        print("="*60)
        
        if not self.driver:
            print("Neo4j驱动未初始化")
            return False
        
        with self.driver.session() as session:
            # 1. 基本搜索
            print("\n1. 基本搜索 - 查找所有项目:")
            try:
                result = session.run("MATCH (p:Project) RETURN p.name, p.status ORDER BY p.id")
                projects = list(result)
                for i, project in enumerate(projects, 1):
                    print(f"   {i}. {project['p.name']} ({project['p.status']})")
            except Exception as e:
                print(f"   搜索出错: {e}")
            
            # 2. 按团队搜索
            print("\n2. 按团队搜索 - 查找所有团队:")
            try:
                result = session.run("MATCH (t:Team) RETURN t.name, t.project_id ORDER BY t.id")
                teams = list(result)
                for i, team in enumerate(teams, 1):
                    print(f"   {i}. {team['t.name']} (项目ID: {team['t.project_id']})")
            except Exception as e:
                print(f"   搜索出错: {e}")
            
            # 3. 按开发者搜索
            print("\n3. 按开发者搜索 - 查找所有开发者:")
            try:
                result = session.run("MATCH (d:Developer) RETURN d.name, d.role, d.team_id ORDER BY d.id")
                developers = list(result)
                for i, dev in enumerate(developers, 1):
                    print(f"   {i}. {dev['d.name']} ({dev['d.role']}, 团队ID: {dev['d.team_id']})")
            except Exception as e:
                print(f"   搜索出错: {e}")
            
            # 4. 关系搜索 - 查找团队和项目的关系
            print("\n4. 关系搜索 - 团队和项目的关系:")
            try:
                result = session.run("""
                    MATCH (t:Team)-[:BELONGS_TO]->(p:Project)
                    RETURN t.name as team_name, p.name as project_name
                    ORDER BY t.id
                """)
                relations = list(result)
                for i, rel in enumerate(relations, 1):
                    print(f"   {i}. {rel['team_name']} 属于 {rel['project_name']}")
            except Exception as e:
                print(f"   搜索出错: {e}")
            
            # 5. 关系搜索 - 查找开发者和团队的关系
            print("\n5. 关系搜索 - 开发者和团队的关系:")
            try:
                result = session.run("""
                    MATCH (d:Developer)-[:MEMBER_OF]->(t:Team)
                    RETURN d.name as developer_name, t.name as team_name
                    ORDER BY d.id
                """)
                relations = list(result)
                for i, rel in enumerate(relations, 1):
                    print(f"   {i}. {rel['developer_name']} 是 {rel['team_name']} 的成员")
            except Exception as e:
                print(f"   搜索出错: {e}")
            
            # 6. 复合查询 - 查找特定项目的所有团队成员
            print("\n6. 复合查询 - 电商平台项目的所有团队成员:")
            try:
                result = session.run("""
                    MATCH (p:Project {name: '电商平台项目'})<-[:BELONGS_TO]-(t:Team)<-[:MEMBER_OF]-(d:Developer)
                    RETURN d.name as developer_name, d.role as role, t.name as team_name
                    ORDER BY d.id
                """)
                members = list(result)
                for i, member in enumerate(members, 1):
                    print(f"   {i}. {member['developer_name']} ({member['role']}) - {member['team_name']}")
            except Exception as e:
                print(f"   搜索出错: {e}")
            
            # 7. 统计查询 - 按角色统计开发者
            print("\n7. 统计查询 - 按角色统计开发者:")
            try:
                result = session.run("""
                    MATCH (d:Developer)
                    RETURN d.role as role, count(d) as count
                    ORDER BY count DESC
                """)
                stats = list(result)
                for i, stat in enumerate(stats, 1):
                    print(f"   {i}. {stat['role']}: {stat['count']}人")
            except Exception as e:
                print(f"   搜索出错: {e}")
            
            # 8. 路径查询 - 查找从项目到开发者的完整路径
            print("\n8. 路径查询 - 从项目到开发者的完整路径:")
            try:
                result = session.run("""
                    MATCH path = (p:Project)-[:BELONGS_TO]-(t:Team)-[:MEMBER_OF]-(d:Developer)
                    WHERE p.name = '移动应用项目'
                    RETURN p.name as project, t.name as team, d.name as developer
                    ORDER BY d.id
                """)
                paths = list(result)
                for i, path in enumerate(paths, 1):
                    print(f"   {i}. {path['project']} -> {path['team']} -> {path['developer']}")
            except Exception as e:
                print(f"   搜索出错: {e}")
        
        return True
    
    def show_graph_summary(self):
        """显示知识图谱摘要"""
        print("\n" + "="*60)
        print("知识图谱摘要")
        print("="*60)
        
        if not self.driver:
            print("Neo4j驱动未初始化")
            return
        
        with self.driver.session() as session:
            try:
                # 统计节点数量
                result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
                print(f"\n节点统计:")
                total_nodes = 0
                for record in result:
                    label = record['label']
                    count = record['count']
                    total_nodes += count
                    print(f"  - {label}: {count}个")
                
                # 统计关系数量
                result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
                print(f"\n关系统计:")
                total_relations = 0
                for record in result:
                    rel_type = record['type']
                    count = record['count']
                    total_relations += count
                    print(f"  - {rel_type}: {count}个")
                
                print(f"\n总计:")
                print(f"  - 总节点数: {total_nodes}")
                print(f"  - 总关系数: {total_relations}")
                print(f"  - 图谱类型: 直接Neo4j本体知识图谱")
                print(f"  - 数据来源: SQLite数据库")
                
            except Exception as e:
                print(f"获取图谱摘要失败: {e}")
    
    def demonstrate_queries(self):
        """演示传统查询功能"""
        try:
            logger.info("开始演示传统查询功能...")
            
            if not self.query_engine:
                logger.error("查询引擎未初始化")
                return
            
            # 1. 按概念类型查询
            logger.info("\n=== 按概念类型查询演示 ===")
            class_results = self.query_engine.query_by_concept_type(ConceptType.CLASS)
            logger.info(f"找到 {len(class_results)} 个类概念")
            for result in class_results:
                logger.info(f"  - {result['name']}: {result['label']}")
            
            instance_results = self.query_engine.query_by_concept_type(ConceptType.INSTANCE)
            logger.info(f"找到 {len(instance_results)} 个实例概念")
            for result in instance_results:
                logger.info(f"  - {result['name']}: {result['label']}")
            
            # 2. 按关系类型查询
            logger.info("\n=== 按关系类型查询演示 ===")
            instance_of_results = self.query_engine.query_by_relation_type(RelationType.INSTANCE_OF)
            logger.info(f"找到 {len(instance_of_results)} 个INSTANCE_OF关系")
            for result in instance_of_results:
                logger.info(f"  - {result['source']['name']} -> {result['target']['name']}")
            
            # 3. 概念详情查询
            logger.info("\n=== 概念详情查询演示 ===")
            project_details = self.query_engine.get_concept_details("电商平台项目")
            if project_details:
                logger.info("电商平台项目概念详情:")
                concept = project_details['concept']
                logger.info(f"  概念: {concept.get('name', 'N/A')}")
                logger.info(f"  定义: {concept.get('definition', concept.get('description', 'N/A'))}")
                logger.info(f"  相关概念数: {len(project_details['related_concepts'])}")
                logger.info(f"  层次结构路径数: {len(project_details['hierarchy'])}")
            
        except Exception as e:
            logger.error(f"查询演示失败: {e}")
    
    
    def show_statistics(self):
        """显示统计信息"""
        try:
            logger.info("\n=== 图谱统计信息 ===")
            
            if not self.query_engine:
                logger.error("查询引擎未初始化")
                return
            
            stats = self.query_engine.get_graph_statistics()
            
            logger.info(f"总节点数: {stats.get('total_nodes', 0)}")
            logger.info(f"总关系数: {stats.get('total_relations', 0)}")
            logger.info(f"平均连接度: {stats.get('average_degree', 0):.2f}")
            
            logger.info("\n概念类型分布:")
            concept_types = stats.get("concept_types", {})
            for concept_type, count in concept_types.items():
                logger.info(f"  - {concept_type}: {count}")
            
            logger.info("\n关系类型分布:")
            relations = stats.get("relations", {})
            for relation_type, count in relations.items():
                logger.info(f"  - {relation_type}: {count}")
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.neo4j_connector:
                self.neo4j_connector.close()
                logger.info("Neo4j连接已关闭")
            if self.driver:
                self.driver.close()
                logger.info("Neo4j驱动已关闭")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

def main():
    """主函数 - 基于数据库的本体知识图谱查询演示"""
    searcher = OntologyKnowledgeGraphSearcher()
    
    try:
        print("基于数据库的本体知识图谱查询演示开始！")
        print("="*80)
        
        # 初始化搜索演示器
        if not searcher.initialize():
            logger.error("搜索演示器初始化失败，退出程序")
            sys.exit(1)
        
        # 显示知识图谱摘要
        searcher.show_graph_summary()
        
        # 演示搜索功能
        searcher.demonstrate_search_capabilities()
        
        # 演示传统查询功能
        searcher.demonstrate_queries()
        
        # 显示统计信息
        searcher.show_statistics()
        
        print("\n" + "="*80)
        print("基于数据库的本体知识图谱查询演示完成！")
        print("\n主要特性总结:")
        print("  - 基于数据库表的自动本体构建")
        print("  - 实例与数据源记录的直接绑定")
        print("  - 从表字段自动分析建立关系")
        print("  - 支持多种数据源类型 (SQLite、API、消息队列)")
        print("  - 直接基于Neo4j的知识图谱构建")
        print("  - 数据完全一致，无外部干扰")
        print("  - 结构化查询和统计功能")
        
    except KeyboardInterrupt:
        print("\n用户中断演示")
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        searcher.cleanup()

if __name__ == "__main__":
    main()