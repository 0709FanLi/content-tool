"""
内容创作应用主入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
from dotenv import load_dotenv
import os

# 加载.env文件
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

from src.api.routers import auth, projects, scripts, keyframes, videos, files, models
from src.config.settings import settings
from src.models.database import create_tables, get_db
from src.utils.logging import setup_logging
from src.utils.exceptions import ApiError, setup_exception_handlers


# 设置日志
setup_logging()

logger = structlog.get_logger(__name__)


async def init_default_user():
    """初始化默认测试用户（仅在开发环境）"""
    # 仅在开发环境创建测试用户
    if not settings.debug:
        return
    
    # 检查是否允许创建测试用户（通过环境变量控制）
    create_test_user = os.getenv("CREATE_TEST_USER", "false").lower() == "true"
    if not create_test_user:
        logger.info("跳过测试用户创建（设置 CREATE_TEST_USER=true 以启用）")
        return
    
    from src.models.database import async_session_maker
    from src.services.auth_service import AuthService
    from src.models.schemas import UserCreate
    
    # 从环境变量获取测试用户信息，如果没有则使用默认值
    test_username = os.getenv("TEST_USERNAME", "testuser")
    test_email = os.getenv("TEST_EMAIL", "test@example.com")
    test_password = os.getenv("TEST_PASSWORD")
    
    if not test_password:
        logger.warning("未设置 TEST_PASSWORD 环境变量，跳过测试用户创建")
        return
    
    async with async_session_maker() as db:
        auth_service = AuthService(db)
        
        # 检查用户是否已存在
        existing_user = await auth_service.get_user_by_username(test_username)
        if existing_user:
            logger.info("测试用户已存在", username=test_username)
            return
        
        # 创建测试用户
        try:
            user_data = UserCreate(
                username=test_username,
                email=test_email,
                password=test_password
            )
            user = await auth_service.create_user(user_data)
            logger.info("测试用户创建成功", username=user.username, user_id=user.id)
        except ValueError as e:
            logger.warning("测试用户创建失败（可能已存在）", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting Content Creation API")

    # 创建数据库表
    await create_tables()
    
    # 初始化默认用户
    await init_default_user()

    yield

    logger.info("Shutting down Content Creation API")


def create_application() -> FastAPI:
    """创建FastAPI应用实例"""

    app = FastAPI(
        title=settings.app_name,
        description="内容创作平台API",
        version="1.0.0",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 设置异常处理器
    setup_exception_handlers(app)

    # 中间件配置
    # CORS 配置：允许前端源（包括协议和端口）
    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:5173",
    ]
    # 如果配置中有自定义的 CORS 源，则使用配置的
    if settings.cors_origins:
        import json
        try:
            custom_origins = json.loads(settings.cors_origins)
            if isinstance(custom_origins, list):
                cors_origins.extend(custom_origins)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid CORS origins format, using defaults")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

    # 路由注册
    app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
    app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
    app.include_router(scripts.router, prefix="/api/scripts", tags=["脚本管理"])
    app.include_router(keyframes.router, prefix="/api/keyframes", tags=["关键帧管理"])
    app.include_router(videos.router, prefix="/api/videos", tags=["视频管理"])
    app.include_router(files.router, prefix="/api/files", tags=["文件管理"])
    app.include_router(models.router, prefix="/api/models", tags=["模型管理"])

    # 健康检查
    @app.get("/health", tags=["健康检查"])
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client=request.client.host if request.client else None,
        )

        response = await call_next(request)

        logger.info(
            "Request completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
        )

        return response

    return app


# 创建应用实例
app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_config=None,  # 使用我们的日志配置
    )
