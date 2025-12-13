# 修复音频时长字段数据和项目状态更新问题

本文档说明如何修复项目ID为1的1.0.0版本项目的以下问题：
1. `audio_duration` 字段缺少数据
2. 视频生成失败时项目状态不更新为 FAILED

## 问题背景

### 问题1：audio_duration 字段缺少数据
在1.0.0版本中，升级到新版本后虽然添加了 `audio_duration` 字段，但没有自动填充已存在的音频段落的时长数据。这导致视频生成时无法从数据库读取音频时长，而是需要实时计算，效率较低。

### 问题2：视频生成失败时项目状态不更新
当视频生成失败时，虽然记录了错误日志，但由于应用上下文问题，项目状态没有被正确更新为 `FAILED`，导致用户在界面上看不到错误状态。

## 解决方案

### 修复1：自动填充 audio_duration 字段

#### 方案A：自动迁移（推荐）
应用启动时会自动检测并执行迁移006，如果发现 `audio_duration` 为 NULL 的记录，将自动从音频文件获取时长并填充到数据库。

**前置条件**：需要安装 moviepy 库
```bash
pip install moviepy
```

**执行过程**：
1. 启动应用
2. 应用会自动执行迁移006
3. 日志中会显示填充进度
4. 完成后即可正常生成视频

#### 方案B：手动执行脚本
如果自动迁移失败或未执行，可以手动运行脚本：

```bash
# 进入项目根目录
cd d:\github\NovelToVideo-main

# 运行脚本填充 audio_duration
python scripts/populate_audio_duration.py
```

**脚本输出示例**：
```
======================================================================
填充 audio_duration 字段数据
======================================================================

开始填充 audio_duration 字段，共 2259 条记录
...
填充完成！成功: 2259, 跳过: 0, 错误: 0

======================================================================
✅ 成功完成！
现在可以正常生成视频了。
======================================================================
```

### 修复2：项目状态更新修复

已在以下文件中修复：

1. **app/services/task_scheduler.py** - 视频生成任务处理器
   - 当视频生成返回失败时，使用应用上下文更新项目状态为 FAILED
   - 当视频生成异常时，使用应用上下文更新项目状态为 FAILED
   
2. **app/services/video_service.py** - 视频服务
   - 当视频合成失败时，更新项目状态为 FAILED
   - 异常时也会更新项目状态为 FAILED

**变更详情**：
- 在线程内使用 `TaskScheduler._app.app_context()` 包装数据库操作
- 确保数据库连接正确建立在 Flask 应用上下文中

## 验证修复

### 验证1：检查 audio_duration 数据

使用 SQLite 查看数据库中的数据：
```sql
-- 检查 audio_duration 是否已填充
SELECT COUNT(*) as total,
       COUNT(audio_duration) as filled,
       SUM(CASE WHEN audio_duration IS NULL THEN 1 ELSE 0 END) as null_count
FROM text_segments
WHERE project_id = 1;

-- 应该显示：
-- total=2259, filled=2259, null_count=0
```

### 验证2：测试视频生成失败状态

1. 尝试生成视频（此时应该不会出现"没有找到待处理的视频合成队列"错误）
2. 如果生成失败，检查项目状态是否正确显示为 "失败"

## 文件变更说明

### 新增文件
- `scripts/populate_audio_duration.py` - 手动填充脚本

### 修改文件
1. **app/utils/migrations.py**
   - 添加迁移006：`_migration_006_populate_audio_duration()`
   - 在迁移列表中添加迁移006

2. **app/services/task_scheduler.py**
   - 修复 `_run_video_task()` 方法中的应用上下文问题
   - 添加失败时的项目状态更新

3. **app/services/video_service.py**
   - 添加视频合成失败时的项目状态更新

## 常见问题

### Q1：moviepy 未安装怎么办？
**A**：执行以下命令安装：
```bash
pip install moviepy
```

### Q2：手动执行脚本后仍然出现错误？
**A**：检查以下几点：
1. 确认音频文件存在于 `temp/audio/{project_id}/` 目录
2. 查看日志中是否有具体的错误信息
3. 确认数据库中 `audio_path` 字段不为空

### Q3：项目状态仍然显示为"处理中"？
**A**：
1. 确认已应用本修复中的所有代码变更
2. 重启 Flask 应用
3. 检查浏览器缓存，刷新页面
4. 查看应用日志是否有错误信息

## 相关文档

- [数据库迁移](DATABASE_MIGRATIONS.md) - 了解更多迁移信息
- [视频生成优化](VIDEO_GENERATION_OPTIMIZATION.md) - 了解视频生成流程
