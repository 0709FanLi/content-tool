"""测试图片生成接口功能"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.services.image_generation_service import image_generation_service
from src.config.settings import settings


async def test_image_generation_config():
    """测试图片生成配置."""
    print("\n" + "="*60)
    print("测试图片生成配置")
    print("="*60)
    
    # 检查环境变量
    grsai_key_env = os.getenv('GRSAI_KEY')
    image_gen_key_env = os.getenv('IMAGE_GENERATION_API_KEY')
    
    print(f"\n环境变量检查:")
    print(f"  GRSAI_KEY: {'✅ 已设置' if grsai_key_env else '❌ 未设置'}")
    if grsai_key_env:
        print(f"    值: {grsai_key_env[:10]}...{grsai_key_env[-5:] if len(grsai_key_env) > 15 else ''}")
    
    print(f"  IMAGE_GENERATION_API_KEY: {'✅ 已设置' if image_gen_key_env else '❌ 未设置'}")
    if image_gen_key_env:
        print(f"    值: {image_gen_key_env[:10]}...{image_gen_key_env[-5:] if len(image_gen_key_env) > 15 else ''}")
    
    # 检查配置
    print(f"\n配置检查:")
    print(f"  settings.grsai_key: {'✅ 已设置' if settings.grsai_key else '❌ 未设置'}")
    print(f"  settings.image_generation_api_key: {'✅ 已设置' if settings.image_generation_api_key else '❌ 未设置'}")
    print(f"  settings.image_generation_base_url: {settings.image_generation_base_url}")
    print(f"  settings.image_generation_timeout: {settings.image_generation_timeout}")
    
    # 检查服务实例
    print(f"\n服务实例检查:")
    print(f"  image_generation_service.api_key: {'✅ 已设置' if image_generation_service.api_key else '❌ 未设置'}")
    if image_generation_service.api_key:
        masked_key = image_generation_service.api_key[:10] + "..." + image_generation_service.api_key[-5:] if len(image_generation_service.api_key) > 15 else image_generation_service.api_key[:10] + "..."
        print(f"    值: {masked_key}")
    print(f"  image_generation_service.base_url: {image_generation_service.base_url}")
    print(f"  image_generation_service.timeout: {image_generation_service.timeout}")
    
    if not image_generation_service.api_key:
        print("\n❌ 错误: 图片生成API密钥未配置!")
        print("   请确保在 .env 文件中设置 GRSAI_KEY 环境变量")
        return False
    
    print("\n✅ 配置检查通过")
    return True


async def test_image_generation_api():
    """测试图片生成API调用."""
    print("\n" + "="*60)
    print("测试图片生成API调用")
    print("="*60)
    
    if not image_generation_service.api_key:
        print("\n❌ 跳过API测试: API密钥未配置")
        return False
    
    # 测试提示词
    test_prompt = "一只可爱的小猫坐在窗台上，阳光透过窗户洒在它身上"
    
    print(f"\n测试参数:")
    print(f"  提示词: {test_prompt}")
    print(f"  模型: nano-banana-fast")
    print(f"  比例: auto")
    
    try:
        print("\n开始调用图片生成API...")
        result = await image_generation_service.generate_image_nano_banana(
            prompt=test_prompt,
            model='nano-banana-fast',
            aspect_ratio='auto',
            quality='720p'
        )
        
        print("\n✅ API调用成功!")
        print(f"  任务ID: {result.get('task_id')}")
        print(f"  状态: {result.get('status')}")
        print(f"  图片URL: {result.get('url')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ API调用失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数."""
    print("\n" + "="*60)
    print("图片生成接口测试")
    print("="*60)
    
    # 测试配置
    config_ok = await test_image_generation_config()
    
    if not config_ok:
        print("\n配置检查失败，请检查 .env 文件中的 GRSAI_KEY 设置")
        return
    
    # 自动进行API测试
    print("\n" + "-"*60)
    print("开始进行API调用测试...")
    
    api_ok = await test_image_generation_api()
    if api_ok:
        print("\n" + "="*60)
        print("✅ 所有测试通过!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ API测试失败，请检查网络连接和API密钥")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

