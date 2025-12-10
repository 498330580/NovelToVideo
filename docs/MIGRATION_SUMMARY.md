# 相对路径迁移总结

## 改动背景
将 `video_synthesis_queue` 和 `temp_video_segments` 表中的文件路径从绝对路径改为相对路径存储，提高项目的可移植性。

## 改动范围

### 1. 数据模型改动

#### TempVideoSegment (app/models/temp_video_segment.py)
**新增方法：**
- `get_absolute_temp_video_path()` - 获取临时视频的绝对路径
  - 如果存储的是相对路径，基于 `DefaultConfig.TEMP_VIDEO_DIR` 进行拼接
  - 如果存储的是绝对路径，直接返回

#### VideoSynthesisQueue (app/models/video_synthesis_queue.py)  
**新增方法：**
- `get_absolute_output_video_path()` - 获取最终输出视频的绝对路径
  - 如果存储的是相对路径，基于项目的输出目录进行拼接
  - 如果存储的是绝对路径，直接返回

### 2. 服务层改动

#### VideoService (app/services/video_service.py)

**generate_and_save_queue() 方法改动：**
- 创建 TempVideoSegment 时，存储相对路径而非绝对路径
  - 旧：`os.path.join(DefaultConfig.TEMP_VIDEO_DIR, str(project_id), f'segment_{segment.id}.mp4')`
  - 新：`os.path.join(str(project_id), f'segment_{segment.id}.mp4')`
  
- 创建 VideoSynthesisQueue 时，存储相对路径而非绝对路径
  - 旧：`os.path.join(output_path, f'{safe_name}_{video_index:03d}.{config.get("format", "mp4")}')`
  - 新：`f'{safe_name}_{video_index:03d}.{config.get("format", "mp4")}'`

**_synthesize_from_queue() 方法改动：**
- 读取队列时，使用 `get_absolute_output_video_path()` 获取绝对路径
- 处理临时视频时，使用 `get_absolute_temp_video_path()` 获取绝对路径
- 删除临时文件时，使用绝对路径进行操作

### 3. 数据迁移

**迁移脚本：** `migrate_relative_paths.py`

**转换规则：**

1. **temp_video_segments 表：**
   - 从绝对路径转换为相对于 `TEMP_VIDEO_DIR` 的相对路径
   - 示例转换：
     ```
     F:\github\小说转视频\temp\1\segment_1.mp4
     → 1\segment_1.mp4
     ```

2. **video_synthesis_queue 表：**
   - 从绝对路径转换为相对于项目输出目录的相对路径
   - 示例转换：
     ```
     F:\github\小说转视频\output\正版修仙\正版修仙_001.mp4
     → 正版修仙_001.mp4
     ```

**迁移结果：**
- ✅ temp_video_segments：2259 条记录转换
- ✅ video_synthesis_queue：161 条记录转换

## 好处

### 1. **提高可移植性**
- 项目可以移动到不同的磁盘或目录而不影响数据库中的路径
- 在不同开发机器、测试环境、生产环境之间迁移更加方便

### 2. **减少数据库大小**
- 相对路径通常比绝对路径短
- 特别是在深度目录结构中，节省空间明显

### 3. **提高安全性**
- 不暴露系统的完整文件路径信息
- 在备份、分享数据库时更安全

### 4. **符合最佳实践**
- 数据库中存储相对路径是行业标准做法
- 与 VideoSegment 模型保持一致（已使用相对路径）

## 使用说明

### 运行迁移脚本
```bash
cd f:\github\小说转视频
.\.venv\Scripts\Activate.ps1
python migrate_relative_paths.py
```

### 代码使用示例

**获取绝对路径进行文件操作：**
```python
# TempVideoSegment
temp_segment = TempVideoSegment.get_by_id(1)
abs_path = temp_segment.get_absolute_temp_video_path()
if os.path.exists(abs_path):
    os.remove(abs_path)

# VideoSynthesisQueue
queue = VideoSynthesisQueue.get_by_id(1)
abs_path = queue.get_absolute_output_video_path()
```

**存储路径：**
```python
# 只存储相对路径
TempVideoSegment.create(
    project_id=1,
    text_segment_id=1,
    temp_video_path='1/segment_1.mp4'  # 相对于 TEMP_VIDEO_DIR
)

VideoSynthesisQueue.create(
    project_id=1,
    video_index=1,
    output_video_path='test_001.mp4',  # 相对于项目输出目录
    temp_segment_ids=[1, 2, 3],
    total_duration=3600
)
```

## 向后兼容性

✅ 完全向后兼容！

新增的 `get_absolute_*_path()` 方法在以下情况都能正确处理：
- 数据库中存储的是新格式（相对路径）
- 数据库中存储的是旧格式（绝对路径）
- 路径混合的情况

## 相关文件变更

- ✅ `app/models/temp_video_segment.py` - 新增 `get_absolute_temp_video_path()` 方法
- ✅ `app/models/video_synthesis_queue.py` - 新增 `get_absolute_output_video_path()` 方法
- ✅ `app/services/video_service.py` - 修改生成和使用路径的方式
- ✅ `migrate_relative_paths.py` - 数据迁移脚本（已执行）

## 测试建议

1. **验证数据库数据**
   ```sql
   -- 验证转换是否成功
   SELECT id, temp_video_path FROM temp_video_segments LIMIT 5;
   SELECT id, output_video_path FROM video_synthesis_queue LIMIT 5;
   ```

2. **功能测试**
   - 验证生成新队列时，路径正确存储为相对路径
   - 验证合成视频时，能正确转换为绝对路径并操作文件
   - 验证断点续传功能正常工作

3. **集成测试**
   - 创建新项目并执行完整的视频合成流程
   - 验证临时文件和输出文件都能正确生成
