"""
APL相关Pydantic模型
定义APL API请求和响应的数据模型
"""

from typing import List, Optional, TypeVar, Generic
from pydantic import BaseModel, Field


class APLGeneralInfo(BaseModel):
    """APL通用信息模型"""

    title: str = Field(..., description="APL标题")
    comment: Optional[str] = Field(None, description="APL注释")
    author: Optional[str] = Field(None, description="APL作者")
    create_time: Optional[str] = Field(None, description="创建时间")
    latest_change_time: Optional[str] = Field(None, description="最后修改时间")


class APLCharacterConfig(BaseModel):
    """APL角色配置模型"""

    cinema: Optional[List[int]] = Field(None, description="角色影画等级")
    weapon: Optional[str] = Field(None, description="角色武器")
    equip_set4: Optional[str] = Field(None, description="四件套装备")


class APLCharactersInfo(BaseModel):
    """APL角色信息模型"""

    required: Optional[List[str]] = Field(None, description="必须角色列表")
    optional: Optional[List[str]] = Field(None, description="可选角色列表")

    class Config:
        extra = "allow"  # 允许动态字段用于存储各个角色的具体配置


class APLLogicInfo(BaseModel):
    """APL逻辑信息模型"""

    logic: str = Field(..., description="APL逻辑代码")


class APLTemplateInfo(BaseModel):
    """APL模板信息模型"""

    id: str = Field(..., description="模板ID")
    title: str = Field(..., description="模板标题")
    author: Optional[str] = Field(None, description="模板作者")
    comment: Optional[str] = Field(None, description="模板注释")
    create_time: Optional[str] = Field(None, description="创建时间")
    latest_change_time: Optional[str] = Field(None, description="最后修改时间")
    source: str = Field(..., description="模板来源 (default/custom)")
    file_path: str = Field(..., description="文件路径")


class APLFileInfo(BaseModel):
    """APL文件信息模型"""

    id: str = Field(..., description="文件ID")
    name: str = Field(..., description="文件名")
    path: str = Field(..., description="相对路径")
    source: str = Field(..., description="文件来源 (default/custom)")
    full_path: str = Field(..., description="完整文件路径")


class APLFileContent(BaseModel):
    """APL文件内容模型"""

    file_id: str = Field(..., description="文件ID")
    content: str = Field(..., description="文件内容")
    file_path: str = Field(..., description="文件路径")


class APLConfigCreateRequest(BaseModel):
    """创建APL配置请求模型"""

    title: str = Field(..., description="APL标题")
    comment: Optional[str] = Field(None, description="APL注释")
    author: Optional[str] = Field(None, description="APL作者")
    characters: Optional[APLCharactersInfo] = Field(None, description="角色配置")
    apl_logic: Optional[APLLogicInfo] = Field(None, description="APL逻辑")


class APLConfigUpdateRequest(BaseModel):
    """更新APL配置请求模型"""

    title: Optional[str] = Field(None, description="APL标题")
    comment: Optional[str] = Field(None, description="APL注释")
    author: Optional[str] = Field(None, description="APL作者")
    characters: Optional[APLCharactersInfo] = Field(None, description="角色配置")
    apl_logic: Optional[APLLogicInfo] = Field(None, description="APL逻辑")


class APLFileCreateRequest(BaseModel):
    """创建APL文件请求模型"""

    name: str = Field(..., description="文件名")
    content: str = Field(..., description="文件内容")


class APLFileUpdateRequest(BaseModel):
    """更新APL文件请求模型"""

    content: str = Field(..., description="文件内容")


class APLValidateRequest(BaseModel):
    """APL语法验证请求模型"""

    apl_code: str = Field(..., description="APL代码")


class APLParseRequest(BaseModel):
    """APL代码解析请求模型"""

    apl_code: str = Field(..., description="APL代码")


class APLValidateResponse(BaseModel):
    """APL语法验证响应模型"""

    valid: bool = Field(..., description="语法是否有效")
    message: Optional[str] = Field(None, description="验证消息")
    errors: Optional[List[str]] = Field(None, description="错误列表")


class APLParseAction(BaseModel):
    """APL解析动作模型"""

    line: int = Field(..., description="行号")
    character: str = Field(..., description="角色")
    action_type: str = Field(..., description="动作类型")
    action_id: str = Field(..., description="动作ID")
    conditions: List[str] = Field(..., description="条件列表")


class APLParseResponse(BaseModel):
    """APL代码解析响应模型"""

    parsed: bool = Field(..., description="是否解析成功")
    actions: Optional[List[APLParseAction]] = Field(None, description="解析的动作列表")
    error: Optional[str] = Field(None, description="错误信息")


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """通用API响应模型"""

    code: int = Field(..., description="响应码")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
