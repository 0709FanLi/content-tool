# 内容创作后端

基于 FastAPI 构建的内容创作平台后端服务。

## 快速开始

### 环境要求
- Python 3.8+
- PostgreSQL (生产环境) 或 SQLite (开发环境)

### 安装依赖
```bash
# 安装Python依赖
pip install -r requirements.txt

# 或者使用uv
uv pip install -r requirements.txt
```

### 环境配置
复制环境变量文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件配置数据库和其他设置。

### 数据库初始化
```bash
# 初始化数据库表
python -c "
import asyncio
from src.models.database import create_tables
asyncio.run(create_tables())
"
```

## 服务管理

### 使用开发环境管理脚本

```bash
# 启动服务
./dev.sh start

# 停止服务
./dev.sh stop

# 重启服务
./dev.sh restart

# 查看服务状态
./dev.sh status

# 查看服务日志
./dev.sh logs

# 清理临时文件
./dev.sh clean

# 显示帮助
./dev.sh help
```

### 手动管理

```bash
# 启动服务
export DEBUG=true
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
export JWT_SECRET_KEY="your-secret-key"
python -c "from src.main import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=8000)"

# 停止服务
./stop.sh
```

### 使用重启脚本
```bash
# 一键重启服务
./restart.sh
```

## API文档

服务启动后，可以通过以下地址访问：

- **API文档**: http://localhost:8000/docs
- **交互式API文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 主要功能

### 用户认证
- 用户注册 (`POST /auth/register`)
- 用户登录 (`POST /auth/login`)
- 令牌刷新 (`POST /auth/refresh`)
- 获取当前用户信息 (`GET /auth/me`)

### 项目管理
- 项目CRUD操作
- 项目状态管理
- 最近项目列表

### 脚本管理
- 脚本生成和优化
- 脚本内容编辑

### 关键帧管理
- AI关键帧生成
- 关键帧上传和管理

### 视频管理
- 视频片段生成
- 视频导出

### 文件管理
- 文件上传下载
- 文件存储管理

## 开发指南

### 项目结构
```
src/
├── main.py              # 应用入口
├── api/                 # API接口层
│   ├── routers/        # 路由定义
│   └── middleware/     # 中间件
├── services/           # 业务逻辑层
├── models/             # 数据模型
│   ├── database.py     # 数据库连接
│   ├── tables/         # ORM模型
│   └── schemas/        # Pydantic模型
├── utils/              # 工具函数
└── config/             # 配置管理
```

### 代码规范
- 使用类型提示
- 遵循 PEP 8 规范
- 使用结构化日志
- 编写单元测试

### 数据库迁移
```bash
# 生成迁移文件
alembic revision --autogenerate -m "migration message"

# 执行迁移
alembic upgrade head
```

## 测试

```bash
# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行所有测试
pytest
```

## 部署

### 生产环境配置
1. 设置生产数据库 (PostgreSQL)
2. 配置Redis缓存
3. 设置环境变量
4. 使用反向代理 (Nginx)
5. 配置SSL证书

### Docker部署
```bash
# 构建镜像
docker build -t content-creation-backend .

# 运行容器
docker run -p 8000:8000 content-creation-backend
```

## 监控和日志

- 结构化日志输出到控制台和文件
- 健康检查端点
- 请求日志中间件
- 错误处理和异常记录

## 安全考虑

- JWT认证和授权
- 密码哈希存储
- 请求频率限制
- CORS配置
- 输入验证和清理
