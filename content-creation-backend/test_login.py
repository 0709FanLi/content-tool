"""测试登录功能"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from src.models.tables import User
from src.utils.security import verify_password, get_password_hash

async def test_login():
    # 创建数据库连接
    database_url = "sqlite+aiosqlite:///content_creation.db"
    engine = create_async_engine(database_url, echo=True)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        # 查询用户
        username = "111111"
        password = "q111111"
        
        print(f"\n===== 测试登录 =====")
        print(f"用户名: {username}")
        print(f"密码: {password}")
        
        # 查询用户
        stmt = select(User).where((User.username == username) | (User.email == username))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ 用户不存在")
            return
        
        print(f"✅ 找到用户: ID={user.id}, username={user.username}, email={user.email}")
        print(f"存储的哈希值: {user.hashed_password}")
        
        # 计算密码哈希
        computed_hash = get_password_hash(password)
        print(f"计算的哈希值: {computed_hash}")
        
        # 验证密码
        is_valid = verify_password(password, user.hashed_password)
        print(f"密码验证结果: {'✅ 通过' if is_valid else '❌ 失败'}")
        
        if user.hashed_password == computed_hash:
            print("✅ 哈希值匹配")
        else:
            print("❌ 哈希值不匹配")
            print(f"差异: 存储的={user.hashed_password}")
            print(f"      计算的={computed_hash}")

if __name__ == "__main__":
    asyncio.run(test_login())

