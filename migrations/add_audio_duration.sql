-- 为 text_segments 表添加 audio_duration 字段
-- 用于存储每个音频段落的时长（秒）

ALTER TABLE text_segments ADD COLUMN audio_duration REAL;

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_text_segments_audio_duration ON text_segments(audio_duration);
