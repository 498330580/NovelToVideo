"""视频合成队列模型"""
import json
from app.utils.database import execute_query


class VideoSynthesisQueue:
    """视频合成队列数据模型"""
    
    # 队列状态常量
    STATUS_PENDING = 'pending'  # 未处理
    STATUS_SYNTHESIZING = 'synthesizing'  # 正在合成
    STATUS_COMPLETED = 'completed'  # 已完成
    
    def __init__(self, id=None, project_id=None, video_index=None, output_video_path=None,
                 temp_segment_ids=None, total_duration=None, status=STATUS_PENDING,
                 created_at=None, updated_at=None):
        self.id = id
        self.project_id = project_id
        self.video_index = video_index
        self.output_video_path = output_video_path
        # temp_segment_ids 可以是列表或JSON字符串
        if isinstance(temp_segment_ids, list):
            self.temp_segment_ids = temp_segment_ids
        elif isinstance(temp_segment_ids, str):
            try:
                self.temp_segment_ids = json.loads(temp_segment_ids)
            except:
                self.temp_segment_ids = []
        else:
            self.temp_segment_ids = []
        self.total_duration = total_duration
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def create(cls, project_id, video_index, output_video_path, temp_segment_ids, total_duration):
        """
        创建视频合成队列记录
        
        Args:
            project_id: 项目ID
            video_index: 视频序号
            output_video_path: 最终输出视频路径
            temp_segment_ids: 临时视频片段ID列表
            total_duration: 总时长
            
        Returns:
            队列记录ID
        """
        if isinstance(temp_segment_ids, list):
            temp_segment_ids_json = json.dumps(temp_segment_ids)
        else:
            temp_segment_ids_json = temp_segment_ids
        
        query = '''
            INSERT INTO video_synthesis_queue 
            (project_id, video_index, output_video_path, temp_segment_ids, total_duration, status)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        
        queue_id = execute_query(
            query,
            (project_id, video_index, output_video_path, temp_segment_ids_json, total_duration, cls.STATUS_PENDING),
            fetch=False
        )
        
        return queue_id
    
    @classmethod
    def get_by_id(cls, queue_id):
        """
        根据ID获取队列记录
        
        Args:
            queue_id: 队列ID
            
        Returns:
            VideoSynthesisQueue对象或None
        """
        query = 'SELECT * FROM video_synthesis_queue WHERE id = ?'
        rows = execute_query(query, (queue_id,))
        
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
        获取项目的所有队列记录
        
        Args:
            project_id: 项目ID
            
        Returns:
            VideoSynthesisQueue对象列表
        """
        query = '''
            SELECT * FROM video_synthesis_queue 
            WHERE project_id = ? 
            ORDER BY video_index
        '''
        rows = execute_query(query, (project_id,))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def get_by_project_and_index(cls, project_id, video_index):
        """
        获取项目指定索引的队列记录
        
        Args:
            project_id: 项目ID
            video_index: 视频序号
            
        Returns:
            VideoSynthesisQueue对象或None
        """
        query = '''
            SELECT * FROM video_synthesis_queue 
            WHERE project_id = ? AND video_index = ?
        '''
        rows = execute_query(query, (project_id, video_index))
        if not isinstance(rows, (list, tuple)):
            rows = []
        
        if len(rows) > 0:
            return cls._from_row(rows[0])
        return None
    
    @classmethod
    def get_by_status(cls, project_id, status):
        """
        获取指定状态的队列记录
        
        Args:
            project_id: 项目ID
            status: 状态
            
        Returns:
            VideoSynthesisQueue对象列表
        """
        query = '''
            SELECT * FROM video_synthesis_queue 
            WHERE project_id = ? AND status = ?
            ORDER BY video_index
        '''
        rows = execute_query(query, (project_id, status))
        if not isinstance(rows, (list, tuple)):
            rows = []
        return [cls._from_row(row) for row in rows]
    
    @classmethod
    def get_pending_queue(cls, project_id):
        """
        获取项目的第一个未处理的队列记录
        
        Args:
            project_id: 项目ID
            
        Returns:
            VideoSynthesisQueue对象或None
        """
        query = '''
            SELECT * FROM video_synthesis_queue 
            WHERE project_id = ? AND status = ?
            ORDER BY video_index
            LIMIT 1
        '''
        rows = execute_query(query, (project_id, cls.STATUS_PENDING))
        if not isinstance(rows, (list, tuple)):
            rows = []
        
        if len(rows) > 0:
            return cls._from_row(rows[0])
        return None
    
    @classmethod
    def update_status(cls, queue_id, status):
        """
        更新队列记录状态
        
        Args:
            queue_id: 队列ID
            status: 新状态
        """
        query = 'UPDATE video_synthesis_queue SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
        execute_query(query, (status, queue_id), fetch=False)
    
    @classmethod
    def _from_row(cls, row):
        """
        从数据库行创建对象
        
        Args:
            row: 数据库行
            
        Returns:
            VideoSynthesisQueue对象
        """
        return cls(
            id=row['id'],
            project_id=row['project_id'],
            video_index=row['video_index'],
            output_video_path=row['output_video_path'],
            temp_segment_ids=row['temp_segment_ids'],
            total_duration=row['total_duration'],
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def to_dict(self):
        """
        转换为字典
        
        Returns:
            队列记录信息字典
        """
        return {
            'id': self.id,
            'project_id': self.project_id,
            'video_index': self.video_index,
            'output_video_path': self.output_video_path,
            'temp_segment_ids': self.temp_segment_ids,
            'total_duration': self.total_duration,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def get_temp_segment_ids_json(self):
        """
        获取JSON格式的临时视频片段ID列表
        
        Returns:
            JSON字符串
        """
        return json.dumps(self.temp_segment_ids)
