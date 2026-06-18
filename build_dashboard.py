#!/usr/bin/env python3
"""AI 金融投资情报看板 — 数据管道
用法: python3 build_dashboard.py
功能:
  1. 从 AI HOT API 拉取最新 AI 行业数据
  2. 按金融投资维度重新分类 (关键词匹配)
  3. 合并手动精选的金融专题内容
  4. 生成 data/current.json (最新数据) 和 data/history.json (历史存档)
  5. 保存每日快照 data/YYYY-MM-DD.json
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta

# ─── 路径 ───
BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

# ─── 6 大分类配置 ───
CATEGORIES = [
    {"key": "c1", "label": "公司财报与估值",      "color": "#ef4444"},
    {"key": "c2", "label": "融资、并购与IPO",     "color": "#f59e0b"},
    {"key": "c3", "label": "市场竞争格局",         "color": "#3b82f6"},
    {"key": "c4", "label": "产业链与宏观影响",     "color": "#8b5cf6"},
    {"key": "c5", "label": "投资策略与机构观点",   "color": "#10b981"},
    {"key": "c6", "label": "AI技术在金融行业的应用","color": "#06b6d4"},
]

# ─── 关键词分类规则 (按优先级) ───
CATEGORY_KEYWORDS = [
    ("c1", ["财报", "营收", "亏损", "利润", "估值", "现金消耗", "订阅份额", "revenue", "profit", "loss", "subscription", "pricing", "token economy", "领先优势", "领先地位"]),
    ("c2", ["IPO", "上市", "融资", "并购", "收购", "债券", "投资", "funding", "acquire", "invest", "估值", "billion", "partner network", "合作伙伴", "发行"]),
    ("c3", ["竞争", "市场份额", "转移", "离开", "加入", "赶超", "vs", "对决", "监管决定", "偏袒", "人才的", "market share", "rival", "competitor", "五角大楼", "白宫"]),
    ("c4", ["芯片", "供应链", "价格暴涨", "裁员", "成本", "基础设施", "涨价", "供应", "短缺", "chip", "supply", "hardware", "托管", "infrastructure"]),
    ("c5", ["投资者", "选股", "投资建议", "策略", "stocks to buy", "市场研判", "板块", "买入", "持仓", "股价", "涨停", "strategy", "outlook", "黄金时代", "指数"]),
    ("c6", ["金融", "银行", "证券", "量化", "风控", "投研", "客服", "监管", "合规", "finance", "banking", "trading", "investment tool", "证监会", "交易所", "券商", "评级", "研报"]),
]

def classify_item(item):
    """根据标题和摘要的关键词分类"""
    title = (item.get("title", "") + " " + item.get("summary", "")).lower()
    for key, keywords in CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw.lower() in title:
                return key
    # 默认归入行业应用
    return "c6"

def fetch_aihot(url, desc=""):
    """调用 AI HOT API"""
    ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        count = data.get("count", 0)
        print(f"  [OK] {desc}: {count} items")
        return data.get("items", [])
    except Exception as e:
        print(f"  [FAIL] {desc}: {e}")
        return []

def merge_and_dedupe(items_list):
    """合并多个数据源，按 URL 去重，保留最新的"""
    seen = {}
    for items in items_list:
        for item in items:
            url = item.get("url", "")
            if url not in seen or item.get("publishedAt", "") > seen[url].get("publishedAt", ""):
                seen[url] = item
    merged = list(seen.values())
    merged.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
    return merged

def add_manual_finance():
    """返回手动精选的金融专题内容（这些 AI HOT 可能覆盖不到）"""
    return [
        {"title":"方正证券研报「穿越」乌龙：AI 写研报将 2024 年国常会内容标为 2026 年","url":"https://baijiahao.baidu.com/s?id=1868062172770480923","source":"中国证券报（中证网）","publishedAt":"2026-06-15T11:28:00Z","summary":"方正证券 6 月 9 日发布的房地产研报将 2024 年政务会议完整台词标记为「2026 年最新会议部署」，引发市场争议。业内指出这是 AI 幻觉+网络信息污染+人工审核缺失三重叠加的结果。暴露了 AI 辅助写研报的监管真空。","tag":"合规风险","tagClass":"tag-bear","is_manual":True},
        {"title":"阿里云：金融智能体终于敢「真干活」，自研芯片金融部署超 10 万卡","url":"https://baijiahao.baidu.com/s?id=1868165143429109026","source":"阿里云官方（百家号）","publishedAt":"2026-06-16T13:00:00Z","summary":"阿里云智能副总裁张翅表示金融智能体已从「外挂」进化到「原生」，覆盖财富管理、信贷风控、投研投顾、合规监控等核心场景。平头哥真武 AI 芯片在金融行业部署超 10 万卡，覆盖 150+ 家主流金融机构。","tag":"金融科技","tagClass":"tag-bull","is_manual":True},
        {"title":"中原银行 AI 智能体、中信建投「信谛听」平台上线","url":"https://www.hlxxi.com/?p=196","source":"HLXXI 行业观察","publishedAt":"2026-06-14T10:30:00Z","summary":"金融 AI 智能体两标志性事件：中原银行外呼营销智能体获奖；中信建投证券核心业务切换至国产大模型。竞争正从「模型参数竞赛」转向「规模化交付能力」。","tag":"落地案例","tagClass":"tag-bull","is_manual":True},
        {"title":"AI 量化投资工具深度测评：AlphaGBM 领衔，散户入门门槛降低","url":"https://blog.csdn.net/2501_94780923/article/details/161677031","source":"CSDN AI 专栏","publishedAt":"2026-06-04T08:00:00Z","summary":"2026 年主流 AI 量化分析工具五维雷达测评。WorldQuant Brain、QuantConnect 等平台降低散户参与门槛。文章指出数据治理、模型可解释性、算力部署是未来焦点。","tag":"量化投资","tagClass":"tag-bull","is_manual":True},
        {"title":"证监会：系统推进 AI 在资本市场的应用研究与落地实践","url":"https://mp.weixin.qq.com/s?__biz=MjM5MTg0NDY1Mw==&mid=2654022901&idx=1","source":"证监会官网（微信公众号）","publishedAt":"2026-06-16T10:00:00Z","summary":"证监会科技监管司副司长在 2026 中国国际金融展上表示，行业已积极运用大模型等 AI 技术推动业务与监管全面数字化、智能化升级。正研究制定金融 AI 应用监管框架。","tag":"监管政策","tagClass":"tag-neutral","is_manual":True},
        {"title":"工行领航 AI+ 行动：30+ 业务场景落地 500+ AI 应用","url":"https://baijiahao.baidu.com/s?id=1862587351059405547","source":"百家号","publishedAt":"2026-04-16T09:00:00Z","summary":"工商银行将「数字工行」升级为「数智工行」，在 30 余个业务领域落地超 500 个 AI 应用场景。AI 数字员工承担工作量达 5.5 万人年。","tag":"银行","tagClass":"tag-bull","is_manual":True},
        {"title":"2026 年 6 月 A 股市场研判：AI 引领继续向上","url":"https://www.vzkoo.com/read/1077819510130001390b71f9e1e8.html","source":"未来智库","publishedAt":"2026-06-01T00:00:00Z","summary":"当前市场主要矛盾集中于海外美联储政策动向及 AI 产业叙事。国内经济与政策变化构成支撑，AI 产业链有望引领延续上涨。","tag":"策略","tagClass":"tag-bull","is_manual":True},
        {"title":"中概 AI 三条变现路径：算力收租最容易被财报验证","url":"https://baijiahao.baidu.com/s?id=1868304927357195714","source":"百家号","publishedAt":"2026-06-18T10:30:00Z","summary":"从百模大战到财报验证，分析指出中概 AI 最确定的变现路径是算力收租。阿里云 2026 年 Q1 收入同比增长 38%。","tag":"变现路径","tagClass":"tag-neutral","is_manual":True},
    ]

def main():
    print("=" * 50)
    print("AI 金融投资情报看板 — 数据管道")
    print(f"运行时间: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 50)

    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now().strftime("%Y-%m-%d")

    # Step 1: 从 AI HOT 拉取数据
    print("\n📡 Step 1: 拉取 AI HOT 数据...")
    
    base = "https://aihot.virxact.com/api/public/items"
    items1 = fetch_aihot(f"{base}?mode=selected&q=OpenAI&since={since}&take=50", "AI HOT (q=OpenAI)")
    items2 = fetch_aihot(f"{base}?mode=selected&category=industry&since={since}&take=30", "AI HOT (category=industry)")
    items3 = fetch_aihot(f"{base}?mode=selected&category=ai-models&since={since}&take=20", "AI HOT (category=ai-models)")
    items4 = fetch_aihot(f"{base}?mode=selected&category=ai-products&since={since}&take=20", "AI HOT (category=ai-products)")

    # Step 2: 合并去重
    print("\n🔀 Step 2: 合并去重...")
    all_items = merge_and_dedupe([items1, items2, items3, items4])
    print(f"  去重后: {len(all_items)} 条")

    # Step 3: 添加手动精选金融内容 + 分类
    print("\n🏷️  Step 3: 分类 + 补充金融内容...")
    manual = add_manual_finance()
    for item in manual:
        item["category"] = "c6"  # 金融行业应用
    all_items = manual + all_items

    # 给 AI HOT 数据做分类
    for item in all_items:
        if "category" not in item or item.get("category") in ("ai-models","ai-products","industry","paper","tip"):
            item["category"] = classify_item(item)
        # 确保有 tag 字段
        if "tag" not in item:
            item["tag"] = "AI动态"
            item["tagClass"] = "tag-neutral"
        if "tagClass" not in item:
            item["tagClass"] = "tag-neutral"

    # Step 4: 构建输出数据
    print("\n📦 Step 4: 构建输出...")
    output = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeWindow": {"start": since, "end": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
        "totalCount": len(all_items),
        "categories": CATEGORIES,
        "items": all_items,
    }
    
    # 各分类统计
    cat_counts = {}
    for cat in CATEGORIES:
        cat_counts[cat["key"]] = sum(1 for it in all_items if it.get("category") == cat["key"])
    output["catCounts"] = cat_counts
    
    print(f"  总计: {len(all_items)} 条")
    for cat in CATEGORIES:
        print(f"  {cat['label']}: {cat_counts[cat['key']]} 条")

    # Step 5: 写入文件
    print("\n💾 Step 5: 写入文件...")
    
    # current.json (最新)
    current_path = os.path.join(DATA, "current.json")
    with open(current_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {current_path}")

    # 每日快照
    snap_path = os.path.join(DATA, f"{today}.json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {snap_path}")

    # history.json (追加)
    history_path = os.path.join(DATA, "history.json")
    history = []
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    
    # 检查今天是否已有记录（避免同一天重复）
    exists = any(h.get("date") == today for h in history)
    if not exists:
        history.append({
            "date": today,
            "totalCount": len(all_items),
            "catCounts": cat_counts,
            "generatedAt": output["generatedAt"],
        })
        # 只保留最近 30 天
        history = history[-30:]
    
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {history_path} (累计 {len(history)} 天)")

    # Step 6: 更新部署目录
    print("\n🚀 Step 6: 更新部署目录...")
    deploy_dir = os.path.join(BASE, "deploy")
    deploy_data = os.path.join(deploy_dir, "data")
    os.makedirs(deploy_data, exist_ok=True)
    
    import shutil
    # 复制数据文件到部署目录
    for fname in ["current.json", "history.json", f"{today}.json"]:
        src = os.path.join(DATA, fname)
        dst = os.path.join(deploy_data, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    print(f"  ✓ 数据已复制到 {deploy_dir}/data/")
    print(f"  ℹ️  部署命令: 使用 CloudStudio 部署 {deploy_dir} 目录")
    print(f"  ℹ️  当前部署文件: {deploy_dir}/index.html + data/*.json")

    print("\n✅ 完成!")
    return output

if __name__ == "__main__":
    main()
