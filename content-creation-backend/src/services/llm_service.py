"""
大模型调用服务
支持DeepSeek和通义千问（阿里云DashScope）
"""

import os
import json
from typing import Optional, Any
import httpx
from openai import OpenAI
import structlog

from src.config.settings import settings
from src.utils.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)


def retry_decorator(max_attempts: int = 3, wait_multiplier: int = 1, wait_min: int = 2, wait_max: int = 10):
    """
    重试装饰器
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import asyncio
            attempt = 0
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            "Max retry attempts reached",
                            function=func.__name__,
                            error=str(e),
                            attempts=attempt
                        )
                        raise
                    
                    wait_time = min(wait_min * (wait_multiplier ** (attempt - 1)), wait_max)
                    logger.warning(
                        "Retrying function",
                        function=func.__name__,
                        attempt=attempt,
                        wait_time=wait_time,
                        error=str(e)
                    )
                    await asyncio.sleep(wait_time)
            return None
        return wrapper
    return decorator


class DeepSeekService:
    """DeepSeek服务类"""

    def __init__(self) -> None:
        # 支持多种环境变量名
        self.api_key = (
            settings.deep_seek or
            os.getenv("DEEP_SEEK") or
            os.getenv("DEEPSEEK_API_KEY") or
            os.getenv("deepseek_api_key") or
            ""
        )
        self.base_url = "https://api.deepseek.com"
        self.timeout = 60

    @retry_decorator(max_attempts=3, wait_multiplier=1, wait_min=2, wait_max=10)
    async def generate_script(
        self,
        inspiration: str,
        style: str,
        total_duration: int,
        segment_duration: int,
        model: str = "deepseek-chat",
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """
        生成脚本
        
        Args:
            inspiration: 创意灵感
            style: 脚本风格
            total_duration: 视频总时长（秒）
            segment_duration: 单个视频时长（秒）
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的脚本内容
        """
        if not self.api_key:
            raise ExternalServiceError("DeepSeek", "API Key未配置")

        # 计算片段数量
        segment_count = total_duration // segment_duration
        
        # 计算每个片段的内容长度参考（按正常语速，每秒约2-3个汉字）
        # 为了确保内容足够详细，我们提高内容长度要求
        content_length_min = segment_duration * 3  # 提高最小长度
        content_length_max = segment_duration * 5  # 提高最大长度，确保内容足够详细
        
        # 构建系统提示词
        system_prompt = f"""你是一个专业的视频脚本创作专家。你的任务是根据用户的创意和风格要求，生成一个结构化的视频脚本。

脚本要求：
1. 视频总时长：{total_duration}秒
2. 单个片段时长：{segment_duration}秒
3. 片段数量：{segment_count}个
4. 脚本风格：{style}

脚本格式要求：
- **必须包含第0帧（开场画面）**：在第一个片段之前，格式为 `第0帧：详细描述开场画面...` 或 `(0:00 - 0:00) 开场画面：...`，描述视频开始前的初始状态或开场画面
- 每个片段必须按照时间范围格式：开始时间-结束时间 内容描述
- 时间格式：0-{segment_duration}s, {segment_duration}-{segment_duration * 2}s, ... 以此类推
- **重要：每个片段的内容描述必须非常详细和具体，能够充分描述{segment_duration}秒的视频内容**
- **内容长度要求：每个片段的内容描述必须包含{content_length_min}-{content_length_max}个汉字，确保内容足够详细**
- **内容详细度要求：**
  * 必须包含具体的动作描述（如：小黄猫在街头缓慢踱步，四处张望，寻找食物）
  * 必须包含环境细节（如：在繁华的街道上，人来人往，小黄猫躲在角落）
  * 必须包含情感表达（如：眼神中透露着渴望和不安）
  * 必须包含视觉元素（如：阳光洒在街道上，小黄猫的毛发在微风中轻轻摆动）
- 每个片段的内容描述要生动具体，符合{style}的风格特点
- 片段之间要有连贯性，形成完整的故事线
- **禁止使用简单的一句话描述，必须用多个句子详细描述场景、动作、情感等细节**
- **第0帧和第一帧的过渡要求（非常重要）：**
  * 第0帧应该描述开场时的静态或初始状态（如：人物坐在某个位置、场景的初始布局等）
  * 第一帧（0-{segment_duration}s）应该描述从第0帧状态开始的第一个动作或变化（如：人物开始某个动作、场景开始变化等）
  * 在提示词中明确体现从第0帧到第一帧的视觉过渡和连贯性，确保两帧之间的动作和场景自然衔接
  * 例如：如果第0帧是"一位年轻女性坐在明亮的化妆镜前，眉头微皱"，第一帧应该是"这位女性开始用手指轻抚眼角的细纹，然后拿起手机"，体现动作的连续性和过渡
- **一致性要求（非常重要）：**
  * 如果在多个片段中出现同一个物品、角色、对象或概念，必须保持完全一致的描述（包括第0帧）
  * 同一物品的颜色、大小、形状、特征等属性在所有片段中必须保持一致
  * 同一角色的名称、外观、特征在所有片段中必须保持一致（例如：如果第0帧提到"小黄猫"，后续所有片段都必须使用"小黄猫"，不能变成"黄色小猫"、"小橘猫"等）
  * 同一地点的名称、环境特征在所有片段中必须保持一致
  * 在生成脚本前，请先确定所有重复出现的元素，并建立统一的描述标准，确保整个脚本中这些元素的描述完全一致

请直接输出脚本内容，不要添加任何解释或说明。"""

        user_prompt = f"""请根据以下创意生成视频脚本：

创意：{inspiration}

请按照上述格式要求，生成脚本，包括：
1. **第0帧（开场画面）**：描述视频开始前的初始状态或开场画面，必须详细具体，包含场景、人物、环境等细节
2. **{segment_count}个片段**：每个片段的内容描述必须非常详细，包含{content_length_min}-{content_length_max}个汉字，详细描述场景、动作、情感、视觉元素等，确保能够充分描述{segment_duration}秒的视频内容。不要使用简单的一句话，要用多个句子详细描述。

**特别注意：**
- **第0帧和第一帧的过渡**：第0帧应该描述静态或初始状态，第一帧（0-{segment_duration}s）应该描述从第0帧开始的第一个动作或变化，在提示词中明确体现视觉过渡和连贯性，确保两帧之间的动作和场景自然衔接
- **一致性要求**：如果在多个片段中出现同一个物品、角色或对象，请确保在所有片段（包括第0帧）中使用完全相同的名称和特征描述，不要使用同义词或不同的表达方式。例如，如果第0帧中出现了"小黄猫"，那么在所有后续片段中都应该使用"小黄猫"，而不是"黄色小猫"、"小橘猫"等其他表达。"""

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"].strip()
                logger.info(
                    "DeepSeek script generation completed",
                    model=model,
                    segment_count=segment_count
                )
                return content
        except httpx.HTTPStatusError as e:
            logger.error(
                "DeepSeek API error",
                status_code=e.response.status_code,
                response=e.response.text
            )
            raise ExternalServiceError("DeepSeek", f"API调用失败: {e.response.status_code}")
        except Exception as e:
            logger.error("DeepSeek service error", error=str(e))
            raise ExternalServiceError("DeepSeek", f"服务异常: {str(e)}")

    @retry_decorator(max_attempts=3, wait_multiplier=1, wait_min=2, wait_max=10)
    async def optimize_script(
        self,
        script_content: str,
        creative_description: str,
        model: str = "deepseek-chat",
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """
        优化脚本，使用创意描述作为补充
        
        Args:
            script_content: 原始脚本内容
            creative_description: 创意描述（用于优化脚本）
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            优化后的脚本内容
        """
        if not self.api_key:
            raise ExternalServiceError("DeepSeek", "API Key未配置")

        # 构建系统提示词
        system_prompt = """你是一个专业的视频脚本优化专家。你的任务是根据用户提供的创意描述，对现有脚本进行优化和改进。

优化要求：
1. 保持脚本的原有结构和时间格式
2. 根据创意描述，增强脚本的细节描述和表现力
3. 确保优化后的脚本更加生动、具体、有感染力
4. 保持脚本的连贯性和完整性
5. 使用创意描述中的语言风格和表达方式

请直接输出优化后的脚本内容，不要添加任何解释或说明。保持原有的时间格式（如：0-6s 内容描述）。"""

        user_prompt = f"""请根据以下创意描述优化脚本：

原始脚本：
{script_content}

创意描述（请使用这个描述的语言风格和表达方式来优化脚本）：
{creative_description}

请使用创意描述中的语言风格和表达方式，对原始脚本进行优化，使其更加生动、具体、有感染力。保持脚本的原有结构和时间格式。"""

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"].strip()
                logger.info(
                    "DeepSeek script optimization completed",
                    model=model
                )
                return content
        except httpx.HTTPStatusError as e:
            logger.error(
                "DeepSeek API error",
                status_code=e.response.status_code,
                response=e.response.text
            )
            raise ExternalServiceError("DeepSeek", f"API调用失败: {e.response.status_code}")
        except Exception as e:
            logger.error("DeepSeek service error", error=str(e))
            raise ExternalServiceError("DeepSeek", f"服务异常: {str(e)}")


class QwenService:
    """通义千问服务类（阿里云DashScope）"""

    def __init__(self) -> None:
        self.api_key = settings.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY") or ""
        self.base_url = settings.qwen_base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )

    @retry_decorator(max_attempts=3, wait_multiplier=1, wait_min=2, wait_max=10)
    async def generate_script(
        self,
        inspiration: str,
        style: str,
        total_duration: int,
        segment_duration: int,
        model: str = "qwen-plus",
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """
        生成脚本
        
        Args:
            inspiration: 创意灵感
            style: 脚本风格
            total_duration: 视频总时长（秒）
            segment_duration: 单个视频时长（秒）
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            生成的脚本内容
        """
        if not self.api_key or not self.client:
            raise ExternalServiceError("Qwen", "API Key未配置")

        # 计算片段数量
        segment_count = total_duration // segment_duration
        
        # 计算每个片段的内容长度参考（按正常语速，每秒约2-3个汉字）
        # 为了确保内容足够详细，我们提高内容长度要求
        content_length_min = segment_duration * 3  # 提高最小长度
        content_length_max = segment_duration * 5  # 提高最大长度，确保内容足够详细
        
        # 构建系统提示词
        system_prompt = f"""你是一个专业的视频脚本创作专家。你的任务是根据用户的创意和风格要求，生成一个结构化的视频脚本。

脚本要求：
1. 视频总时长：{total_duration}秒
2. 单个片段时长：{segment_duration}秒
3. 片段数量：{segment_count}个
4. 脚本风格：{style}

脚本格式要求：
- **必须包含第0帧（开场画面）**：在第一个片段之前，格式为 `第0帧：详细描述开场画面...` 或 `(0:00 - 0:00) 开场画面：...`，描述视频开始前的初始状态或开场画面
- 每个片段必须按照时间范围格式：开始时间-结束时间 内容描述
- 时间格式：0-{segment_duration}s, {segment_duration}-{segment_duration * 2}s, ... 以此类推
- **重要：每个片段的内容描述必须非常详细和具体，能够充分描述{segment_duration}秒的视频内容**
- **内容长度要求：每个片段的内容描述必须包含{content_length_min}-{content_length_max}个汉字，确保内容足够详细**
- **内容详细度要求：**
  * 必须包含具体的动作描述（如：小黄猫在街头缓慢踱步，四处张望，寻找食物）
  * 必须包含环境细节（如：在繁华的街道上，人来人往，小黄猫躲在角落）
  * 必须包含情感表达（如：眼神中透露着渴望和不安）
  * 必须包含视觉元素（如：阳光洒在街道上，小黄猫的毛发在微风中轻轻摆动）
- 每个片段的内容描述要生动具体，符合{style}的风格特点
- 片段之间要有连贯性，形成完整的故事线
- **禁止使用简单的一句话描述，必须用多个句子详细描述场景、动作、情感等细节**
- **第0帧和第一帧的过渡要求（非常重要）：**
  * 第0帧应该描述开场时的静态或初始状态（如：人物坐在某个位置、场景的初始布局等）
  * 第一帧（0-{segment_duration}s）应该描述从第0帧状态开始的第一个动作或变化（如：人物开始某个动作、场景开始变化等）
  * 在提示词中明确体现从第0帧到第一帧的视觉过渡和连贯性，确保两帧之间的动作和场景自然衔接
  * 例如：如果第0帧是"一位年轻女性坐在明亮的化妆镜前，眉头微皱"，第一帧应该是"这位女性开始用手指轻抚眼角的细纹，然后拿起手机"，体现动作的连续性和过渡
- **一致性要求（非常重要）：**
  * 如果在多个片段中出现同一个物品、角色、对象或概念，必须保持完全一致的描述（包括第0帧）
  * 同一物品的颜色、大小、形状、特征等属性在所有片段中必须保持一致
  * 同一角色的名称、外观、特征在所有片段中必须保持一致（例如：如果第0帧提到"小黄猫"，后续所有片段都必须使用"小黄猫"，不能变成"黄色小猫"、"小橘猫"等）
  * 同一地点的名称、环境特征在所有片段中必须保持一致
  * 在生成脚本前，请先确定所有重复出现的元素，并建立统一的描述标准，确保整个脚本中这些元素的描述完全一致

请直接输出脚本内容，不要添加任何解释或说明。"""

        user_prompt = f"""请根据以下创意生成视频脚本：

创意：{inspiration}

请按照上述格式要求，生成脚本，包括：
1. **第0帧（开场画面）**：描述视频开始前的初始状态或开场画面，必须详细具体，包含场景、人物、环境等细节
2. **{segment_count}个片段**：每个片段的内容描述必须非常详细，包含{content_length_min}-{content_length_max}个汉字，详细描述场景、动作、情感、视觉元素等，确保能够充分描述{segment_duration}秒的视频内容。不要使用简单的一句话，要用多个句子详细描述。

**特别注意：**
- **第0帧和第一帧的过渡**：第0帧应该描述静态或初始状态，第一帧（0-{segment_duration}s）应该描述从第0帧开始的第一个动作或变化，在提示词中明确体现视觉过渡和连贯性，确保两帧之间的动作和场景自然衔接
- **一致性要求**：如果在多个片段中出现同一个物品、角色或对象，请确保在所有片段（包括第0帧）中使用完全相同的名称和特征描述，不要使用同义词或不同的表达方式。例如，如果第0帧中出现了"小黄猫"，那么在所有后续片段中都应该使用"小黄猫"，而不是"黄色小猫"、"小橘猫"等其他表达。"""

        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = completion.choices[0].message.content.strip()
            logger.info(
                "Qwen script generation completed",
                model=model,
                segment_count=segment_count
            )
            return content
        except Exception as e:
            logger.error("Qwen service error", error=str(e))
            raise ExternalServiceError("Qwen", f"服务异常: {str(e)}")

    @retry_decorator(max_attempts=3, wait_multiplier=1, wait_min=2, wait_max=10)
    async def optimize_script(
        self,
        script_content: str,
        creative_description: str,
        model: str = "qwen-plus",
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> str:
        """
        优化脚本，使用创意描述作为补充
        
        Args:
            script_content: 原始脚本内容
            creative_description: 创意描述（用于优化脚本）
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            优化后的脚本内容
        """
        if not self.api_key or not self.client:
            raise ExternalServiceError("Qwen", "API Key未配置")

        # 构建系统提示词
        system_prompt = """你是一个专业的视频脚本优化专家。你的任务是根据用户提供的创意描述，对现有脚本进行优化和改进。

优化要求：
1. 保持脚本的原有结构和时间格式
2. 根据创意描述，增强脚本的细节描述和表现力
3. 确保优化后的脚本更加生动、具体、有感染力
4. 保持脚本的连贯性和完整性
5. 使用创意描述中的语言风格和表达方式

请直接输出优化后的脚本内容，不要添加任何解释或说明。保持原有的时间格式（如：0-6s 内容描述）。"""

        user_prompt = f"""请根据以下创意描述优化脚本：

原始脚本：
{script_content}

创意描述（请使用这个描述的语言风格和表达方式来优化脚本）：
{creative_description}

请使用创意描述中的语言风格和表达方式，对原始脚本进行优化，使其更加生动、具体、有感染力。保持脚本的原有结构和时间格式。"""

        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = completion.choices[0].message.content.strip()
            logger.info(
                "Qwen script optimization completed",
                model=model
            )
            return content
        except Exception as e:
            logger.error("Qwen service error", error=str(e))
            raise ExternalServiceError("Qwen", f"服务异常: {str(e)}")


class LLMService:
    """LLM服务统一入口"""

    def __init__(self):
        self.deepseek_service = DeepSeekService()
        self.qwen_service = QwenService()

    async def generate_script(
        self,
        inspiration: str,
        style: str,
        total_duration: int,
        segment_duration: int,
        model: str = "deepseek-chat",
        **kwargs
    ) -> str:
        """
        生成脚本（统一入口）
        
        Args:
            inspiration: 创意灵感
            style: 脚本风格
            total_duration: 视频总时长（秒）
            segment_duration: 单个视频时长（秒）
            model: 模型名称（deepseek-chat 或 qwen-plus）
            **kwargs: 其他参数
            
        Returns:
            生成的脚本内容
        """
        if model.startswith("deepseek") or model == "deepseek-chat":
            return await self.deepseek_service.generate_script(
                inspiration=inspiration,
                style=style,
                total_duration=total_duration,
                segment_duration=segment_duration,
                model=model,
                **kwargs
            )
        elif model.startswith("qwen") or model == "qwen-plus":
            return await self.qwen_service.generate_script(
                inspiration=inspiration,
                style=style,
                total_duration=total_duration,
                segment_duration=segment_duration,
                model=model,
                **kwargs
            )
        else:
            raise ValueError(f"不支持的模型: {model}")

    async def optimize_script(
        self,
        script_content: str,
        creative_description: str,
        model: str = "deepseek-chat",
        **kwargs
    ) -> str:
        """
        优化脚本（统一入口）
        
        Args:
            script_content: 原始脚本内容
            creative_description: 创意描述（用于优化脚本）
            model: 模型名称（deepseek-chat 或 qwen-plus）
            **kwargs: 其他参数
            
        Returns:
            优化后的脚本内容
        """
        if model.startswith("deepseek") or model == "deepseek-chat":
            return await self.deepseek_service.optimize_script(
                script_content=script_content,
                creative_description=creative_description,
                model=model,
                **kwargs
            )
        elif model.startswith("qwen") or model == "qwen-plus":
            return await self.qwen_service.optimize_script(
                script_content=script_content,
                creative_description=creative_description,
                model=model,
                **kwargs
            )
        else:
            raise ValueError(f"不支持的模型: {model}")

    def get_available_models(self) -> list[dict[str, str]]:
        """
        获取可用模型列表
        
        Returns:
            模型列表，每个模型包含id和name
        """
        models = []
        
        # 检查DeepSeek是否配置
        if self.deepseek_service.api_key:
            models.append({
                "id": "deepseek-chat",
                "name": "DeepSeek Chat"
            })
        
        # 检查Qwen是否配置
        if self.qwen_service.api_key:
            models.append({
                "id": "qwen-plus",
                "name": "通义千问 Plus"
            })
        
        return models

