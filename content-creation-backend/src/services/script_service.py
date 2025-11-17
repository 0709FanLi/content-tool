"""
脚本生成服务
"""

import re
import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.services.llm_service import LLMService
from src.models.schemas.script import ScriptSegment, GenerateScriptRequest, ScriptUpdate
from src.models.tables.script import Script
from src.utils.exceptions import ValidationError, NotFoundError

logger = structlog.get_logger(__name__)


class ScriptService:
    """脚本生成服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_service = LLMService()

    def parse_script_content(self, content: str, segment_duration: int) -> List[ScriptSegment]:
        """
        解析脚本内容，提取时间段和内容
        
        支持多种格式：
        1. (0:00 - 6:00) 内容...
        2. 0-6s 内容...
        3. 第0帧：内容...
        4. 最后一帧：内容...
        
        Args:
            content: 脚本内容
            segment_duration: 单个片段时长
            
        Returns:
            脚本片段列表
        """
        segments = []
        segment_index = 0
        
        # 分割成段落（使用空行分隔）
        paragraphs = re.split(r'\n\s*\n+', content.strip())
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # 匹配格式1：(X:XX - X:XX) 内容
            # 例如：(0:00 - 6:00) 这位年轻女性...
            # 注意：此格式中，如果两个时间都是个位数分钟数，则表示秒数
            # 例如：(0:00 - 6:00) 表示 0-360秒，(0:00 - 0:06) 表示 0-6秒
            time_pattern_1 = r'^\((\d+):(\d+)\s*-\s*(\d+):(\d+)\)\s*(.+)$'
            match1 = re.match(time_pattern_1, paragraph, re.DOTALL)
            
            if match1:
                start_min = int(match1.group(1))
                start_sec = int(match1.group(2))
                end_min = int(match1.group(3))
                end_sec = int(match1.group(4))
                content_text = match1.group(5).strip()
                
                # 时间解析规则：
                # 1. 如果秒数部分不为0，则按标准MM:SS格式解析（分钟:秒）
                # 2. 如果秒数部分为0，则分钟部分可能表示秒数
                #    例如：(0:00 - 6:00) 可能表示 0秒到6秒，也可能表示 0分到6分
                #    判断依据：如果分钟部分小于60，则视为秒数；否则视为分钟
                
                if start_sec == 0 and end_sec == 0 and start_min < 60 and end_min < 60:
                    # 秒数部分为0且分钟部分小于60，视为秒数表示法
                    # (0:00 - 6:00) -> 0秒到6秒
                    start_time = start_min
                    end_time = end_min
                else:
                    # 标准MM:SS格式
                    # (0:06 - 0:12) -> 6秒到12秒
                    # (1:00 - 2:00) -> 60秒到120秒
                    start_time = start_min * 60 + start_sec
                    end_time = end_min * 60 + end_sec
                
                segment = ScriptSegment(
                    id=f"segment_{segment_index}",
                    time_start=float(start_time),
                    time_end=float(end_time),
                    content=content_text
                )
                segments.append(segment)
                segment_index += 1
                continue
            
            # 匹配格式2：0-6s 内容 或 0s-6s 内容
            time_pattern_2 = r'^(\d+)s?\s*[-~]\s*(\d+)s?\s*(.+)$'
            match2 = re.match(time_pattern_2, paragraph, re.DOTALL)
            
            if match2:
                start_time = int(match2.group(1))
                end_time = int(match2.group(2))
                content_text = match2.group(3).strip()
                
                # 移除可能的冒号
                if content_text.startswith(':'):
                    content_text = content_text[1:].strip()
                
                segment = ScriptSegment(
                    id=f"segment_{segment_index}",
                    time_start=float(start_time),
                    time_end=float(end_time),
                    content=content_text
                )
                segments.append(segment)
                segment_index += 1
                continue
            
            # 匹配格式3：第0帧：内容（不作为segment，跳过）
            if paragraph.startswith('第0帧：') or paragraph.startswith('第0帧:'):
                # 第0帧通常是开场画面，不作为正式segment
                logger.info("Skipping frame 0", content=paragraph[:50])
                continue
            
            # 匹配格式4：最后一帧：内容（不作为segment，跳过）
            if paragraph.startswith('最后一帧：') or paragraph.startswith('最后一帧:'):
                # 最后一帧通常是结束画面，不作为正式segment
                logger.info("Skipping last frame", content=paragraph[:50])
                continue
            
            # 如果没有匹配到任何格式，使用默认时间范围
            # 这种情况通常不应该发生，记录警告
            logger.warning("No time pattern matched", paragraph=paragraph[:50])
            start_time = segment_index * segment_duration
            end_time = (segment_index + 1) * segment_duration
            
            segment = ScriptSegment(
                id=f"segment_{segment_index}",
                time_start=float(start_time),
                time_end=float(end_time),
                content=paragraph
            )
            segments.append(segment)
            segment_index += 1
        
        # 如果解析失败（没有任何segment），尝试按行解析
        if not segments:
            logger.warning("No segments parsed, falling back to line-by-line parsing")
            lines = content.strip().split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line and not line.startswith('第0帧') and not line.startswith('最后一帧'):
                    start_time = i * segment_duration
                    end_time = (i + 1) * segment_duration
                    segment = ScriptSegment(
                        id=f"segment_{i}",
                        time_start=float(start_time),
                        time_end=float(end_time),
                        content=line
                    )
                    segments.append(segment)
        
        logger.info(f"Parsed {len(segments)} segments from script")
        return segments

    async def generate_script(
        self,
        request: GenerateScriptRequest,
        model: str = "deepseek-chat"
    ) -> dict:
        """
        生成脚本
        
        Args:
            request: 生成脚本请求
            model: 使用的模型名称
            
        Returns:
            包含脚本内容和片段的字典
        """
        # 验证参数
        if request.total_duration < request.segment_duration:
            raise ValidationError("视频总时长不能小于单个视频时长")
        
        if request.total_duration % request.segment_duration != 0:
            logger.warning(
                "Duration not divisible",
                total_duration=request.total_duration,
                segment_duration=request.segment_duration
            )
        
        # 获取风格描述
        styles = self.get_script_styles()
        style_info = next((s for s in styles if s["id"] == request.style), None)
        style_description = style_info["description"] if style_info else request.style
        
        # 调用LLM生成脚本
        logger.info(
            "Generating script",
            inspiration=request.inspiration[:50],
            style=request.style,
            model=model,
            total_duration=request.total_duration,
            segment_duration=request.segment_duration
        )
        
        script_content = await self.llm_service.generate_script(
            inspiration=request.inspiration,
            style=style_description,
            total_duration=request.total_duration,
            segment_duration=request.segment_duration,
            model=model
        )
        
        # 解析脚本内容
        segments = self.parse_script_content(script_content, request.segment_duration)
        
        # 如果解析的片段数量不对，重新生成
        expected_segments = request.total_duration // request.segment_duration
        if len(segments) != expected_segments:
            logger.warning(
                "Segment count mismatch",
                expected=expected_segments,
                actual=len(segments)
            )
            # 可以在这里添加重新生成的逻辑，或者调整片段
        
        return {
            "content": script_content,
            "segments": segments,
            "style": request.style,
            "total_duration": request.total_duration,
            "segment_duration": request.segment_duration
        }

    async def create_script(
        self,
        project_id: int,
        content: str,
        style: str,
        total_duration: int,
        segment_duration: int,
        segments: List[ScriptSegment]
    ) -> Script:
        """
        创建脚本记录到数据库
        
        Args:
            project_id: 项目ID
            content: 脚本内容
            style: 脚本风格
            total_duration: 总时长
            segment_duration: 单段时长
            segments: 脚本片段列表
            
        Returns:
            创建的脚本对象
        """
        # 将segments转换为JSON格式
        segments_json = [
            {
                "id": seg.id,
                "time_start": seg.time_start,
                "time_end": seg.time_end,
                "content": seg.content,
                "scene": seg.scene,
                "presenter": seg.presenter,
                "subtitle": seg.subtitle
            }
            for seg in segments
        ]
        
        script = Script(
            project_id=project_id,
            content=content,
            style=style,
            total_duration=total_duration,
            segment_duration=segment_duration,
            segments=segments_json
        )
        
        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)
        
        logger.info("脚本创建成功", script_id=script.id, project_id=project_id)
        return script

    async def get_script(self, script_id: int, project_id: int) -> Optional[Script]:
        """
        获取脚本
        
        Args:
            script_id: 脚本ID
            project_id: 项目ID
            
        Returns:
            脚本对象，如果不存在返回None
        """
        from sqlalchemy import select
        result = await self.db.execute(
            select(Script).where(
                Script.id == script_id,
                Script.project_id == project_id
            )
        )
        script = result.scalar_one_or_none()
        return script

    async def update_script(
        self,
        script_id: int,
        project_id: int,
        script_data: ScriptUpdate
    ) -> Script:
        """
        更新脚本
        
        Args:
            script_id: 脚本ID
            project_id: 项目ID
            script_data: 脚本更新数据
            
        Returns:
            更新后的脚本对象
            
        Raises:
            NotFoundError: 脚本不存在
        """
        script = await self.get_script(script_id, project_id)
        if not script:
            raise NotFoundError(f"脚本 {script_id} 不存在")
        
        # 更新字段
        update_data = script_data.model_dump(exclude_unset=True)
        
        # 如果更新segments，需要转换为JSON格式
        if "segments" in update_data and update_data["segments"] is not None:
            segments_json = [
                {
                    "id": seg.id,
                    "time_start": seg.time_start,
                    "time_end": seg.time_end,
                    "content": seg.content,
                    "scene": seg.scene,
                    "presenter": seg.presenter,
                    "subtitle": seg.subtitle
                }
                for seg in update_data["segments"]
            ]
            update_data["segments"] = segments_json
        
        for field, value in update_data.items():
            setattr(script, field, value)
        
        await self.db.commit()
        await self.db.refresh(script)
        
        logger.info("脚本更新成功", script_id=script_id, project_id=project_id)
        return script

    async def optimize_script(
        self,
        script_id: int,
        project_id: int,
        creative_description: str,
        model: str = "deepseek-chat"
    ) -> Script:
        """
        优化脚本，使用创意描述作为补充
        
        Args:
            script_id: 脚本ID
            project_id: 项目ID
            creative_description: 创意描述（用于优化脚本）
            model: 使用的模型名称
            
        Returns:
            优化后的脚本对象
            
        Raises:
            NotFoundError: 脚本不存在
        """
        script = await self.get_script(script_id, project_id)
        if not script:
            raise NotFoundError(f"脚本 {script_id} 不存在")
        
        if not script.content:
            raise ValidationError("脚本内容为空，无法优化")
        
        logger.info(
            "Optimizing script",
            script_id=script_id,
            model=model,
            creative_description_length=len(creative_description)
        )
        
        # 调用LLM优化脚本
        optimized_content = await self.llm_service.optimize_script(
            script_content=script.content,
            creative_description=creative_description,
            model=model
        )
        
        # 更新脚本内容
        script.content = optimized_content
        script.optimized_content = optimized_content
        
        await self.db.commit()
        await self.db.refresh(script)
        
        logger.info("脚本优化成功", script_id=script_id, project_id=project_id)
        return script

    @staticmethod
    def get_script_styles() -> List[dict]:
        """
        获取脚本风格列表
        
        Returns:
            风格列表
        """
        return [
            {
                "id": "storytelling",
                "name": "故事化叙事风格",
                "description": "通过一个具体的故事或场景引入理论或知识的科普。脚本结构：开端（问题）：展示一个普通人或企业面临的困境。发展（引入理论知识）：科学理论如何介入，解决问题。高潮（价值升华）：展示问题解决后的美好结果。结尾（呼吁）：点明主题，如'xxx生活习惯，让你更年轻'。"
            },
            {
                "id": "visual_animation",
                "name": "可视化动画/图形动画风格",
                "description": "特点：用生动的动画、MG（Motion Graphics）来解释抽象的医学概念（如神经网络）。脚本结构：提出概念：'什么是抗炎？'比喻解释：用动画过程，类比细胞抵抗炎症的过程。步骤拆解：分解为几个可视化步骤。总结应用：快速展示该技术在日常生活中的应用。"
            }
        ]

