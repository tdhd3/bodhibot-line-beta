#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CBETA 經文下載腳本
此腳本用於批量下載CBETA經文並存儲到本地，以便初始化應用程序的經文數據。
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path

# 將專案根目錄添加到路徑中
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.data_processing.cbeta_processor import CBETAProcessor

async def download_all_sutras():
    """下載並處理所有支持的經文"""
    print("初始化CBETA處理器...")
    processor = CBETAProcessor()
    
    # 將所有經文ID打印到控制台
    print(f"準備下載以下經文:")
    for i, sutra in enumerate(settings.SUPPORTED_SUTRAS, 1):
        print(f"{i}. {sutra['name']} (ID: {sutra['id']})")
    
    # 處理所有經文
    print("\n開始下載經文...")
    await processor.process_all_sutras()
    print("所有經文下載完成。")

async def download_sutra_by_id(sutra_id: str):
    """下載並處理指定ID的經文"""
    processor = CBETAProcessor()
    
    # 查找經文名稱
    sutra_name = None
    for sutra in settings.SUPPORTED_SUTRAS:
        if sutra['id'] == sutra_id:
            sutra_name = sutra['name']
            break
    
    if not sutra_name:
        print(f"錯誤: 未找到ID為 {sutra_id} 的經文。請使用 --list 選項查看支持的經文")
        return
    
    print(f"開始下載經文: {sutra_name} (ID: {sutra_id})...")
    await processor.process_sutra(sutra_id, sutra_name)
    print(f"經文 {sutra_name} 下載完成。")

def list_available_sutras():
    """列出所有可用的經文"""
    print("可下載的經文列表:")
    print("-" * 30)
    print("| {:^5} | {:^8} | {:^10} |".format("序號", "經文ID", "經文名稱"))
    print("-" * 30)
    
    for i, sutra in enumerate(settings.SUPPORTED_SUTRAS, 1):
        print("| {:^5} | {:^8} | {:^10} |".format(i, sutra['id'], sutra['name']))
    
    print("-" * 30)
    print("使用方法: python scripts/download_cbeta.py --id <經文ID>")
    print("          例如: python scripts/download_cbeta.py --id T0945")
    print("或: python scripts/download_cbeta.py --all 下載所有經文")

async def main():
    parser = argparse.ArgumentParser(description='下載CBETA經文並創建向量索引')
    parser.add_argument('--list', action='store_true', help='列出所有支持的經文')
    parser.add_argument('--id', type=str, help='指定要下載的經文ID')
    parser.add_argument('--all', action='store_true', help='下載所有支持的經文')
    parser.add_argument('--name', type=str, help='根據名稱查找經文ID')
    parser.add_argument('--skip-index', action='store_true', help='跳過創建向量索引')
    parser.add_argument('--text-only', action='store_true', help='僅下載文本版本，不嘗試獲取XML')
    args = parser.parse_args()

    # 創建CBETA處理器
    processor = CBETAProcessor()
    
    # 確保數據目錄存在
    os.makedirs("data/cbeta", exist_ok=True)
    os.makedirs("data/vector_db", exist_ok=True)
    
    if args.list:
        # 顯示所有支持的經文
        print("支持的經文列表:")
        for sutra in settings.SUPPORTED_SUTRAS:
            print(f"{sutra['id']}: {sutra['name']}")
        return

    if args.name:
        # 根據名稱查找經文ID
        found = False
        search_term = args.name.lower()
        print(f"搜索包含 '{args.name}' 的經文:")
        for sutra in settings.SUPPORTED_SUTRAS:
            if search_term in sutra['name'].lower():
                print(f"{sutra['id']}: {sutra['name']}")
                found = True
        
        if not found:
            print(f"沒有找到包含 '{args.name}' 的經文")
        return

    if args.all:
        # 下載所有支持的經文
        print("開始下載所有支持的經文...")
        successfully_downloaded = []
        
        for sutra in settings.SUPPORTED_SUTRAS:
            print(f"下載 {sutra['id']}: {sutra['name']}...")
            success = await processor._download_sutra(sutra['id'])
            if success:
                successfully_downloaded.append(sutra['id'])
                print(f"✓ 成功下載 {sutra['id']}: {sutra['name']}")
            else:
                print(f"✗ 下載失敗 {sutra['id']}: {sutra['name']}")
        
        if not args.skip_index and successfully_downloaded:
            print("\n創建向量索引...")
            for sutra_id in successfully_downloaded:
                # 查找經文名稱
                sutra_name = None
                for sutra in settings.SUPPORTED_SUTRAS:
                    if sutra['id'] == sutra_id:
                        sutra_name = sutra['name']
                        break
                if sutra_name:
                    await processor.process_sutra(sutra_id, sutra_name)
            print("向量索引創建完成")
        
        print(f"\n下載完成。成功: {len(successfully_downloaded)}/{len(settings.SUPPORTED_SUTRAS)}")
        
    elif args.id:
        # 下載指定ID的經文
        sutra_id = args.id
        sutra_name = "未知經文"
        
        # 檢查ID是否在支持列表中
        valid_id = False
        for sutra in settings.SUPPORTED_SUTRAS:
            if sutra['id'].lower() == sutra_id.lower():
                sutra_id = sutra['id']  # 使用正確的大小寫
                sutra_name = sutra['name']
                valid_id = True
                break
        
        if not valid_id:
            print(f"警告: {sutra_id} 不在支持的經文列表中")
            proceed = input("是否繼續? (y/n): ")
            if proceed.lower() != 'y':
                return
        
        print(f"開始下載 {sutra_id}: {sutra_name}...")
        success = await processor._download_sutra(sutra_id)
        
        if success:
            print(f"✓ 成功下載 {sutra_id}: {sutra_name}")
            
            if not args.skip_index:
                print("\n創建向量索引...")
                await processor.process_sutra(sutra_id, sutra_name)
                print("向量索引創建完成")
        else:
            print(f"✗ 下載失敗 {sutra_id}")
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main()) 