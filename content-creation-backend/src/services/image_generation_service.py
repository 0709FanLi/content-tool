"""
图片生成服务
封装调用Nano Banana、Sora Image和火山即梦 API的逻辑
"""

import os
from typing import Any, Dict, Optional, List
import httpx
import structlog

from src.config.settings import settings
from src.services.volc_jimeng_service import volc_jimeng_service

logger = structlog.get_logger(__name__)


class ImageGenerationService:
    """图片生成服务类."""

    def __init__(self) -> None:
        """初始化图片生成服务."""
        # 优先读取 GRSAI_KEY，然后是 IMAGE_GENERATION_API_KEY
        self.api_key = (
            os.getenv('GRSAI_KEY')
            or os.getenv('IMAGE_GENERATION_API_KEY')
            or settings.grsai_key
            or settings.image_generation_api_key
        )
        self.base_url = (
            os.getenv('IMAGE_GENERATION_BASE_URL')
            or settings.image_generation_base_url
        )
        self.timeout = settings.image_generation_timeout

        if not self.api_key:
            logger.warning('Image generation API key not configured')

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头.

        Returns:
            请求头字典
        """
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    async def generate_image_nano_banana(
        self,
        prompt: str,
        model: str = 'nano-banana-fast',
        aspect_ratio: str = 'auto',
        quality: str = '720p',
        reference_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用Nano Banana模型生成图片.

        Args:
            prompt: 提示词
            model: 模型名称 (nano-banana-fast, nano-banana)
            aspect_ratio: 图像比例
            quality: 清晰度（暂未使用，保留接口兼容性）
            reference_image_url: 参考图片URL（可选，用于提高一致性）

        Returns:
            包含图片URL的字典

        Raises:
            Exception: API调用失败
        """
        if not self.api_key:
            raise Exception('图片生成API密钥未配置')

        url = f'{self.base_url}/v1/draw/nano-banana'

        payload = {
            'model': model,
            'prompt': prompt,
            'aspectRatio': aspect_ratio,
            'webHook': '-1',  # 使用轮询方式，立即返回id
            'shutProgress': False
        }
        
        # 如果提供了参考图片，添加到payload（注意：Nano Banana API 使用 urls 参数，是一个数组）
        if reference_image_url:
            payload['urls'] = [reference_image_url]
            logger.info(
                'Using reference image for generation',
                reference_image_url=reference_image_url
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 第一步：提交任务，获取id
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                result = response.json()

                if result.get('code') != 0:
                    raise Exception(
                        f"API错误: {result.get('msg', '未知错误')}"
                    )

                task_id = result['data']['id']
                logger.info(
                    'Image generation task created',
                    model=model,
                    task_id=task_id
                )

                # 第二步：轮询获取结果
                result_url = f'{self.base_url}/v1/draw/result'
                max_polls = 60  # 最多轮询60次
                poll_interval = 2  # 每2秒轮询一次

                for i in range(max_polls):
                    import asyncio
                    await asyncio.sleep(poll_interval)

                    poll_response = await client.post(
                        result_url,
                        json={'id': task_id},
                        headers=self._get_headers()
                    )
                    poll_response.raise_for_status()
                    poll_result = poll_response.json()

                    if poll_result.get('code') != 0:
                        raise Exception(
                            f"轮询错误: {poll_result.get('msg', '未知错误')}"
                        )

                    data = poll_result.get('data', {})
                    status = data.get('status')

                    if status == 'succeeded':
                        # 成功，返回图片URL
                        results = data.get('results', [])
                        if results and len(results) > 0:
                            image_url = results[0].get('url')
                            logger.info(
                                'Image generated successfully',
                                task_id=task_id,
                                image_url=image_url
                            )
                            return {
                                'url': image_url,
                                'task_id': task_id,
                                'status': 'succeeded'
                            }
                        else:
                            raise Exception('生成成功但未返回图片URL')

                    elif status == 'failed':
                        # 失败
                        failure_reason = data.get('failure_reason', '')
                        error = data.get('error', '')
                        error_msg = (
                            f"生成失败: {failure_reason}"
                            if failure_reason
                            else f"生成失败: {error}"
                        )
                        logger.error(
                            'Image generation failed',
                            task_id=task_id,
                            failure_reason=failure_reason,
                            error=error
                        )
                        raise Exception(error_msg)

                    # 继续轮询
                    logger.debug(
                        'Polling image generation status',
                        task_id=task_id,
                        status=status,
                        progress=data.get('progress', 0)
                    )

                # 超时
                raise Exception('图片生成超时')

        except httpx.HTTPStatusError as e:
            logger.error(
                'HTTP error in image generation',
                status_code=e.response.status_code,
                error=str(e)
            )
            raise Exception(f'HTTP错误: {e.response.status_code}')
        except httpx.RequestError as e:
            logger.error('Request error in image generation', error=str(e))
            raise Exception(f'请求错误: {str(e)}')
        except Exception as e:
            logger.error('Error in image generation', error=str(e))
            raise

    async def generate_image_sora(
        self,
        prompt: str,
        aspect_ratio: str = 'auto',
        quality: str = '720p'
    ) -> Dict[str, Any]:
        """使用Sora Image模型生成图片.

        Args:
            prompt: 提示词
            aspect_ratio: 图像比例 (auto, 1:1, 3:2, 2:3)
            quality: 清晰度（暂未使用，保留接口兼容性）

        Returns:
            包含图片URL的字典

        Raises:
            Exception: API调用失败
        """
        if not self.api_key:
            raise Exception('图片生成API密钥未配置')

        url = f'{self.base_url}/v1/draw/completions'

        # 转换aspect_ratio格式
        size_map = {
            'auto': 'auto',
            '1:1': '1:1',
            '3:2': '3:2',
            '2:3': '2:3',
            '16:9': '3:2',  # Sora Image不支持16:9，使用3:2
            '9:16': '2:3'   # Sora Image不支持9:16，使用2:3
        }
        size = size_map.get(aspect_ratio, 'auto')

        payload = {
            'model': 'sora-image',
            'prompt': prompt,
            'size': size,
            'variants': 1,
            'webHook': '-1',  # 使用轮询方式，立即返回id
            'shutProgress': False
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 第一步：提交任务，获取id
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                result = response.json()

                if result.get('code') != 0:
                    raise Exception(
                        f"API错误: {result.get('msg', '未知错误')}"
                    )

                task_id = result['data']['id']
                logger.info(
                    'Image generation task created',
                    model='sora-image',
                    task_id=task_id
                )

                # 第二步：轮询获取结果
                result_url = f'{self.base_url}/v1/draw/result'
                max_polls = 60  # 最多轮询60次
                poll_interval = 2  # 每2秒轮询一次

                for i in range(max_polls):
                    import asyncio
                    await asyncio.sleep(poll_interval)

                    poll_response = await client.post(
                        result_url,
                        json={'id': task_id},
                        headers=self._get_headers()
                    )
                    poll_response.raise_for_status()
                    poll_result = poll_response.json()

                    if poll_result.get('code') != 0:
                        raise Exception(
                            f"轮询错误: {poll_result.get('msg', '未知错误')}"
                        )

                    data = poll_result.get('data', {})
                    status = data.get('status')

                    if status == 'succeeded':
                        # 成功，返回图片URL
                        results = data.get('results', [])
                        if results and len(results) > 0:
                            image_url = results[0].get('url')
                            logger.info(
                                'Image generated successfully',
                                task_id=task_id,
                                image_url=image_url
                            )
                            return {
                                'url': image_url,
                                'task_id': task_id,
                                'status': 'succeeded'
                            }
                        else:
                            # 兼容旧格式
                            image_url = data.get('url')
                            if image_url:
                                logger.info(
                                    'Image generated successfully',
                                    task_id=task_id,
                                    image_url=image_url
                                )
                                return {
                                    'url': image_url,
                                    'task_id': task_id,
                                    'status': 'succeeded'
                                }
                            raise Exception('生成成功但未返回图片URL')

                    elif status == 'failed':
                        # 失败
                        failure_reason = data.get('failure_reason', '')
                        error = data.get('error', '')
                        error_msg = (
                            f"生成失败: {failure_reason}"
                            if failure_reason
                            else f"生成失败: {error}"
                        )
                        logger.error(
                            'Image generation failed',
                            task_id=task_id,
                            failure_reason=failure_reason,
                            error=error
                        )
                        raise Exception(error_msg)

                    # 继续轮询
                    logger.debug(
                        'Polling image generation status',
                        task_id=task_id,
                        status=status,
                        progress=data.get('progress', 0)
                    )

                # 超时
                raise Exception('图片生成超时')

        except httpx.HTTPStatusError as e:
            logger.error(
                'HTTP error in image generation',
                status_code=e.response.status_code,
                error=str(e)
            )
            raise Exception(f'HTTP错误: {e.response.status_code}')
        except httpx.RequestError as e:
            logger.error('Request error in image generation', error=str(e))
            raise Exception(f'请求错误: {str(e)}')
        except Exception as e:
            logger.error('Error in image generation', error=str(e))
            raise

    async def generate_image_jimeng(
        self,
        prompt: str,
        aspect_ratio: str = '1:1',
        quality: Optional[str] = None,
        reference_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用火山即梦模型生成图片.

        Args:
            prompt: 提示词
            aspect_ratio: 图像比例（1:1, 16:9, 9:16等）
            quality: 清晰度（1K, 2K, 4K）
            reference_image_url: 参考图片URL（可选）

        Returns:
            包含图片URL的字典

        Raises:
            Exception: API调用失败
        """
        # 定义质量对应的尺寸倍数
        quality_multipliers = {
            '1K': 1.0,
            '2K': 1.5,
            '4K': 2.0
        }
        multiplier = quality_multipliers.get(quality, 1.0) if quality else 1.0
        
        # 转换aspect_ratio为size格式（基础尺寸）
        base_size_map = {
            '1:1': (1024, 1024),
            '16:9': (1920, 1080),
            '9:16': (1080, 1920),
            '4:3': (1024, 768),
            '3:4': (768, 1024),
            '3:2': (1536, 1024),
            '2:3': (1024, 1536),
            '5:4': (1280, 1024),
            '4:5': (1024, 1280),
            '21:9': (2560, 1080)
        }
        base_width, base_height = base_size_map.get(aspect_ratio, (1024, 1024))
        
        # 根据质量调整尺寸
        width = int(base_width * multiplier)
        height = int(base_height * multiplier)
        size = f"{width}x{height}"

        # 准备参考图列表
        reference_images: Optional[List[str]] = None
        if reference_image_url:
            reference_images = [reference_image_url]

        # 调用即梦服务
        image_url = await volc_jimeng_service.generate_image(
            prompt=prompt,
            size=size,
            reference_image_urls=reference_images
        )

        return {
            'url': image_url,
            'status': 'succeeded'
        }

    async def generate_image(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = 'auto',
        quality: str = '720p',
        reference_image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成图片（根据模型类型选择对应的API）.

        Args:
            prompt: 提示词
            model: 模型名称 (jimeng_t2i_v40, nano-banana-fast, nano-banana, sora-image)
            aspect_ratio: 图像比例
            quality: 清晰度
            reference_image_url: 参考图片URL（可选，用于提高一致性）

        Returns:
            包含图片URL的字典

        Raises:
            Exception: API调用失败
        """
        if model == 'jimeng_t2i_v40':
            return await self.generate_image_jimeng(
                prompt, aspect_ratio, quality, reference_image_url
            )
        elif model in ['nano-banana-fast', 'nano-banana']:
            return await self.generate_image_nano_banana(
                prompt, model, aspect_ratio, quality, reference_image_url
            )
        elif model == 'sora-image':
            # Sora Image 暂不支持参考图片
            return await self.generate_image_sora(
                prompt, aspect_ratio, quality
            )
        else:
            raise Exception(f'不支持的模型: {model}')


# 创建全局图片生成服务实例
image_generation_service = ImageGenerationService()

