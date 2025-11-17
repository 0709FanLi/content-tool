"""
图片模型配置服务
管理图片生成模型的配置信息，包括模型列表、图像比例选项等
"""

from typing import Dict, List
import structlog

logger = structlog.get_logger(__name__)


class ImageModelService:
    """图片模型服务类"""

    # 模型配置
    MODEL_CONFIGS: Dict[str, Dict] = {
        "jimeng_t2i_v40": {
            "name": "即梦 4.0",
            "description": "火山引擎即梦4.0，支持图生图，高质量图片生成",
            "aspect_ratios": [
                "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3",
                "5:4", "4:5", "21:9"
            ],
            "qualities": ["1K", "2K", "4K"],
            "has_quality_selector": True,
            "supports_reference": True  # 支持参考图
        },
        "nano-banana-fast": {
            "name": "Nano Banana Fast",
            "description": "快速版本",
            "aspect_ratios": [
                "auto", "1:1", "16:9", "9:16", "4:3", "3:4",
                "3:2", "2:3", "5:4", "4:5", "21:9"
            ],
            "qualities": [],  # 无清晰度参数
            "has_quality_selector": False,
            "supports_reference": True  # 支持参考图
        },
        "nano-banana": {
            "name": "Nano Banana",
            "description": "标准版本",
            "aspect_ratios": [
                "auto", "1:1", "16:9", "9:16", "4:3", "3:4",
                "3:2", "2:3", "5:4", "4:5", "21:9"
            ],
            "qualities": [],  # 无清晰度参数
            "has_quality_selector": False,
            "supports_reference": True  # 支持参考图
        },
        "sora-image": {
            "name": "Sora Image",
            "description": "图片生成模型",
            "aspect_ratios": [
                "auto", "1:1", "3:2", "2:3"
            ],
            "qualities": [],  # 无清晰度参数
            "has_quality_selector": False,
            "supports_reference": False  # 不支持参考图
        }
    }

    @classmethod
    def get_available_models(cls) -> List[Dict]:
        """
        获取可用的图片生成模型列表

        Returns:
            模型列表，每个模型包含完整配置信息
        """
        models = []
        for model_id, config in cls.MODEL_CONFIGS.items():
            model_config = config.copy()
            model_config["id"] = model_id
            models.append(model_config)

        logger.info("Retrieved image models", count=len(models))
        return models

    @classmethod
    def get_aspect_ratios(cls, model_id: str) -> List[str]:
        """
        根据模型ID获取支持的图像比例选项
        
        Args:
            model_id: 模型ID
            
        Returns:
            图像比例选项列表
            
        Raises:
            ValueError: 如果模型ID不存在
        """
        if model_id not in cls.MODEL_CONFIGS:
            raise ValueError(f"不支持的模型: {model_id}")
        
        aspect_ratios = cls.MODEL_CONFIGS[model_id]["aspect_ratios"]
        logger.info("Retrieved aspect ratios", model=model_id, count=len(aspect_ratios))
        return aspect_ratios

    @classmethod
    def get_qualities(cls, model_id: str) -> List[str]:
        """
        根据模型ID获取支持的清晰度选项
        
        Args:
            model_id: 模型ID
            
        Returns:
            清晰度选项列表
            
        Raises:
            ValueError: 如果模型ID不存在
        """
        if model_id not in cls.MODEL_CONFIGS:
            raise ValueError(f"不支持的模型: {model_id}")
        
        qualities = cls.MODEL_CONFIGS[model_id]["qualities"]
        logger.info("Retrieved qualities", model=model_id, count=len(qualities))
        return qualities

    @classmethod
    def get_model_config(cls, model_id: str) -> Dict:
        """
        获取模型的完整配置信息
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型配置字典
            
        Raises:
            ValueError: 如果模型ID不存在
        """
        if model_id not in cls.MODEL_CONFIGS:
            raise ValueError(f"不支持的模型: {model_id}")
        
        config = cls.MODEL_CONFIGS[model_id].copy()
        config["id"] = model_id
        return config

