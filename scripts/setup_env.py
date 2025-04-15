#!/usr/bin/env python3
"""
環境設置腳本
檢查並安裝所有必要的依賴，創建必要的目錄
"""

import os
import sys
import subprocess
from pathlib import Path

def check_command(command):
    """檢查命令是否可用"""
    try:
        subprocess.run(f"{command} --version", shell=True, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def install_dependencies():
    """安裝所有依賴項"""
    print("📦 正在安裝依賴項...")
    
    # 檢查 pip 是否可用
    if not check_command("pip"):
        print("❌ 未找到 pip，請先安裝 Python 及 pip")
        sys.exit(1)
    
    # 安裝依賴項
    try:
        subprocess.run("pip install -r requirements.txt", shell=True, check=True)
        print("✅ 依賴項安裝成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依賴項安裝失敗: {e}")
        sys.exit(1)

def create_directories():
    """創建必要的目錄"""
    print("📁 檢查並創建必要的目錄...")
    
    required_dirs = [
        "data",
        "data/input",
        "data/output",
        "data/cbeta",
        "data/vector_db"
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            print(f"  創建目錄: {dir_path}")
            path.mkdir(parents=True, exist_ok=True)
    
    print("✅ 目錄檢查和創建完成")

def check_env_file():
    """檢查環境變數文件"""
    print("🔑 檢查環境變數文件...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_file.exists() and env_example.exists():
        print("  創建 .env 文件 (從 .env.example 複製)")
        with open(env_example, "r", encoding="utf-8") as src:
            content = src.read()
        with open(env_file, "w", encoding="utf-8") as dst:
            dst.write(content)
        print("  請編輯 .env 文件並填入您的 API 密鑰和設定")
    
    if env_file.exists():
        print("✅ .env 文件存在")
    else:
        print("❌ .env 文件不存在，請手動創建")

def main():
    """主函數"""
    print("===== 佛教智慧對話系統環境設置 =====")
    
    # 獲取腳本所在目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 切換到專案根目錄
    os.chdir(os.path.join(script_dir, ".."))
    
    # 安裝依賴項
    install_dependencies()
    
    # 創建必要的目錄
    create_directories()
    
    # 檢查環境變數文件
    check_env_file()
    
    print("\n✨ 環境設置完成！")
    print("您可以通過以下命令啟動應用程序:")
    print("  python -m app.main")
    print("\n要測試應用程序功能，請執行:")
    print("  python -m unittest discover tests")

if __name__ == "__main__":
    main() 