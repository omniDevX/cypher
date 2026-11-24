"""Ontology知识图谱查询引擎 - 基于直接Neo4j实现"""
import logging
from typing import List, Dict, Any, Optional, Union
from config.neo4j_connector import Neo4jConnector
from .ontology_models import RelationType, ConceptType

class OntologyQueryEngine:
    """Ontology查询引擎 - 基于直接Neo4j实现"""
    
    def __init__(self, neo4j_connector: Neo4jConnector):
        self.neo4j = neo4j_connector
        self.logger = logging.getLogger(__name__)
    
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """语义搜索 - 基于直接Neo4j实现"""
        try:
            with self.neo4j.driver.session() as session:
                # 搜索所有节点类型
                search_query = """
                MATCH (n)
                WHERE n.name CONTAINS $query 
                   OR n.title CONTAINS $query
                   OR n.description CONTAINS $query
                RETURN n as node, labels(n)[0] as node_type, 1.0 as score
                ORDER BY n.name
                LIMIT $limit
                """
                
                result = session.run(search_query, {"query": query, "limit": limit})
                return [{"concept": dict(record["node"]), "node_type": record["node_type"], "score": record["score"]} for record in result]
                
        except Exception as e:
            self.logger.error(f"语义搜索失败: {e}")
            return []
    
    def query_by_concept_type(self, concept_type: ConceptType) -> List[Dict[str, Any]]:
        """根据概念类型查询 - 基于直接Neo4j实现"""
        try:
            with self.neo4j.driver.session() as session:
                # 根据概念类型映射到不同的节点标签
                if concept_type == ConceptType.CLASS:
                    query = """
                    MATCH (n:Project)
                    RETURN n.name as name, 'Project' as label, n.description as definition
                    UNION
                    MATCH (n:Team)
                    RETURN n.name as name, 'Team' as label, n.description as definition
                    UNION
                    MATCH (n:Developer)
                    RETURN n.name as name, 'Developer' as label, n.role as definition
                    ORDER BY name
                    """
                elif concept_type == ConceptType.INSTANCE:
                    query = """
                    MATCH (n:Requirement)
                    RETURN n.title as name, 'Requirement' as label, n.description as definition
                    UNION
                    MATCH (n:Task)
                    RETURN n.title as name, 'Task' as label, n.description as definition
                    ORDER BY name
                    """
                else:
                    query = """
                    MATCH (n)
                    RETURN n.name as name, labels(n)[0] as label, 
                           COALESCE(n.description, n.title, '') as definition
                    ORDER BY name
                    LIMIT 10
                    """
                
                result = session.run(query)
                return [{"name": record["name"], "label": record["label"], "definition": record["definition"]} for record in result]
                
        except Exception as e:
            self.logger.error(f"按概念类型查询失败: {e}")
            return []
    
    def query_by_relation_type(self, relation_type: RelationType) -> List[Dict[str, Any]]:
        """根据关系类型查询 - 基于直接Neo4j实现"""
        try:
            with self.neo4j.driver.session() as session:
                # 映射关系类型到Neo4j关系类型
                relation_mapping = {
                    RelationType.HAS_PROPERTY: "HAS_PROPERTY",
                    RelationType.IS_A: "IS_A", 
                    RelationType.PART_OF: "PART_OF",
                    RelationType.BELONGS_TO: "BELONGS_TO",
                    RelationType.IMPLEMENTS: "IMPLEMENTS",
                    RelationType.RELATED_TO: "RELATED_TO",
                    RelationType.INSTANCE_OF: "INSTANCE_OF"
                }
                
                neo4j_relation = relation_mapping.get(relation_type, "BELONGS_TO")
                
                query = f"""
                MATCH (source)-[r:{neo4j_relation}]->(target)
                RETURN source as source_node, target as target_node, 
                       type(r) as relation_type, properties(r) as properties
                ORDER BY source.name, target.name
                """
                
                result = session.run(query)
                relations = []
                for record in result:
                    source_node = dict(record["source_node"])
                    target_node = dict(record["target_node"])
                    
                    # 为节点添加标准化的name属性
                    if 'name' not in source_node and 'title' in source_node:
                        source_node['name'] = source_node['title']
                    if 'name' not in target_node and 'title' in target_node:
                        target_node['name'] = target_node['title']
                    
                    relations.append({
                        "source": source_node, 
                        "target": target_node,
                        "relation_type": record["relation_type"],
                        "properties": record["properties"]
                    })
                return relations
                
        except Exception as e:
            self.logger.error(f"按关系类型查询失败: {e}")
            return []
    
    def get_concept_details(self, concept_name: str) -> Optional[Dict[str, Any]]:
        """获取概念详细信息 - 基于直接Neo4j实现"""
        try:
            with self.neo4j.driver.session() as session:
                # 查找概念节点
                concept_query = """
                MATCH (n)
                WHERE n.name = $concept_name OR n.title = $concept_name
                RETURN n as concept, labels(n) as labels
                LIMIT 1
                """
                
                result = session.run(concept_query, {"concept_name": concept_name})
                record = result.single()
                
                if not record:
                    return None
                
                concept = dict(record["concept"])
                labels = record["labels"]
                
                # 查找相关概念（通过关系连接的概念）
                related_query = """
                MATCH (n)-[r]-(related)
                WHERE n.name = $concept_name OR n.title = $concept_name
                RETURN DISTINCT related as related_concept, type(r) as relation_type
                LIMIT 10
                """
                
                related_result = session.run(related_query, {"concept_name": concept_name})
                related_concepts = []
                for rel_record in related_result:
                    related_concepts.append({
                        "concept": dict(rel_record["related_concept"]),
                        "relation_type": rel_record["relation_type"]
                    })
                
                # 查找层次结构路径
                hierarchy_query = """
                MATCH path = (n)-[:BELONGS_TO*]->(root)
                WHERE n.name = $concept_name OR n.title = $concept_name
                RETURN path
                LIMIT 5
                """
                
                hierarchy_result = session.run(hierarchy_query, {"concept_name": concept_name})
                hierarchy = []
                for path_record in hierarchy_result:
                    path = path_record["path"]
                    path_nodes = [dict(node) for node in path.nodes]
                    hierarchy.append(path_nodes)
                
                return {
                    "concept": concept,
                    "labels": labels,
                    "related_concepts": related_concepts,
                    "hierarchy": hierarchy
                }
                
        except Exception as e:
            self.logger.error(f"获取概念详情失败: {e}")
            return None
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息 - 基于直接Neo4j实现"""
        try:
            with self.neo4j.driver.session() as session:
                # 统计节点数量
                node_count_query = "MATCH (n) RETURN count(n) as total_nodes"
                node_result = session.run(node_count_query)
                total_nodes = node_result.single()["total_nodes"]
                
                # 统计关系数量
                relation_count_query = "MATCH ()-[r]->() RETURN count(r) as total_relations"
                relation_result = session.run(relation_count_query)
                total_relations = relation_result.single()["total_relations"]
                
                # 统计各类型节点数量
                node_types_query = """
                MATCH (n) 
                RETURN labels(n)[0] as node_type, count(n) as count
                ORDER BY count DESC
                """
                node_types_result = session.run(node_types_query)
                concept_types = {record["node_type"]: record["count"] for record in node_types_result}
                
                # 统计各类型关系数量
                relation_types_query = """
                MATCH ()-[r]->() 
                RETURN type(r) as relation_type, count(r) as count
                ORDER BY count DESC
                """
                relation_types_result = session.run(relation_types_query)
                relations = {record["relation_type"]: record["count"] for record in relation_types_result}
                
                # 计算平均连接度
                avg_degree = (total_relations * 2) / total_nodes if total_nodes > 0 else 0
                
                return {
                    "total_nodes": total_nodes,
                    "total_relations": total_relations,
                    "average_degree": avg_degree,
                    "concept_types": concept_types,
                    "relations": relations
                }
                
        except Exception as e:
            self.logger.error(f"获取图谱统计失败: {e}")
            return {
                "total_nodes": 0,
                "total_relations": 0,
                "average_degree": 0,
                "concept_types": {},
                "relations": {}
            }
    
    def find_path(self, start_concept: str, end_concept: str, max_depth: int = 3) -> List[List[Dict[str, Any]]]:
        """查找两个概念之间的路径"""
        try:
            with self.neo4j.driver.session() as session:
                path_query = f"""
                MATCH path = (start)-[*1..{max_depth}]-(end)
                WHERE (start.name = $start_concept OR start.title = $start_concept)
                  AND (end.name = $end_concept OR end.title = $end_concept)
                RETURN path
                LIMIT 10
                """
                
                result = session.run(path_query, {
                    "start_concept": start_concept,
                    "end_concept": end_concept
                })
                
                paths = []
                for record in result:
                    path = record["path"]
                    path_nodes = []
                    for node in path.nodes:
                        path_nodes.append(dict(node))
                    paths.append(path_nodes)
                
                return paths
                
        except Exception as e:
            self.logger.error(f"查找路径失败: {e}")
            return []
    
    def get_neighbors(self, concept_name: str, depth: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """获取概念的邻居节点"""
        try:
            with self.neo4j.driver.session() as session:
                neighbors_query = f"""
                MATCH (n)-[r*1..{depth}]-(neighbor)
                WHERE n.name = $concept_name OR n.title = $concept_name
                RETURN DISTINCT neighbor as neighbor_node, 
                       length(r) as distance,
                       type(r[0]) as relation_type
                ORDER BY distance, neighbor.name
                """
                
                result = session.run(neighbors_query, {"concept_name": concept_name})
                
                neighbors = {}
                for record in result:
                    distance = record["distance"]
                    relation_type = record["relation_type"]
                    neighbor = dict(record["neighbor_node"])
                    
                    if distance not in neighbors:
                        neighbors[distance] = []
                    
                    neighbors[distance].append({
                        "concept": neighbor,
                        "relation_type": relation_type
                    })
                
                return neighbors
                
        except Exception as e:
            self.logger.error(f"获取邻居节点失败: {e}")
            return {}