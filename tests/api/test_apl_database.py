"""
APL数据库测试
测试APL数据库操作功能
"""

import os
import shutil
import tempfile

import pytest

from zsim.api_src.services.database.apl_db import APLDatabase
from zsim.define import COSTOM_APL_DIR, DEFAULT_APL_DIR, SQLITE_PATH


class TestAPLDatabase:
    """APL数据库测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """设置和清理测试环境"""
        # 保存原始目录
        original_default_dir = DEFAULT_APL_DIR
        original_custom_dir = COSTOM_APL_DIR
        original_sqlite_path = SQLITE_PATH
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        test_default_dir = os.path.join(temp_dir, "default")
        test_custom_dir = os.path.join(temp_dir, "custom")

        # 创建目录
        os.makedirs(test_default_dir, exist_ok=True)
        os.makedirs(test_custom_dir, exist_ok=True)

        # 修改全局变量
        import zsim.define

        zsim.define.DEFAULT_APL_DIR = test_default_dir
        zsim.define.COSTOM_APL_DIR = test_custom_dir

        # 重新导入APLDatabase以使用新的目录
        import zsim.api_src.services.database.apl_db

        zsim.api_src.services.database.apl_db.DEFAULT_APL_DIR = test_default_dir
        zsim.api_src.services.database.apl_db.COSTOM_APL_DIR = test_custom_dir
        zsim.api_src.services.database.apl_db.SQLITE_PATH = os.path.join(
            test_default_dir, "test_zsim.db"
        )

        yield test_default_dir, test_custom_dir

        # 清理
        shutil.rmtree(temp_dir)
        zsim.define.DEFAULT_APL_DIR = original_default_dir
        zsim.define.COSTOM_APL_DIR = original_custom_dir
        zsim.api_src.services.database.apl_db.SQLITE_PATH = original_sqlite_path

    def test_create_and_get_apl_config(self, setup_and_teardown):
        """测试创建和获取APL配置"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建测试配置数据
        config_data = {
            "title": "Test APL Config",
            "author": "Test Author",
            "characters": {
                "required": ["Character1"],
                "optional": ["Character2"],
                "Character1": {"cinema": [0, 1, 2], "weapon": "TestWeapon"},
            },
            "apl_logic": {"logic": "# Test APL logic"},
        }

        # 创建APL配置
        config_id = db.create_apl_config(config_data)
        assert isinstance(config_id, str)
        assert len(config_id) > 0

        # 获取APL配置
        retrieved_config = db.get_apl_config(config_id)
        assert retrieved_config is not None
        assert retrieved_config["title"] == "Test APL Config"
        assert retrieved_config["author"] == "Test Author"
        assert retrieved_config["characters"]["required"] == ["Character1"]

    def test_update_apl_config(self, setup_and_teardown):
        """测试更新APL配置"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建初始配置
        config_data = {"title": "Original Title", "author": "Original Author"}
        config_id = db.create_apl_config(config_data)

        # 更新配置
        updated_data = {
            "title": "Updated Title",
            "author": "Updated Author",
            "characters": {"required": ["NewCharacter"]},
        }
        success = db.update_apl_config(config_id, updated_data)
        assert success is True

        # 验证更新
        retrieved_config = db.get_apl_config(config_id)
        assert retrieved_config is not None
        assert retrieved_config["title"] == "Updated Title"
        assert retrieved_config["author"] == "Updated Author"
        assert retrieved_config["characters"]["required"] == ["NewCharacter"]

    def test_delete_apl_config(self, setup_and_teardown):
        """测试删除APL配置"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建配置
        config_data = {"title": "Test Config"}
        config_id = db.create_apl_config(config_data)

        # 验证配置存在
        retrieved_config = db.get_apl_config(config_id)
        assert retrieved_config is not None

        # 删除配置
        success = db.delete_apl_config(config_id)
        assert success is True

        # 验证配置已删除
        retrieved_config = db.get_apl_config(config_id)
        assert retrieved_config is None

    def test_get_apl_templates(self, setup_and_teardown):
        """测试获取APL模板"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建测试TOML文件
        default_toml_content = """
[general]
title = "Default Template"
author = "Default Author"
"""
        custom_toml_content = """
[general]
title = "Custom Template"
author = "Custom Author"
"""

        # 写入默认模板文件
        with open(
            os.path.join(test_default_dir, "default_template.toml"), "w", encoding="utf-8"
        ) as f:
            f.write(default_toml_content)

        # 写入自定义模板文件
        with open(
            os.path.join(test_custom_dir, "custom_template.toml"), "w", encoding="utf-8"
        ) as f:
            f.write(custom_toml_content)

        # 获取模板
        templates = db.get_apl_templates()
        assert len(templates) == 2

        # 验证模板信息
        titles = [t["title"] for t in templates]
        assert "Default Template" in titles
        assert "Custom Template" in titles

    def test_get_apl_files(self, setup_and_teardown):
        """测试获取APL文件列表"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建测试文件
        with open(os.path.join(test_default_dir, "file1.toml"), "w", encoding="utf-8") as f:
            f.write("# Test file 1")

        with open(os.path.join(test_custom_dir, "file2.toml"), "w", encoding="utf-8") as f:
            f.write("# Test file 2")

        # 获取文件列表
        files = db.get_apl_files()
        assert len(files) == 2

        # 验证文件信息
        filenames = [f["name"] for f in files]
        assert "file1.toml" in filenames
        assert "file2.toml" in filenames

    def test_get_apl_file_content(self, setup_and_teardown):
        """测试获取APL文件内容"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建测试文件
        test_content = "# Test APL Content\n1|action+=|1_S1|condition==True"
        file_path = os.path.join(test_custom_dir, "test_file.toml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(test_content)

        # 获取文件内容
        file_id = "custom_test_file.toml"
        content = db.get_apl_file_content(file_id)
        assert content is not None
        assert content["content"] == test_content
        assert content["file_id"] == file_id

    def test_create_apl_file(self, setup_and_teardown):
        """测试创建APL文件"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建文件数据
        file_data = {"name": "new_file.toml", "content": "# New APL File Content"}

        # 创建文件
        file_id = db.create_apl_file(file_data)
        assert file_id == "custom_new_file.toml"

        # 验证文件已创建
        file_path = os.path.join(test_custom_dir, "new_file.toml")
        assert os.path.exists(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == "# New APL File Content"

    def test_update_apl_file(self, setup_and_teardown):
        """测试更新APL文件"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建初始文件
        initial_content = "# Initial Content"
        file_path = os.path.join(test_custom_dir, "update_test.toml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(initial_content)

        # 更新文件
        new_content = "# Updated Content"
        success = db.update_apl_file("custom_update_test.toml", new_content)
        assert success is True

        # 验证更新
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == new_content

    def test_delete_apl_file(self, setup_and_teardown):
        """测试删除APL文件"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建文件
        file_content = "# Test Content"
        file_path = os.path.join(test_custom_dir, "delete_test.toml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)

        # 验证文件存在
        assert os.path.exists(file_path)

        # 删除文件
        success = db.delete_apl_file("custom_delete_test.toml")
        assert success is True

        # 验证文件已删除
        assert not os.path.exists(file_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
