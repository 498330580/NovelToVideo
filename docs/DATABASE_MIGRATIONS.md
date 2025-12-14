# 数据库自动迁移说明

## 概述

从版本 1.x.x 开始，应用已实现**自动迁移机制**，用户无需手动执行数据库迁移脚本。升级应用后，在启动时会自动检测并执行所有待处理的迁移。

## 工作原理

### 自动执行流程

```
应用启动 (run.py)
    ↓
初始化数据库 (init_db)
    ↓
执行自动迁移 (run_migrations) ← 新增
    ↓
扫描 db_migrations 表获取当前版本
    ↓
按顺序执行所有大于当前版本的迁移
    ↓
记录迁移执行结果
    ↓
应用正常运行
```

### 迁移版本跟踪

应用创建 `db_migrations` 表来追踪已执行的迁移：

```sql
CREATE TABLE db_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL UNIQUE,           -- 迁移版本号
    name TEXT NOT NULL,                        -- 迁移描述
    status TEXT NOT NULL,                      -- 'completed' 或 'failed'
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 迁移列表

### 迁移 #1: 为 text_segments 表添加 audio_duration 字段

**版本**: 1.0.1+  
**说明**: 添加 `audio_duration` 字段用于存储音频时长，优化视频合成性能  
**影响**: 
- 音频合成时会自动保存音频时长到数据库
- 视频合成时优先从数据库读取时长，避免扫描音频文件
- 视频合成启动速度提升 100-1000 倍

## 用户升级流程

### 从 1.0.0 升级到 1.0.1+

1. **下载新版本应用**
   ```bash
   git pull origin main
   ```

2. **启动应用** （无需任何额外步骤）
   ```bash
   .venv\Scripts\Activate.ps1
   python run.py
   ```

3. **观察日志输出**
   
   应用启动时会输出迁移执行日志：
   
   ```
   ======================================================================
   开始检查并执行数据库迁移...
   ======================================================================
   当前数据库迁移版本: 0
   
   执行迁移 #1: 为 text_segments 表添加 audio_duration 字段
   迁移001: 开始为 text_segments 表添加 audio_duration 字段...
   迁移001: 成功添加 audio_duration 字段
   迁移001: 成功创建索引
   迁移001: 完成！后续视频合成会从数据库读取音频时长
   ✅ 迁移 #1 成功
   ======================================================================
   ✨ 所有迁移执行完成
   ======================================================================
   ```

4. **应用正常使用**
   
   迁移完成后，应用会继续正常启动，无需任何手动操作。

## 故障排查

### 迁移失败怎么办？

如果某个迁移在自动执行时失败，应用仍会启动（但会记录警告日志）。

**恢复步骤：**

1. **检查日志** 查看具体错误信息
   ```
   tail -f logs/app.log | grep "迁移"
   ```

2. **手动执行迁移** （可选）
   ```bash
   .venv\Scripts\Activate.ps1
   python scripts/migrate_add_audio_duration.py
   ```

3. **重启应用**
   ```bash
   python run.py
   ```

### 已执行的迁移会重复执行吗？

**不会**。应用通过 `db_migrations` 表追踪已执行的迁移版本，只会执行大于当前版本的迁移。

例如：
- 首次启动：执行迁移 #1 → 版本升级到 1
- 第二次启动：检测版本已是 1，无需执行任何迁移
- 升级到有迁移 #2 的版本：只执行迁移 #2

## 开发者指南

### 添加新迁移

如果需要添加新的数据库迁移，请按以下步骤操作：

1. **在 `app/utils/migrations.py` 中添加新的迁移函数**

   ```python
   def _migration_002_your_migration_name():
       """
       迁移002：简要说明
       详细说明...
       """
       try:
           conn = get_db_connection()
           cursor = conn.cursor()
           
           # 执行迁移逻辑
           logger.info("迁移002: 开始...")
           
           # ... 你的代码 ...
           
           conn.commit()
           conn.close()
           logger.info("迁移002: 完成！")
           return True
           
       except Exception as e:
           logger.error(f"迁移002失败: {str(e)}", exc_info=True)
           return False
   ```

2. **在 `run_migrations()` 的 migrations 字典中注册新迁移**

   ```python
   migrations = {
       1: (_migration_001_add_audio_duration, "为 text_segments 表添加 audio_duration 字段"),
       2: (_migration_002_your_migration_name, "迁移002的简要说明"),  # 新增
   }
   ```

3. **更新版本号** （在 VERSION 文件中）
   ```
   1.0.2
   ```

4. **编写迁移说明** （在本文档中添加新的迁移项）

### 迁移的最佳实践

- ✅ 每个迁移应该是原子操作（全部成功或全部失败）
- ✅ 添加详细的日志记录
- ✅ 检查字段/表是否已存在，避免重复创建
- ✅ 处理所有可能的异常
- ❌ 不要执行耗时操作（如读取所有音频文件）在迁移中
- ❌ 不要在迁移中修改应用代码逻辑

## 常见问题

**Q: 迁移会影响现有数据吗？**  
A: 不会。迁移只添加新字段或索引，不删除或修改现有数据。

**Q: 可以回滚迁移吗？**  
A: 当前暂不支持迁移回滚。如需回滚，请使用数据库备份或手动编辑 `db_migrations` 表。

**Q: 迁移会花多长时间？**  
A: 迁移001 通常在几秒内完成。迁移耗时取决于数据库大小和系统性能。

**Q: 多个应用实例同时启动会产生冲突吗？**  
A: SQLite 会处理并发访问，但建议避免多个应用实例同时启动。如果发生冲突，重启应用即可自动恢复。
