import requests, json
import csv
import sys
from datetime import datetime
import os

URL = "http://libzw.csu.edu.cn/api.php/v3areas/95"
HEAD = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
}

def get_minutes_from_midnight():
    """获取从当天00:00开始的分钟数"""
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = now - midnight
    return int(delta.total_seconds() // 60)

def walk(node, results):
    """递归统计 childArea，只收集具有TotalCount的叶节点"""
    if "TotalCount" in node:
        results.append({
            "minute": get_minutes_from_midnight(),
            "id": node["id"],
            "name": node["name"],
            "TotalCount": node["TotalCount"],
            "UnavailableSpace": node["UnavailableSpace"],
            "AvailableSpace": node["TotalCount"] - node["UnavailableSpace"]
        })
    # 递归子节点
    for ch in node.get("childArea", []):
        walk(ch, results)

def save_to_csv(data, date_str):
    """追加数据到按日期命名的CSV文件"""
    if not data:
        print("没有数据可保存")
        return
    
    filename = f"{date_str}.csv"
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['minute', 'id', 'name', 'TotalCount', 'UnavailableSpace', 'AvailableSpace']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # 如果文件不存在，写入表头
        if not file_exists:
            writer.writeheader()
        
        for row in data:
            writer.writerow(row)
    
    print(f"数据已追加到 {filename}")

def main():
    # 获取日期参数，默认为今天
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 更新请求头中的Referer
    HEAD["Referer"] = f"http://libzw.csu.edu.cn/web/seat2/area/95/day/{date_str.replace('-', '-')}"
    
    try:
        j = requests.get(URL, headers=HEAD, timeout=10).json()
        root = j["data"]["list"]
        rows = []
        walk(root, rows)

        # 输出到控制台
        current_minute = get_minutes_from_midnight()
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"\n=== 区域 95 · {date_str} · 第{current_minute}分钟 ({current_time}) ===")
        total_available = sum(r['AvailableSpace'] for r in rows)
        total_seats = sum(r['TotalCount'] for r in rows)
        print(f"总计可用座位: {total_available}/{total_seats}")
        
        for r in rows:
            print(f"{r['name']:<15} 可用 {r['AvailableSpace']:>3}/{r['TotalCount']:<3}")
        
        # 保存到CSV
        save_to_csv(rows, date_str)
        
    except Exception as e:
        print(f"获取数据失败: {e}")

if __name__ == "__main__":
    main()
