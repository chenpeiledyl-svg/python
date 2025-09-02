#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
读取座位数据CSV并绘制“剩余空间(AvailableSpace)”折线图。
- X 轴：当天从 00:00 起算的分钟数（同时显示成 HH:MM 刻度）
- Y 轴：AvailableSpace
- 按 name 分组绘制多条折线（例如 A区、B区、C区）

用法示例：
  python plot_available_space.py data.csv
  # 或者让它自己找当前目录下的 data.csv：
  python plot_available_space.py
"""

import sys
import os
from datetime import timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FuncFormatter

def pick_chinese_font():
    """尽量设置中文字体（在没有中文字体的环境下也能退化运行）"""
    try:
        from matplotlib import font_manager
        # 常见中文字体候选
        candidates = [
            "SimHei", "Microsoft YaHei", "Noto Sans CJK SC",
            "Source Han Sans SC", "WenQuanYi Zen Hei", "PingFang SC"
        ]
        installed = {f.name for f in font_manager.fontManager.ttflist}
        for name in candidates:
            if name in installed:
                plt.rcParams["font.sans-serif"] = [name]
                break
        # 解决负号显示问题
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass

def minute_to_hhmm(m):
    """把 0..1439 的分钟数转为 HH:MM 字符串"""
    m = int(m)
    if m < 0:
        m = 0
    # 允许超过 1440 的值，按天内取模仅用于标签；原始数值仍用于排序
    m_mod = m % (24 * 60)
    td = timedelta(minutes=m_mod)
    h = td.seconds // 3600
    mm = (td.seconds % 3600) // 60
    return f"{h:02d}:{mm:02d}"

def load_data(path: str) -> pd.DataFrame:
    # 读取 CSV（自动识别 UTF-8/GBK；若失败再退回 utf-8）
    encodings = ["utf-8-sig", "utf-8", "gbk"]
    last_err = None
    for enc in encodings:
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except Exception as e:
            last_err = e
    else:
        raise last_err

    required = {"minute", "id", "name", "TotalCount", "UnavailableSpace", "AvailableSpace"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV 缺少列：{missing}")

    # 清理并排序
    df = df.copy()
    df["minute"] = pd.to_numeric(df["minute"], errors="coerce")
    df["AvailableSpace"] = pd.to_numeric(df["AvailableSpace"], errors="coerce")
    df = df.dropna(subset=["minute", "AvailableSpace"])
    df = df.sort_values(["name", "minute"])
    return df

def plot_available_space(df: pd.DataFrame, out_png: str = "available_space.png"):
    pick_chinese_font()

    # 透视为宽表：index=minute, columns=name, values=AvailableSpace
    wide = df.pivot_table(index="minute", columns="name", values="AvailableSpace", aggfunc="last")
    wide = wide.sort_index()

    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    wide.plot(ax=ax, marker="o", linewidth=1.8, markersize=3)  # 默认配色即可

    ax.set_title("各区剩余空间（AvailableSpace）随时间变化")
    ax.set_xlabel("时间（当天分钟数 / HH:MM）")
    ax.set_ylabel("剩余空间")

    # X 轴整数刻度 + 同时显示 HH:MM 标签（稀疏显示，避免拥挤）
    ax.xaxis.set_major_locator(MaxNLocator(nbins=10, integer=True))
    def dual_label(x, pos):
        return f"{int(x)}\n{minute_to_hhmm(x)}"
    ax.xaxis.set_major_formatter(FuncFormatter(dual_label))

    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(title="区域（name）", loc="best", fontsize=9)

    plt.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    print(f"✅ 已保存图像：{os.path.abspath(out_png)}")

def main():
    # 从命令行参数取文件名，否则尝试 data.csv
    path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    if not os.path.exists(path):
        # 兼容从粘贴板或重定向输入：python plot_available_space.py - < data.csv
        if path == "-" or not sys.stdin.isatty():
            df = pd.read_csv(sys.stdin)
        else:
            print(f"未找到文件：{path}\n示例：python plot_available_space.py data.csv")
            sys.exit(1)
    else:
        df = load_data(path)

    plot_available_space(df)

if __name__ == "__main__":
    main()
