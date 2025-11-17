"""
脚本相关数据模型
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ScriptSegment(BaseModel):
    """脚本段落模型"""
    id: str
    time_start: float
    time_end: float
    content: str
    scene: Optional[str] = None
    presenter: Optional[str] = None
    subtitle: Optional[str] = None


class ScriptBase(BaseModel):
    """脚本基础模型"""
    content: str = Field(..., max_length=10000)
    style: Optional[str] = Field(None, max_length=50)
    total_duration: Optional[int] = Field(None, ge=60, le=3600)  # 60秒到1小时
    segment_duration: Optional[int] = Field(None, ge=5, le=300)  # 5秒到5分钟


class ScriptCreate(ScriptBase):
    """脚本创建模型"""
    project_id: int


class ScriptUpdate(BaseModel):
    """脚本更新模型"""
    content: Optional[str] = Field(None, max_length=10000)
    style: Optional[str] = Field(None, max_length=50)
    total_duration: Optional[int] = Field(None, ge=60, le=3600)
    segment_duration: Optional[int] = Field(None, ge=5, le=300)
    segments: Optional[List[ScriptSegment]] = None
    optimized_content: Optional[str] = Field(None, max_length=10000)


class ScriptResponse(ScriptBase):
    """脚本响应模型"""
    id: int
    project_id: int
    segments: Optional[List[ScriptSegment]] = None
    optimized_content: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateScriptRequest(BaseModel):
    """生成脚本请求模型"""
    inspiration: str = Field(..., min_length=1, max_length=3000)
    style: str = Field(..., min_length=1, max_length=50)
    total_duration: int = Field(..., ge=1, le=3600, alias="totalDuration")  # 最小1秒
    segment_duration: int = Field(..., ge=5, le=300, alias="segmentDuration")
    project_id: Optional[int] = Field(None, alias="projectId")
    
    class Config:
        populate_by_name = True  # 允许同时使用别名和原始字段名


class OptimizeScriptRequest(BaseModel):
    """优化脚本请求模型"""
    optimization: str = Field(..., min_length=1, max_length=500)
