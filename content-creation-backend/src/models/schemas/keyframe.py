"""
关键帧相关数据模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class KeyframeStatus(str, Enum):
    """关键帧状态枚举"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class KeyframeBase(BaseModel):
    """关键帧基础模型"""
    segment_id: str = Field(..., max_length=100)
    prompt: Optional[str] = Field(None, max_length=1000)


class KeyframeCreate(KeyframeBase):
    """关键帧创建模型"""
    script_id: int


class KeyframeUpdate(BaseModel):
    """关键帧更新模型"""
    image_url: Optional[str] = Field(None, max_length=500)
    prompt: Optional[str] = Field(None, max_length=1000)
    status: Optional[KeyframeStatus] = None
    error_message: Optional[str] = Field(None, max_length=500)


class KeyframeResponse(KeyframeBase):
    """关键帧响应模型"""
    id: int
    script_id: int = Field(..., alias="scriptId")
    image_url: Optional[str] = Field(None, alias="imageUrl")
    status: KeyframeStatus
    error_message: Optional[str] = Field(None, alias="errorMessage")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    segment_id: str = Field(..., alias="segmentId")

    class Config:
        from_attributes = True
        populate_by_name = True


class GenerateKeyframeRequest(BaseModel):
    """生成关键帧请求模型"""
    script_id: int
    model: str = Field(..., max_length=50)
    aspect_ratio: str = Field(..., max_length=20)
    quality: Optional[str] = Field(None, max_length=20)


class GenerateKeyframesResponse(BaseModel):
    """批量生成关键帧响应模型"""
    keyframes: List[KeyframeResponse]
    total_count: int = Field(..., alias="totalCount")
    
    class Config:
        populate_by_name = True


class UploadKeyframeImageRequest(BaseModel):
    """上传关键帧图片请求模型"""
    file: bytes
    filename: str
