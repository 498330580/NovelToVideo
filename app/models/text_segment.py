"""文本段落模型"""
from app.utils.database import execute_query, execute_many


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
        
        if rows:
            return cls._from_row(rows[0])
        return None
    
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
        
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def update_audio_status(cls, segment_id, status, audio_path=None):
        """
        更新音频状态
        
        Args:
            segment_id: 段落ID
            status: 新状态
            audio_path: 音频文件路径
        """
        if audio_path:
            query = '''
                UPDATE text_segments 
                SET audio_status = ?, audio_path = ?
                WHERE id = ?
            '''
            execute_query(query, (status, audio_path, segment_id), fetch=False)
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
        
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def _from_row(cls, row):
        """
        从数据库行创建对象
        
        Args:
            row: 数据库行
            
        Returns:
            TextSegment对象
        """
        return cls(
            id=row['id'],
            project_id=row['project_id'],
            segment_index=row['segment_index'],
            content=row['content'],
            word_count=row['word_count'],
            chapter_title=row['chapter_title'],
            audio_status=row['audio_status'],
            audio_path=row['audio_path'],
            created_at=row['created_at']
        )
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            段落信息字典
        """
        return {
            'id': self.id,
            'project_id': self.project_id,
            'segment_index': self.segment_index,
            'content': self.content[:100] + '...' if len(self.content) > 100 else self.content,
            'word_count': self.word_count,
            'chapter_title': self.chapter_title,
            'audio_status': self.audio_status,
            'audio_path': self.audio_path,
            'created_at': self.created_at
        }
