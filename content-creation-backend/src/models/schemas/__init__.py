"""
数据模型统一出口
"""

from .auth import *
from .project import *
from .script import *
from .keyframe import *
from .video import *
from .file import *
from .response import *

__all__ = [
    # 响应
    "ApiResponse", "PageResponse",
    
    # 认证
    "UserBase", "UserCreate", "UserUpdate", "UserResponse",
    "Token", "TokenData", "LoginRequest", "LoginResponse",
    "RefreshTokenRequest", "ChangePasswordRequest",

    # 项目
    "ProjectStatus", "ProjectBase", "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectDetailResponse",

    # 脚本
    "ScriptSegment", "ScriptBase", "ScriptCreate", "ScriptUpdate", "ScriptResponse",
    "GenerateScriptRequest", "OptimizeScriptRequest",

    # 关键帧
    "KeyframeStatus", "KeyframeBase", "KeyframeCreate", "KeyframeUpdate", "KeyframeResponse",
    "GenerateKeyframeRequest", "GenerateKeyframesResponse", "UploadKeyframeImageRequest",

    # 视频
    "VideoStatus", "VideoSegmentBase", "VideoSegmentCreate", "VideoSegmentUpdate", "VideoSegmentResponse",
    "GenerateVideoRequest", "GenerateVideosResponse", "ExportVideosRequest", "ExportVideosResponse",

    # 文件
    "FileBase", "FileCreate", "FileUpdate", "FileResponse",
    "UploadFileResponse", "FileUploadRequest",
]
