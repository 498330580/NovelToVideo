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
    
    # edge-tts的字节限制
    EDGE_TTS_BYTE_LIMIT = 4096
    
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
            
            # 直接使用edge-tts字节限制进行分段，移除章节分段模式
            segments = TextProcessor._segment_by_edge_tts_limit(text_content)
            
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
    def _segment_by_edge_tts_limit(text_content):
        """
        按edge-tts字节限制分段
        
        Args:
            text_content: 文本内容
            
        Returns:
            段落列表
        """
        segments = []
        
        # 预处理文本
        processed_text = TextProcessor._preprocess_text(text_content)
        
        # 按edge-tts的字节限制进行分段
        text_segments = TextProcessor._split_text_by_byte_length(processed_text, TextProcessor.EDGE_TTS_BYTE_LIMIT)
        
        for idx, segment_text in enumerate(text_segments):
            # 清理段落文本
            cleaned_text = segment_text.strip()
            if cleaned_text:
                segments.append({
                    'content': cleaned_text,
                    'word_count': len(cleaned_text),
                    'chapter_title': None
                })
        
        return segments
    
    @staticmethod
    def _preprocess_text(text):
        """
        预处理文本以提高分割质量
        
        Args:
            text: 原始文本
            
        Returns:
            预处理后的文本
        """
        # 移除不兼容字符（这里简化处理）
        # 标准化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 确保段落间有适当间距
        paragraphs = text.split('\n')
        processed_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:  # 非空段落
                processed_paragraphs.append(para)
        
        return '\n\n'.join(processed_paragraphs)
    
    @staticmethod
    def _split_text_by_byte_length(text, byte_length):
        """
        按字节长度分割文本（模拟edge-tts的分割逻辑）
        
        Args:
            text: 文本内容
            byte_length: 最大字节长度
            
        Returns:
            分段后的文本列表
        """
        segments = []
        encoded_text = text.encode('utf-8')
        
        current_pos = 0
        while current_pos < len(encoded_text):
            # 计算当前段的结束位置
            end_pos = min(current_pos + byte_length, len(encoded_text))
            
            # 如果不是最后一段，尝试在自然边界处分割
            if end_pos < len(encoded_text):
                # 优先在段落边界分割
                paragraph_break = encoded_text.rfind(b'\n\n', current_pos, end_pos)
                if paragraph_break != -1:
                    end_pos = paragraph_break + 2  # 包含换行符
                else:
                    # 其次在句子边界分割
                    sentence_end = encoded_text.rfind(b'. ', current_pos, end_pos)
                    if sentence_end != -1:
                        end_pos = sentence_end + 2  # 包含句点和空格
                    else:
                        # 最后在单词边界分割
                        word_break = encoded_text.rfind(b' ', current_pos, end_pos)
                        if word_break != -1:
                            end_pos = word_break + 1  # 包含空格
                        # 如果找不到自然边界，就直接在字节限制处分割
            
            # 提取并解码段落
            segment_bytes = encoded_text[current_pos:end_pos]
            try:
                segment_text = segment_bytes.decode('utf-8')
                segments.append(segment_text)
            except UnicodeDecodeError:
                # 如果解码失败，尝试找到安全的UTF-8分割点
                safe_end_pos = TextProcessor._find_safe_utf8_split_point(encoded_text, current_pos, end_pos)
                safe_segment_bytes = encoded_text[current_pos:safe_end_pos]
                segment_text = safe_segment_bytes.decode('utf-8', errors='ignore')
                segments.append(segment_text)
                end_pos = safe_end_pos
            
            current_pos = end_pos
        
        return segments
    
    @staticmethod
    def _find_safe_utf8_split_point(encoded_text, start_pos, end_pos):
        """
        查找安全的UTF-8分割点
        
        Args:
            encoded_text: 编码后的字节文本
            start_pos: 起始位置
            end_pos: 结束位置
            
        Returns:
            安全的分割点位置
        """
        # 从结束位置向前查找，直到找到一个安全的UTF-8边界
        for i in range(end_pos, start_pos, -1):
            try:
                # 尝试从start_pos到i解码
                test_bytes = encoded_text[start_pos:i]
                test_bytes.decode('utf-8')
                return i
            except UnicodeDecodeError:
                continue
        
        # 如果找不到安全点，返回起始位置+1
        return start_pos + 1
    
    @staticmethod
    def _segment_by_word_count(text_content, max_words):
        """
        按字数分段（保留原有方法以兼容性）
        
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