# 后端开发规范 - 内容创作应用

## 项目概述
基于FastAPI构建的内容创作应用后端服务，提供AI驱动的内容创作API，支持从脚本生成到视频导出的完整工作流。

## 技术栈选择
- **FastAPI**: 高性能异步Web框架，支持自动API文档生成
- **SQLAlchemy**: ORM数据库操作，支持异步查询
- **Pydantic**: 数据验证和序列化
- **PostgreSQL**: 主数据库，支持JSON字段存储复杂数据
- **Redis**: 缓存和会话存储
- **MinIO**: 对象存储，处理文件上传和分发
- **JWT**: 用户认证和授权
- **httpx**: 异步HTTP客户端，调用AI模型API
- **Celery**: 异步任务队列，处理视频生成等耗时任务

## 项目结构

```
content-creation-backend/
├── src/
│   ├── main.py                     # 应用入口，FastAPI实例和路由注册
│   ├── api/                        # API接口层
│   │   ├── __init__.py
│   │   ├── routers/                # 路由模块，按功能分组
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # 认证接口（登录、注册、token刷新）
│   │   │   ├── projects.py         # 项目管理接口
│   │   │   ├── scripts.py          # 脚本管理接口
│   │   │   ├── keyframes.py        # 关键帧管理接口
│   │   │   ├── videos.py           # 视频管理接口
│   │   │   └── files.py            # 文件上传下载接口
│   │   ├── dependencies.py         # 依赖注入（数据库会话、当前用户、文件服务）
│   │   └── middleware/             # 中间件
│   │       ├── auth.py             # 认证中间件
│   │       └── cors.py             # CORS中间件
│   ├── services/                   # 服务层，业务逻辑核心
│   │   ├── __init__.py
│   │   ├── auth_service.py         # 用户认证服务
│   │   ├── project_service.py      # 项目管理服务
│   │   ├── script_service.py       # 脚本生成和优化服务
│   │   ├── keyframe_service.py     # 关键帧生成服务
│   │   ├── video_service.py        # 视频生成服务
│   │   ├── file_service.py         # 文件存储服务
│   │   ├── llm_service.py          # 大模型调用服务（OpenAI、Stability AI等）
│   │   └── task_service.py         # 异步任务服务
│   ├── models/                     # 数据模型层
│   │   ├── __init__.py
│   │   ├── database.py             # 数据库连接和配置
│   │   ├── schemas/                # Pydantic模型（API请求/响应）
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # 认证相关schema
│   │   │   ├── project.py          # 项目相关schema
│   │   │   ├── script.py           # 脚本相关schema
│   │   │   ├── keyframe.py         # 关键帧相关schema
│   │   │   ├── video.py            # 视频相关schema
│   │   │   └── file.py             # 文件相关schema
│   │   └── tables/                 # SQLAlchemy ORM模型
│   │       ├── __init__.py
│   │       ├── user.py             # 用户表
│   │       ├── project.py          # 项目表
│   │       ├── script.py           # 脚本表
│   │       ├── keyframe.py         # 关键帧表
│   │       ├── video_segment.py    # 视频片段表
│   │       └── file.py             # 文件表
│   ├── utils/                      # 工具模块
│   │   ├── __init__.py
│   │   ├── logging.py              # 结构化日志配置
│   │   ├── exceptions.py           # 自定义异常类
│   │   ├── security.py             # 安全工具（密码哈希、JWT处理）
│   │   ├── validation.py           # 数据验证工具
│   │   ├── file_utils.py           # 文件处理工具
│   │   └── ai_models.py            # AI模型配置和工具
│   ├── config/                     # 配置模块
│   │   ├── __init__.py
│   │   └── settings.py             # 应用配置类
│   └── tasks/                      # Celery异步任务
│       ├── __init__.py
│       ├── celery_app.py           # Celery应用实例
│       ├── keyframe_tasks.py       # 关键帧生成任务
│       └── video_tasks.py          # 视频生成任务
├── tests/                          # 测试目录
│   ├── __init__.py
│   ├── conftest.py                 # 测试配置和fixtures
│   ├── unit/                       # 单元测试
│   │   ├── test_services.py        # 服务层测试
│   │   └── test_utils.py           # 工具函数测试
│   └── integration/                # 集成测试
│       ├── test_api.py             # API接口测试
│       └── test_database.py        # 数据库集成测试
├── docs/                           # 文档目录
│   ├── api.md                      # API文档
│   ├── database.md                 # 数据库设计文档
│   ├── deployment.md               # 部署文档
│   └── architecture.md             # 系统架构说明
├── scripts/                        # 脚本目录
│   ├── init_db.py                  # 数据库初始化脚本
│   ├── migrate_db.py               # 数据库迁移脚本
│   ├── backup.py                   # 数据备份脚本
│   └── docker/                     # Docker相关脚本
│       ├── Dockerfile
│       ├── docker-compose.yml
│       └── nginx.conf
├── .env.example                    # 环境变量示例文件
├── .gitignore                      # Git忽略文件
├── README.md                       # 项目说明文档
├── requirements.txt                # Python依赖列表
├── pyproject.toml                  # 项目配置（可选）
└── alembic/                        # 数据库迁移目录
    ├── versions/                   # 迁移版本文件
    ├── env.py                      # 迁移环境配置
    └── alembic.ini                 # Alembic配置
```

## 核心业务模块

### 1. 用户认证模块
- JWT token认证
- 用户注册和登录
- 密码重置功能
- 用户权限管理

### 2. 项目管理模块
- 项目的CRUD操作
- 项目状态管理（草稿、进行中、完成）
- 最近项目列表
- 项目数据关联（脚本、关键帧、视频）

### 3. 脚本管理模块
- 脚本生成（调用大模型API）
- 脚本优化和编辑
- 脚本版本管理
- 脚本模板支持

### 4. 关键帧管理模块
- 关键帧图片生成（调用AI绘画API）
- 关键帧编辑和替换
- 批量关键帧生成
- 关键帧与脚本段落关联

### 5. 视频管理模块
- 视频片段生成（调用视频生成API）
- 视频导出和打包
- 视频预览和播放
- 视频质量控制

### 6. 文件管理模块
- 文件上传和存储（MinIO）
- 文件访问控制
- 文件类型验证
- 文件清理和备份

## 开发规范

### 企业级Python开发规则

#### 1. 代码风格与命名规范
- **PEP 8遵守**：4空格缩进，行长不超过79字符
- **类型提示**：所有函数、方法添加完整类型注解
- **命名规则**：
  - 类：CamelCase（如`UserService`）
  - 函数/变量：snake_case（如`create_user`）
  - 常量：UPPER_SNAKE_CASE（如`DEFAULT_TIMEOUT`）

#### 2. 架构分层原则
- **API层**：仅处理HTTP请求/响应，不包含业务逻辑
- **服务层**：核心业务逻辑，处理数据操作和外部API调用
- **模型层**：数据定义和验证
- **工具层**：通用功能和辅助函数

#### 3. 错误处理与日志
- **自定义异常**：继承`HTTPException`定义业务异常
- **结构化日志**：使用JSON格式，包含请求ID、用户ID等上下文
- **错误响应**：统一的错误响应格式

#### 4. 数据库操作规范
- **异步查询**：使用`async_session`进行数据库操作
- **事务管理**：重要操作使用事务确保数据一致性
- **查询优化**：避免N+1查询，使用`selectinload`预加载关联数据

#### 5. AI模型集成规范
- **服务封装**：在`llm_service.py`中统一封装AI API调用
- **重试机制**：使用`tenacity`库实现API调用重试
- **错误处理**：区分可重试错误和不可重试错误
- **配置管理**：API密钥等敏感信息通过环境变量配置

#### 6. 异步任务处理
- **Celery集成**：耗时任务（如视频生成）使用Celery异步处理
- **任务状态**：任务状态存储在Redis中，支持实时查询
- **错误恢复**：失败任务支持重试和手动干预

#### 7. 文件存储规范
- **对象存储**：使用MinIO进行文件存储
- **访问控制**：文件URL设置过期时间，防止直接访问
- **文件验证**：上传前验证文件类型、大小等
- **清理策略**：定期清理临时文件和过期文件

## 安全规范

### 认证与授权
- JWT token认证，token设置合理过期时间
- 密码使用bcrypt哈希存储
- API访问频率限制
- CORS配置限制允许的域名

### 数据安全
- 敏感数据加密存储
- SQL注入防护（使用ORM参数化查询）
- XSS防护（输入数据验证和清理）
- 文件上传安全检查

### API安全
- 请求签名验证（可选）
- API版本管理
- 废弃API的平滑迁移
- 错误信息不泄露敏感数据

## 测试规范

### 单元测试
- 服务层核心逻辑测试
- 工具函数测试
- Mock外部依赖（AI API、数据库）

### 集成测试
- API接口测试
- 数据库操作测试
- 文件上传下载测试

### 测试覆盖率
- 目标覆盖率：>80%
- 核心业务模块：>90%

## 部署规范

### 容器化部署
- Docker多阶段构建
- 非root用户运行
- 最小化镜像大小

### 环境配置
- 开发/测试/生产环境分离
- 环境变量管理敏感配置
- 配置热重载支持

### 监控告警
- 应用性能监控（APM）
- 错误日志收集
- 业务指标监控

## 性能优化

### 数据库优化
- 索引优化
- 查询优化
- 连接池配置

### 缓存策略
- Redis缓存热点数据
- API响应缓存
- 文件元数据缓存

### 异步处理
- 耗时任务异步化
- 消息队列解耦
- 事件驱动架构
