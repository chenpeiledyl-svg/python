import requests, json
import csv

URL   = "http://libzw.csu.edu.cn/api.php/v3areas/95"
DAY   = "2025-09-01"      # 想查询的日期
HEAD  = {                 # 你的 headers；Cookie 可留空试试
    "Referer": f"http://libzw.csu.edu.cn/web/seat2/area/95/day/{DAY.replace('-','-')}",
    "User-Agent":"Mozilla/5.0",
    "X-Requested-With":"XMLHttpRequest"
}

def walk(node, results):
    """递归统计 childArea，只收集具有TotalCount的叶节点"""
    if "TotalCount" in node:                      # 只处理有TotalCount的节点
        results.append({
            "id": node["id"],
            "name": node["name"],
            "TotalCount": node["TotalCount"],
            "UnavailableSpace": node["UnavailableSpace"]
        })
    # 递归子节点
    for ch in node.get("childArea", []):
        walk(ch, results)

def save_to_csv(data, filename="seat_data.csv"):
    """保存数据到CSV文件"""
    if not data:
        print("没有数据可保存")
        return
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'name', 'TotalCount', 'UnavailableSpace']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    print(f"数据已保存到 {filename}")

def main():
    j = requests.get(URL, headers=HEAD, timeout=10).json()
    root = j["data"]["list"]                 # ← 顶层节点
    rows = []
    walk(root, rows)

    # 输出到控制台
    print(f"\n=== 区域 95 · {DAY} ===")
    for r in rows:
        free = r['TotalCount'] - r['UnavailableSpace']
        print(f"{r['name']:<12} 余量 {free:>3}/{r['TotalCount']:<3}")
    
    # 保存到CSV
    save_to_csv(rows)
    
    # 打印CSV格式预览
    print("\nCSV格式预览:")
    print("id,name,TotalCount,UnavailableSpace")
    for r in rows:
        print(f"{r['id']},{r['name']},{r['TotalCount']},{r['UnavailableSpace']}")

if __name__ == "__main__":
    main()
