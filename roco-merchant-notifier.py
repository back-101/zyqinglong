# -*- coding: utf-8 -*-
"""
cron: 0 5 8,12,16,20 * * *
new Env('洛克王国');
"""

import os
import requests
import asyncio
from datetime import datetime, timedelta, timezone

# ================= 1. 核心配置 =================
ROCOM_API_KEY = os.environ.get("ROCOM_API_KEY", "")
GAME_API_URL = "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info?refresh=true"

# ================= 2. 青龙推送适配 =================
def load_send():
    """动态加载青龙内置的通知模块"""
    cur_path = os.path.abspath(__file__)
    parent_path = os.path.dirname(cur_path)
    notify_file = os.path.join(parent_path, "notify.py")

    if os.path.exists(notify_file):
        try:
            from notify import send
            return send
        except ImportError:
            return None
    return None

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(timezone(timedelta(hours=8)))

# ================= 3. 逻辑处理 =================
def get_status_msg(data):
    """扁平化处理：直接生成纯文本通知内容"""
    if not data or "merchantActivities" not in data:
        return "⚠️ 获取数据失败：接口返回格式异常"
    
    现在_ms = int(get_beijing_time().timestamp() * 1000)
    activity = data["merchantActivities"][0] if data["merchantActivities"] else {}
    all_items = (activity.get("get_props") or []) + (activity.get("get_pets") or [])
    
    active_items = []
    for item in all_items:
        s_time = item.get("start_time")
        e_time = item.get("end_time")
        # 筛选当前时间段的商品
        if s_time and e_time:
            if int(s_time) <= now_ms < int(e_time):
                active_items.append(f"· {item.get('name')} ({item.get('price_str', '点击查看')})")
        else:
            active_items.append(f"· {item.get('name')} (全天)")

    if not active_items:
        return "🛒 当前时段暂无正在售卖的商品。"

    msg = [
        f"📅 活动：{activity.get('name', '远行商人')}",
        f"⏰ 刷新：08:05 / 12:05 / 16:05 / 20:05",
        f"--- 当前在售商品 ({len(active_items)}) ---",
        "\n".join(active_items)
    ]
    return "\n".join(msg)

# ================= 4. 主入口 =================
async def main():
    send = load_send()
    title = "📢 洛克王国：远行商人情报"
    
    try:
        headers = {"X-API-Key": ROCOM_API_KEY} if ROCOM_API_KEY else {}
        resp = requests.get(GAME_API_URL, headers=headers, timeout=20)
        res_json = resp.json()
        
        if res_json.get("code") == 0:
            content = get_status_msg(res_json.get("data", {}))
        else:
            content = f"❌ 接口报错: {res_json.get('message')}"
            
    except Exception as e:
        content = f"🚀 网络请求异常: {str(e)}"

    print(f"{title}\n{content}")
    
    if send:
        send(title, content)
    else:
        print("\n[提示] 未检测到 notify.py，请在青龙面板中配置推送渠道。")

if __name__ == "__main__":
    asyncio.run(main())
