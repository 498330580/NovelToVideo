-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    output_path TEXT NOT NULL,
    config_json TEXT NOT NULL
);

-- 文本段落表
CREATE TABLE IF NOT EXISTS text_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    segment_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    chapter_title TEXT,
    audio_status TEXT DEFAULT 'pending',
    audio_path TEXT,
    audio_duration REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 视频片段表
CREATE TABLE IF NOT EXISTS video_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    segment_index INTEGER NOT NULL,
    duration REAL NOT NULL,
    video_path TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    progress REAL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 临时视频片段表（用于跟踪中间视频片段）
CREATE TABLE IF NOT EXISTS temp_video_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    text_segment_id INTEGER NOT NULL,
    temp_video_path TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending: 未处理, synthesized: 已合成临时视频, merged: 已合成最终视频, deleted: 已删除
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (text_segment_id) REFERENCES text_segments (id) ON DELETE CASCADE
);

-- 视频合成队列表（用于不同时段的视频合成任务）
CREATE TABLE IF NOT EXISTS video_synthesis_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    video_index INTEGER NOT NULL,  -- 视频序号(1, 2, 3...)
    output_video_path TEXT NOT NULL,  -- 最终视频路径
    temp_segment_ids TEXT NOT NULL,  -- JSON格式: [1, 2, 3] - 包含的temp_video_segments ID列表
    total_duration REAL NOT NULL,  -- 总时長
    status TEXT DEFAULT 'pending',  -- pending: 未处理, synthesizing: 正在合成, completed: 已完成
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_text_segments_project_id ON text_segments(project_id);
CREATE INDEX IF NOT EXISTS idx_text_segments_audio_status ON text_segments(audio_status);
CREATE INDEX IF NOT EXISTS idx_text_segments_audio_duration ON text_segments(audio_duration);
CREATE INDEX IF NOT EXISTS idx_video_segments_project_id ON video_segments(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_temp_video_segments_project_id ON temp_video_segments(project_id);
CREATE INDEX IF NOT EXISTS idx_temp_video_segments_status ON temp_video_segments(status);
CREATE INDEX IF NOT EXISTS idx_video_synthesis_queue_project_id ON video_synthesis_queue(project_id);
CREATE INDEX IF NOT EXISTS idx_video_synthesis_queue_status ON video_synthesis_queue(status);
