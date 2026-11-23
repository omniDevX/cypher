https://github.com/charles-wang888/ontology_knowledgegraph.git

# 面向对象本体知识图谱系统

一个基于Neo4j图数据库的智能本体知识图谱构建与查询系统，支持从SQLite关系型数据库自动构建语义化的知识图谱，并提供丰富的查询和分析功能。

## 🎯 项目概述

本项目实现了一个完整的本体知识图谱系统，能够将传统的关系型数据库（SQLite）中的结构化数据自动转换为图数据库（Neo4j）中的语义化知识图谱。系统采用面向对象的设计理念，支持多种实体类型和关系类型，并提供强大的查询和分析功能。

### 核心特性

- 🏗️ **自动本体构建**: 从SQLite数据库自动构建Neo4j知识图谱
- 🔍 **智能查询引擎**: 支持语义搜索、概念检索、关系分析
- 📊 **多维度分析**: 提供图谱统计、路径发现、邻居分析
- 🎯 **面向对象设计**: 支持类、实例、属性、方法等OOP概念
- 🔗 **关系自动发现**: 基于数据源字段自动分析建立语义关系
- 📈 **实时同步**: 支持数据源与知识图谱的实时同步

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQLite数据库   │───▶│   本体构建器     │───▶│   Neo4j图数据库  │
│  (结构化数据)    │    │ (数据转换引擎)   │    │  (语义化图谱)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   查询引擎       │
                       │ (智能分析服务)   │
                       └─────────────────┘
```

## 📁 项目结构

```
Ontology_Research/
├── config/                     # 配置文件
│   ├── config.py              # 系统配置
│   └── neo4j_connector.py     # Neo4j连接器
├── ds/                        # 数据源模块
│   ├── data_source_mapper.py  # 数据源映射器
│   └── software_engineering_data.py  # 软件工程演示数据
├── ontology/                  # 本体核心模块
│   ├── ontology_models.py     # 数据模型定义
│   ├── ontology_builder.py    # 本体构建器
│   └── ontology_query_engine.py  # 查询引擎
├── main_build.py             # 主构建程序
├── main_search.py            # 主查询程序
├── requirements.txt          # 依赖包列表
└── software_engineering.db   # SQLite演示数据库
```
## 构建效果
<img width="721" height="634" alt="1" src="https://github.com/user-attachments/assets/3e39b8eb-a819-4b30-862f-9e3d12fe6670" />


## 🚀 快速开始

### 环境要求

- Python 3.8+
- Neo4j 4.0+
- SQLite 3

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置Neo4j

1. 启动Neo4j数据库
2. 修改 `config/config.py` 中的连接配置：
```python
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "your_password"
```

### 运行演示

#### 1. 构建知识图谱

```bash
python main_build.py
```

这将：
- 创建SQLite演示数据库
- 从数据库构建本体知识图谱
- 建立实体类和INSTANCE_OF关系
- 验证构建结果

#### 2. 查询知识图谱

```bash
python main_search.py
```

这将演示：
- 基本搜索功能
- 按概念类型查询
- 按关系类型查询
- 图谱统计分析

## 📊 数据模型

### 实体类型

- **Project**: 软件工程项目
- **Team**: 开发团队
- **Developer**: 开发者
- **Requirement**: 功能需求
- **Task**: 开发任务

### 关系类型

- **BELONGS_TO**: 属于关系（团队属于项目）
- **MEMBER_OF**: 成员关系（开发者属于团队）
- **IMPLEMENTS**: 实现关系（任务实现需求）
- **ASSIGNED_TO**: 分配关系（任务分配给开发者）
- **INSTANCE_OF**: 实例关系（实例属于类）

## 🔧 核心模块

### ontology_models.py
**数据模型定义模块**，提供完整的数据结构支持：
- 枚举类型定义（关系类型、概念类型、数据源类型）
- 数据源抽象层（支持SQLite、API、消息队列等）
- 本体概念模型（类、属性、方法、实例）
- 关系分析器（自动发现和建立语义关系）

### ontology_builder.py
**本体构建引擎**，负责数据转换和图谱构建：
- Neo4j数据库连接管理
- 本体模式创建和约束定义
- 分步节点创建（项目、团队、开发者、需求、任务）
- 关系建立和验证
- 构建过程监控和错误处理

### ontology_query_engine.py
**智能查询引擎**，提供多样化的查询和分析服务：
- 语义搜索和全文检索
- 按概念类型和关系类型查询
- 概念详情获取和层次结构分析
- 图谱统计和连接度计算
- 路径发现和邻居分析

## 📈 功能特性

### 自动本体构建
- 从SQLite表结构自动生成本体类
- 基于外键关系自动建立语义关系
- 支持数据源模式自动发现
- 提供完整的构建验证机制

### 智能查询分析
- 支持Cypher查询语言
- 提供语义搜索和概念检索
- 支持多维度图谱分析
- 实时统计和诊断功能

### 面向对象支持
- 支持类、实例、属性、方法定义
- 提供继承、多态、封装等OOP特性
- 支持静态方法和类变量
- 提供访问修饰符和接口支持

### 数据源集成
- 支持多种数据源类型
- 提供统一的数据访问接口
- 支持实时数据同步
- 提供数据源模式自动发现

## 🎯 使用示例

### 基本查询

```python
from ontology.ontology_query_engine import OntologyQueryEngine
from config.neo4j_connector import Neo4jConnector

# 初始化查询引擎
connector = Neo4jConnector()
connector.connect()
query_engine = OntologyQueryEngine(connector)

# 语义搜索
results = query_engine.semantic_search("数据分析")

# 按概念类型查询
classes = query_engine.query_by_concept_type(ConceptType.CLASS)

# 获取概念详情
details = query_engine.get_concept_details("电商平台项目")
```

### 图谱分析

```python
# 获取图谱统计
stats = query_engine.get_graph_statistics()
print(f"总节点数: {stats['total_nodes']}")
print(f"总关系数: {stats['total_relations']}")

# 查找路径
paths = query_engine.find_path("张三", "电商平台项目")

# 获取邻居节点
neighbors = query_engine.get_neighbors("数据分析仪表板")
```

## 📊 演示数据

系统包含完整的软件工程领域演示数据：

- **3个项目**: 电商平台项目、移动应用项目、数据分析平台
- **4个团队**: 前端开发团队、后端开发团队、移动开发团队、数据团队
- **6个开发者**: 不同角色和技能的专业人员
- **6个需求**: 涵盖用户注册、商品浏览、购物车等功能
- **6个任务**: 具体的开发工作项

## 🔍 查询示例

### 查找特定项目的所有团队成员
```cypher
MATCH (p:Project {name: '电商平台项目'})<-[:BELONGS_TO]-(t:Team)<-[:MEMBER_OF]-(d:Developer)
RETURN d.name, d.role, t.name
```

### 查找需求的所有相关任务
```cypher
MATCH (r:Requirement {title: '购物车功能'})<-[:IMPLEMENTS]-(t:Task)
RETURN t.title, t.status, t.assigned_to
```

### 查找开发者的工作负载
```cypher
MATCH (d:Developer)-[:ASSIGNED_TO]-(t:Task)
RETURN d.name, count(t) as task_count
```

## 🛠️ 开发指南

### 添加新的实体类型

1. 在 `ontology_models.py` 中定义新的概念类型
2. 在 `ontology_builder.py` 中添加节点创建方法
3. 在 `ontology_query_engine.py` 中添加查询支持

### 添加新的关系类型

1. 在 `RelationType` 枚举中添加新类型
2. 在 `RelationAnalyzer` 中添加关系分析逻辑
3. 在构建器中添加关系创建代码

### 扩展数据源支持

1. 继承 `DataSource` 基类
2. 实现 `connect()`, `get_records()`, `get_schema()` 方法
3. 在数据源映射器中注册新类型

## 📝 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至项目维护者

---

**注意**: 本项目仅用于学习和研究目的，请根据实际需求进行适当修改和扩展。
