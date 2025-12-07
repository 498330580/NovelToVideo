# 路径相对化修改总结

## 修改目的
将数据库中存储的路径从绝对路径改为相对路径，避免项目文件夹位置变化后路径失效。

## 修改内容

### 1. Project 模型 (`app/models/project.py`)

#### 新增方法：
- `convert_to_relative_path(absolute_path)`: 将绝对路径转换为相对路径（仅保存目录名）
- `convert_to_absolute_path(relative_path)`: 将相对路径转换为绝对路径（拼接 output 目录）
- `get_absolute_output_path()`: 获取项目的绝对输出路径

#### 修改方法：
- `to_dict()`: 返回绝对路径供前端显示

#### 路径存储格式：
- **数据库存储**: `{项目名称}` (相对路径，仅目录名)
- **实际路径**: `output/{项目名称}` (绝对路径)

### 2. ProjectService (`app/services/project_service.py`)

#### 修改内容：
- `create_project()`: 创建项目时保存相对路径到数据库
- `delete_project()`: 使用 `get_absolute_output_path()` 获取绝对路径进行删除

### 3. VideoService (`app/services/video_service.py`)

#### 修改内容：
- `generate_project_videos()`: 使用 `get_absolute_output_path()` 获取输出路径
- `_merge_and_split_videos()`: 保存视频片段时使用相对路径

#### 视频片段路径格式：
- **数据库存储**: `{项目名称}/{文件名}` (相对路径)
- **实际路径**: `output/{项目名称}/{文件名}` (绝对路径)

### 4. TextSegment 模型 (`app/models/text_segment.py`)

#### 已有修复：
- `get_absolute_audio_path()`: 修复为包含项目ID的路径
- `convert_to_absolute_path()`: 标记为过时，添加警告注释

#### 音频路径格式：
- **数据库存储**: `segment_{id}.mp3` (文件名)
- **实际路径**: `temp/audio/{project_id}/segment_{id}.mp3` (绝对路径)

## 数据库迁移

### 迁移脚本：`scripts/migrate_output_paths.py`

#### 功能：
将现有项目的 `output_path` 从绝对路径转换为相对路径

#### 运行方法：
```bash
python scripts/migrate_output_paths.py
```

#### 迁移效果：
- 旧路径: `D:\github\NovelToVideo-main\output\项目名称`
- 新路径: `项目名称`

## 目录结构

```
NovelToVideo-main/
├── output/                      # 输出目录（基准目录）
│   ├── 项目1/                   # 项目输出文件夹（相对路径）
│   │   ├── 项目1_1.mp4
│   │   ├── 项目1_2.mp4
│   │   └── ...
│   └── 项目2/
│       └── ...
├── temp/                        # 临时目录
│   ├── audio/
│   │   ├── 1/                   # 项目ID=1的音频文件
│   │   │   ├── segment_1.mp3
│   │   │   └── ...
│   │   └── 2/
│   ├── images/
│   │   ├── 1/
│   │   ├── 2/
│   │   └── custom_backgrounds/  # 全局共享
│   └── video_segments/
│       ├── 1/
│       └── 2/
└── data/
    └── novel_to_video.db        # 数据库
```

## 数据库字段说明

### projects 表
- `output_path`: 相对路径，仅存储项目目录名（如 "项目名称"）

### text_segments 表
- `audio_path`: 相对路径，仅存储文件名（如 "segment_1.mp3"）
- 需要配合 `project_id` 构建完整路径: `temp/audio/{project_id}/{audio_path}`

### video_segments 表
- `video_path`: 相对路径，存储 "项目目录/文件名"（如 "项目名称/项目名称_1.mp4"）
- 完整路径: `output/{video_path}`

## 优势

1. **可移植性**: 项目文件夹可以移动到任何位置，只要相对结构不变即可
2. **跨平台**: 相对路径在不同操作系统间更兼容
3. **简洁性**: 数据库存储的路径更短，更易维护
4. **向后兼容**: 代码会自动处理绝对路径（通过 `os.path.isabs()` 检查）

## 注意事项

1. 所有获取文件路径的地方都应该使用 `get_absolute_*_path()` 方法
2. 保存路径到数据库时应该使用 `convert_to_relative_path()` 方法
3. 前端显示路径时会自动转换为绝对路径（通过 `to_dict()` 方法）
4. 现有数据库需要运行迁移脚本才能正常工作
