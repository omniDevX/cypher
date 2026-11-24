重新规划:5 个前台模块 + 1 个非界面接口
#	模块	用户的任务	主要角色	包含的功能
1	探索(Explore)	找到并看懂一个数据对象	Viewer 及以上所有人	搜索筛选;对象详情页(概览、业务定义、FIBO 映射、Lineage 标签、影响分析标签、变更历史)
2	维护(Curate)	补充和修正知识	Editor	编辑定义/负责人/标签;确认或修改 LLM 推荐的 FIBO 映射;Excel/文档上传和批量导入
3	审批(Govern)	把关修改,认证 CDE	Steward	待办队列;变更 diff 和影响提示;批准/驳回;CDE 认证状态
4	对话(Chat)	用自然语言问,不想点界面	所有人	问答、引用链接到模块 1 的详情页
5	管理(Admin)	管人、管配置、查审计	Admin、审计	用户角色、SSO 配置、审计日志
6	Agent API(无界面)	让其他 AI 系统调用	AI Agent	同一套权限和审计下的查询接口


ontology_knowledgegraph/
├── app/
│   ├── api/                      # FastAPI app, auth middleware, route registration
│   │   ├── explore.py
│   │   ├── curate.py
│   │   ├── govern.py
│   │   ├── chat.py
│   │   ├── admin.py
│   │   └── agent.py
│   ├── modules/                  # User workflows and business rules
│   │   ├── explore/
│   │   ├── curate/
│   │   ├── govern/
│   │   ├── chat/
│   │   ├── admin/
│   │   └── agent/
│   ├── domain/                   # Shared concepts and policies
│   │   ├── objects.py            # Data object, business definition, CDE
│   │   ├── lineage.py
│   │   ├── fibo.py
│   │   ├── changes.py
│   │   ├── users.py              # Roles and access rules
│   │   └── audit.py
│   ├── graph/                    # Neo4j driver, graph schema, Cypher repositories
│   │   ├── client.py
│   │   ├── schema.py
│   │   └── repositories/
│   ├── services/                 # Shared infrastructure integrations
│   │   ├── llm.py
│   │   ├── documents.py
│   │   ├── search.py
│   │   ├── identity.py           # SSO provider integration
│   │   └── audit.py
│   ├── workers/                  # Background jobs: imports, re-indexing, impact analysis
│   └── main.py                   # Thin app startup
├── frontend/                     # React UI: Explore, Curate, Govern, Chat, Admin
├── migrations/                   # PostgreSQL migrations, if relational storage remains
└── main_build.py                 # Thin CLI for data/graph build tasks



Start with Borrower 360. It gives you a concrete end-to-end business workflow:
Select Borrower → FastAPI → Parameterized Cypher → Neo4j → Structured Result → React UI

Yes. Ontology Mapping fits well as the next workflow, using the loan graph’s existing FIBO mappings as the starting point.

A practical first step is to choose one loan graph entity or property—such as Loan, currentBalance, or borrowerRole—and show its mapped FIBO class or property, including the mapping source and confidence if those are available. We can inspect the importer model to see what mapping metadata it actually contains, then shape the workflow around that.


rbc.md describes the platform’s main outcome as business-readable lineage from legacy SQL, with CDEs linked to ontology terms.

The app currently has borrower exploration and legacy-to-graph mapping, but no SQL lineage feature. The next step should be a separate SQL Lineage workflow that reads the legacy SQL and shows table/column dependencies, then lets users connect those lineage elements to saved mappings and CDEs. The existing legacy_loan_demo.sql is a suitable synthetic input.


You’re right. The legacy DDL doesn’t need to match the names used in the transformation SQL. The lineage now comes from fibo/sql/sql.sql; it parses six queries, 31 output columns, and their projection, join, filter, and grouping dependencies.

The implementation stores the SQL source, lineage nodes and edges, graph terms, and mapping/CDE links in Neo4j. PostgreSQL remains the mapping registry. Saving a mapping triggers a graph sync; otherwise, use Build graph lineage on the SQL Lineage page for the initial sync. I haven’t written to Aura from here.

The parser/API and frontend build successfully. This parser handles the SQL patterns in sql.sql; it isn’t yet a general-purpose parser for arbitrary SQL.