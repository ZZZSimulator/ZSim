"""
APL相关API路由
提供APL模板、配置、文件管理等API接口
"""

from fastapi import APIRouter, HTTPException, status
from ..services.apl_service import APLService
from ..models.apl import (
    APLConfigCreateRequest,
    APLConfigUpdateRequest,
    APLFileCreateRequest,
    APLFileUpdateRequest,
    APLValidateRequest,
    APLParseRequest,
    APIResponse,
    APLTemplateInfo,
    APLFileInfo,
    APLFileContent,
)

router = APIRouter()
apl_service = APLService()


@router.get(
    "/apl/templates",
    tags=["APL"],
    response_model=APIResponse[list[APLTemplateInfo]],
)
async def get_apl_templates():
    """
    获取APL模板列表
    """
    try:
        templates = apl_service.get_apl_templates()
        return APIResponse(code=200, message="Success", data=templates)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取APL模板失败: {str(e)}"
        )


@router.post(
    "/apl/configs/",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def create_apl_config(config_data: APLConfigCreateRequest):
    """
    创建APL配置
    """
    try:
        result = apl_service.create_apl_config(config_data)
        return APIResponse(code=200, message="Success", data=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"APL配置数据无效: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建APL配置失败: {str(e)}"
        )


@router.get(
    "/apl/configs/",
    tags=["APL"],
    response_model=APIResponse[list],
)
async def get_apl_configs():
    """
    获取所有APL配置
    """
    # 这里需要实现获取所有APL配置的逻辑
    try:
        # 暂时返回空列表作为占位符
        return APIResponse(code=200, message="Success", data=[])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取APL配置列表失败: {str(e)}",
        )


@router.get(
    "/apl/configs/{config_id}",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def get_apl_config(config_id: str):
    """
    获取特定APL配置
    """
    try:
        config = apl_service.get_apl_config(config_id)
        if config:
            return APIResponse(code=200, message="Success", data=config)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APL配置未找到")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取APL配置失败: {str(e)}"
        )


@router.put(
    "/apl/configs/{config_id}",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def update_apl_config(config_id: str, config_data: APLConfigUpdateRequest):
    """
    更新APL配置
    """
    try:
        result = apl_service.update_apl_config(config_id, config_data)
        return APIResponse(code=200, message="Success", data=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"APL配置数据无效: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新APL配置失败: {str(e)}"
        )


@router.delete(
    "/apl/configs/{config_id}",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def delete_apl_config(config_id: str):
    """
    删除APL配置
    """
    try:
        result = apl_service.delete_apl_config(config_id)
        return APIResponse(code=200, message="Success", data=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"删除APL配置失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除APL配置失败: {str(e)}"
        )


@router.get(
    "/apl/files",
    tags=["APL"],
    response_model=APIResponse[list[APLFileInfo]],
)
async def get_apl_files():
    """
    获取所有APL文件列表
    """
    try:
        files = apl_service.get_apl_files()
        return APIResponse(code=200, message="Success", data=files)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取APL文件列表失败: {str(e)}",
        )


@router.post(
    "/apl/files",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def create_apl_file(file_data: APLFileCreateRequest):
    """
    创建新APL文件
    """
    try:
        result = apl_service.create_apl_file(file_data)
        return APIResponse(code=200, message="Success", data=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"APL文件数据无效: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建APL文件失败: {str(e)}"
        )


@router.get(
    "/apl/files/{file_id}",
    tags=["APL"],
    response_model=APIResponse[APLFileContent],
)
async def get_apl_file(file_id: str):
    """
    获取APL文件内容
    """
    try:
        content = apl_service.get_apl_file_content(file_id)
        return APIResponse(code=200, message="Success", data=content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"APL文件未找到: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取APL文件内容失败: {str(e)}",
        )


@router.put(
    "/apl/files/{file_id}",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def update_apl_file(file_id: str, file_data: APLFileUpdateRequest):
    """
    更新APL文件内容
    """
    try:
        result = apl_service.update_apl_file(file_id, file_data.content)
        return APIResponse(code=200, message="Success", data=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"更新APL文件失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"更新APL文件失败: {str(e)}"
        )


@router.delete(
    "/apl/files/{file_id}",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def delete_apl_file(file_id: str):
    """
    删除APL文件
    """
    try:
        result = apl_service.delete_apl_file(file_id)
        return APIResponse(code=200, message="Success", data=result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"删除APL文件失败: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除APL文件失败: {str(e)}"
        )


@router.post(
    "/apl/validate",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def validate_apl(request: APLValidateRequest):
    """
    验证APL语法
    """
    try:
        result = apl_service.validate_apl_syntax(request.apl_code)
        return APIResponse(code=200, message="Success", data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"验证APL语法失败: {str(e)}"
        )


@router.post(
    "/apl/parse",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def parse_apl(request: APLParseRequest):
    """
    解析APL代码
    """
    try:
        result = apl_service.parse_apl_code(request.apl_code)
        return APIResponse(code=200, message="Success", data=result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解析APL代码失败: {str(e)}"
        )


@router.get(
    "/apl/export/{config_id}",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def export_apl_config(config_id: str, file_path: str):
    """
    导出APL配置到TOML文件
    """
    try:
        success = apl_service.export_apl_config(config_id, file_path)
        if success:
            return APIResponse(code=200, message="Success", data={"message": "APL配置导出成功"})
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APL配置未找到")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"导出APL配置失败: {str(e)}"
        )


@router.post(
    "/apl/import",
    tags=["APL"],
    response_model=APIResponse[dict],
)
async def import_apl_config(file_path: str):
    """
    从TOML文件导入APL配置
    """
    try:
        config_id = apl_service.import_apl_config(file_path)
        if config_id:
            return APIResponse(code=200, message="Success", data={"config_id": config_id, "message": "APL配置导入成功"})
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="APL配置导入失败")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"导入APL配置失败: {str(e)}"
        )