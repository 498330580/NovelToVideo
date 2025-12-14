# 📚 NovelToVideo 文档中心

欢迎来到小说转视频系统的文档中心！这里包含了所有重要的开发和使用文档。

## 📖 文档导航

### 🚀 快速开始
- **[CHANGELOG.md](CHANGELOG.md)** - 更新日志
  - 版本功能和特性说明
  - 已修复问题和优化内容
  - 系统需求

- **[RELEASE_NOTES.md](RELEASE_NOTES.md)** - 发布说明
  - 系统需求和部署指南
  - 已知限制和注意事项
  - 后续版本规划

### 📋 版本信息
- **[RELEASE_SUMMARY.md](RELEASE_SUMMARY.md)** - 发布总结
  - 版本统计和变更清单
  - 核心成就和修复内容
  - 发布工件和部署方式

### 🔧 技术文档

#### 架构和优化
- **[VIDEO_GENERATION_OPTIMIZATION.md](VIDEO_GENERATION_OPTIMIZATION.md)** - 视频生成内存优化方案
  - 内存优化问题分析
  - 新流程设计（两阶段处理）
  - 性能对比和使用建议

- **[RELATIVE_PATH_MIGRATION.md](RELATIVE_PATH_MIGRATION.md)** - 路径相对化改造
  - 数据库路径改为相对路径
  - 迁移脚本和方案说明
  - 目录结构和数据库字段说明

## 📑 文档详情

### CHANGELOG.md
**内容**: 项目更新日志
- 版本功能和新增特性列表
- 已修复的问题清单
- 代码优化说明
- 系统需求和部署方式
- 已知限制

**适合人群**: 所有用户、版本管理人员

---

### RELEASE_NOTES.md
**内容**: 系统发布说明
- 发布亮点和版本信息
- 部署环境要求
- 快速启动指南（传统和Docker部署）
- 版本支持说明
- 升级和后续计划

**适合人群**: 系统管理员、初次部署用户

---

### RELEASE_SUMMARY.md
**内容**: 版本发布总结
- 发布完成情况和文件清单
- 代码变更统计
- 核心成就和已修复问题
- 版本特点和支持情况
- 后续版本方向

**适合人群**: 项目经理、开发团队

---

### VIDEO_GENERATION_OPTIMIZATION.md
**内容**: 视频生成内存优化方案
- 问题描述（WinError 1455内存溢出）
- 优化方案详解
  - 阶段一：逐个生成并保存
  - 阶段二：合并和分片
- 核心优化点和实现细节
- 性能对比（优化前后）
- 临时文件管理策略
- 使用建议和监控日志

**适合人群**: 后端开发者、系统优化工程师

---

### RELATIVE_PATH_MIGRATION.md
**内容**: 数据库路径相对化改造
- 修改目的和内容总结
- 各个模块的改动说明
  - Project 模型：路径转换方法
  - ProjectService：创建和删除逻辑
  - VideoService：绝对路径使用
  - TextSegment：音频路径修复
- 数据库迁移脚本说明
- 目录结构和数据库字段说明
- 优势和注意事项

**适合人群**: 数据库管理员、后端开发者

---

## 🎯 常见问题

### Q: 我应该先看哪个文档？
A: 根据你的角色：
- **快速了解**: 先看 CHANGELOG.md
- **初次部署**: 看 RELEASE_NOTES.md
- **了解版本**: 看 RELEASE_SUMMARY.md
- **优化视频生成**: 看 VIDEO_GENERATION_OPTIMIZATION.md
- **数据库升级**: 看 RELATIVE_PATH_MIGRATION.md

### Q: 如何迁移现有数据库？
A: 参考 RELATIVE_PATH_MIGRATION.md 中的数据库迁移部分

### Q: 视频生成出错怎么办？
A: 查看 VIDEO_GENERATION_OPTIMIZATION.md 中的监控和日志部分

### Q: 支持哪些操作系统？
A: 查看 RELEASE_NOTES.md 中的版本支持说明

---

## 📊 文件结构

```
docs/
├── README.md                           # 本文件（文档导航）
├── CHANGELOG.md                        # 更新日志
├── RELEASE_NOTES.md                    # 发布说明
├── RELEASE_SUMMARY.md                  # 发布总结
├── VIDEO_GENERATION_OPTIMIZATION.md    # 视频生成优化方案
└── RELATIVE_PATH_MIGRATION.md          # 路径相对化改造
```

---

## 🔗 相关资源

### 项目仓库
- GitHub: https://github.com/498330580/NovelToVideo.git

### 项目根目录文件
- `README.md` - 项目总体说明
- `requirements.txt` - Python依赖列表
- `docker-compose.yml` - Docker部署配置

---

## 💡 开发建议

### 代码修改前必读
1. 阅读 RELATIVE_PATH_MIGRATION.md 了解路径规范
2. 阅读 VIDEO_GENERATION_OPTIMIZATION.md 理解内存管理

### 新增功能建议
1. 遵循现有的路径相对化规范
2. 使用 `get_absolute_*_path()` 获取绝对路径
3. 参考内存优化方案处理大数据

### 性能优化建议
1. 查看 VIDEO_GENERATION_OPTIMIZATION.md 中的优化思路
2. 确保临时文件正确清理
3. 监控系统资源使用

---

## 📝 更新历史

### v1.0.0 (2025-12-04)
- ✅ 首次发布完整文档
- ✅ 添加路径相对化文档
- ✅ 添加视频生成优化文档

---

## 👥 贡献者

感谢所有为项目文档做出贡献的开发者！

---

## 📄 许可证

本项目文档遵循与项目相同的许可证。

---

**最后更新**: 2025-12-07  
**维护者**: NovelToVideo 开发团队

