"""
脚本解析工具
解析脚本内容，根据时间戳提取段落
"""

import re
from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class ScriptSegment:
    """脚本段落数据类."""

    def __init__(
        self,
        segment_id: str,
        time_range: str,
        content: str,
        is_first: bool = False,
        is_last: bool = False,
        is_frame_0: bool = False
    ):
        """初始化脚本段落.

        Args:
            segment_id: 段落ID
            time_range: 时间段（如 "0:00 - 0:25"）
            content: 段落内容（不包含时间戳）
            is_first: 是否为第一段
            is_last: 是否为最后一段
            is_frame_0: 是否为第0帧（开场画面）
        """
        self.segment_id = segment_id
        self.time_range = time_range
        self.content = content
        self.is_first = is_first
        self.is_last = is_last
        self.is_frame_0 = is_frame_0

    def to_dict(self) -> Dict:
        """转换为字典.

        Returns:
            段落字典
        """
        return {
            'segment_id': self.segment_id,
            'time_range': self.time_range,
            'content': self.content,
            'is_first': self.is_first,
            'is_last': self.is_last
        }


def parse_script(script_content: str) -> List[ScriptSegment]:
    """解析脚本内容，根据时间戳提取段落，包括第0帧.

    Args:
        script_content: 脚本内容

    Returns:
        段落列表（包括第0帧、各个片段）

    Example:
        >>> script = "第0帧：开场画面...\\n(0:00 - 0:25) 开场：引起共鸣..."
        >>> segments = parse_script(script)
        >>> len(segments) > 0
        True
    """
    if not script_content or not script_content.strip():
        logger.warning('Empty script content')
        return []

    segments: List[ScriptSegment] = []
    
    # 匹配第0帧（开场画面）
    # 格式1：第0帧：内容
    # 格式2：(0:00 - 0:00) 开场画面：内容
    # 格式3：开场画面：内容（在第一个时间戳之前）
    frame_0_pattern = r'(?:^第0帧[：:]\s*(.+?)(?=\n|$)|^\(0:00\s*-\s*0:00\)\s*开场画面[：:]\s*(.+?)(?=\n|$)|^(开场画面[：:]\s*.+?)(?=\n\d+-\d+s|\n\(|\Z))'
    frame_0_match = re.search(frame_0_pattern, script_content, re.MULTILINE | re.DOTALL)
    
    # 提取第0帧内容
    frame_0_content = None
    if frame_0_match:
        frame_0_content = (frame_0_match.group(1) or frame_0_match.group(2) or frame_0_match.group(3)).strip()
        if frame_0_content:
            segments.append(ScriptSegment(
                segment_id='frame_0',
                time_range='0:00 - 0:00',
                content=frame_0_content,
                is_frame_0=True
            ))
            logger.info('Frame 0 (opening) found and parsed')
    
    # 匹配时间戳格式：
    # 1. (0:00 - 0:25) 或 (0:00-0:25) - 原有格式（冒号分隔的时间）
    # 2. (0-6s) 或 (6-12s) - 新格式（括号内的秒数）
    # 3. 0-6s 或 6-12s - 新格式（行首的秒数）
    time_pattern = r'(?:\((\d+:\d+)\s*-\s*(\d+:\d+)\)|\((\d+)-(\d+)s\)|^(\d+)-(\d+)s\s)'

    # 找到所有时间戳的位置
    matches = list(re.finditer(time_pattern, script_content, re.MULTILINE))
    
    if not matches:
        logger.warning('No time segments found in script')
        # 如果没有时间戳但有第0帧，返回第0帧
        if frame_0_content:
            return segments
        # 否则返回整个脚本作为一个段落
        return [
            ScriptSegment(
                segment_id='segment_0',
                time_range='',
                content=script_content.strip(),
                is_first=True,
                is_last=True
            )
        ]

    for i, match in enumerate(matches):
        # 处理不同的匹配格式
        if match.group(1) and match.group(2):
            # 格式1：(0:00 - 0:25) - 冒号分隔的时间
            start_time = match.group(1)
            end_time = match.group(2)
        elif match.group(3) and match.group(4):
            # 格式2：(0-6s) - 括号内的秒数
            start_seconds = int(match.group(3))
            end_seconds = int(match.group(4))
            start_time = f'0:{start_seconds:02d}' if start_seconds < 60 else f'{start_seconds // 60}:{start_seconds % 60:02d}'
            end_time = f'0:{end_seconds:02d}' if end_seconds < 60 else f'{end_seconds // 60}:{end_seconds % 60:02d}'
        elif match.group(5) and match.group(6):
            # 格式3：0-6s - 行首的秒数
            start_seconds = int(match.group(5))
            end_seconds = int(match.group(6))
            start_time = f'0:{start_seconds:02d}' if start_seconds < 60 else f'{start_seconds // 60}:{start_seconds % 60:02d}'
            end_time = f'0:{end_seconds:02d}' if end_seconds < 60 else f'{end_seconds // 60}:{end_seconds % 60:02d}'
        else:
            continue
            
        time_range = f'{start_time} - {end_time}'
        
        # 确定段落内容的起始位置
        segment_start = match.end()
        
        # 确定段落内容的结束位置
        if i < len(matches) - 1:
            # 不是最后一段，内容到下一个时间戳之前
            segment_end = matches[i + 1].start()
        else:
            # 最后一段，内容到脚本末尾
            segment_end = len(script_content)

        # 提取段落内容（去除时间戳行）
        segment_content = script_content[segment_start:segment_end].strip()
        
        # 移除可能存在的其他时间戳行
        segment_content = re.sub(
            time_pattern, '', segment_content
        ).strip()
        
        # 清理多余的空行
        segment_content = re.sub(r'\n\s*\n+', '\n\n', segment_content)
        segment_content = segment_content.strip()

        # 生成段落ID（如果有第0帧，从segment_0开始；否则从segment_0开始）
        segment_id = f'segment_{i}'

        # 判断是否为第一段和最后一段
        is_first = i == 0
        is_last = i == len(matches) - 1

        segment = ScriptSegment(
            segment_id=segment_id,
            time_range=time_range,
            content=segment_content,
            is_first=is_first,
            is_last=is_last
        )

        segments.append(segment)

    logger.info(
        'Script parsed successfully',
        total_segments=len(segments),
        has_frame_0=any(s.is_frame_0 for s in segments),
        first_segment=segments[0].segment_id if segments else None,
        last_segment=segments[-1].segment_id if segments else None
    )

    return segments


def extract_prompt_for_segment(
    segment: ScriptSegment, is_first_frame: bool = False
) -> str:
    """提取段落的提示词（用于图片生成）.

    Args:
        segment: 脚本段落
        is_first_frame: 是否为第一段的第一帧

    Returns:
        提示词文本
    """
    prompt = segment.content

    # 如果是第一段第一帧，添加开场关键词
    if is_first_frame and segment.is_first:
        prompt = f'{prompt} 开场画面，第一帧，初始场景'

    return prompt.strip()


def get_segment_by_id(
    segments: List[ScriptSegment], segment_id: str
) -> Optional[ScriptSegment]:
    """根据段落ID获取段落.

    Args:
        segments: 段落列表
        segment_id: 段落ID

    Returns:
        段落对象，如果不存在返回None
    """
    for segment in segments:
        if segment.segment_id == segment_id:
            return segment
    return None

