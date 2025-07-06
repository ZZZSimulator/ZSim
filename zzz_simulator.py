import subprocess
import sys
import platform


def check_uv_installed() -> bool:
    """
    检查系统是否安装了uv工具

    Returns:
        bool: 是否已安装
    """
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["where", "uv"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.run(
                ["command", "-v", "uv"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return True
    except subprocess.CalledProcessError:
        return False


def install_uv() -> bool:
    """
    自动安装uv工具

    Returns:
        bool: 是否安装成功
    """
    print("正在自动安装uv工具...")
    try:
        if platform.system() == "Windows":
            subprocess.run(
                [
                    "powershell",
                    "-ExecutionPolicy",
                    "ByPass",
                    "-c",
                    "irm https://astral.sh/uv/install.ps1 | iex",
                ],
                check=True,
            )
        else:
            try:
                subprocess.run(
                    ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                    check=True,
                )
            except subprocess.CalledProcessError:
                print("curl安装失败，尝试使用wget...")
                subprocess.run(
                    ["sh", "-c", "wget -qO- https://astral.sh/uv/install.sh | sh"],
                    check=True,
                )
        return True
    except subprocess.CalledProcessError:
        print("安装失败，请手动安装")
        return False


def main() -> None:
    """主程序入口"""
    if not check_uv_installed():
        if not install_uv():
            input("按任意键退出...")
            sys.exit(1)

    # 运行主程序
    subprocess.run(["uv", "run", "zsim", "app", "--server.headless=true"])


if __name__ == "__main__":
    main()
