"""
项目表模型
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from src.models.database import Base


class ProjectStatus(str, enum.Enum):
    """项目状态枚举"""
    DRAFT = "draft"
    SCRIPT_GENERATED = "script_generated"
    KEYFRAMES_GENERATING = "keyframes_generating"
    KEYFRAMES_COMPLETED = "keyframes_completed"
    VIDEO_GENERATING = "video_generating"
    COMPLETED = "completed"


class Project(Base):
    """项目表"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.DRAFT)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 对话内容
    conversation_content: Mapped[str] = mapped_column(Text, nullable=True)
    # 图像模型配置
    image_model: Mapped[str] = mapped_column(String(100), nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(50), nullable=True)
    quality: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # 关联关系
    user: Mapped["User"] = relationship("User", back_populates="projects")
    scripts: Mapped[list["Script"]] = relationship(
        "Script",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status.value})>"
