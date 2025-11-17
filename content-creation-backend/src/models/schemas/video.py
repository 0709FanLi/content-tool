"""
视频相关数据模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class VideoStatus(str, Enum):
    """视频状态枚举"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoSegmentResponse(BaseModel):
    """视频片段响应模型"""
    id: int
    script_id: int = Field(..., alias="scriptId")
    segment_index: int = Field(..., alias="segmentIndex")
    first_frame_url: Optional[str] = Field(None, alias="firstFrameUrl")
    last_frame_url: Optional[str] = Field(None, alias="lastFrameUrl")
    prompt: Optional[str] = None
    video_url: Optional[str] = Field(None, alias="videoUrl")
    model: Optional[str] = None
    aspect_ratio: Optional[str] = Field(None, alias="aspectRatio")
    status: VideoStatus
    duration: float
    error_message: Optional[str] = Field(None, alias="errorMessage")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class GenerateVideoRequest(BaseModel):
    """生成视频请求模型"""
    script_id: int = Field(..., alias="scriptId")
    model: str = Field(default="veo3.1-fast", max_length=50)
    aspect_ratio: str = Field(default="16:9", max_length=20, alias="aspectRatio")
    duration: Optional[float] = Field(default=6.0, gt=0)  # 视频时长（秒，默认6s）

    class Config:
        populate_by_name = True


class GenerateVideosResponse(BaseModel):
    """批量生成视频响应模型"""
    video_segments: List[VideoSegmentResponse] = Field(..., alias="videoSegments")
    total_count: int = Field(..., alias="totalCount")

    class Config:
        populate_by_name = True


class RegenerateVideoSegmentRequest(BaseModel):
    """重新生成单个视频片段请求模型"""
    model: Optional[str] = Field(None, max_length=50)

    class Config:
        populate_by_name = True


class ExportVideosRequest(BaseModel):
    """导出视频请求模型"""
    script_id: int = Field(..., alias="scriptId")

    class Config:
        populate_by_name = True


class ExportVideosResponse(BaseModel):
    """导出视频响应模型"""
    download_url: str = Field(..., alias="downloadUrl")
    expires_in: int = Field(..., alias="expiresIn")  # 过期时间（秒）

    class Config:
        populate_by_name = True


class VideoModelInfo(BaseModel):
    """视频模型信息"""
    id: str
    name: str
    description: str
    supports_first_last_frame: bool = Field(..., alias="supportsFirstLastFrame")

    class Config:
        populate_by_name = True


class VideoModelsResponse(BaseModel):
    """视频模型列表响应"""
    models: List[VideoModelInfo]

    class Config:
        populate_by_name = True
