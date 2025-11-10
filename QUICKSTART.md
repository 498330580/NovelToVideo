# 快速启动指南

## 1. 安装依赖

```bash
# 确保在项目根目录
cd C:\Users\andy\.qoder\worktree\小说转视频\qoder\project-creation-and-optimization-1762781629

# 激活虚拟环境(如果有)
# Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

如果安装速度慢,可以使用国内镜像:
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 2. 安装 FFmpeg (必需)

### Windows
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压到某个目录,如 `C:\ffmpeg`
3. 添加 `C:\ffmpeg\bin` 到系统环境变量 PATH

### 验证安装
```bash
ffmpeg -version
```

## 3. 启动应用

```bash
python run.py
```

启动成功后,会看到类似输出:
```
数据库初始化完成
启动Flask应用...
访问 http://127.0.0.1:5000 打开Web管理面板
 * Running on http://0.0.0.0:5000
```

## 4. 访问Web界面

打开浏览器访问: http://127.0.0.1:5000

## 5. 创建第一个项目

1. 在首页填写项目信息
2. 粘贴小说文本(可以先用一小段测试,如100字)
3. 调整参数(可使用默认值)
4. 点击"创建项目"
5. 查看处理进度

## 6. 查看输出

生成的视频文件在 `output/项目名称/` 目录下

## 常见问题

### ModuleNotFoundError: No module named 'flask'
解决: `pip install flask`

### ModuleNotFoundError: No module named 'edge_tts'
解决: `pip install edge-tts`

### moviepy 相关错误
解决: 确保已安装 ffmpeg

### 端口被占用
修改 run.py 中的端口号:
```python
app.run(host='0.0.0.0', port=5001)
```

### 网络连接问题
Edge TTS 需要访问微软服务器,确保网络畅通

## 测试用小说文本

```
第一章 开始

这是一个测试章节。系统会自动识别章节标题,并进行语音合成。

你可以粘贴更多的文本内容,系统会自动分段处理。

第二章 继续

第二章的内容...
```

## 项目目录说明

- `output/` - 生成的视频文件
- `temp/` - 临时音频、图片和视频片段
- `logs/` - 日志文件
- `data/` - 数据库文件

## 停止应用

在终端按 `Ctrl + C`

## 下一步

- 查看 README.md 了解完整功能
- 在配置页面查看所有可用参数
- 探索项目管理功能
