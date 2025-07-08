# 删除指定目录与所有子目录下的__pycache__文件夹
import os
import shutil


def remove_pycache(directory):
    for root, dirs, files in os.walk(directory):
        print(f"Scanning: {root}")
        for dir_name in dirs:
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                shutil.rmtree(pycache_path)
                print(f"Removed: {pycache_path}")


if __name__ == "__main__":
    directory_to_clean = "./"
    remove_pycache(directory_to_clean)
