"""
APL数据库服务
负责APL相关数据的数据库操作
"""

import asyncio
import os
import uuid
from typing import Any, Self

import aiofiles
import aiosqlite
import toml

from zsim.define import COSTOM_APL_DIR, DEFAULT_APL_DIR, SQLITE_PATH


class APLDatabase:
    """APL数据库操作类"""

    def __init__(self):
        """初始化APL数据库"""
        self.__initialized = False

    @classmethod
    async def creat(cls) -> Self:
        """初始化APL数据库"""
        self = cls()
        await self._init_database()
        self.__initialized = True
        return self

    async def _init_database(self):
        """初始化数据库表"""
        if self.__initialized:
            return

        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS apl_configs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    comment TEXT,
                    create_time TEXT,
                    latest_change_time TEXT,
                    content TEXT NOT NULL
                )
            """)
            await db.commit()

    async def get_apl_templates(self) -> list[dict[str, Any]]:
        """获取所有APL模板"""
        default_templates = await self._get_apl_from_dir(DEFAULT_APL_DIR, "default")
        custom_templates = await self._get_apl_from_dir(COSTOM_APL_DIR, "custom")
        return default_templates + custom_templates

    async def get_apl_config(self, config_id: str) -> dict[str, Any] | None:
        """异步获取特定APL配置"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            async with db.execute(
                "SELECT title, author, comment, create_time, latest_change_time, content FROM apl_configs WHERE id = ?",
                (config_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    # 解析TOML内容
                    content = toml.loads(row[5])
                    result = {
                        "title": row[0],
                        "author": row[1],
                        "comment": row[2],
                        "create_time": row[3],
                        "latest_change_time": row[4],
                        **content,
                    }
                    return result
                return None

    async def create_apl_config(self, config_data: dict[str, Any]) -> str:
        """异步创建新的APL配置"""
        from datetime import datetime

        # 生成唯一ID
        config_id = str(uuid.uuid4())

        # 提取通用信息
        title = config_data.get("title", "")
        author = config_data.get("author", "")
        comment = config_data.get("comment", "")

        # 系统决定创建时间和最后修改时间
        current_time = datetime.now().isoformat()
        create_time = current_time
        latest_change_time = current_time

        # 创建要存储的配置数据副本（不包含通用信息）
        content_data = config_data.copy()
        content_data.pop("title", None)
        content_data.pop("author", None)
        content_data.pop("comment", None)
        content_data.pop("create_time", None)
        content_data.pop("latest_change_time", None)

        # 将配置数据转换为TOML格式
        content = toml.dumps(content_data)

        async with aiosqlite.connect(SQLITE_PATH) as db:
            await db.execute(
                """
                INSERT INTO apl_configs 
                (id, title, author, comment, create_time, latest_change_time, content)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (config_id, title, author, comment, create_time, latest_change_time, content),
            )
            await db.commit()
        return config_id

    async def update_apl_config(self, config_id: str, config_data: dict[str, Any]) -> bool:
        """异步更新APL配置"""
        from datetime import datetime

        # 提取通用信息
        title = config_data.get("title", "")
        author = config_data.get("author", "")
        comment = config_data.get("comment", "")

        # 获取现有的create_time（保持不变）
        # 系统决定最后修改时间
        latest_change_time = datetime.now().isoformat()

        # 创建要存储的配置数据副本（不包含通用信息）
        content_data = config_data.copy()
        content_data.pop("title", None)
        content_data.pop("author", None)
        content_data.pop("comment", None)
        content_data.pop("create_time", None)
        content_data.pop("latest_change_time", None)

        # 将配置数据转换为TOML格式
        content = toml.dumps(content_data)

        async with aiosqlite.connect(SQLITE_PATH) as db:
            # 先获取现有的create_time
            async with db.execute(
                "SELECT create_time FROM apl_configs WHERE id = ?", (config_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    create_time = row[0]
                else:
                    # 如果记录不存在，使用当前时间作为create_time
                    create_time = latest_change_time

            cursor = await db.execute(
                """
                UPDATE apl_configs 
                SET title = ?, author = ?, comment = ?, create_time = ?, latest_change_time = ?, content = ?
                WHERE id = ?
                """,
                (title, author, comment, create_time, latest_change_time, content, config_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_apl_config(self, config_id: str) -> bool:
        """异步删除APL配置"""
        async with aiosqlite.connect(SQLITE_PATH) as db:
            cursor = await db.execute("DELETE FROM apl_configs WHERE id = ?", (config_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def export_apl_config(self, config_id: str, file_path: str) -> bool:
        """导出APL配置到TOML文件"""
        try:
            config = await self.get_apl_config(config_id)
            if config:
                # 创建要导出的配置数据副本（不包含数据库特定字段）
                export_data = config.copy()
                export_data.pop("create_time", None)
                export_data.pop("latest_change_time", None)

                # 将配置数据转换为TOML格式并保存到文件
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(toml.dumps(export_data))
                return True
            else:
                return False
        except Exception as e:
            print(f"Error exporting APL config {config_id}: {e}")
            return False

    async def import_apl_config(self, file_path: str) -> str | None:
        """从TOML文件导入APL配置"""
        try:
            # 读取TOML文件
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                config_data = toml.loads(await f.read())

            # 保存到数据库
            config_id = await self.create_apl_config(config_data)
            return config_id
        except Exception as e:
            print(f"Error importing APL config from {file_path}: {e}")
            return None

    async def get_apl_files(self) -> list[dict[str, Any]]:
        """获取所有APL文件列表"""
        # 获取默认APL文件
        default_files = await self._get_apl_files_from_dir(DEFAULT_APL_DIR, "default")
        # 获取自定义APL文件
        custom_files = await self._get_apl_files_from_dir(COSTOM_APL_DIR, "custom")
        return default_files + custom_files

    async def get_apl_file_content(self, file_id: str) -> dict[str, Any] | None:
        """获取APL文件内容"""
        # 根据file_id获取对应的APL文件内容
        # 解析file_id获取source和相对路径
        try:
            if file_id.startswith("default_"):
                rel_path = file_id[len("default_") :]
                base_dir = DEFAULT_APL_DIR
            elif file_id.startswith("custom_"):
                rel_path = file_id[len("custom_") :]
                base_dir = COSTOM_APL_DIR
            else:
                return None

            file_path = os.path.join(base_dir, rel_path)

            if os.path.exists(file_path):
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()

                return {"file_id": file_id, "content": content, "file_path": file_path}
            else:
                return None
        except Exception as e:
            print(f"Error reading APL file {file_id}: {e}")
            return None

    async def create_apl_file(self, file_data: dict[str, Any]) -> str:
        """创建新的APL文件"""
        # 实现创建APL文件的逻辑
        try:
            name = file_data.get("name", "new_apl.toml")
            content = file_data.get("content", "")

            # 确保文件名以.toml结尾
            if not name.endswith(".toml"):
                name += ".toml"

            # 保存到自定义目录
            file_path = os.path.join(COSTOM_APL_DIR, name)

            # 确保目录存在
            os.makedirs(COSTOM_APL_DIR, exist_ok=True)

            # 写入文件
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)

            # 生成文件ID
            file_id = f"custom_{name}"
            return file_id
        except Exception as e:
            raise Exception(f"Failed to create APL file: {e}")

    async def update_apl_file(self, file_id: str, content: str) -> bool:
        """更新APL文件内容"""
        # 实现更新APL文件内容的逻辑
        try:
            # 解析file_id获取source和相对路径
            if file_id.startswith("default_"):
                # 不允许更新默认文件
                return False
            elif file_id.startswith("custom_"):
                rel_path = file_id[len("custom_") :]
                base_dir = COSTOM_APL_DIR
            else:
                return False

            file_path = os.path.join(base_dir, rel_path)

            if os.path.exists(file_path):
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(content)
                return True
            else:
                return False
        except Exception as e:
            print(f"Error updating APL file {file_id}: {e}")
            return False

    async def delete_apl_file(self, file_id: str) -> bool:
        """删除APL文件"""
        # 实现删除APL文件的逻辑
        try:
            # 解析file_id获取source和相对路径
            if file_id.startswith("default_"):
                # 不允许删除默认文件
                return False
            elif file_id.startswith("custom_"):
                rel_path = file_id[len("custom_") :]
                base_dir = COSTOM_APL_DIR
            else:
                return False

            file_path = os.path.join(base_dir, rel_path)

            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            else:
                return False
        except Exception as e:
            print(f"Error deleting APL file {file_id}: {e}")
            return False

    async def _get_apl_from_dir(self, apl_dir: str, source_type: str) -> list[dict[str, Any]]:
        """从指定目录获取APL模板"""
        apl_list = []

        if not os.path.exists(apl_dir):
            return apl_list

        for root, _, files in os.walk(apl_dir):
            for file in files:
                if file.endswith(".toml"):
                    file_path = os.path.join(root, file)
                    try:
                        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                            apl_data = toml.loads(await f.read())

                        # 提取基本信息
                        general_info = apl_data.get("general", {})
                        apl_info = {
                            "id": f"{source_type}_{os.path.relpath(file_path, apl_dir).replace(os.sep, '_')}",
                            "title": general_info.get("title", ""),
                            "author": general_info.get("author", ""),
                            "comment": general_info.get("comment", ""),
                            "create_time": general_info.get("create_time", ""),
                            "latest_change_time": general_info.get("latest_change_time", ""),
                            "source": source_type,
                            "file_path": file_path,
                        }
                        apl_list.append(apl_info)
                    except Exception as e:
                        # 记录错误但继续处理其他文件
                        print(f"Error loading APL file {file_path}: {e}")

        return apl_list

    async def _get_apl_files_from_dir(self, apl_dir: str, source_type: str) -> list[dict[str, Any]]:
        """从指定目录获取APL文件列表"""
        return await asyncio.to_thread(self._sync_get_apl_files_from_dir, apl_dir, source_type)

    def _sync_get_apl_files_from_dir(self, apl_dir: str, source_type: str) -> list[dict[str, Any]]:
        file_list = []

        if not os.path.exists(apl_dir):
            return file_list

        for root, _, files in os.walk(apl_dir):
            for file in files:
                if file.endswith(".toml"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, apl_dir)

                    file_info = {
                        "id": f"{source_type}_{rel_path.replace(os.sep, '_')}",
                        "name": file,
                        "path": rel_path,
                        "source": source_type,
                        "full_path": file_path,
                    }
                    file_list.append(file_info)

        return file_list


__apl_db: APLDatabase | None = None


async def get_apl_db() -> APLDatabase:
    global __apl_db
    if __apl_db is None:
        __apl_db = await APLDatabase.creat()
    return __apl_db
