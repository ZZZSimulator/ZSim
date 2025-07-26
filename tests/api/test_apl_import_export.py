"""
APL导入导出测试
测试APL配置的导入和导出功能
"""

import os
import toml
import pytest
import tempfile
import shutil
from zsim.api_src.services.database.apl_db import APLDatabase
from zsim.define import DEFAULT_APL_DIR, COSTOM_APL_DIR


class TestAPLImportExport:
    """APL导入导出测试类"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """设置和清理测试环境"""
        # 保存原始目录
        original_default_dir = DEFAULT_APL_DIR
        original_custom_dir = COSTOM_APL_DIR

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
        zsim.api_src.services.database.apl_db.APL_DATABASE_FILE = os.path.join(
            test_default_dir, "apl_configs.db"
        )

        yield test_default_dir, test_custom_dir

        # 清理
        shutil.rmtree(temp_dir)
        zsim.define.DEFAULT_APL_DIR = original_default_dir
        zsim.define.COSTOM_APL_DIR = original_custom_dir

    def test_export_apl_config(self, setup_and_teardown):
        """测试导出APL配置"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建测试配置数据
        config_data = {
            "title": "Test Export Config",
            "author": "Test Author",
            "comment": "Test Comment",
            "characters": {
                "required": ["Character1"],
                "optional": ["Character2"],
                "Character1": {"cinema": [0, 1, 2], "weapon": "TestWeapon"},
            },
            "apl_logic": {"logic": "# Test APL logic"},
        }

        # 创建APL配置
        config_id = db.create_apl_config(config_data)

        # 导出配置到文件
        export_file_path = os.path.join(test_custom_dir, "exported_config.toml")
        success = db.export_apl_config(config_id, export_file_path)

        # 验证导出成功
        assert success is True
        assert os.path.exists(export_file_path)

        # 验证导出的文件内容
        with open(export_file_path, "r", encoding="utf-8") as f:
            exported_data = toml.load(f)

        assert exported_data["title"] == "Test Export Config"
        assert exported_data["author"] == "Test Author"
        assert exported_data["comment"] == "Test Comment"
        assert exported_data["characters"]["required"] == ["Character1"]

    def test_import_apl_config(self, setup_and_teardown):
        """测试导入APL配置"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建TOML文件用于导入
        import_data = {
            "title": "Test Import Config",
            "author": "Import Author",
            "comment": "Import Comment",
            "characters": {
                "required": ["ImportChar1"],
                "optional": ["ImportChar2"],
                "ImportChar1": {"cinema": [3, 4, 5], "weapon": "ImportWeapon"},
            },
            "apl_logic": {"logic": "# Import APL logic"},
        }

        import_file_path = os.path.join(test_custom_dir, "import_config.toml")
        with open(import_file_path, "w", encoding="utf-8") as f:
            toml.dump(import_data, f)

        # 导入配置
        config_id = db.import_apl_config(import_file_path)

        # 验证导入成功
        assert config_id is not None
        assert isinstance(config_id, str)
        assert len(config_id) > 0

        # 验证导入的配置内容
        imported_config = db.get_apl_config(config_id)
        assert imported_config is not None
        assert imported_config["title"] == "Test Import Config"
        assert imported_config["author"] == "Import Author"
        assert imported_config["characters"]["required"] == ["ImportChar1"]

    def test_import_export_roundtrip(self, setup_and_teardown):
        """测试导入导出往返一致性"""
        test_default_dir, test_custom_dir = setup_and_teardown
        db = APLDatabase()

        # 创建原始配置
        original_data = {
            "title": "Roundtrip Test Config",
            "author": "Roundtrip Author",
            "comment": "Roundtrip Comment",
            "create_time": "2025-01-01T00:00:00.000+08:00",
            "latest_change_time": "2025-01-01T00:00:00.000+08:00",
            "characters": {
                "required": ["CharA", "CharB"],
                "optional": ["CharC"],
                "CharA": {"cinema": [0, 1], "weapon": "WeaponA", "equip_set4": "SetA"},
                "CharB": {"cinema": [2, 3], "weapon": "WeaponB"},
                "CharC": {"cinema": [4]},
            },
            "apl_logic": {"logic": "# Roundtrip test logic\n1|action+=|1_S1|condition==True"},
        }

        # 创建配置
        config_id = db.create_apl_config(original_data)

        # 导出配置
        export_file_path = os.path.join(test_custom_dir, "roundtrip_test.toml")
        success = db.export_apl_config(config_id, export_file_path)
        assert success is True

        # 从导出的文件重新导入
        new_config_id = db.import_apl_config(export_file_path)
        assert new_config_id is not None

        # 验证导入的配置与原始配置一致
        imported_data = db.get_apl_config(new_config_id)
        assert imported_data is not None

        # 比较关键字段
        assert imported_data["title"] == original_data["title"]
        assert imported_data["author"] == original_data["author"]
        assert imported_data["comment"] == original_data["comment"]
        assert imported_data["characters"]["required"] == original_data["characters"]["required"]
        assert imported_data["characters"]["optional"] == original_data["characters"]["optional"]
        assert imported_data["apl_logic"]["logic"] == original_data["apl_logic"]["logic"]

        # 比较角色配置
        for char_name in ["CharA", "CharB", "CharC"]:
            if char_name in original_data["characters"]:
                assert char_name in imported_data["characters"]
                orig_char_config = original_data["characters"][char_name]
                imported_char_config = imported_data["characters"][char_name]
                for key, value in orig_char_config.items():
                    assert imported_char_config[key] == value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
