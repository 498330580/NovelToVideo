## 项目简介

> ⚠️ **重要提示**: 本系统生成的音频和视频文件占用磁盘空间较大，请确保部署到具有足够存储容量的硬盘空间中（建议至少10GB可用空间）。
> 
这是一个基于 Web 的小说语音视频生成系统,能够将文本小说自动转换为带语音旁白的视频内容。系统采用 Flask 提供 Web 管理界面,使用微软 Edge TTS 进行高质量语音合成,并通过视频处理技术生成最终的视频文件。

## 📚 文档说明

项目的所有技术文档已整理到 **[docs](docs/)** 文件夹，包括：

| 文档 | 说明 |
|------|------|
| **[docs/README.md](docs/README.md)** | 📖 文档导航中心 - 所有文档的索引和快速链接 |
| **[docs/CHANGELOG.md](docs/CHANGELOG.md)** | 📝 更新日志 - 版本功能、修复和优化记录 |
| **[docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)** | 🚀 发布说明 - 部署要求和使用指南 |
| **[docs/RELEASE_SUMMARY.md](docs/RELEASE_SUMMARY.md)** | 📊 发布总结 - 版本统计和核心成就 |
| **[docs/VIDEO_GENERATION_OPTIMIZATION.md](docs/VIDEO_GENERATION_OPTIMIZATION.md)** | ⚡ 内存优化方案 - 视频生成的优化细节 |
| **[docs/RELATIVE_PATH_MIGRATION.md](docs/RELATIVE_PATH_MIGRATION.md)** | 🔧 路径相对化改造 - 数据库和路径管理方案 |

**💡 快速开始**: 首先查看 [docs/README.md](docs/README.md) 了解所有文档的详细说明。

### 核心功能

- ✅ 自动化将文字内容转换为视频格式
- ✅ 提供可视化的 Web 管理界面
- ✅ 支持大规模文本处理,自动分段与合并
- ✅ 多线程并行处理(最多16线程),提升生成效率
- ✅ 灵活的参数配置(语音、视频、分段参数)
- ✅ 实时任务进度监控
- ✅ 支持多项目管理

## 技术栈

- **后端框架**: Flask 3.0.0
- **语音合成**: edge-tts 6.1.9
- **图像处理**: Pillow 10.1.0
- **视频处理**: moviepy 1.0.3
- **数据库**: SQLite 3
- **运行环境**: Python 3.10

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows/Linux/macOS 操作系统
- 至少 2GB 可用内存
- 至少 10GB 可用磁盘空间

### Docker部署（推荐）

1. **确保已安装Docker**

2. **构建并启动容器**

```bash
# 克隆或下载项目
cd 小说转视频

# 使用docker-compose启动服务
docker-compose up -d
```

3. **访问Web界面**

打开浏览器访问: http://localhost:5000

4. **停止服务**

```bash
docker-compose down
```

### 传统安装方式

1. **克隆或下载项目**

```bash
cd 小说转视频
```

2. **激活虚拟环境**

```bash
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **运行应用**

```bash
python run.py
```

5. **访问 Web 界面**

打开浏览器访问: http://127.0.0.1:5000


### 首次使用

1. 在首页点击"创建项目"
2. 填写项目名称和描述
3. 粘贴小说文本内容
4. 根据需要调整语音、视频和分段参数
5. 点击"创建项目"按钮
6. 系统自动开始处理,可在项目详情页查看进度
7. 处理完成后,在输出目录查看生成的视频文件

## 功能说明

### 项目管理

- **创建项目**: 输入项目信息和小说文本,系统自动分段处理
- **查看项目列表**: 查看所有项目及其状态
- **项目详情**: 查看分段信息、处理进度、任务历史
- **删除项目**: 删除项目及其所有相关文件，包括：
  - 项目输出目录中的视频文件
  - 临时音频文件目录
  - 临时图片文件目录（包括项目特定的自定义背景图片）
  - 临时视频片段目录
  - 数据库中的项目记录及相关段落信息

### 参数配置

#### 语音参数

| 参数 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| voice | 语音角色 | zh-CN-XiaoxiaoNeural | 支持20+种中文语音 |
| rate | 语速 | +0% | -50% ~ +100% |
| pitch | 音调 | +0Hz | -50Hz ~ +50Hz |
| volume | 音量 | +0% | -50% ~ +50% |

#### 视频参数

| 参数 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| resolution | 分辨率 | 1920x1080 | 1280x720, 1920x1080, 2560x1440 |
| fps | 帧率 | 30 | 24, 30, 60 |
| bitrate | 码率 | 2000k | 1000k ~ 10000k |
| format | 视频格式 | mp4 | mp4, avi, mkv |
| segment_duration | 分片时长(秒) | 600 | 300 ~ 3600 |

#### 分段参数

| 参数 | 说明 | 默认值 | 可选值 |
|------|------|--------|--------|
| segment_mode | 分段模式 | edge_tts | edge_tts(按Edge-TTS字节限制) |
| max_words | 最大字数 | 10000 | 5000 ~ 20000 |

### 任务监控

- 实时显示任务进度百分比
- 展示当前处理的段落信息
- 查看任务历史记录
- 错误日志查看


### 目录结构

```
app/
├── models/
│   ├── project.py             # 项目模型与状态管理
│   ├── task.py                # 任务模型与状态管理
│   ├── text_segment.py        # 文本分段模型
│   └── video_segment.py       # 视频分段模型
├── services/
│   ├── project_service.py     # 项目管理服务
│   ├── task_scheduler.py      # 后台任务调度与执行
│   ├── tts_service.py         # 语音合成服务
│   ├── video_service.py       # 视频生成服务
│   └── text_processor.py      # 文本分段与预处理
├── routes/
│   ├── project_routes.py      # 项目相关 REST 接口与页面路由
│   ├── task_routes.py         # 任务查询接口
│   └── config_routes.py       # 配置相关接口
├── utils/
│   ├── database.py            # 数据库工具与连接管理
│   ├── file_handler.py        # 文件工具
│   └── logger.py              # 日志工具
├── templates/
│   ├── base.html              # 基础布局
│   ├── dashboard.html         # 首页仪表盘
│   ├── project_list.html      # 项目列表
│   ├── project_detail.html    # 项目详情
│   └── project_create.html    # 创建项目
├── static/
│   ├── css/                   # 样式
│   └── js/                    # 脚本
config/
├── __init__.py
├── default.py                 # 默认配置
└── development.py             # 开发环境配置
migrations/
└── init_db.sql                # 初始化数据库脚本
requirements.txt               # 依赖列表
run.py                         # 应用入口
```

## 使用流程

### 1. 文本导入

系统接收小说文本后,会自动进行:
- 文本编码检测与转换
- 非法字符过滤
- 文本长度验证(最大500万字)

### 2. 文本分段

根据选择的分段模式:
- **按Edge-TTS字节限制分段**: 按照Edge-TTS服务的4096字节限制自动分段，确保语音合成稳定性

### 3. 语音合成

- 多线程并行处理(最多16线程)
- 自动重试机制(失败最多重试3次)
- 支持自定义语音角色、语速、音调、音量

### 4. 视频生成

- 自动生成带项目名称的背景图片
- 将音频与图片合成为视频片段
- 按设定时长分片输出

### 5. 输出结果

生成的视频文件保存在 `output/项目名称/` 目录下,文件命名格式: `项目名称_序号.格式`

## 配置说明

### 数据库配置

默认使用 SQLite 数据库,文件位置: `data/novel_to_video.db`

### 文件路径配置

- 输出目录: `./output`
- 临时目录: `./temp`
- 日志目录: `./logs`

### 性能配置

- 最大线程数: 16
- 最大并发项目数: 5
- 单个项目最大字数: 500万字
- 临时文件最大占用: 50GB

## 常见问题

### 安装问题

**Q: pip install 失败?**
A: 尝试使用国内镜像源:
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

**Q: moviepy 安装失败?**
A: 需要先安装 ffmpeg:
- Windows: 下载 ffmpeg 并添加到系统 PATH
- Linux: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

**Q: Docker部署时视频处理失败?**
A: Docker镜像中需要安装ffmpeg，已在Dockerfile中添加相关安装命令。

### 运行问题

**Q: 启动时提示端口被占用?**
A: 修改 `run.py` 中的端口号:
```python
app.run(host='0.0.0.0', port=5001)  # 改为其他端口
```

**Q: 语音合成失败?**
A: 检查网络连接,Edge TTS 需要访问微软服务器

**Q: 视频生成失败?**
A: 检查磁盘空间是否充足,确保 ffmpeg 已正确安装

### 性能问题

**Q: 处理速度慢?**
A: 
- 减少 max_words 參数,增加段落数量
- 降低视频分辨率和码率
- 确保系统有足够的内存

**Q: 内存占用高?**
A:
- 减少并发线程数
- 及时清理临时文件
- 降低视频质量參数

## ✅ 已修复的问题

**内存溢出问题** ([详见优化方案](docs/VIDEO_GENERATION_OPTIMIZATION.md))
- 原问题：视频合成时出现 `[WinError 1455] 页面文件太小，无法完成操作` 错误
- 原因：2259个音频片段同时加载到内存中
- 解决方案：采用两阶段处理，逐个生成并保存到临时目录，再合并分片
- 效果：内存占用从 N×片段大小 → 1×片段大小

**路径相对化** ([详见改造方案](docs/RELATIVE_PATH_MIGRATION.md))
- 项目文件夹位置变化后仍能正确识别路径
- 数据库中存储相对路径而非绝对路径
- 项目可以随意移动而不影响功能

**其他修复**
- 修复 UnboundLocalError：移除视频生成时的局部导入冲突
- 修复默认背景图片生成问题
- 修复启动速度慢的问题（优化项目状态重置逻辑）
- 修复项目详情页面加载速度（使用估算而非实际读取音频时长）
- 修复视频段落统计数据不一致问题

**任务调度上下文问题** ([详见源代码](app/services/task_scheduler.py))
- 原问题：任务调度触发语音合成时报 `Working outside of application context`
- 原因：后台任务访问数据库时缺少 Flask 应用上下文
- 解决方案：在线程执行任务前使用 `with TaskScheduler._app.app_context()` 包裹
- 验证：应用启动时正确传递 Flask 实例到 TaskScheduler

## 🚀 下一步

整个项目部署了丰富的技术优化和改造，详细文档请查看 [docs](docs/) 文档库：

- 🚀 **[开始使用](docs/RELEASE_NOTES.md)** - 部署和配置指南
- 🔧 **[优化视频生成](docs/VIDEO_GENERATION_OPTIMIZATION.md)** - 内存优化方案
- 📖 **[管理数据库](docs/RELATIVE_PATH_MIGRATION.md)** - 路径相对化改造
- 📝 **[版本更新](docs/CHANGELOG.md)** - 查看特性和修复

## 开发指南

### 扩展语音引擎

在 `app/services/tts_service.py` 中实现统一的 TTS 服务接口,可以轻松切换到其他语音引擎(如阿里云、腾讯云等)。

### 自定义视频样式

修改 `app/services/video_service.py` 中的 `_generate_background_image` 方法,实现自定义背景图片生成逻辑。

### 添加新功能

1. 在 `app/models/` 中定义数据模型
2. 在 `app/services/` 中实现业务逻辑
3. 在 `app/routes/` 中添加路由处理
4. 在 `app/templates/` 中创建前端页面

## 注意事项

1. **版权声明**: 请确保使用的小说文本拥有合法版权或使用许可
2. **资源管理**: 定期清理临时文件和日志文件
3. **数据备份**: 重要项目建议备份数据库文件
4. **网络要求**: Edge TTS 需要稳定的网络连接
5. **磁盘空间**: 确保有足够的磁盘空间存储临时文件和输出视频
6. **文件清理**: 删除项目时会自动清理相关的临时文件，包括：
   - 项目输出目录中的视频文件
   - 临时音频文件目录
   - 临时图片文件目录
   - 临时视频片段目录
   - 项目使用的自定义背景图片

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议,欢迎提交 Issue。
