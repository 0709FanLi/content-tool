"""
关键帧生成服务
处理关键帧的生成、更新、上传等操作
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import structlog

from src.models.tables.keyframe import Keyframe, KeyframeStatus
from src.models.tables.script import Script
from src.models.database import async_session_maker
from src.services.image_generation_service import image_generation_service
from src.services.oss_service import oss_service
from src.utils.script_parser import (
    parse_script,
    extract_prompt_for_segment,
    ScriptSegment
)
from src.utils.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)

STALE_KEYFRAME_TIMEOUT = timedelta(minutes=5)


class KeyframeService:
    """关键帧生成服务类."""

    def __init__(self, db: AsyncSession):
        """初始化关键帧服务.

        Args:
            db: 数据库会话
        """
        self.db = db

    async def generate_keyframes(
        self,
        script_id: int,
        model: str,
        aspect_ratio: str,
        quality: Optional[str]
    ) -> List[Keyframe]:
        """批量生成关键帧（异步后台任务）.

        Args:
            script_id: 脚本ID
            model: 图片生成模型
            aspect_ratio: 图像比例
            quality: 清晰度

        Returns:
            关键帧列表

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

        if not script.content:
            raise ValidationError('脚本内容为空')

        # 解析脚本段落
        segments = parse_script(script.content)

        if not segments:
            raise ValidationError('脚本中没有找到有效段落')

        # 删除该脚本的所有旧关键帧
        await self.db.execute(
            delete(Keyframe).where(Keyframe.script_id == script_id)
        )
        await self.db.commit()
        
        logger.info(
            'Old keyframes deleted',
            script_id=script_id
        )

        # 创建关键帧记录（状态为generating）
        # 注意：创建顺序非常重要，必须按照生成顺序创建，以确保串行生成时参考图片的顺序正确
        keyframes: List[Keyframe] = []

        # 提取普通段落（不包括第0帧）
        normal_segments = [s for s in segments if not s.is_frame_0]
        
        if not normal_segments:
            raise ValidationError('脚本中没有有效的段落')

        # 1. 首先创建第0帧（如果存在）- 命名为 segment_0_first_frame
        frame_0_segment = next((s for s in segments if s.is_frame_0), None)
        if frame_0_segment:
            frame_0_keyframe = Keyframe(
                script_id=script_id,
                segment_id=f'{normal_segments[0].segment_id}_first_frame',  # 使用第一个普通段落的ID加上_first_frame
                prompt=frame_0_segment.content,  # 直接使用第0帧的内容作为提示词
                status=KeyframeStatus.GENERATING
            )
            self.db.add(frame_0_keyframe)
            keyframes.append(frame_0_keyframe)
            logger.info('Frame 0 keyframe created', 
                       segment_id=frame_0_keyframe.segment_id,
                       prompt_preview=frame_0_segment.content[:50])

        # 2. 然后按顺序创建每段的关键帧（跳过第0帧）
        for segment in segments:
            # 跳过第0帧
            if segment.is_frame_0:
                continue
                
            keyframe = Keyframe(
                script_id=script_id,
                segment_id=segment.segment_id,
                prompt=segment.content,  # 使用段落的原始内容作为提示词
                status=KeyframeStatus.GENERATING
            )
            self.db.add(keyframe)
            keyframes.append(keyframe)

        await self.db.commit()

        # 保存关键帧ID列表，用于后台任务
        keyframe_ids = [kf.id for kf in keyframes]

        # 启动后台任务异步生成图片
        asyncio.create_task(
            self._generate_keyframes_background(
                keyframe_ids, segments, model, aspect_ratio, quality
            )
        )

        logger.info(
            'Keyframes generation started',
            script_id=script_id,
            total_keyframes=len(keyframes)
        )

        return keyframes

    async def _generate_keyframes_background(
        self,
        keyframe_ids: List[int],
        segments: List[ScriptSegment],
        model: str,
        aspect_ratio: str,
        quality: Optional[str]
    ) -> None:
        """后台任务：串行生成关键帧图片，每帧参考前一帧提高一致性.

        Args:
            keyframe_ids: 关键帧ID列表
            segments: 脚本段落列表
            model: 图片生成模型
            aspect_ratio: 图像比例
            quality: 清晰度
        """
        try:
            # 创建段落映射
            segment_map = {seg.segment_id: seg for seg in segments}

            # 串行生成关键帧，每一帧参考前一帧
            previous_image_url: Optional[str] = None
            
            for i, keyframe_id in enumerate(keyframe_ids):
                logger.info(
                    'Generating keyframe sequentially',
                    current=i + 1,
                    total=len(keyframe_ids),
                    keyframe_id=keyframe_id,
                    has_reference=previous_image_url is not None
                )
                
                # 生成当前关键帧，传入前一帧的图片URL作为参考
                result_url = await self._generate_single_keyframe_image_with_session(
                    keyframe_id, segment_map, model, aspect_ratio, quality, previous_image_url
                )
                
                # 如果生成成功，更新 previous_image_url 供下一帧使用
                if result_url:
                    previous_image_url = result_url
                    logger.info(
                        'Keyframe generated, will use as reference for next frame',
                        keyframe_id=keyframe_id,
                        reference_url=previous_image_url
                    )
                else:
                    logger.warning(
                        'Keyframe generation failed, continuing without reference',
                        keyframe_id=keyframe_id
                    )
                    
        except Exception as e:
            logger.error(
                'Error in background keyframe generation',
                error=str(e),
                exc_info=True
            )

    async def _generate_single_keyframe_image_with_session(
        self,
        keyframe_id: int,
        segment_map: dict,
        model: str,
        aspect_ratio: str,
        quality: Optional[str],
        reference_image_url: Optional[str] = None
    ) -> Optional[str]:
        """生成单个关键帧图片（使用独立的数据库会话）.

        Args:
            keyframe_id: 关键帧ID
            segment_map: 段落映射
            model: 图片生成模型
            aspect_ratio: 图像比例
            quality: 清晰度
            reference_image_url: 参考图片URL（可选）
            
        Returns:
            生成的图片URL，失败时返回None
        """
        # 为每个任务创建独立的数据库会话
        async with async_session_maker() as db:
            try:
                # 查询关键帧对象
                result = await db.execute(
                    select(Keyframe).where(Keyframe.id == keyframe_id)
                )
                keyframe = result.scalar_one_or_none()
                
                if not keyframe:
                    logger.error(
                        'Keyframe not found',
                        keyframe_id=keyframe_id
                    )
                    return None

                # 判断是否为旧格式的第一帧（兼容旧数据）
                is_old_first_frame = keyframe.segment_id.endswith('_first_frame')

                # 生成提示词
                # 注意：所有关键帧的prompt在创建时就已经正确设置了
                # segment_X_first_frame -> 使用第0帧的内容
                # segment_0 -> 使用segment_0的内容
                # 因此这里直接使用已保存的prompt即可，不需要重新提取
                
                if keyframe.prompt:
                    # 如果关键帧已有prompt，直接使用（这是最常见的情况）
                    prompt = keyframe.prompt
                elif is_old_first_frame:
                    # 兼容旧数据：如果关键帧没有prompt，尝试从segment提取
                    base_segment_id = keyframe.segment_id.replace('_first_frame', '')
                    segment = segment_map.get(base_segment_id)
                    if segment:
                        prompt = extract_prompt_for_segment(segment, is_old_first_frame)
                    else:
                        prompt = ''
                        logger.warning(
                            'No prompt found for old format keyframe',
                            keyframe_id=keyframe_id,
                            segment_id=keyframe.segment_id
                        )
                else:
                    # 兜底：使用空prompt（这种情况不应该发生）
                    prompt = ''
                    logger.warning(
                        'No prompt found for keyframe',
                        keyframe_id=keyframe_id,
                        segment_id=keyframe.segment_id
                    )

                # 调用图片生成API（传入参考图URL以提高一致性）
                logger.info(
                    'Calling image generation API',
                    keyframe_id=keyframe_id,
                    segment_id=keyframe.segment_id,
                    has_reference=reference_image_url is not None,
                    prompt_preview=prompt[:100] if prompt else ''
                )
                
                result = await image_generation_service.generate_image(
                    prompt=prompt,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    quality=quality,
                    reference_image_url=reference_image_url  # 传入参考图URL
                )

                image_url = result.get('url')
                if not image_url:
                    raise Exception('图片生成成功但未返回URL')

                # 上传到OSS
                from io import BytesIO
                import httpx

                async with httpx.AsyncClient() as client:
                    image_response = await client.get(image_url)
                    image_response.raise_for_status()
                    image_data = image_response.content

                # 生成文件名
                filename = f'keyframe_{keyframe.id}.jpg'

                # 上传到OSS
                upload_result = await oss_service.upload_from_url(
                    url=image_url,
                    filename=filename,
                    category='keyframes'
                )

                # 重新查询关键帧以更新状态（使用当前会话）
                result = await db.execute(
                    select(Keyframe).where(Keyframe.id == keyframe_id)
                )
                keyframe_to_update = result.scalar_one_or_none()
                
                if keyframe_to_update:
                    keyframe_to_update.image_url = upload_result['url']
                    keyframe_to_update.prompt = prompt
                    keyframe_to_update.status = KeyframeStatus.COMPLETED
                    keyframe_to_update.error_message = None
                    await db.commit()

                    logger.info(
                        'Keyframe image generated successfully',
                        keyframe_id=keyframe_id,
                        segment_id=keyframe_to_update.segment_id,
                        image_url=upload_result['url']
                    )
                    
                    # 返回生成的图片URL供下一帧参考
                    return upload_result['url']
                else:
                    logger.error(
                        'Keyframe not found when updating',
                        keyframe_id=keyframe_id
                    )
                    return None

            except Exception as e:
                # 失败即停止，更新状态为failed
                logger.error(
                    'Failed to generate keyframe image',
                    keyframe_id=keyframe_id,
                    error=str(e),
                    exc_info=True
                )

                try:
                    # 重新查询关键帧以更新状态
                    result = await db.execute(
                        select(Keyframe).where(Keyframe.id == keyframe_id)
                    )
                    keyframe_to_update = result.scalar_one_or_none()
                    
                    if keyframe_to_update:
                        keyframe_to_update.status = KeyframeStatus.FAILED
                        keyframe_to_update.error_message = str(e)
                        await db.commit()
                except Exception as commit_error:
                    logger.error(
                        'Failed to update keyframe status',
                        keyframe_id=keyframe_id,
                        error=str(commit_error),
                        exc_info=True
                    )
                
                return None

    async def regenerate_keyframe(
        self,
        keyframe_id: int,
        model: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None
    ) -> Keyframe:
        """重新生成单个关键帧.

        Args:
            keyframe_id: 关键帧ID
            model: 图片生成模型（可选，使用项目默认配置）
            aspect_ratio: 图像比例（可选）
            quality: 清晰度（可选）

        Returns:
            更新后的关键帧

        Raises:
            NotFoundError: 关键帧不存在
        """
        result = await self.db.execute(
            select(Keyframe).where(Keyframe.id == keyframe_id)
        )
        keyframe = result.scalar_one_or_none()

        if not keyframe:
            raise NotFoundError(f'关键帧不存在: {keyframe_id}')

        # 获取脚本以获取默认配置
        script_result = await self.db.execute(
            select(Script).where(Script.id == keyframe.script_id)
        )
        script = script_result.scalar_one_or_none()

        # 使用提供的参数或默认配置
        if not model and script:
            # 从项目获取默认模型配置（需要扩展Script或Project模型）
            model = 'jimeng_t2i_v40'  # 默认值：火山即梦4.0

        if not aspect_ratio:
            aspect_ratio = 'auto'

        if not quality:
            quality = '720p'

        # 更新状态为generating
        keyframe.status = KeyframeStatus.GENERATING
        keyframe.error_message = None
        await self.db.commit()

        # 保存关键帧ID和参数，用于后台任务（在提交后获取）
        saved_keyframe_id = keyframe.id
        saved_model = model
        saved_aspect_ratio = aspect_ratio
        saved_quality = quality

        # 启动后台任务重新生成（使用 ensure_future 确保任务正确启动）
        # 注意：必须在数据库提交后创建任务，避免会话问题
        try:
            task = asyncio.ensure_future(
                self._regenerate_keyframe_background(
                    saved_keyframe_id, saved_model, saved_aspect_ratio, saved_quality
                )
            )
            # 添加错误回调，确保任务异常能被记录
            task.add_done_callback(
                lambda t: logger.error(
                    'Background regenerate task failed',
                    error=str(t.exception()) if t.exception() else 'Unknown error',
                    keyframe_id=saved_keyframe_id
                ) if t.exception() else None
            )
        except Exception as e:
            logger.error(
                'Failed to start background regenerate task',
                error=str(e),
                keyframe_id=saved_keyframe_id,
                exc_info=True
            )
            # 如果任务启动失败，更新状态为失败
            keyframe.status = KeyframeStatus.FAILED
            keyframe.error_message = f'启动后台任务失败: {str(e)}'
            await self.db.commit()

        return keyframe

    async def _regenerate_keyframe_background(
        self,
        keyframe_id: int,
        model: str,
        aspect_ratio: str,
        quality: str
    ) -> None:
        """后台任务：重新生成关键帧图片.

        Args:
            keyframe_id: 关键帧ID
            model: 图片生成模型
            aspect_ratio: 图像比例
            quality: 清晰度
        """
        # 创建新的数据库会话用于后台任务
        async with async_session_maker() as db:
            try:
                # 重新查询关键帧对象（使用新的会话）
                result = await db.execute(
                    select(Keyframe).where(Keyframe.id == keyframe_id)
                )
                keyframe = result.scalar_one_or_none()

                if not keyframe:
                    logger.error(
                        'Keyframe not found for regeneration',
                        keyframe_id=keyframe_id
                    )
                    return

                prompt = keyframe.prompt or ''

                # 调用图片生成API
                result = await image_generation_service.generate_image(
                    prompt=prompt,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    quality=quality
                )

                image_url = result.get('url')
                if not image_url:
                    raise Exception('图片生成成功但未返回URL')

                # 上传到OSS
                filename = f'keyframe_{keyframe.id}.jpg'
                upload_result = await oss_service.upload_from_url(
                    url=image_url,
                    filename=filename,
                    category='keyframes'
                )

                # 更新关键帧记录（使用新的数据库会话）
                keyframe.image_url = upload_result['url']
                keyframe.status = KeyframeStatus.COMPLETED
                keyframe.error_message = None

                await db.commit()

                logger.info(
                    'Keyframe regenerated successfully',
                    keyframe_id=keyframe.id,
                    image_url=upload_result['url']
                )

            except Exception as e:
                logger.error(
                    'Failed to regenerate keyframe',
                    keyframe_id=keyframe_id,
                    error=str(e),
                    exc_info=True
                )

                try:
                    # 重新查询关键帧以更新状态
                    result = await db.execute(
                        select(Keyframe).where(Keyframe.id == keyframe_id)
                    )
                    keyframe_to_update = result.scalar_one_or_none()
                    
                    if keyframe_to_update:
                        keyframe_to_update.status = KeyframeStatus.FAILED
                        keyframe_to_update.error_message = str(e)
                        await db.commit()
                except Exception as commit_error:
                    logger.error(
                        'Failed to update keyframe status',
                        keyframe_id=keyframe_id,
                        error=str(commit_error),
                        exc_info=True
                    )

    async def update_keyframe_prompt(
        self, keyframe_id: int, prompt: str
    ) -> Keyframe:
        """更新关键帧提示词.

        Args:
            keyframe_id: 关键帧ID
            prompt: 新的提示词

        Returns:
            更新后的关键帧

        Raises:
            NotFoundError: 关键帧不存在
        """
        result = await self.db.execute(
            select(Keyframe).where(Keyframe.id == keyframe_id)
        )
        keyframe = result.scalar_one_or_none()

        if not keyframe:
            raise NotFoundError(f'关键帧不存在: {keyframe_id}')

        keyframe.prompt = prompt
        await self.db.commit()

        logger.info(
            'Keyframe prompt updated',
            keyframe_id=keyframe_id,
            prompt=prompt[:50]  # 只记录前50个字符
        )

        return keyframe

    async def upload_keyframe_image(
        self, keyframe_id: int, file_data: bytes, filename: str
    ) -> Keyframe:
        """上传本地图片替换关键帧.

        Args:
            keyframe_id: 关键帧ID
            file_data: 文件数据
            filename: 文件名

        Returns:
            更新后的关键帧

        Raises:
            NotFoundError: 关键帧不存在
        """
        from io import BytesIO

        result = await self.db.execute(
            select(Keyframe).where(Keyframe.id == keyframe_id)
        )
        keyframe = result.scalar_one_or_none()

        if not keyframe:
            raise NotFoundError(f'关键帧不存在: {keyframe_id}')

        # 上传到OSS
        file_stream = BytesIO(file_data)
        upload_result = oss_service.upload_file(
            file_data=file_stream,
            filename=filename,
            category='keyframes',
            content_type='image/jpeg'
        )

        # 更新关键帧记录
        keyframe.image_url = upload_result['url']
        keyframe.status = KeyframeStatus.COMPLETED
        keyframe.error_message = None

        await self.db.commit()

        logger.info(
            'Keyframe image uploaded',
            keyframe_id=keyframe_id,
            image_url=upload_result['url']
        )

        return keyframe

    async def get_keyframes_by_script_id(
        self, script_id: int
    ) -> List[Keyframe]:
        """获取脚本的所有关键帧.

        Args:
            script_id: 脚本ID

        Returns:
            关键帧列表
        """
        result = await self.db.execute(
            select(Keyframe)
            .where(Keyframe.script_id == script_id)
            .order_by(Keyframe.created_at)
        )
        keyframes = result.scalars().all()

        await self._refresh_stale_keyframes(keyframes)

        return list(keyframes)

    async def _refresh_stale_keyframes(self, keyframes: List[Keyframe]) -> None:
        """将长时间未更新的关键帧标记为失败，避免持续轮询."""
        if not keyframes:
            return

        now = datetime.now(timezone.utc)
        has_updates = False

        for keyframe in keyframes:
            if keyframe.status != KeyframeStatus.GENERATING or not keyframe.updated_at:
                continue

            updated_at = keyframe.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)

            if now - updated_at > STALE_KEYFRAME_TIMEOUT:
                keyframe.status = KeyframeStatus.FAILED
                keyframe.error_message = '生成超时，请重新生成关键帧'
                has_updates = True
                logger.warning(
                    'Keyframe generation timed out',
                    keyframe_id=keyframe.id,
                    script_id=keyframe.script_id,
                    segment_id=keyframe.segment_id,
                    last_updated=updated_at.isoformat()
                )

        if has_updates:
            await self.db.commit()

    async def get_keyframe_by_id(self, keyframe_id: int) -> Optional[Keyframe]:
        """根据ID获取关键帧.

        Args:
            keyframe_id: 关键帧ID

        Returns:
            关键帧对象，如果不存在返回None
        """
        result = await self.db.execute(
            select(Keyframe).where(Keyframe.id == keyframe_id)
        )
        return result.scalar_one_or_none()

