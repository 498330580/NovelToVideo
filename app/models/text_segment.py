"""文本段落模型"""
import os
from pathlib import Path
from app.utils.database import execute_query, execute_many
from config import DefaultConfig


class TextSegment:
    """文本段落数据模型"""
    
    # 音频状态常量
    AUDIO_STATUS_PENDING = 'pending'
    AUDIO_STATUS_SYNTHESIZING = 'synthesizing'
    AUDIO_STATUS_COMPLETED = 'completed'
    AUDIO_STATUS_FAILED = 'failed'
    
    def __init__(self, id=None, project_id=None, segment_index=None, content=None,
                 word_count=None, chapter_title=None, audio_status=AUDIO_STATUS_PENDING,
                 audio_path=None, created_at=None):
        self.id = id
        self.project_id = project_id
        self.segment_index = segment_index
        self.content = content
        self.word_count = word_count
        self.chapter_title = chapter_title
        self.audio_status = audio_status
        self.audio_path = audio_path
        self.created_at = created_at
    
    @classmethod
    def create(cls, project_id, segment_index, content, word_count, chapter_title=None):
        """
        创建文本段落
        
        Args:
            project_id: 项目ID
            segment_index: 段落序号
            content: 文本内容
            word_count: 字数
            chapter_title: 章节标题
            
        Returns:
            段落ID
        """
        query = '''
            INSERT INTO text_segments 
            (project_id, segment_index, content, word_count, chapter_title)
            VALUES (?, ?, ?, ?, ?)
        '''
        
        segment_id = execute_query(
            query,
            (project_id, segment_index, content, word_count, chapter_title),
            fetch=False
        )
        
        return segment_id
    
    @classmethod
    def create_batch(cls, segments_data):
        """
        批量创建文本段落
        
        Args:
            segments_data: 段落数据列表
            
        Returns:
            影响的行数
        """
        query = '''
            INSERT INTO text_segments 
            (project_id, segment_index, content, word_count, chapter_title)
            VALUES (?, ?, ?, ?, ?)
        '''
        
        return execute_many(query, segments_data)
    
    @classmethod
    def get_by_id(cls, segment_id):
        """
        根据ID获取段落
        
        Args:
            segment_id: 段落ID
            
        Returns:
            TextSegment对象或None
        """
        query = 'SELECT * FROM text_segments WHERE id = ?'
        rows = execute_query(query, (segment_id,))
        # 防御性处理返回类型：确保可迭代且至少一个元素
        if not rows:
            return None
        try:
            first = rows[0] if isinstance(rows, (list, tuple)) and rows else None
        except Exception:
            first = None
        if first is None:
            return None
        return cls._from_row(first)
    
    @classmethod
    def get_by_project(cls, project_id):
        """
        获取项目的所有段落
        
        Args:
            project_id: 项目ID
            
        Returns:
            TextSegment对象列表
        """
        query = '''
            SELECT * FROM text_segments 
            WHERE project_id = ? 
            ORDER BY segment_index
        '''
        rows = execute_query(query, (project_id,))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def get_pending_segments(cls, project_id, limit=None):
        """
        获取待处理的段落
        
        Args:
            project_id: 项目ID
            limit: 限制数量
            
        Returns:
            TextSegment对象列表
        """
        query = '''
            SELECT * FROM text_segments 
            WHERE project_id = ? AND audio_status = ? 
            ORDER BY segment_index
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        rows = execute_query(query, (project_id, cls.AUDIO_STATUS_PENDING))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def update_audio_status(cls, segment_id, status, audio_path=None):
        """
        更新音频状态
        
        Args:
            segment_id: 段落ID
            status: 新状态
            audio_path: 音频文件路径（支持绝对路径或相对路径，会自动转换为相对路径保存）
        """
        if audio_path:
            # 转换为相对路径后保存
            relative_path = cls.convert_to_relative_path(audio_path)
            query = '''
                UPDATE text_segments 
                SET audio_status = ?, audio_path = ?
                WHERE id = ?
            '''
            execute_query(query, (status, relative_path, segment_id), fetch=False)
        else:
            query = '''
                UPDATE text_segments 
                SET audio_status = ?
                WHERE id = ?
            '''
            execute_query(query, (status, segment_id), fetch=False)
    
    @classmethod
    def get_completed_segments(cls, project_id):
        """
        获取已完成的段落
        
        Args:
            project_id: 项目ID
            
        Returns:
            TextSegment对象列表
        """
        query = '''
            SELECT * FROM text_segments 
            WHERE project_id = ? AND audio_status = ? 
            ORDER BY segment_index
        '''
        rows = execute_query(query, (project_id, cls.AUDIO_STATUS_COMPLETED))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def get_failed_segments(cls, project_id):
        """
        获取失败的段落
        
        Args:
            project_id: 项目ID
            
        Returns:
            TextSegment对象列表
        """
        query = '''
            SELECT * FROM text_segments 
            WHERE project_id = ? AND audio_status = ? 
            ORDER BY segment_index
        '''
        rows = execute_query(query, (project_id, cls.AUDIO_STATUS_FAILED))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]

    @classmethod
    def reset_audio_status_by_project(cls, project_id, from_status, to_status):
        """
        重置项目内指定音频状态的段落为新状态
        
        Args:
            project_id: 项目ID
            from_status: 原状态
            to_status: 新状态
        """
        query = '''
            UPDATE text_segments
            SET audio_status = ?
            WHERE project_id = ? AND audio_status = ?
        '''
        execute_query(query, (to_status, project_id, from_status), fetch=False)

    @classmethod
    def delete_by_project(cls, project_id):
        """
        删除项目的所有文本段落
        
        Args:
            project_id: 项目ID
        """
        query = 'DELETE FROM text_segments WHERE project_id = ?'
        execute_query(query, (project_id,), fetch=False)
    
    @classmethod
    def _from_row(cls, row):
        """
        从数据库行创建对象
        
        Args:
            row: 数据库行
            
        Returns:
            TextSegment对象
        """
        # 使用安全的字典访问，避免类型检查器对未知/不支持 __getitem__ 的对象报错
        try:
            get = row.get  # 优先使用映射类型的 get
        except AttributeError:
            # 兜底处理，尝试按字典构造
            try:
                row = dict(row)
                get = row.get
            except Exception:
                # 无法转为字典时直接抛出更易读的异常
                raise TypeError(f"无法从行对象构建 TextSegment，期望映射类型，得到: {type(row)}")

        return cls(
            id=get('id'),
            project_id=get('project_id'),
            segment_index=get('segment_index'),
            content=get('content'),
            word_count=get('word_count'),
            chapter_title=get('chapter_title'),
            audio_status=get('audio_status', cls.AUDIO_STATUS_PENDING),
            audio_path=get('audio_path'),
            created_at=get('created_at')
        )
    
    @staticmethod
    def convert_to_relative_path(absolute_path):
        """
        将绝对路径转换为相对路径
        相对于 temp/audio 目录
        
        Args:
            absolute_path: 绝对路径
            
        Returns:
            相对路径（仅文件名）
        """
        if not absolute_path:
            return None
        
        # 只保存文件名（最后一部分）
        return os.path.basename(absolute_path)
    
    @staticmethod
    def convert_to_absolute_path(relative_path):
        """
        [已过时] 将相对路径转换为绝对路径
        
        ⚠️ 警告：此方法已过时，无法正确处理项目ID子目录！
        请使用实例方法 get_absolute_audio_path() 替代。
        
        该方法无法处理新的目录结构：temp/audio/{project_id}/{filename}
        保留此方法仅为向后兼容，但不应在新代码中使用。
        
        Args:
            relative_path: 相对路径（通常是文件名）
            
        Returns:
            绝对路径（不包含项目ID，可能不正确）
        """
        if not relative_path:
            return None
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(relative_path):
            return relative_path
        
        # ⚠️ 注意：此路径不包含项目ID，可能不正确
        # 应该使用 get_absolute_audio_path() 实例方法替代
        return os.path.join(DefaultConfig.TEMP_AUDIO_DIR, relative_path)
    
    def get_absolute_audio_path(self):
        """
        获取绝对音频路径
        
        Returns:
            绝对路径
        """
        if not self.audio_path:
            return None
        
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(self.audio_path):
            return self.audio_path
        
        # 拼接到 temp/audio/{project_id}/ 目录
        return os.path.join(DefaultConfig.TEMP_AUDIO_DIR, str(self.project_id), self.audio_path)
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            段落信息字典
        """
        # 处理 content 为 None 的情况，避免 len/切片错误
        _content = self.content or ''
        _content_preview = _content[:100] + '...' if len(_content) > 100 else _content

        return {
            'id': self.id,
            'project_id': self.project_id,
            'segment_index': self.segment_index,
            'content': _content_preview,
            'word_count': self.word_count,
            'chapter_title': self.chapter_title,
            'audio_status': self.audio_status,
            'audio_path': self.audio_path,
            'created_at': self.created_at
        }
