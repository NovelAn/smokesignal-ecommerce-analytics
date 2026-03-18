"""
系统级数据库配置管理器
支持从用户主目录读取 database_config.json 配置文件
"""
import os
import json
import re
import pymysql.cursors


class DBConfigManager:
    """数据库配置管理器"""

    # 系统级配置文件路径（用户主目录）
    SYSTEM_DB_CONFIG_PATH = os.path.join(os.path.expanduser("~"), "database_config.json")

    @classmethod
    def load_db_config(cls):
        """
        加载数据库配置
        返回: databases 列表，格式: [{"name": "...", "host": "...", ...}, ...]
        """
        if not os.path.exists(cls.SYSTEM_DB_CONFIG_PATH):
            raise FileNotFoundError(
                f"数据库配置文件不存在: {cls.SYSTEM_DB_CONFIG_PATH}\n"
                f"请创建配置文件或从其他项目复制。"
            )

        with open(cls.SYSTEM_DB_CONFIG_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove comments (lines starting with //)
        lines = [line for line in content.splitlines() if not line.strip().startswith('//')]
        content = '\n'.join(lines)

        # Remove trailing commas
        content = re.sub(r',(\s*[}\]])', r'\1', content)

        try:
            config = json.loads(content)
        except json.JSONDecodeError as e:
            # If parsing fails, try to give a helpful error
            raise json.JSONDecodeError(f"解析配置文件失败: {e.msg}", e.doc, e.pos)

        return config.get('databases', [])

    @classmethod
    def get_db_config_for_pymysql(cls):
        """
        获取适配 PyMySQL 的数据库配置
        返回: 格式化的数据库配置列表
        """
        dbs = cls.load_db_config()
        result = []
        for db in dbs:
            result.append({
                "host": db.get("host"),
                "user": db.get("user"),
                "password": db.get("password"),
                "database": db.get("database"),
                "port": db.get("port"),
                "charset": db.get("charset", "utf8mb4"),
                "cursorclass": pymysql.cursors.DictCursor  # 使用实际的类，不是字符串
            })
        return result
