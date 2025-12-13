"""临时视频片段模型"""
from app.utils.database import execute_query


class TempVideoSegment:
    """临时视频片段数据模型（中间视频）"""
    
    # 临时视频状态常量
    STATUS_PENDING = 'pending'  # 未处理
    STATUS_SYNTHESIZED = 'synthesized'  # 已合成临时视频
    STATUS_MERGED = 'merged'  # 已合成最终视频
    STATUS_DELETED = 'deleted'  # 已删除
    
    def __init__(self, id=None, project_id=None, text_segment_id=None, temp_video_path=None,
                 status=STATUS_PENDING, created_at=None, updated_at=None):
        self.id = id
        self.project_id = project_id
        self.text_segment_id = text_segment_id
        self.temp_video_path = temp_video_path
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def create(cls, project_id, text_segment_id, temp_video_path):
        """
        创建临时视频片段记录
        
        Args:
            project_id: 项目ID
            text_segment_id: 文本段落ID
            temp_video_path: 临时视频路径
            
        Returns:
            临时视频片段ID
        """
        query = '''
            INSERT INTO temp_video_segments 
            (project_id, text_segment_id, temp_video_path, status)
            VALUES (?, ?, ?, ?)
        '''
        
        segment_id = execute_query(
            query,
            (project_id, text_segment_id, temp_video_path, cls.STATUS_PENDING),
            fetch=False
        )
        
        return segment_id
    
    @classmethod
    def get_by_id(cls, segment_id):
        """
        根据ID获取临时视频片段
        
        Args:
            segment_id: 临时视频片段ID
            
        Returns:
            TempVideoSegment对象或None
        """
        query = 'SELECT * FROM temp_video_segments WHERE id = ?'
        rows = execute_query(query, (segment_id,))
        
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
        获取项目的所有临时视频片段
        
        Args:
            project_id: 项目ID
            
        Returns:
            TempVideoSegment对象列表
        """
        query = '''
            SELECT * FROM temp_video_segments 
            WHERE project_id = ? 
            ORDER BY id
        '''
        rows = execute_query(query, (project_id,))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def get_by_text_segment(cls, text_segment_id):
        """
        根据文本段落ID获取临时视频片段
        
        Args:
            text_segment_id: 文本段落ID
            
        Returns:
            TempVideoSegment对象或None
        """
        query = 'SELECT * FROM temp_video_segments WHERE text_segment_id = ?'
        rows = execute_query(query, (text_segment_id,))
        if not isinstance(rows, (list, tuple)):
            rows = []
        
        if len(rows) > 0:
            return cls._from_row(rows[0])
        return None
    
    @classmethod
    def get_by_status(cls, project_id, status):
        """
        获取指定状态的临时视频片段
        
        Args:
            project_id: 项目ID
            status: 状态
            
        Returns:
            TempVideoSegment对象列表
        """
        query = '''
            SELECT * FROM temp_video_segments 
            WHERE project_id = ? AND status = ?
            ORDER BY id
        '''
        rows = execute_query(query, (project_id, status))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def update_status(cls, segment_id, status):
        """
        更新临时视频片段状态
        
        Args:
            segment_id: 临时视频片段ID
            status: 新状态
        """
        query = 'UPDATE temp_video_segments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
        execute_query(query, (status, segment_id), fetch=False)
    
    @classmethod
    def delete(cls, segment_id):
        """
        标记临时视频片段为已删除
        
        Args:
            segment_id: 临时视频片段ID
        """
        cls.update_status(segment_id, cls.STATUS_DELETED)
    
    @classmethod
    def _from_row(cls, row):
        """
        从数据库行创建对象
        
        Args:
            row: 数据库行
            
        Returns:
            TempVideoSegment对象
        """
        return cls(
            id=row['id'],
            project_id=row['project_id'],
            text_segment_id=row['text_segment_id'],
            temp_video_path=row['temp_video_path'],
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def get_absolute_temp_video_path(self):
        """
        获取临时视频的绝对路径
        
        Returns:
            绝对路径
        """
        import os
        from config import DefaultConfig
        
        # 如果 temp_video_path 已经是绝对路径，直接返回
        if os.path.isabs(self.temp_video_path):
            return self.temp_video_path
        
        # 否则以 TEMP_VIDEO_DIR 为基础路径
        return os.path.join(DefaultConfig.TEMP_VIDEO_DIR, self.temp_video_path)
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            临时视频片段信息字典
        """
        return {
            'id': self.id,
            'project_id': self.project_id,
            'text_segment_id': self.text_segment_id,
            'temp_video_path': self.temp_video_path,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
