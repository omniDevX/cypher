"""Neo4j数据库连接器"""
from neo4j import GraphDatabase
import logging
from typing import List, Dict, Any, Optional
from .config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from ontology.ontology_models import OntologyConcept, OntologyClass, OntologyInstance, SemanticRelation

class Neo4jConnector:
    """Neo4j数据库连接器"""
    
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # 测试连接
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
            self.logger.info("Neo4j数据库连接已关闭")
    
    def create_constraints(self):
        """创建数据库约束和索引"""
        constraints = [
            # 原有的Ontology约束
            "CREATE CONSTRAINT concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT instance_id_unique IF NOT EXISTS FOR (i:Instance) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT class_name_unique IF NOT EXISTS FOR (cl:Class) REQUIRE cl.name IS UNIQUE",
            "CREATE INDEX concept_name_index IF NOT EXISTS FOR (c:Concept) ON (c.name)",
            "CREATE INDEX instance_name_index IF NOT EXISTS FOR (i:Instance) ON (i.name)",
            "CREATE INDEX relation_type_index IF NOT EXISTS FOR ()-[r:RELATION]-() ON (r.type)",
            
            # Graphiti需要的约束和索引
            "CREATE CONSTRAINT episodic_uuid_unique IF NOT EXISTS FOR (e:Episodic) REQUIRE e.uuid IS UNIQUE",
            "CREATE CONSTRAINT entity_uuid_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.uuid IS UNIQUE",
            "CREATE INDEX episodic_valid_at_index IF NOT EXISTS FOR (e:Episodic) ON (e.valid_at)",
            "CREATE INDEX episodic_group_id_index IF NOT EXISTS FOR (e:Episodic) ON (e.group_id)",
            "CREATE INDEX episodic_source_index IF NOT EXISTS FOR (e:Episodic) ON (e.source)",
            "CREATE INDEX entity_group_id_index IF NOT EXISTS FOR (e:Entity) ON (e.group_id)",
            "CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    self.logger.info(f"创建约束/索引: {constraint}")
                except Exception as e:
                    self.logger.warning(f"创建约束/索引失败: {e}")
    
    def create_ontology_indexes(self):
        """创建本体需要的全文索引"""
        with self.driver.session() as session:
            try:
                # 创建项目节点的全文索引
                session.run("""
                    CREATE FULLTEXT INDEX project_fulltext IF NOT EXISTS
                    FOR (p:Project) ON EACH [p.name, p.description]
                    OPTIONS {indexConfig: {
                        `fulltext.analyzer`: 'standard',
                        `fulltext.eventually_consistent`: true
                    }}
                """)
                self.logger.info("创建Project全文索引成功")
                
                # 创建团队节点的全文索引
                session.run("""
                    CREATE FULLTEXT INDEX team_fulltext IF NOT EXISTS
                    FOR (t:Team) ON EACH [t.name, t.description]
                    OPTIONS {indexConfig: {
                        `fulltext.analyzer`: 'standard',
                        `fulltext.eventually_consistent`: true
                    }}
                """)
                self.logger.info("创建Team全文索引成功")
                
                # 创建开发者节点的全文索引
                session.run("""
                    CREATE FULLTEXT INDEX developer_fulltext IF NOT EXISTS
                    FOR (d:Developer) ON EACH [d.name, d.role, d.skills]
                    OPTIONS {indexConfig: {
                        `fulltext.analyzer`: 'standard',
                        `fulltext.eventually_consistent`: true
                    }}
                """)
                self.logger.info("创建Developer全文索引成功")
                
            except Exception as e:
                self.logger.warning(f"创建本体全文索引失败: {e}")
    
    def initialize_ontology_schema(self):
        """初始化本体数据库模式"""
        self.logger.info("初始化本体数据库模式...")
        
        # 创建约束和索引
        self.create_constraints()
        self.create_ontology_indexes()
        
        self.logger.info("本体数据库模式初始化完成")
    
    def create_concept_node(self, concept: OntologyConcept):
        """创建概念节点"""
        with self.driver.session() as session:
            query = """
            CREATE (c:Concept:Class {
                id: $id,
                name: $name,
                label: $label,
                definition: $definition,
                concept_type: $concept_type,
                namespace: $namespace,
                created_at: datetime($created_at),
                properties: $properties
            })
            RETURN c
            """
            
            # 序列化properties为字符串列表
            properties_data = []
            if concept.properties:
                for prop in concept.properties:
                    prop_str = f"{prop.name}:{prop.domain}->{prop.range_type}"
                    if prop.functional:
                        prop_str += ":functional"
                    if prop.transitive:
                        prop_str += ":transitive"
                    if prop.symmetric:
                        prop_str += ":symmetric"
                    if prop.cardinality:
                        prop_str += f":{prop.cardinality}"
                    properties_data.append(prop_str)
            
            result = session.run(query, {
                "id": concept.id,
                "name": concept.name,
                "label": concept.label,
                "definition": concept.definition,
                "concept_type": concept.concept_type,
                "namespace": concept.namespace,
                "created_at": concept.created_at.isoformat(),
                "properties": properties_data
            })
            
            single_result = result.single()
            return single_result["c"] if single_result else None
    
    def create_instance_node(self, instance: OntologyInstance):
        """创建实例节点"""
        with self.driver.session() as session:
            query = """
            CREATE (i:Concept:Instance {
                id: $id,
                name: $name,
                label: $label,
                definition: $definition,
                concept_type: $concept_type,
                namespace: $namespace,
                created_at: datetime($created_at),
                property_values: $property_values
            })
            RETURN i
            """
            
            # 序列化property_values为字符串
            property_values_data = ""
            if instance.property_values:
                property_parts = []
                for key, value in instance.property_values.items():
                    property_parts.append(f"{key}:{value}")
                property_values_data = ";".join(property_parts)
            
            result = session.run(query, {
                "id": instance.id,
                "name": instance.name,
                "label": instance.label,
                "definition": instance.instance_of,
                "concept_type": instance.concept_type,
                "namespace": instance.namespace,
                "created_at": instance.created_at.isoformat(),
                "property_values": property_values_data
            })
            
            single_result = result.single()
            return single_result["i"] if single_result else None
    
    def create_relation(self, relation: SemanticRelation):
        """创建关系"""
        with self.driver.session() as session:
            query = """
            MATCH (s:Concept {name: $subject})
            MATCH (o:Concept {name: $object})
            CREATE (s)-[r:RELATION {
                id: $id,
                predicate: $predicate,
                type: $relation_type,
                confidence: $confidence,
                temporal_context: datetime($temporal_context),
                source: $source,
                metadata: $metadata
            }]->(o)
            RETURN r
            """
            
            # 序列化metadata为字符串
            metadata_data = ""
            if relation.metadata:
                metadata_parts = []
                for key, value in relation.metadata.items():
                    metadata_parts.append(f"{key}:{value}")
                metadata_data = ";".join(metadata_parts)
            
            result = session.run(query, {
                "id": relation.id,
                "subject": relation.subject,
                "object": relation.object,
                "predicate": relation.predicate,
                "relation_type": relation.relation_type,
                "confidence": relation.confidence,
                "temporal_context": relation.temporal_context.isoformat() if relation.temporal_context else None,
                "source": relation.source,
                "metadata": metadata_data
            })
            
            single_result = result.single()
            return single_result["r"] if single_result else None
    
    def create_hierarchy_relation(self, child_concept: str, parent_concept: str):
        """创建层次关系"""
        with self.driver.session() as session:
            query = """
            MATCH (child:Concept {name: $child})
            MATCH (parent:Concept {name: $parent})
            CREATE (child)-[r:IS_A {
                type: 'is_a',
                confidence: 1.0
            }]->(parent)
            RETURN r
            """
            
            result = session.run(query, {
                "child": child_concept,
                "parent": parent_concept
            })
            
            single_result = result.single()
            return single_result["r"] if single_result else None
    
    def query_concept_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称查询概念"""
        with self.driver.session() as session:
            query = """
            MATCH (c:Concept {name: $name})
            RETURN c
            """
            
            result = session.run(query, {"name": name})
            record = result.single()
            return dict(record["c"]) if record else None
    
    def query_related_concepts(self, concept_name: str, relation_type: str = None) -> List[Dict[str, Any]]:
        """查询相关概念"""
        with self.driver.session() as session:
            if relation_type:
                query = """
                MATCH (c:Concept {name: $concept_name})-[r:RELATION {type: $relation_type}]->(related:Concept)
                RETURN related, r
                """
                result = session.run(query, {"concept_name": concept_name, "relation_type": relation_type})
            else:
                query = """
                MATCH (c:Concept {name: $concept_name})-[r:RELATION]->(related:Concept)
                RETURN related, r
                """
                result = session.run(query, {"concept_name": concept_name})
            
            return [{"concept": dict(record["related"]), "relation": dict(record["r"])} for record in result]
    
    def query_concept_hierarchy(self, root_concept: str) -> List[Dict[str, Any]]:
        """查询概念层次结构"""
        with self.driver.session() as session:
            query = """
            MATCH path = (root:Concept {name: $root})-[:IS_A*0..]->(ancestor:Concept)
            RETURN path
            ORDER BY length(path)
            """
            
            result = session.run(query, {"root": root_concept})
            return [{"path": [dict(node) for node in record["path"].nodes]} for record in result]
    
    def query_by_property(self, property_name: str, property_value: Any) -> List[Dict[str, Any]]:
        """根据属性查询概念"""
        with self.driver.session() as session:
            query = """
            MATCH (c:Concept)
            WHERE c[$property_name] = $property_value
            RETURN c
            """
            
            result = session.run(query, {"property_name": property_name, "property_value": property_value})
            return [dict(record["c"]) for record in result]
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        with self.driver.session() as session:
            stats = {}
            
            # 节点统计
            node_count_query = "MATCH (n) RETURN labels(n) as labels, count(n) as count"
            node_result = session.run(node_count_query)
            stats["nodes"] = {record["labels"][0]: record["count"] for record in node_result}
            
            # 关系统计
            relation_count_query = "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count"
            relation_result = session.run(relation_count_query)
            stats["relations"] = {record["type"]: record["count"] for record in relation_result}
            
            # 概念类型统计
            concept_type_query = "MATCH (c:Concept) RETURN c.concept_type as type, count(c) as count"
            concept_result = session.run(concept_type_query)
            stats["concept_types"] = {record["type"]: record["count"] for record in concept_result}
            
            return stats
    
    def clear_database(self):
        """清空数据库"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            self.logger.info("数据库已清空")
    
    def export_graph_data(self) -> Dict[str, Any]:
        """导出图谱数据"""
        with self.driver.session() as session:
            # 导出所有节点
            nodes_query = "MATCH (n) RETURN n"
            nodes_result = session.run(nodes_query)
            nodes = [dict(record["n"]) for record in nodes_result]
            
            # 导出所有关系
            relations_query = "MATCH (a)-[r]->(b) RETURN a, r, b"
            relations_result = session.run(relations_query)
            relations = []
            for record in relations_result:
                relations.append({
                    "source": dict(record["a"]),
                    "relation": dict(record["r"]),
                    "target": dict(record["b"])
                })
            
            return {"nodes": nodes, "relations": relations}
