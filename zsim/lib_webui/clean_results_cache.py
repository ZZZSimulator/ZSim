import json
import os

try:
    from zsim.define import NORMAL_MODE_ID_JSON
except ModuleNotFoundError:
    pass

from .constants import results_dir, IDDuplicateError


# 获取合法的结果缓存
def get_all_results(
    *, id_cache_path=NORMAL_MODE_ID_JSON, results_dir=results_dir
) -> dict[str : str | int | None]:
    # 读取id_cache.json文件
    # 如果文件不存在则创建空的id_cache
    if not os.path.exists(id_cache_path):
        os.makedirs(os.path.dirname(id_cache_path), exist_ok=True)
        with open(id_cache_path, "w") as f:
            json.dump({}, f)

    with open(id_cache_path, "r") as f:
        id_cache = json.load(f)

    # 获取results文件夹内的所有文件夹名
    folder_names = [
        name
        for name in os.listdir(results_dir)
        if os.path.isdir(os.path.join(results_dir, name))
    ]

    # 找出需要删除的key
    keys_to_delete = []
    for key in list(id_cache.keys()):
        if key not in folder_names:
            keys_to_delete.append(key)

    # 删除无对应文件夹的key
    for key in keys_to_delete:
        del id_cache[key]

    # 找出需要新建的key
    for folder_name in folder_names:
        if folder_name not in id_cache.keys():
            id_cache[folder_name] = "Unkown results"

    # 将更新后的id_cache写回id_cache.json文件
    with open(id_cache_path, "w") as f:
        json.dump(id_cache, f, indent=4)

    return id_cache


def rename_result(
    former_name: str,
    new_name: str,
    new_comment: str = None,
    *,
    id_cache_path=NORMAL_MODE_ID_JSON,
    results_dir=results_dir,
):
    """
    重命名结果文件夹并更新id_cache.json文件中的对应条目。

    参数:
        former_name (str): 原文件夹名称
        new_name (str): 新文件夹名称
        new_comment (str, optional): 新的备注信息，默认为None表示保留原备注
        id_cache_path (str, optional, keyword only): id_cache.json文件路径，默认为ID_CACHE_JSON
        results_dir (str, optional, keyword only): 结果文件夹路径，默认为results_dir

    返回:
        None

    异常:
        FileNotFoundError: 当原文件夹不存在时抛出
        IDDuplicateError: 当新文件夹已存在时抛出
        JSONDecodeError: 当id_cache.json文件格式错误时抛出

    示例:
        >>> rename_result("old_result", "new_result", "测试结果")
        # 将old_result重命名为new_result，并更新备注为"测试结果"
    """
    # 读取id_cache.json文件
    with open(id_cache_path, "r") as f:
        id_cache = json.load(f)

    # 检查新名称是否已存在且与旧名称不同
    if former_name != new_name:
        new_path = os.path.join(results_dir, new_name)
        if os.path.exists(new_path):
            raise IDDuplicateError(f"新名称 {new_name} 已存在，请使用其他名称。")

        # 重命名文件夹
        former_path = os.path.join(results_dir, former_name)
        os.rename(former_path, new_path)

        # 更新id_cache字典
        id_cache[new_name] = id_cache[former_name]
        del id_cache[former_name]

    if new_comment is not None:
        id_cache[new_name] = new_comment

    # 将更新后的id_cache写回id_cache.json文件
    with open(id_cache_path, "w") as f:
        json.dump(id_cache, f, indent=4)


def delete_result(
    former_name: str, *, id_cache_path=NORMAL_MODE_ID_JSON, results_dir=results_dir
):
    """
    删除结果文件夹并更新id_cache.json文件中的对应条目。
    参数:
        former_name (str): 需要删除的结果文件夹名称
        id_cache_path (str, optional, keyword only): id_cache.json文件路径，默认为ID_CACHE_JSON
        results_dir (str, optional, keyword only): 结果文件夹路径，默认为results_dir
    返回:
        None
    异常:
        FileNotFoundError: 当目标文件夹不存在时抛出
        JSONDecodeError: 当id_cache.json文件格式错误时抛出
    """
    import shutil

    # 删除文件夹
    folder_path = os.path.join(results_dir, former_name)
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"目标文件夹 {former_name} 不存在。")
    shutil.rmtree(folder_path)
    # 更新id_cache.json
    with open(id_cache_path, "r") as f:
        id_cache = json.load(f)
    if former_name in id_cache:
        del id_cache[former_name]
    with open(id_cache_path, "w") as f:
        json.dump(id_cache, f, indent=4)


if __name__ == "__main__":
    get_all_results()
