"""Labels, properties, relationships, and Cypher constraints for the demo graph."""

ENTITY_CLASSES = {
    "Developer": {
        "label": "开发者",
        "definition": "参与项目开发的人员",
        "properties": ["id:integer:required:unique", "name:string:required", "email:string:unique", "role:string", "team_id:integer", "experience_years:integer", "skills:string", "created_at:datetime"],
    },
    "Project": {
        "label": "项目",
        "definition": "完整的软件开发项目",
        "properties": ["id:integer:required:unique", "name:string:required", "description:string", "status:string", "start_date:date", "end_date:date", "budget:float", "created_at:datetime"],
    },
    "Team": {
        "label": "团队",
        "definition": "参与项目的软件开发团队",
        "properties": ["id:integer:required:unique", "name:string:required", "project_id:integer", "leader_id:integer", "description:string", "created_at:datetime"],
    },
    "Requirement": {
        "label": "需求",
        "definition": "项目的功能或非功能需求",
        "properties": ["id:integer:required:unique", "title:string:required", "description:string", "project_id:integer", "priority:string", "status:string", "complexity:string", "assigned_to:integer", "created_at:datetime"],
    },
    "Task": {
        "label": "任务",
        "definition": "实现需求的具体工作项",
        "properties": ["id:integer:required:unique", "title:string:required", "description:string", "requirement_id:integer", "assigned_to:integer", "status:string", "priority:string", "estimated_hours:float", "actual_hours:float", "created_at:datetime"],
    },
}

UNIQUE_CONSTRAINTS = [
    "CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (n:Project) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT team_id_unique IF NOT EXISTS FOR (n:Team) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT developer_id_unique IF NOT EXISTS FOR (n:Developer) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (n:Requirement) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT task_id_unique IF NOT EXISTS FOR (n:Task) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT entity_class_name_unique IF NOT EXISTS FOR (n:EntityClass) REQUIRE n.name IS UNIQUE",
]

RELATIONSHIPS = [
    ("Team", "project_id", "Project", "BELONGS_TO"),
    ("Developer", "team_id", "Team", "MEMBER_OF"),
    ("Requirement", "project_id", "Project", "BELONGS_TO"),
    ("Task", "requirement_id", "Requirement", "IMPLEMENTS"),
    ("Task", "assigned_to", "Developer", "ASSIGNED_TO"),
    ("Requirement", "assigned_to", "Developer", "ASSIGNED_TO"),
]
