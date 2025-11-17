"""
模型管理路由
提供可用模型列表和脚本风格列表
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.models.database import get_db
from src.services.llm_service import LLMService
from src.services.script_service import ScriptService
from src.services.image_model_service import ImageModelService

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.get("/script")
async def get_script_models():
    """
    获取可用于脚本生成的模型列表
    
    Returns:
        可用模型列表
    """
    llm_service = LLMService()
    models = llm_service.get_available_models()
    
    logger.info("Retrieved script models", count=len(models))
    
    return {
        "code": 200,
        "message": "success",
        "data": models
    }


@router.get("/script-styles")
async def get_script_styles():
    """
    获取脚本风格列表
    
    Returns:
        脚本风格列表
    """
    styles = ScriptService.get_script_styles()
    
    logger.info("Retrieved script styles", count=len(styles))
    
    return {
        "code": 200,
        "message": "success",
        "data": styles
    }


@router.get("/image")
async def get_image_models():
    """
    获取可用于图片生成的模型列表
    
    Returns:
        可用图片模型列表
    """
    models = ImageModelService.get_available_models()
    
    logger.info("Retrieved image models", count=len(models))
    
    return {
        "code": 200,
        "message": "success",
        "data": models
    }



