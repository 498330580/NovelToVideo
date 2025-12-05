"""数据库工具模块"""
import sqlite3
from flask import g
from pathlib import Path


def get_db():
    """获取数据库连接"""
    if 'db' not in g:
        from config import DefaultConfig
        
        # 确保数据库目录存在
        db_path = Path(DefaultConfig.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        g.db = sqlite3.connect(
            DefaultConfig.DATABASE_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        
        # 启用外键约束
        g.db.execute('PRAGMA foreign_keys = ON')
        
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    
    if db is not None:
        db.close()


def init_db():
    """初始化数据库"""
    from config import DefaultConfig
    
    db = get_db()
    
    # 检查是否已初始化（通过检查初始化标记表）
    try:
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='db_init_marker'")
        if cursor.fetchone():
            # 检查标记是否存在
            cursor = db.execute("SELECT COUNT(*) as count FROM db_init_marker")
            result = cursor.fetchone()
            if result and result['count'] > 0:
                print('数据库已初始化，跳过初始化步骤')
                return
    except:
        # 如果检查失败，继续执行初始化
        pass
    
    # 读取并执行SQL初始化脚本
    sql_path = Path(__file__).parent.parent.parent / 'migrations' / 'init_db.sql'
    with open(sql_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    
    # 创建初始化标记表并插入标记
    db.execute('''
        CREATE TABLE IF NOT EXISTS db_init_marker (
            id INTEGER PRIMARY KEY,
            initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入初始化标记
    db.execute("INSERT OR REPLACE INTO db_init_marker (id) VALUES (1)")
    
    db.commit()
    print('数据库初始化成功!')


def execute_query(query, params=None, fetch=True):
    """
    执行SQL查询
    
    Args:
        query: SQL查询语句
        params: 查询参数
        fetch: 是否返回查询结果
        
    Returns:
        查询结果列表或None
    """
    db = get_db()
    cursor = db.cursor()
    
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    
    if fetch:
        return cursor.fetchall()
    else:
        db.commit()
        return cursor.lastrowid


def execute_many(query, params_list):
    """
    批量执行SQL语句
    
    Args:
        query: SQL查询语句
        params_list: 参数列表
        
    Returns:
        影响的行数
    """
    db = get_db()
    cursor = db.cursor()
    cursor.executemany(query, params_list)
    db.commit()
    return cursor.rowcount
