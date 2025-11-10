"""文本处理服务"""
import re
from app.models.text_segment import TextSegment
from app.models.task import Task
from app.models.project import Project
from app.utils.logger import get_logger
from config import DefaultConfig

logger = get_logger(__name__)


class TextProcessor:
    """文本处理服务类"""
    
    @staticmethod
    def process_text(project_id, text_content, config, task_id=None):
        """
        处理文本并分段
        
        Args:
            project_id: 项目ID
            text_content: 文本内容
            config: 配置字典
            task_id: 任务ID
            
        Returns:
            (成功标志, 错误信息)
        """
        try:
            if task_id:
                Task.update_status(task_id, Task.STATUS_RUNNING)
            
            segment_mode = config.get('segment_mode', DefaultConfig.DEFAULT_SEGMENT_MODE)
            max_words = config.get('max_words', DefaultConfig.DEFAULT_MAX_WORDS)
            
            # 根据分段模式处理文本
            if segment_mode == 'chapter':
                segments = TextProcessor._segment_by_chapter(text_content, max_words)
            else:
                segments = TextProcessor._segment_by_word_count(text_content, max_words)
            
            # 批量插入段落
            segments_data = [
                (project_id, idx, seg['content'], seg['word_count'], seg.get('chapter_title'))
                for idx, seg in enumerate(segments)
            ]
            
            TextSegment.create_batch(segments_data)
            
            logger.info(f'文本分段完成: 项目ID={project_id}, 段落数={len(segments)}')
            
            if task_id:
                Task.update_progress(task_id, 100.0)
                Task.update_status(task_id, Task.STATUS_COMPLETED)
            
            # 更新项目状态
            Project.update_status(project_id, Project.STATUS_PENDING)
            
            return True, None
            
        except Exception as e:
            logger.error(f'文本处理失败: {str(e)}', exc_info=True)
            if task_id:
                Task.update_status(task_id, Task.STATUS_FAILED, str(e))
            return False, str(e)
    
    @staticmethod
    def _segment_by_chapter(text_content, max_words):
        """
        按章节分段
        
        Args:
            text_content: 文本内容
            max_words: 单段最大字数
            
        Returns:
            段落列表
        """
        segments = []
        
        # 尝试识别章节
        chapter_pattern = '|'.join(DefaultConfig.CHAPTER_PATTERNS)
        lines = text_content.split('\n')
        
        current_chapter = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否为章节标题
            is_chapter = False
            for pattern in DefaultConfig.CHAPTER_PATTERNS:
                if re.match(pattern, line):
                    is_chapter = True
                    break
            
            if is_chapter:
                # 保存上一章节
                if current_content:
                    content = '\n'.join(current_content)
                    # 如果章节过长,需要二次分段
                    if len(content) > max_words:
                        sub_segments = TextProcessor._segment_by_word_count(content, max_words)
                        for sub_seg in sub_segments:
                            sub_seg['chapter_title'] = current_chapter
                            segments.append(sub_seg)
                    else:
                        segments.append({
                            'content': content,
                            'word_count': len(content),
                            'chapter_title': current_chapter
                        })
                
                # 开始新章节
                current_chapter = line
                current_content = []
            else:
                current_content.append(line)
        
        # 保存最后一章
        if current_content:
            content = '\n'.join(current_content)
            if len(content) > max_words:
                sub_segments = TextProcessor._segment_by_word_count(content, max_words)
                for sub_seg in sub_segments:
                    sub_seg['chapter_title'] = current_chapter
                    segments.append(sub_seg)
            else:
                segments.append({
                    'content': content,
                    'word_count': len(content),
                    'chapter_title': current_chapter
                })
        
        # 如果没有识别到章节,则按字数分段
        if not segments:
            return TextProcessor._segment_by_word_count(text_content, max_words)
        
        return segments
    
    @staticmethod
    def _segment_by_word_count(text_content, max_words):
        """
        按字数分段
        
        Args:
            text_content: 文本内容
            max_words: 单段最大字数
            
        Returns:
            段落列表
        """
        segments = []
        
        # 在自然断句处分段
        sentence_endings = r'[。！？!?\n]'
        sentences = re.split(sentence_endings, text_content)
        
        current_segment = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_len = len(sentence)
            
            # 如果单个句子就超过最大长度,则单独成段
            if sentence_len > max_words:
                # 先保存当前段落
                if current_segment:
                    content = '。'.join(current_segment) + '。'
                    segments.append({
                        'content': content,
                        'word_count': len(content),
                        'chapter_title': None
                    })
                    current_segment = []
                    current_length = 0
                
                # 将长句子分段
                for i in range(0, sentence_len, max_words):
                    chunk = sentence[i:i+max_words]
                    segments.append({
                        'content': chunk,
                        'word_count': len(chunk),
                        'chapter_title': None
                    })
            else:
                # 如果加上这句话会超过最大长度,则先保存当前段落
                if current_length + sentence_len > max_words and current_segment:
                    content = '。'.join(current_segment) + '。'
                    segments.append({
                        'content': content,
                        'word_count': len(content),
                        'chapter_title': None
                    })
                    current_segment = []
                    current_length = 0
                
                current_segment.append(sentence)
                current_length += sentence_len
        
        # 保存最后一段
        if current_segment:
            content = '。'.join(current_segment) + '。'
            segments.append({
                'content': content,
                'word_count': len(content),
                'chapter_title': None
            })
        
        return segments
