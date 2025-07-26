"""
APL业务逻辑服务
负责APL相关业务逻辑处理
"""

from typing import Any, Optional
from .database.apl_db import APLDatabase
from ..models.apl import (
    APLTemplateInfo,
    APLFileInfo,
    APLFileContent,
    APLConfigCreateRequest,
    APLConfigUpdateRequest,
    APLFileCreateRequest,
    APLFileUpdateRequest,
    APLValidateResponse,
    APLParseResponse,
)


class APLService:
    """APL业务逻辑服务类"""

    def __init__(self):
        """初始化APL服务"""
        self.db = APLDatabase()

    def get_apl_templates(self) -> list[APLTemplateInfo]:
        """获取APL模板列表"""
        templates = self.db.get_apl_templates()
        return [APLTemplateInfo(**template) for template in templates]

    def get_apl_config(self, config_id: str) -> dict[str, Any] | None:
        """获取特定APL配置"""
        return self.db.get_apl_config(config_id)

    def create_apl_config(self, config_data: APLConfigCreateRequest) -> dict[str, Any]:
        """创建新的APL配置"""
        # 验证配置数据
        if not self._validate_apl_config(config_data.model_dump()):
            raise ValueError("Invalid APL configuration data")

        config_id = self.db.create_apl_config(config_data.model_dump())
        return {"config_id": config_id, "message": "APL configuration created successfully"}

    def update_apl_config(
        self, config_id: str, config_data: APLConfigUpdateRequest
    ) -> dict[str, Any]:
        """更新APL配置"""
        # 验证配置数据
        if not self._validate_apl_config(config_data.model_dump()):
            raise ValueError("Invalid APL configuration data")

        success = self.db.update_apl_config(config_id, config_data.model_dump())
        if success:
            return {"config_id": config_id, "message": "APL configuration updated successfully"}
        else:
            raise ValueError("Failed to update APL configuration")

    def delete_apl_config(self, config_id: str) -> dict[str, Any]:
        """删除APL配置"""
        success = self.db.delete_apl_config(config_id)
        if success:
            return {"config_id": config_id, "message": "APL configuration deleted successfully"}
        else:
            raise ValueError("Failed to delete APL configuration")

    def get_apl_files(self) -> list[APLFileInfo]:
        """获取所有APL文件列表"""
        files = self.db.get_apl_files()
        return [APLFileInfo(**file) for file in files]

    def get_apl_file_content(self, file_id: str) -> APLFileContent:
        """获取APL文件内容"""
        content = self.db.get_apl_file_content(file_id)
        if content is not None:
            return APLFileContent(**content)
        else:
            raise ValueError("APL file not found")

    def create_apl_file(self, file_data: APLFileCreateRequest) -> dict[str, Any]:
        """创建新的APL文件"""
        # 验证文件数据
        if not self._validate_apl_file_data(file_data.model_dump()):
            raise ValueError("Invalid APL file data")

        file_id = self.db.create_apl_file(file_data.model_dump())
        return {"file_id": file_id, "message": "APL file created successfully"}

    def update_apl_file(self, file_id: str, content: str) -> dict[str, Any]:
        """更新APL文件内容"""
        file_data = APLFileUpdateRequest(content=content)
        success = self.db.update_apl_file(file_id, file_data.content)
        if success:
            return {"file_id": file_id, "message": "APL file updated successfully"}
        else:
            raise ValueError("Failed to update APL file")

    def delete_apl_file(self, file_id: str) -> dict[str, Any]:
        """删除APL文件"""
        success = self.db.delete_apl_file(file_id)
        if success:
            return {"file_id": file_id, "message": "APL file deleted successfully"}
        else:
            raise ValueError("Failed to delete APL file")

    def validate_apl_syntax(self, apl_code: str) -> APLValidateResponse:
        """验证APL语法"""
        # 实现APL语法验证逻辑
        # 这里需要根据APL的具体语法规则来实现
        try:
            # 简单的语法检查示例
            lines = apl_code.strip().split("\n")
            errors = []

            for i, line in enumerate(lines, 1):
                line = line.strip()
                # 跳过空行和注释行
                if not line or line.startswith("#"):
                    continue

                # 检查基本格式：动作角色|动作类型|动作ID|条件...
                parts = line.split("|")
                if len(parts) < 3:
                    errors.append(f"Line {i}: Invalid APL format, expected at least 3 parts")

            if errors:
                return APLValidateResponse(valid=False, errors=errors)
            else:
                return APLValidateResponse(valid=True, message="APL syntax is valid")
        except Exception as e:
            return APLValidateResponse(valid=False, errors=[f"Syntax validation error: {str(e)}"])

    def parse_apl_code(self, apl_code: str) -> APLParseResponse:
        """解析APL代码"""
        # 实现APL代码解析逻辑
        try:
            # 简单的解析示例
            lines = apl_code.strip().split("\n")
            parsed_actions = []

            for i, line in enumerate(lines, 1):
                line = line.strip()
                # 跳过空行和注释行
                if not line or line.startswith("#"):
                    continue

                # 解析基本格式：动作角色|动作类型|动作ID|条件...
                parts = line.split("|")
                if len(parts) >= 3:
                    action = {
                        "line": i,
                        "character": parts[0],
                        "action_type": parts[1],
                        "action_id": parts[2],
                        "conditions": parts[3:] if len(parts) > 3 else [],
                    }
                    parsed_actions.append(action)

            return APLParseResponse(parsed=True, actions=parsed_actions)
        except Exception as e:
            return APLParseResponse(parsed=False, error=f"APL parsing error: {str(e)}")

    def _validate_apl_config(self, config_data: dict[str, Any]) -> bool:
        """验证APL配置数据"""
        # 实现APL配置数据验证逻辑
        # 检查必需字段
        required_fields = ["title"]
        for field in required_fields:
            if field not in config_data:
                return False

        # 检查角色配置
        if "characters" in config_data:
            characters = config_data["characters"]
            if not isinstance(characters, dict):
                return False

            # 验证角色配置中的cinema字段格式
            for char_name, char_config in characters.items():
                if char_name in ["required", "optional"]:
                    continue  # 跳过required和optional字段

                if isinstance(char_config, dict) and "cinema" in char_config:
                    cinema = char_config["cinema"]
                    # cinema应该是一个整数列表或None
                    if cinema is not None and not isinstance(cinema, list):
                        return False
                    # 如果是列表，检查所有元素都是整数且在有效范围内(0-6)
                    if isinstance(cinema, list):
                        for c in cinema:
                            if not isinstance(c, int) or c < 0 or c > 6:
                                return False

        # 检查APL逻辑
        if "apl_logic" in config_data:
            apl_logic = config_data["apl_logic"]
            if not isinstance(apl_logic, dict) or "logic" not in apl_logic:
                return False

        return True

    def export_apl_config(self, config_id: str, file_path: str) -> bool:
        """导出APL配置到TOML文件"""
        return self.db.export_apl_config(config_id, file_path)

    def import_apl_config(self, file_path: str) -> Optional[str]:
        """从TOML文件导入APL配置"""
        return self.db.import_apl_config(file_path)
