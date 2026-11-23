"""数据源映射层 - 支持多种数据源类型"""
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from ontology.ontology_models import (
    DataSource, SQLiteDataSource, DataSourceType, 
    OntologyInstance, OntologyClass, RelationAnalyzer
)

logger = logging.getLogger(__name__)

class APIDataSource(DataSource):
    """API数据源"""
    source_type: DataSourceType = DataSourceType.API_ENDPOINT
    endpoint_url: str
    headers: Dict[str, str] = {}
    auth_token: Optional[str] = None
    
    def connect(self) -> bool:
        """测试API连接"""
        try:
            response = requests.get(self.endpoint_url, headers=self.headers, timeout=5)
            return response.status_code < 400
        except Exception as e:
            logger.error(f"API连接失败: {e}")
            return False
    
    def get_records(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """从API获取记录"""
        try:
            headers = self.headers.copy()
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            response = requests.get(self.endpoint_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            else:
                return [data]
        except Exception as e:
            logger.error(f"获取API数据失败: {e}")
            return []
    
    def get_schema(self) -> Dict[str, Any]:
        """获取API数据结构模式"""
        try:
            records = self.get_records()
            if not records:
                return {"schema": "empty"}
            
            # 分析第一条记录的结构
            sample_record = records[0]
            schema = {
                "endpoint": self.endpoint_url,
                "fields": []
            }
            
            for key, value in sample_record.items():
                field_type = type(value).__name__
                schema["fields"].append({
                    "name": key,
                    "type": field_type,
                    "sample_value": str(value)[:100]  # 限制长度
                })
            
            return schema
        except Exception as e:
            logger.error(f"获取API模式失败: {e}")
            return {"error": str(e)}

class MessageQueueDataSource(DataSource):
    """消息队列数据源"""
    source_type: DataSourceType = DataSourceType.MESSAGE_QUEUE
    queue_name: str
    broker_url: str
    
    def connect(self) -> bool:
        """测试消息队列连接"""
        try:
            # 这里需要根据具体的消息队列实现
            # 暂时返回True
            return True
        except Exception:
            return False
    
    def get_records(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """从消息队列获取记录"""
        try:
            # 这里需要根据具体的消息队列实现
            # 暂时返回空列表
            return []
        except Exception as e:
            logger.error(f"获取消息队列数据失败: {e}")
            return []
    
    def get_schema(self) -> Dict[str, Any]:
        """获取消息队列数据结构"""
        return {
            "queue_name": self.queue_name,
            "broker_url": self.broker_url,
            "schema": "message_queue"
        }

class DataSourceMapper:
    """数据源映射器 - 管理多种数据源类型"""
    
    def __init__(self):
        self.data_sources: Dict[str, DataSource] = {}
        self.ontology_instances: Dict[str, List[OntologyInstance]] = {}
    
    def add_data_source(self, data_source: DataSource) -> bool:
        """添加数据源"""
        try:
            if data_source.connect():
                self.data_sources[data_source.id] = data_source
                logger.info(f"数据源 {data_source.name} 添加成功")
                return True
            else:
                logger.error(f"数据源 {data_source.name} 连接失败")
                return False
        except Exception as e:
            logger.error(f"添加数据源失败: {e}")
            return False
    
    def create_ontology_class_from_table(self, table_name: str, data_source: DataSource) -> OntologyClass:
        """从数据库表创建本体类"""
        schema = data_source.get_schema()
        
        # 创建属性定义
        properties = []
        for column in schema["columns"]:
            prop = {
                "name": column["name"],
                "domain": table_name,
                "range_type": column["type"],
                "is_required": column["not_null"],
                "is_unique": column["primary_key"],
                "default_value": column["default_value"]
            }
            properties.append(prop)
        
        # 创建本体类
        ontology_class = OntologyClass(
            name=table_name,
            label=table_name,
            definition=f"从数据库表 {table_name} 生成的面向对象类",
            namespace="database",
            properties=properties,
            data_source=data_source
        )
        
        return ontology_class
    
    def create_instances_from_records(self, records: List[Dict[str, Any]], 
                                    ontology_class: OntologyClass) -> List[OntologyInstance]:
        """从记录创建本体实例"""
        instances = []
        
        for record in records:
            # 创建实例 - 使用数据库中的实际名称而不是生成的名称
            actual_name = record.get('name') or record.get('title') or record.get('id', len(instances))
            instance = OntologyInstance(
                name=str(actual_name),  # 直接使用数据库中的实际名称
                label=f"{ontology_class.label}实例",
                definition=f"{ontology_class.name}的具体实例",
                instance_of=[ontology_class.name],
                property_values=record,
                data_source_id=ontology_class.data_source.id if ontology_class.data_source else None,
                record_id=str(record.get('id', len(instances))),
                record_data=record,
                last_sync_time=datetime.now()
            )
            
            # 分析关系
            if ontology_class.data_source and isinstance(ontology_class.data_source, SQLiteDataSource):
                # 分析外键关系
                schema = ontology_class.data_source.get_schema()
                fk_relations = RelationAnalyzer.analyze_foreign_key_relations(schema, ontology_class.name)
                instance.relations.extend(fk_relations)
                
                # 分析语义关系
                semantic_relations = RelationAnalyzer.analyze_semantic_relations(record, instance.name)
                instance.relations.extend(semantic_relations)
                
                # 分析基于记录数据的具体关系
                concrete_relations = RelationAnalyzer.analyze_concrete_relations(record, instance.name, ontology_class.name)
                instance.relations.extend(concrete_relations)
            elif ontology_class.data_source and hasattr(ontology_class.data_source, "get_schema"):
                schema = ontology_class.data_source.get_schema()
                for foreign_key in schema.get("foreign_keys", []):
                    columns = foreign_key.get("constrained_columns") or []
                    targets = foreign_key.get("referred_columns") or []
                    if columns and targets and record.get(columns[0]) is not None:
                        instance.relations.append({
                            "type": "foreign_key",
                            "relation_name": f"references_{foreign_key['referred_table']}",
                            "object": str(record[columns[0]]),
                            "confidence": 1.0,
                        })
                instance.relations.extend(
                    RelationAnalyzer.analyze_semantic_relations(record, instance.name)
                )
                instance.relations.extend(
                    RelationAnalyzer.analyze_concrete_relations(record, instance.name, ontology_class.name)
                )
            
            instances.append(instance)
        
        return instances
    
    def sync_instances_with_data_source(self, ontology_class_name: str) -> bool:
        """同步实例与数据源"""
        try:
            if ontology_class_name not in self.ontology_instances:
                logger.warning(f"未找到类 {ontology_class_name} 的实例")
                return False
            
            instances = self.ontology_instances[ontology_class_name]
            if not instances:
                return True
            
            # 获取第一个实例的数据源
            first_instance = instances[0]
            if not first_instance.data_source_id:
                logger.warning(f"实例 {first_instance.name} 没有关联的数据源")
                return False
            
            data_source = self.data_sources.get(first_instance.data_source_id)
            if not data_source:
                logger.error(f"未找到数据源 {first_instance.data_source_id}")
                return False
            
            # 同步所有实例
            for instance in instances:
                if not instance.sync_from_data_source(data_source):
                    logger.warning(f"同步实例 {instance.name} 失败")
            
            logger.info(f"成功同步 {len(instances)} 个实例")
            return True
            
        except Exception as e:
            logger.error(f"同步实例失败: {e}")
            return False
    
    def build_ontology_from_database(self, db_path: Any, table_names: List[str], data_source_class=None) -> Dict[str, Any]:
        """从数据库构建完整本体"""
        try:
            source_class = data_source_class or SQLiteDataSource
            connection_string = db_path.render_as_string(hide_password=False) if hasattr(db_path, "render_as_string") else str(db_path)
            # Validate the shared database connection before reading individual tables.
            sqlite_source = source_class(
                name="main_database",
                connection_string=connection_string,
                table_name="main"
            )
            
            if not self.add_data_source(sqlite_source):
                raise Exception("无法连接到数据库")
            
            ontology_classes = []
            all_instances = []
            
            for table_name in table_names:
                # 为每个表创建数据源
                table_source = source_class(
                    name=f"{table_name}_source",
                    connection_string=connection_string,
                    table_name=table_name
                )
                
                # The validation source already checked connectivity. Avoid opening
                # an extra PostgreSQL connection for every table.
                self.data_sources[table_source.id] = table_source
                
                # 创建本体类
                ontology_class = self.create_ontology_class_from_table(table_name, table_source)
                ontology_classes.append(ontology_class)
                
                # 获取记录并创建实例
                records = table_source.get_records()
                instances = self.create_instances_from_records(records, ontology_class)
                all_instances.extend(instances)
                
                # 存储实例
                self.ontology_instances[table_name] = instances
                
                logger.info(f"从表 {table_name} 创建了 {len(instances)} 个实例")
            
            return {
                "classes": ontology_classes,
                "instances": all_instances,
                "data_sources": list(self.data_sources.values())
            }
            
        except Exception as e:
            logger.error(f"从数据库构建本体失败: {e}")
            return {"error": str(e)}
    
    def get_instances_by_relation(self, relation_type: str, target_value: str) -> List[OntologyInstance]:
        """根据关系查找实例"""
        matching_instances = []
        
        for class_name, instances in self.ontology_instances.items():
            for instance in instances:
                for relation in instance.relations:
                    if (relation.get("type") == relation_type and 
                        relation.get("object") == target_value):
                        matching_instances.append(instance)
        
        return matching_instances
    
    def get_all_relations(self) -> List[Dict[str, Any]]:
        """获取所有关系"""
        all_relations = []
        
        for class_name, instances in self.ontology_instances.items():
            for instance in instances:
                for relation in instance.relations:
                    relation_info = {
                        "subject": instance.name,
                        "relation": relation,
                        "class": class_name
                    }
                    all_relations.append(relation_info)
        
        return all_relations
