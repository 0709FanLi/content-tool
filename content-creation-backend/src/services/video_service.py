"""
视频生成服务
处理视频的生成、更新、导出等操作
"""

import asyncio
import httpx
import structlog
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from io import BytesIO
import zipfile
import os
from datetime import datetime, timedelta

from src.models.tables.video_segment import VideoSegment, VideoStatus
from src.models.tables.keyframe import Keyframe, KeyframeStatus
from src.models.tables.script import Script
from src.models.database import async_session_maker
from src.config.settings import settings
from src.services.oss_service import oss_service
from src.utils.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class VideoService:
    """视频生成服务类."""

    def __init__(self, db: AsyncSession):
        """初始化视频服务.

        Args:
            db: 数据库会话
        """
        self.db = db
        self.base_url = settings.image_generation_base_url
        self.api_key = settings.grsai_key

    async def generate_videos(
        self,
        script_id: int,
        model: str = "veo3.1-fast",
        aspect_ratio: str = "16:9",
        duration: float = 6.0
    ) -> List[VideoSegment]:
        """批量生成视频（异步后台任务）.

        根据脚本的关键帧，使用首尾帧方法生成N段视频（方案B）：
        - 第1段：segment_0_first_frame -> segment_0
        - 第2段：segment_0 -> segment_1
        - ...
        - 第N段：segment_(n-2) -> segment_(n-1)
        注意：不使用last_frame

        Args:
            script_id: 脚本ID
            model: 视频生成模型 (默认veo3.1-fast)
            aspect_ratio: 视频比例
            duration: 视频时长（秒，默认6s）

        Returns:
            视频片段列表

        Raises:
            NotFoundError: 脚本不存在
            ValidationError: 参数验证失败
        """
        # 获取脚本
        result = await self.db.execute(
            select(Script).where(Script.id == script_id)
        )
        script = result.scalar_one_or_none()

        if not script:
            raise NotFoundError(f'脚本不存在: {script_id}')

        # 删除该脚本的所有旧视频片段
        await self.db.execute(
            delete(VideoSegment).where(VideoSegment.script_id == script_id)
        )
        await self.db.commit()
        
        logger.info(
            'Old video segments deleted',
            script_id=script_id
        )

        # 获取脚本的所有关键帧，按segment_id排序
        keyframes_result = await self.db.execute(
            select(Keyframe)
            .where(Keyframe.script_id == script_id)
            .where(Keyframe.status == KeyframeStatus.COMPLETED)
            .order_by(Keyframe.segment_id)
        )
        keyframes = list(keyframes_result.scalars().all())

        if not keyframes:
            raise ValidationError('脚本没有已完成的关键帧')

        # 按segment_id分类关键帧
        keyframe_map: Dict[str, Keyframe] = {kf.segment_id: kf for kf in keyframes}

        # 提取普通段落（不包含_first_frame和_last_frame）
        normal_segments = [
            kf for kf in keyframes
            if not kf.segment_id.endswith('_first_frame')
            and not kf.segment_id.endswith('_last_frame')
        ]

        if not normal_segments:
            raise ValidationError('脚本没有有效的段落关键帧')

        # 构建视频片段配置（方案B：生成n个视频，不使用last_frame）
        video_configs = []
        segment_index = 0

        # 第一段：first_frame -> segment_0
        first_segment = normal_segments[0]
        first_frame_key = f'{first_segment.segment_id}_first_frame'
        if first_frame_key not in keyframe_map:
            raise ValidationError(f'缺少首帧关键帧: {first_frame_key}')
        
        first_frame = keyframe_map[first_frame_key]
        video_configs.append({
            'segment_index': segment_index,
            'first_frame_url': first_frame.image_url,
            'last_frame_url': first_segment.image_url,
            'prompt': first_segment.prompt or '',
        })
        segment_index += 1

        # 后续段落：segment_i -> segment_i+1
        # 生成 n-1 个视频（从 segment_0 到 segment_1, segment_1 到 segment_2, ...）
        for i in range(len(normal_segments) - 1):
            current_segment = normal_segments[i]
            next_segment = normal_segments[i + 1]
            video_configs.append({
                'segment_index': segment_index,
                'first_frame_url': current_segment.image_url,
                'last_frame_url': next_segment.image_url,
                'prompt': next_segment.prompt or '',
            })
            segment_index += 1

        # 创建视频片段记录
        video_segments: List[VideoSegment] = []
        for config in video_configs:
            video_segment = VideoSegment(
                script_id=script_id,
                segment_index=config['segment_index'],
                first_frame_url=config['first_frame_url'],
                last_frame_url=config['last_frame_url'],
                prompt=config['prompt'],
                model=model,
                aspect_ratio=aspect_ratio,
                duration=duration,
                status=VideoStatus.GENERATING
            )
            self.db.add(video_segment)
            video_segments.append(video_segment)

        await self.db.commit()

        # 保存视频片段ID列表，用于后台任务
        video_segment_ids = [vs.id for vs in video_segments]

        # 启动后台任务异步生成视频
        asyncio.create_task(
            self._generate_videos_background(video_segment_ids)
        )

        logger.info(
            'Videos generation started',
            script_id=script_id,
            total_segments=len(video_segments),
            model=model
        )

        return video_segments

    async def _generate_videos_background(
        self, video_segment_ids: List[int]
    ) -> None:
        """后台任务：异步生成视频.

        Args:
            video_segment_ids: 视频片段ID列表
        """
        try:
            # 为每个视频片段创建独立的任务
            tasks = []
            for video_segment_id in video_segment_ids:
                task = self._generate_single_video_with_session(video_segment_id)
                tasks.append(task)

            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(
                'Error in background video generation',
                error=str(e),
                exc_info=True
            )

    async def _generate_single_video_with_session(
        self, video_segment_id: int
    ) -> None:
        """生成单个视频片段（使用独立的数据库会话）.

        Args:
            video_segment_id: 视频片段ID
        """
        async with async_session_maker() as db:
            try:
                # 查询视频片段对象
                result = await db.execute(
                    select(VideoSegment).where(VideoSegment.id == video_segment_id)
                )
                video_segment = result.scalar_one_or_none()

                if not video_segment:
                    logger.error(
                        'Video segment not found',
                        video_segment_id=video_segment_id
                    )
                    return

                # 调用视频生成API（获取第三方URL）
                third_party_video_url = await self._call_video_generation_api(
                    model=video_segment.model,
                    prompt=video_segment.prompt,
                    first_frame_url=video_segment.first_frame_url,
                    last_frame_url=video_segment.last_frame_url,
                    aspect_ratio=video_segment.aspect_ratio,
                    duration=video_segment.duration
                )

                logger.info(
                    'Video generated from API',
                    video_segment_id=video_segment_id,
                    third_party_url=third_party_video_url
                )

                # 转存视频到OSS
                filename = f'video_segment_{video_segment_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.mp4'
                
                oss_upload_result = await oss_service.upload_from_url(
                    url=third_party_video_url,
                    filename=filename,
                    category='videos'
                )

                oss_video_url = oss_upload_result['url']

                logger.info(
                    'Video uploaded to OSS',
                    video_segment_id=video_segment_id,
                    oss_url=oss_video_url,
                    oss_object_key=oss_upload_result['object_key']
                )

                # 更新视频片段记录（使用OSS URL）
                video_segment.video_url = oss_video_url
                video_segment.status = VideoStatus.COMPLETED
                video_segment.error_message = None

                await db.commit()

                logger.info(
                    'Video segment completed successfully',
                    video_segment_id=video_segment_id,
                    video_url=oss_video_url
                )

            except Exception as e:
                logger.error(
                    'Failed to generate video',
                    video_segment_id=video_segment_id,
                    error=str(e),
                    exc_info=True
                )

                try:
                    # 重新查询视频片段以更新状态
                    result = await db.execute(
                        select(VideoSegment).where(VideoSegment.id == video_segment_id)
                    )
                    video_segment_to_update = result.scalar_one_or_none()

                    if video_segment_to_update:
                        video_segment_to_update.status = VideoStatus.FAILED
                        video_segment_to_update.error_message = str(e)
                        await db.commit()
                except Exception as commit_error:
                    logger.error(
                        'Failed to update video segment status',
                        video_segment_id=video_segment_id,
                        error=str(commit_error),
                        exc_info=True
                    )

    async def _call_video_generation_api(
        self,
        model: str,
        prompt: str,
        first_frame_url: Optional[str],
        last_frame_url: Optional[str],
        aspect_ratio: str,
        duration: float
    ) -> str:
        """调用第三方视频生成API.

        Args:
            model: 模型名称
            prompt: 提示词
            first_frame_url: 首帧URL
            last_frame_url: 尾帧URL
            aspect_ratio: 视频比例
            duration: 时长

        Returns:
            生成的视频URL

        Raises:
            Exception: API调用失败
        """
        if not self.api_key:
            raise Exception('GRSAI API密钥未配置')

        # 判断使用哪个API
        if model.startswith('sora'):
            return await self._call_sora_api(
                model, prompt, last_frame_url, aspect_ratio, duration
            )
        elif model.startswith('veo'):
            return await self._call_veo_api(
                model, prompt, first_frame_url, last_frame_url, aspect_ratio
            )
        else:
            raise Exception(f'不支持的模型: {model}')

    async def _call_sora_api(
        self,
        model: str,
        prompt: str,
        reference_url: Optional[str],
        aspect_ratio: str,
        duration: float
    ) -> str:
        """调用Sora API生成视频.

        Args:
            model: 模型名称
            prompt: 提示词
            reference_url: 参考图片URL（使用尾帧）
            aspect_ratio: 视频比例
            duration: 时长

        Returns:
            视频URL
        """
        url = f'{self.base_url}/v1/video/sora-video'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        payload = {
            'model': model,
            'prompt': prompt,
            'aspectRatio': aspect_ratio,
            'duration': int(duration),
            'size': 'small',
            'shutProgress': True,
            'webHook': '-1'  # 使用轮询方式
        }

        if reference_url:
            payload['url'] = reference_url

        async with httpx.AsyncClient(timeout=300.0) as client:
            # 提交任务
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get('code') != 0:
                raise Exception(f"Sora API错误: {result.get('msg')}")

            task_id = result['data']['id']

            # 轮询获取结果
            result_url = f'{self.base_url}/v1/draw/result'
            max_attempts = 60  # 最多轮询60次（5分钟）
            attempt = 0

            while attempt < max_attempts:
                await asyncio.sleep(5)  # 每5秒轮询一次

                result_response = await client.post(
                    result_url,
                    json={'id': task_id},
                    headers=headers
                )
                result_response.raise_for_status()
                result_data = result_response.json()

                if result_data.get('code') != 0:
                    raise Exception(f"获取结果失败: {result_data.get('msg')}")

                data = result_data['data']
                status = data.get('status')

                if status == 'succeeded':
                    results = data.get('results', [])
                    if results and results[0].get('url'):
                        return results[0]['url']
                    raise Exception('视频生成成功但未返回URL')
                elif status == 'failed':
                    error = data.get('error', '未知错误')
                    raise Exception(f'视频生成失败: {error}')

                attempt += 1

            raise Exception('视频生成超时')

    async def _call_veo_api(
        self,
        model: str,
        prompt: str,
        first_frame_url: Optional[str],
        last_frame_url: Optional[str],
        aspect_ratio: str
    ) -> str:
        """调用Veo API生成视频.

        Args:
            model: 模型名称
            prompt: 提示词（需要是英文）
            first_frame_url: 首帧URL
            last_frame_url: 尾帧URL
            aspect_ratio: 视频比例

        Returns:
            视频URL
        """
        url = f'{self.base_url}/v1/video/veo'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        payload = {
            'model': model,
            'prompt': prompt,
            'aspectRatio': aspect_ratio,
            'shutProgress': True,
            'webHook': '-1'  # 使用轮询方式
        }

        if first_frame_url:
            payload['firstFrameUrl'] = first_frame_url
        if last_frame_url:
            payload['lastFrameUrl'] = last_frame_url

        async with httpx.AsyncClient(timeout=300.0) as client:
            # 提交任务
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if result.get('code') != 0:
                raise Exception(f"Veo API错误: {result.get('msg')}")

            task_id = result['data']['id']

            # 轮询获取结果
            result_url = f'{self.base_url}/v1/draw/result'
            max_attempts = 60  # 最多轮询60次（5分钟）
            attempt = 0

            while attempt < max_attempts:
                await asyncio.sleep(5)  # 每5秒轮询一次

                result_response = await client.post(
                    result_url,
                    json={'id': task_id},
                    headers=headers
                )
                result_response.raise_for_status()
                result_data = result_response.json()

                if result_data.get('code') != 0:
                    raise Exception(f"获取结果失败: {result_data.get('msg')}")

                data = result_data['data']
                status = data.get('status')

                if status == 'succeeded':
                    video_url = data.get('url')
                    if video_url:
                        return video_url
                    raise Exception('视频生成成功但未返回URL')
                elif status == 'failed':
                    error = data.get('error', '未知错误')
                    raise Exception(f'视频生成失败: {error}')

                attempt += 1

            raise Exception('视频生成超时')

    async def get_video_segments_by_script(
        self, script_id: int
    ) -> List[VideoSegment]:
        """获取脚本的所有视频片段.

        Args:
            script_id: 脚本ID

        Returns:
            视频片段列表
        """
        result = await self.db.execute(
            select(VideoSegment)
            .where(VideoSegment.script_id == script_id)
            .order_by(VideoSegment.segment_index)
        )
        return list(result.scalars().all())

    async def regenerate_video_segment(
        self,
        video_segment_id: int,
        model: Optional[str] = None
    ) -> VideoSegment:
        """重新生成单个视频片段.

        Args:
            video_segment_id: 视频片段ID
            model: 模型（可选，使用原模型）

        Returns:
            更新后的视频片段

        Raises:
            NotFoundError: 视频片段不存在
        """
        result = await self.db.execute(
            select(VideoSegment).where(VideoSegment.id == video_segment_id)
        )
        video_segment = result.scalar_one_or_none()

        if not video_segment:
            raise NotFoundError(f'视频片段不存在: {video_segment_id}')

        # 使用新模型或原模型
        if model:
            video_segment.model = model

        # 更新状态为generating
        video_segment.status = VideoStatus.GENERATING
        video_segment.error_message = None
        video_segment.video_url = None

        await self.db.commit()

        # 启动后台任务重新生成
        asyncio.create_task(
            self._generate_single_video_with_session(video_segment_id)
        )

        return video_segment

    async def export_videos(self, script_id: int) -> Dict[str, Any]:
        """导出脚本的所有视频为zip文件.

        Args:
            script_id: 脚本ID

        Returns:
            包含下载URL和过期时间的字典

        Raises:
            NotFoundError: 脚本不存在或没有视频
        """
        # 获取所有已完成的视频片段
        result = await self.db.execute(
            select(VideoSegment)
            .where(VideoSegment.script_id == script_id)
            .where(VideoSegment.status == VideoStatus.COMPLETED)
            .order_by(VideoSegment.segment_index)
        )
        video_segments = list(result.scalars().all())

        if not video_segments:
            raise NotFoundError('没有已完成的视频片段可以导出')

        # 创建ZIP文件
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 下载每个视频并添加到ZIP
            async with httpx.AsyncClient(timeout=60.0) as client:
                for idx, segment in enumerate(video_segments):
                    if not segment.video_url:
                        continue

                    try:
                        # 下载视频
                        response = await client.get(segment.video_url)
                        response.raise_for_status()
                        video_data = response.content

                        # 添加到ZIP，文件名格式：segment_0.mp4
                        filename = f'segment_{segment.segment_index}.mp4'
                        zip_file.writestr(filename, video_data)

                        logger.info(
                            'Video added to zip',
                            segment_id=segment.id,
                            filename=filename
                        )
                    except Exception as e:
                        logger.error(
                            'Failed to download video for export',
                            segment_id=segment.id,
                            error=str(e)
                        )

        # 上传ZIP到OSS
        zip_buffer.seek(0)
        filename = f'videos_script_{script_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}.zip'

        upload_result = oss_service.upload_file(
            file_data=zip_buffer,
            filename=filename,
            category='exports',
            content_type='application/zip'
        )

        logger.info(
            'Videos exported successfully',
            script_id=script_id,
            zip_url=upload_result['url']
        )

        return {
            'download_url': upload_result['url'],
            'expires_in': 3600  # 1小时过期
        }

    @staticmethod
    def get_available_models() -> List[Dict[str, Any]]:
        """获取可用的视频生成模型列表.

        Returns:
            模型信息列表
        """
        return [
            {
                'id': 'sora-2',
                'name': 'Sora 2',
                'description': '支持单图参考，生成高质量视频',
                'supports_first_last_frame': False
            },
            {
                'id': 'veo3-fast',
                'name': 'Veo 3 Fast',
                'description': '快速生成，支持首尾帧控制',
                'supports_first_last_frame': True
            },
            {
                'id': 'veo3-pro',
                'name': 'Veo 3 Pro',
                'description': '专业级质量，支持首尾帧控制',
                'supports_first_last_frame': True
            },
            {
                'id': 'veo3.1-fast',
                'name': 'Veo 3.1 Fast',
                'description': '最新版本快速模式，支持首尾帧控制',
                'supports_first_last_frame': True
            },
            {
                'id': 'veo3.1-pro',
                'name': 'Veo 3.1 Pro',
                'description': '最新版本专业模式，支持首尾帧控制',
                'supports_first_last_frame': True
            }
        ]

