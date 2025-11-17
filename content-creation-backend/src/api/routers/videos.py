"""
视频管理路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import structlog

from src.models.database import get_db
from src.models.schemas.video import (
    GenerateVideoRequest,
    GenerateVideosResponse,
    VideoSegmentResponse,
    RegenerateVideoSegmentRequest,
    ExportVideosRequest,
    ExportVideosResponse,
    VideoModelsResponse,
    VideoModelInfo
)
from src.models.tables import User
from src.services.video_service import VideoService
from src.api.dependencies import get_current_active_user
from src.utils.exceptions import NotFoundError, ValidationError

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get('/models')
async def get_video_models(
    current_user: User = Depends(get_current_active_user)
):
    """获取可用的视频生成模型列表.

    Returns:
        模型列表（包装格式）
    """
    try:
        models = VideoService.get_available_models()
        
        model_infos = [
            VideoModelInfo(
                id=m['id'],
                name=m['name'],
                description=m['description'],
                supports_first_last_frame=m['supports_first_last_frame']
            )
            for m in models
        ]
        
        result = VideoModelsResponse(models=model_infos)
        
        return {
            "code": 200,
            "message": "success",
            "data": result.model_dump(by_alias=True)
        }
    except Exception as e:
        logger.error('获取视频模型列表失败', error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='获取视频模型列表失败'
        )


@router.post('/generate')
async def generate_videos(
    request: GenerateVideoRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """生成视频片段（异步）.

    Args:
        request: 生成视频请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        视频片段列表（状态为generating，包装格式）

    Raises:
        HTTPException: 生成失败
    """
    try:
        video_service = VideoService(db)
        video_segments = await video_service.generate_videos(
            script_id=request.script_id,
            model=request.model,
            aspect_ratio=request.aspect_ratio,
            duration=request.duration
        )

        # 转换为响应模型
        segment_responses = [
            VideoSegmentResponse(
                id=vs.id,
                script_id=vs.script_id,
                segment_index=vs.segment_index,
                first_frame_url=vs.first_frame_url,
                last_frame_url=vs.last_frame_url,
                prompt=vs.prompt,
                video_url=vs.video_url,
                model=vs.model,
                aspect_ratio=vs.aspect_ratio,
                status=vs.status,
                duration=vs.duration,
                error_message=vs.error_message,
                created_at=vs.created_at,
                updated_at=vs.updated_at
            )
            for vs in video_segments
        ]

        result = GenerateVideosResponse(
            video_segments=segment_responses,
            total_count=len(segment_responses)
        )

        return {
            "code": 200,
            "message": "success",
            "data": result.model_dump(by_alias=True)
        }

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error('生成视频失败', error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='生成视频失败'
        )


@router.get('/script/{script_id}')
async def get_video_segments_by_script(
    script_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取脚本的视频片段列表.

    Args:
        script_id: 脚本ID
        current_user: 当前用户
        db: 数据库会话

    Returns:
        视频片段列表（包装格式）

    Raises:
        HTTPException: 获取失败
    """
    try:
        video_service = VideoService(db)
        video_segments = await video_service.get_video_segments_by_script(
            script_id
        )

        # 转换为响应模型
        segment_responses = [
            VideoSegmentResponse(
                id=vs.id,
                script_id=vs.script_id,
                segment_index=vs.segment_index,
                first_frame_url=vs.first_frame_url,
                last_frame_url=vs.last_frame_url,
                prompt=vs.prompt,
                video_url=vs.video_url,
                model=vs.model,
                aspect_ratio=vs.aspect_ratio,
                status=vs.status,
                duration=vs.duration,
                error_message=vs.error_message,
                created_at=vs.created_at,
                updated_at=vs.updated_at
            )
            for vs in video_segments
        ]

        result = GenerateVideosResponse(
            video_segments=segment_responses,
            total_count=len(segment_responses)
        )

        return {
            "code": 200,
            "message": "success",
            "data": result.model_dump(by_alias=True)
        }

    except Exception as e:
        logger.error('获取视频片段列表失败', error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='获取视频片段列表失败'
        )


@router.post('/{video_segment_id}/regenerate')
async def regenerate_video_segment(
    video_segment_id: int,
    request: RegenerateVideoSegmentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """重新生成单个视频片段（提示词不可修改）.

    Args:
        video_segment_id: 视频片段ID
        request: 重新生成请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        更新后的视频片段（状态为generating，包装格式）

    Raises:
        HTTPException: 重新生成失败
    """
    try:
        video_service = VideoService(db)
        video_segment = await video_service.regenerate_video_segment(
            video_segment_id=video_segment_id,
            model=request.model
        )

        result = VideoSegmentResponse(
            id=video_segment.id,
            script_id=video_segment.script_id,
            segment_index=video_segment.segment_index,
            first_frame_url=video_segment.first_frame_url,
            last_frame_url=video_segment.last_frame_url,
            prompt=video_segment.prompt,
            video_url=video_segment.video_url,
            model=video_segment.model,
            aspect_ratio=video_segment.aspect_ratio,
            status=video_segment.status,
            duration=video_segment.duration,
            error_message=video_segment.error_message,
            created_at=video_segment.created_at,
            updated_at=video_segment.updated_at
        )

        return {
            "code": 200,
            "message": "success",
            "data": result.model_dump(by_alias=True)
        }

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error('重新生成视频失败', error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='重新生成视频失败'
        )


@router.post('/export')
async def export_videos(
    request: ExportVideosRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """导出脚本的所有视频为zip文件.

    Args:
        request: 导出请求
        current_user: 当前用户
        db: 数据库会话

    Returns:
        包含下载URL和过期时间（包装格式）

    Raises:
        HTTPException: 导出失败
    """
    try:
        video_service = VideoService(db)
        export_result = await video_service.export_videos(
            script_id=request.script_id
        )

        result = ExportVideosResponse(
            download_url=export_result['download_url'],
            expires_in=export_result['expires_in']
        )

        return {
            "code": 200,
            "message": "success",
            "data": result.model_dump(by_alias=True)
        }

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error('导出视频失败', error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='导出视频失败'
        )
