"""视频片段模型"""
from app.utils.database import execute_query


class VideoSegment:
    """视频片段数据模型"""
    
    # 视频状态常量
    STATUS_PENDING = 'pending'
    STATUS_GENERATING = 'generating'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    def __init__(self, id=None, project_id=None, segment_index=None, duration=None,
                 video_path=None, status=STATUS_PENDING, created_at=None):
        self.id = id
        self.project_id = project_id
        self.segment_index = segment_index
        self.duration = duration
        self.video_path = video_path
        self.status = status
        self.created_at = created_at
    
    @classmethod
    def create(cls, project_id, segment_index, duration, video_path):
        """
        创建视频片段
        
        Args:
            project_id: 项目ID
            segment_index: 片段序号
            duration: 视频时长
            video_path: 视频文件路径
            
        Returns:
            片段ID
        """
        query = '''
            INSERT INTO video_segments 
            (project_id, segment_index, duration, video_path)
            VALUES (?, ?, ?, ?)
        '''
        
        segment_id = execute_query(
            query,
            (project_id, segment_index, duration, video_path),
            fetch=False
        )
        
        return segment_id
    
    @classmethod
    def get_by_id(cls, segment_id):
        """
        根据ID获取视频片段
        
        Args:
            segment_id: 片段ID
            
        Returns:
            VideoSegment对象或None
        """
        query = 'SELECT * FROM video_segments WHERE id = ?'
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
        获取项目的所有视频片段
        
        Args:
            project_id: 项目ID
            
        Returns:
            VideoSegment对象列表
        """
        query = '''
            SELECT * FROM video_segments 
            WHERE project_id = ? 
            ORDER BY segment_index
        '''
        rows = execute_query(query, (project_id,))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def update_status(cls, segment_id, status):
        """
        更新视频片段状态
        
        Args:
            segment_id: 片段ID
            status: 新状态
        """
        query = 'UPDATE video_segments SET status = ? WHERE id = ?'
        execute_query(query, (status, segment_id), fetch=False)
    
    @classmethod
    def get_by_project_and_index(cls, project_id, segment_index):
        """
        获取项目指定索引的视频片段
        
        Args:
            project_id: 项目ID
            segment_index: 片段索引
            
        Returns:
            VideoSegment对象或None
        """
        query = '''
            SELECT * FROM video_segments 
            WHERE project_id = ? AND segment_index = ?
        '''
        rows = execute_query(query, (project_id, segment_index))
        if not isinstance(rows, (list, tuple)):
            rows = []
        
        if len(rows) > 0:
            return cls._from_row(rows[0])
        return None
    
    @classmethod
    def _from_row(cls, row):
        """
        从数据库行创建对象
        
        Args:
            row: 数据库行
            
        Returns:
            VideoSegment对象
        """
        return cls(
            id=row['id'],
            project_id=row['project_id'],
            segment_index=row['segment_index'],
            duration=row['duration'],
            video_path=row['video_path'],
            status=row['status'],
            created_at=row['created_at']
        )
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            片段信息字典
        """
        return {
            'id': self.id,
            'project_id': self.project_id,
            'segment_index': self.segment_index,
            'duration': self.duration,
            'video_path': self.video_path,
            'status': self.status,
            'created_at': self.created_at
        }
