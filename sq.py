import requests, json
import csv
import sys
from datetime import datetime
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

URL = "http://libzw.csu.edu.cn/api.php/v3areas/95"
LOGIN_URL = "http://libzw.csu.edu.cn/web/seat2/area/95"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('seat_monitor.log'),
            logging.StreamHandler()
        ]
    )

def get_minutes_from_midnight():
    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = now - midnight
    return int(delta.total_seconds() // 60)

def get_headers(date_str):
    """动态生成请求头，不依赖固定Cookie"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://libzw.csu.edu.cn/web/seat2/area/95/day/{date_str.replace('-', '-')}",
        "Connection": "keep-alive"
    }

def test_api_access(headers):
    """测试API是否可访问"""
    try:
        response = requests.get(URL, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "list" in data["data"]:
                return True, "API访问正常"
        return False, f"API返回异常: {response.status_code}"
    except Exception as e:
        return False, f"API访问失败: {e}"

def walk(node, results):
    if "TotalCount" in node:
        results.append({
            "minute": get_minutes_from_midnight(),
            "id": node["id"],
            "name": node["name"],
            "TotalCount": node["TotalCount"],
            "UnavailableSpace": node["UnavailableSpace"],
            "AvailableSpace": node["TotalCount"] - node["UnavailableSpace"]
        })
    for ch in node.get("childArea", []):
        walk(ch, results)

def save_to_csv(data, date_str):
    if not data:
        logging.warning("没有数据可保存")
        return
    
    filename = f"{date_str}.csv"
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['minute', 'id', 'name', 'TotalCount', 'UnavailableSpace', 'AvailableSpace']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            logging.info(f"创建新文件: {filename}")
        
        for row in data:
            writer.writerow(row)
    
    logging.info(f"数据已追加到 {filename}, 共{len(data)}条记录")

def get_session_with_selenium(date_str):
    """使用selenium获取有效的session"""
    options = Options()
    options.add_argument('--headless')  # 无头模式
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    try:
        # 使用webdriver-manager自动管理ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 访问目标页面
        target_url = f"http://libzw.csu.edu.cn/web/seat2/area/95/day/{date_str.replace('-', '-')}"
        logging.info(f"使用selenium访问: {target_url}")
        driver.get(target_url)
        
        # 等待页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # 获取cookies
        cookies = driver.get_cookies()
        session_cookies = {}
        for cookie in cookies:
            session_cookies[cookie['name']] = cookie['value']
        
        driver.quit()
        
        logging.info(f"成功获取session cookies: {list(session_cookies.keys())}")
        return session_cookies
        
    except Exception as e:
        logging.error(f"selenium获取session失败: {e}")
        return None

def get_headers_with_cookies(date_str, cookies=None):
    """生成包含cookies的请求头"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://libzw.csu.edu.cn/web/seat2/area/95/day/{date_str.replace('-', '-')}",
        "Connection": "keep-alive"
    }
    
    if cookies:
        cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        headers["Cookie"] = cookie_string
    
    return headers

def test_api_with_session(headers, cookies=None):
    """使用session测试API访问"""
    try:
        session = requests.Session()
        if cookies:
            session.cookies.update(cookies)
            
        response = session.get(URL, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "list" in data["data"]:
                return True, "API访问正常", session
        return False, f"API返回异常: {response.status_code}", None
    except Exception as e:
        return False, f"API访问失败: {e}", None

def main():
    setup_logging()
    
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    logging.info(f"开始监控座位数据 - 日期: {date_str}")
    
    # 首先尝试无cookies访问
    headers = get_headers_with_cookies(date_str)
    is_accessible, message, session = test_api_with_session(headers)
    
    if not is_accessible:
        logging.warning(f"无cookies访问失败: {message}")
        logging.info("尝试使用selenium获取有效session")
        
        # 使用selenium获取session
        cookies = get_session_with_selenium(date_str)
        if cookies:
            headers = get_headers_with_cookies(date_str, cookies)
            is_accessible, message, session = test_api_with_session(headers, cookies)
            
            if not is_accessible:
                logging.error(f"使用selenium session仍然失败: {message}")
                print(f"API访问失败: {message}")
                return
        else:
            logging.error("selenium获取session失败")
            print("无法获取有效session")
            return
    
    try:
        logging.info(f"请求API: {URL}")
        if session:
            response = session.get(URL, headers=headers, timeout=10)
        else:
            response = requests.get(URL, headers=headers, timeout=10)
        
        if response.status_code == 403:
            logging.warning("可能需要登录认证，尝试无认证访问")
        elif response.status_code == 302:
            logging.warning("遇到重定向，可能需要会话")
        
        response.raise_for_status()
        
        j = response.json()
        
        if "data" not in j or "list" not in j["data"]:
            logging.error(f"API返回数据结构异常: {j}")
            print("API返回数据格式不正确")
            return
            
        root = j["data"]["list"]
        rows = []
        walk(root, rows)

        if not rows:
            logging.warning("未获取到任何座位数据")
            print("警告: 未获取到座位数据，可能需要登录")
            return

        current_minute = get_minutes_from_midnight()
        current_time = datetime.now().strftime("%H:%M:%S")
        total_available = sum(r['AvailableSpace'] for r in rows)
        total_seats = sum(r['TotalCount'] for r in rows)
        
        print(f"\n=== 区域 95 · {date_str} · 第{current_minute}分钟 ({current_time}) ===")
        print(f"总计可用座位: {total_available}/{total_seats}")
        
        logging.info(f"成功获取数据 - 总座位: {total_seats}, 可用: {total_available}, 区域数: {len(rows)}")
        
        for r in rows:
            print(f"{r['name']:<15} 可用 {r['AvailableSpace']:>3}/{r['TotalCount']:<3}")
        
        save_to_csv(rows, date_str)
        logging.info("数据处理完成")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"网络请求失败: {e}")
        print(f"获取数据失败: {e}")
    except Exception as e:
        logging.error(f"程序执行失败: {e}")
        print(f"获取数据失败: {e}")

if __name__ == "__main__":
    main()
