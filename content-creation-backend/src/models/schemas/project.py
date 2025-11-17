"""
项目相关数据模型
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    DRAFT = "draft"
    SCRIPT_GENERATED = "script_generated"
    KEYFRAMES_GENERATING = "keyframes_generating"
    KEYFRAMES_COMPLETED = "keyframes_completed"
    VIDEO_GENERATING = "video_generating"
    COMPLETED = "completed"


class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class ProjectCreate(ProjectBase):
    """项目创建模型"""
    pass


class ProjectUpdate(BaseModel):
    """项目更新模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[ProjectStatus] = None
    conversation_content: Optional[str] = Field(None, max_length=5000, alias="conversationContent")
    image_model: Optional[str] = Field(None, max_length=100, alias="imageModel")
    aspect_ratio: Optional[str] = Field(None, max_length=50, alias="aspectRatio")
    quality: Optional[str] = Field(None, max_length=50)

    class Config:
        populate_by_name = True


class ProjectResponse(ProjectBase):
    """项目响应模型"""
    id: int
    status: ProjectStatus
    user_id: int = Field(..., alias="userId")
    conversation_content: Optional[str] = Field(None, alias="conversationContent")
    image_model: Optional[str] = Field(None, alias="imageModel")
    aspect_ratio: Optional[str] = Field(None, alias="aspectRatio")
    quality: Optional[str] = None
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class ProjectDetailResponse(ProjectResponse):
    """项目详情响应模型"""
    script: Optional["ScriptResponse"] = None
    keyframes: Optional[List["KeyframeResponse"]] = None
    video_segments: Optional[List["VideoSegmentResponse"]] = None


# 避免循环导入
from .script import ScriptResponse
from .keyframe import KeyframeResponse
from .video import VideoSegmentResponse

ProjectDetailResponse.update_forward_refs()
