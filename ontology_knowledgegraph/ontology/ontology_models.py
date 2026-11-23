"""基于面向对象Ontology的数据模型定义"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Callable, Type
from datetime import datetime
from enum import Enum
import uuid
import sqlite3
from abc import ABC, abstractmethod

class RelationType(str, Enum):
    """关系类型枚举"""
    IS_A = "is_a"  # 继承关系
    PART_OF = "part_of"  # 部分关系
    BELONGS_TO = "belongs_to"  # 属于关系
    HAS_PROPERTY = "has_property"  # 属性关系
    RELATED_TO = "related_to"  # 相关关系
    CAUSES = "causes"  # 因果关系
    LOCATED_IN = "located_in"  # 位置关系
    INSTANCE_OF = "instance_of"  # 实例关系
    USES = "uses"  # 使用关系
    IMPLEMENTS = "implements"  # 实现关系
    DEPENDS_ON = "depends_on"  # 依赖关系
    FOREIGN_KEY = "foreign_key"  # 外键关系
    REFERENCE = "reference"  # 引用关系

class ConceptType(str, Enum):
    """概念类型枚举"""
    ENTITY = "Entity"
    CLASS = "Class"
    PROPERTY = "Property"
    RELATION = "Relation"
    INSTANCE = "Instance"
    DATASOURCE = "DataSource"  # 数据源

class DataSourceType(str, Enum):
    """数据源类型枚举"""
    SQLITE_TABLE = "sqlite_table"
    POSTGRESQL_TABLE = "postgresql_table"
    API_ENDPOINT = "api_endpoint"
    MESSAGE_QUEUE = "message_queue"
    FILE = "file"
    REST_API = "rest_api"

class DataSource(BaseModel, ABC):
    """数据源基类"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    source_type: DataSourceType
    connection_string: str
    schema: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
    
    @abstractmethod
    def connect(self) -> bool:
        """连接数据源"""
        pass
    
    @abstractmethod
    def get_records(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取记录"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """获取数据源模式"""
        pass

class SQLiteDataSource(DataSource):
    """SQLite数据源"""
    source_type: DataSourceType = DataSourceType.SQLITE_TABLE
    table_name: str
    
    def connect(self) -> bool:
        """连接SQLite数据库"""
        try:
            conn = sqlite3.connect(self.connection_string)
            conn.close()
            return True
        except Exception:
            return False
    
    def get_records(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取记录"""
        if query is None:
            query = f"SELECT * FROM {self.table_name}"
        
        conn = sqlite3.connect(self.connection_string)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_schema(self) -> Dict[str, Any]:
        """获取表模式"""
        conn = sqlite3.connect(self.connection_string)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            columns = cursor.fetchall()
            
            schema = {
                "table_name": self.table_name,
                "columns": []
            }
            
            for col in columns:
                schema["columns"].append({
                    "name": col[1],
                    "type": col[2],
                    "not_null": bool(col[3]),
                    "default_value": col[4],
                    "primary_key": bool(col[5])
                })
            
            return schema
        finally:
            conn.close()

class OntologyConcept(BaseModel):
    """本体概念基类"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    label: str
    definition: str
    concept_type: ConceptType
    namespace: str = "default"
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class MethodDefinition(BaseModel):
    """方法定义"""
    name: str
    parameters: List[Dict[str, str]] = Field(default_factory=list)  # 参数列表 [{"name": "param1", "type": "string"}]
    return_type: str = "void"
    description: str = ""
    implementation: Optional[str] = None  # 方法实现代码
    
class PropertyDefinition(BaseModel):
    """属性定义"""
    name: str
    domain: str  # 定义域
    range_type: str  # 值域类型
    functional: bool = False  # 是否函数性
    transitive: bool = False  # 是否传递性
    symmetric: bool = False  # 是否对称性
    cardinality: Optional[str] = None  # 基数约束
    default_value: Optional[Any] = None  # 默认值
    is_required: bool = False  # 是否必需
    is_unique: bool = False  # 是否唯一
    validation_rules: List[str] = Field(default_factory=list)  # 验证规则

class OntologyClass(OntologyConcept):
    """面向对象本体类定义"""
    concept_type: ConceptType = ConceptType.CLASS
    sub_classes: List[str] = Field(default_factory=list)
    super_classes: List[str] = Field(default_factory=list)
    disjoint_with: List[str] = Field(default_factory=list)
    equivalent_classes: List[str] = Field(default_factory=list)
    properties: List[PropertyDefinition] = Field(default_factory=list)
    methods: List[MethodDefinition] = Field(default_factory=list)  # 类方法
    instances: List[str] = Field(default_factory=list)
    data_source: Optional[DataSource] = None  # 关联的数据源
    is_abstract: bool = False  # 是否为抽象类
    constructor_params: List[Dict[str, str]] = Field(default_factory=list)  # 构造函数参数
    
    # 新增面向对象特性
    static_methods: List[MethodDefinition] = Field(default_factory=list)  # 静态方法
    class_variables: Dict[str, Any] = Field(default_factory=dict)  # 类变量
    access_modifiers: Dict[str, str] = Field(default_factory=dict)  # 访问修饰符
    interfaces: List[str] = Field(default_factory=list)  # 实现的接口
    mixins: List[str] = Field(default_factory=list)  # 混入类
    constraints: List[str] = Field(default_factory=list)  # 约束条件
    annotations: Dict[str, Any] = Field(default_factory=dict)  # 注解信息

class OntologyProperty(OntologyConcept):
    """本体属性定义"""
    concept_type: ConceptType = ConceptType.PROPERTY
    domain: List[str] = Field(default_factory=list)
    range: List[str] = Field(default_factory=list)
    inverse_property: Optional[str] = None
    property_characteristics: List[str] = Field(default_factory=list)

class OntologyInstance(OntologyConcept):
    """面向对象本体实例定义 - 直接绑定到数据源记录"""
    concept_type: ConceptType = ConceptType.INSTANCE
    instance_of: List[str] = Field(default_factory=list)  # 所属类
    property_values: Dict[str, Any] = Field(default_factory=dict)
    relations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 数据源绑定相关
    data_source_id: Optional[str] = None  # 关联的数据源ID
    record_id: Optional[str] = None  # 数据源中的记录ID
    record_data: Dict[str, Any] = Field(default_factory=dict)  # 原始记录数据
    last_sync_time: Optional[datetime] = None  # 最后同步时间
    
    # 实例方法
    instance_methods: List[MethodDefinition] = Field(default_factory=list)
    
    def sync_from_data_source(self, data_source: DataSource) -> bool:
        """从数据源同步数据"""
        try:
            if self.record_id:
                query = f"SELECT * FROM {data_source.table_name} WHERE id = ?"
                records = data_source.get_records(query)
                if records:
                    self.record_data = records[0]
                    self.property_values.update(self.record_data)
                    self.last_sync_time = datetime.now()
                    return True
            return False
        except Exception:
            return False
    
    def save_to_data_source(self, data_source: DataSource) -> bool:
        """保存到数据源"""
        try:
            # 这里需要根据具体的数据源实现保存逻辑
            # 暂时返回True表示成功
            self.last_sync_time = datetime.now()
            return True
        except Exception:
            return False

class SemanticRelation(BaseModel):
    """语义关系定义"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str
    predicate: str
    object: str
    relation_type: RelationType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    temporal_context: Optional[datetime] = None
    source: Optional[str] = None  # 关系来源
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class OntologyAxiom(BaseModel):
    """本体公理定义"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    axiom_type: str
    subject: str
    predicate: str
    object: str
    description: str
    is_inferred: bool = False

class OntologyNamespace(BaseModel):
    """本体命名空间"""
    prefix: str
    uri: str
    description: str
    concepts: List[str] = Field(default_factory=list)

class RelationAnalyzer:
    """关系分析器 - 从数据源字段中分析建立关系"""
    
    @staticmethod
    def analyze_foreign_key_relations(schema: Dict[str, Any], table_name: str) -> List[Dict[str, Any]]:
        """分析外键关系"""
        relations = []
        columns = schema.get("columns", [])
        
        for column in columns:
            column_name = column["name"]
            # 检查是否为外键（通常以_id结尾或包含外键信息）
            if column_name.endswith("_id") and column_name != "id":
                # 推断关联的表名
                related_table = column_name[:-3] + "s"  # 移除_id并添加s
                relation = {
                    "type": RelationType.FOREIGN_KEY,
                    "subject_table": table_name,
                    "object_table": related_table,
                    "subject_field": column_name,
                    "object_field": "id",
                    "relation_name": f"{table_name}_has_{related_table}",
                    "object": f"{related_table}_table",  # 添加具体的对象引用
                    "confidence": 0.8
                }
                relations.append(relation)
        
        return relations
    
    @staticmethod
    def analyze_reference_relations(record_data: Dict[str, Any], table_name: str) -> List[Dict[str, Any]]:
        """分析引用关系"""
        relations = []
        
        for field_name, field_value in record_data.items():
            if isinstance(field_value, str):
                # 检查是否包含对其他实体的引用
                if "project_id" in field_name.lower() or "user_id" in field_name.lower():
                    relation = {
                        "type": RelationType.REFERENCE,
                        "subject_table": table_name,
                        "subject_field": field_name,
                        "object_value": str(field_value),
                        "relation_name": f"{table_name}_references_{field_name}",
                        "confidence": 0.9
                    }
                    relations.append(relation)
        
        return relations
    
    @staticmethod
    def analyze_semantic_relations(property_values: Dict[str, Any], instance_name: str) -> List[Dict[str, Any]]:
        """分析语义关系"""
        relations = []
        
        # 基于属性值推断关系
        if "project_id" in property_values:
            relations.append({
                "type": RelationType.PART_OF,
                "subject": instance_name,
                "object": f"project_{property_values['project_id']}",
                "relation_name": "belongs_to_project",
                "confidence": 0.9
            })
        
        if "team_id" in property_values:
            relations.append({
                "type": RelationType.PART_OF,
                "subject": instance_name,
                "object": f"team_{property_values['team_id']}",
                "relation_name": "member_of_team",
                "confidence": 0.9
            })
        
        return relations
    
    @staticmethod
    def analyze_concrete_relations(record_data: Dict[str, Any], instance_name: str, table_name: str) -> List[Dict[str, Any]]:
        """分析基于记录数据的具体关系"""
        relations = []
        
        # 基于具体的记录数据创建关系
        if table_name == "teams":
            # 团队关系
            if "project_id" in record_data and record_data["project_id"]:
                relations.append({
                    "type": RelationType.PART_OF,
                    "subject": instance_name,
                    "object": f"projects_{record_data['project_id']}",
                    "relation_name": "belongs_to_project",
                    "confidence": 0.9
                })
            
            if "leader_id" in record_data and record_data["leader_id"]:
                relations.append({
                    "type": RelationType.PART_OF,
                    "subject": f"developers_{record_data['leader_id']}",
                    "object": instance_name,
                    "relation_name": "leads_team",
                    "confidence": 0.9
                })
        
        elif table_name == "developers":
            # 开发者关系
            if "team_id" in record_data and record_data["team_id"]:
                relations.append({
                    "type": RelationType.PART_OF,
                    "subject": instance_name,
                    "object": f"teams_{record_data['team_id']}",
                    "relation_name": "member_of_team",
                    "confidence": 0.9
                })
        
        elif table_name == "requirements":
            # 需求关系
            if "project_id" in record_data and record_data["project_id"]:
                relations.append({
                    "type": RelationType.PART_OF,
                    "subject": instance_name,
                    "object": f"projects_{record_data['project_id']}",
                    "relation_name": "belongs_to_project",
                    "confidence": 0.9
                })
            
            if "assigned_to" in record_data and record_data["assigned_to"]:
                relations.append({
                    "type": RelationType.RELATED_TO,
                    "subject": instance_name,
                    "object": f"developers_{record_data['assigned_to']}",
                    "relation_name": "assigned_to_developer",
                    "confidence": 0.9
                })
        
        elif table_name == "tasks":
            # 任务关系
            if "requirement_id" in record_data and record_data["requirement_id"]:
                relations.append({
                    "type": RelationType.PART_OF,
                    "subject": instance_name,
                    "object": f"requirements_{record_data['requirement_id']}",
                    "relation_name": "implements_requirement",
                    "confidence": 0.9
                })
            
            if "assigned_to" in record_data and record_data["assigned_to"]:
                relations.append({
                    "type": RelationType.RELATED_TO,
                    "subject": instance_name,
                    "object": f"developers_{record_data['assigned_to']}",
                    "relation_name": "assigned_to_developer",
                    "confidence": 0.9
                })
        
        return relations
