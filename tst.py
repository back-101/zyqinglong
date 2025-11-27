# -*- coding: utf-8 -*-
"""
塔斯汀汉堡签到脚本（使用青龙notify模块）
原作者：https://github.com/linbailo/zyqinglong
二改：https://github.com/wanvfx/zyqinglong
最后更新日期：2025.6.8

功能说明：
1. 每日自动签到获取积分
2. 支持多账号管理
3. 使用青龙面板自带的notify.py模块发送通知

使用方法：
1. 添加环境变量 tst_tk_env
2. 格式：每行一个账号，格式为 token
   示例：
   sss113-23129-123123-123123
   sss234-23129-123123-234312
"""

import os
import time
import requests
import json
import sys
from datetime import datetime

# 配置区域
DEBUG_MODE = False  # 调试模式开关
MAX_RETRIES = 3  # 请求最大重试次数

# 全局通知内容
notification_list = []

# 导入青龙通知模块
try:
    sys.path.append('/ql/scripts')
    import notify
except ImportError:
    notify = None
    print("警告：未找到青龙通知模块，通知功能将不可用")

def log_debug(msg):
    """调试日志"""
    if DEBUG_MODE:
        print(f"[DEBUG] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_info(msg):
    """信息日志"""
    print(f"[INFO] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def log_error(msg):
    """错误日志"""
    print(f"[ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}")

def safe_request(method, url, **kwargs):
    """带重试机制的请求函数"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code == 200:
                return response
            log_error(f"请求失败: {url} 状态码: {response.status_code}")
        except Exception as e:
            log_error(f"请求异常: {url} 错误: {str(e)}")
        
        retries += 1
        if retries < MAX_RETRIES:
            time.sleep(2 ** retries)  # 指数退避
    return None

def add_notification(title, content):
    """添加到通知列表"""
    notification_list.append(f"【{title}】\n{content}")
    log_info(f"已添加通知: {title}")

def send_notification():
    """使用青龙通知模块发送通知"""
    if not notification_list:
        log_info("无通知内容，跳过发送")
        return
    
    if notify is None:
        log_error("通知模块未导入，无法发送通知")
        return
    
    content = "\n\n".join(notification_list)
    try:
        notify.send("塔斯汀签到脚本通知", content)
        log_info("通知发送成功")
    except Exception as e:
        log_error(f"发送通知异常: {str(e)}")

def checkin(tk):
    """签到功能"""
    # 获取动态活动ID
    activityId = qdsj(tk)
    
    # 如果动态获取失败，使用计算的活动ID
    if not activityId:
        current_date = datetime.now()
        activityId = 59 + (current_date.year - 2025) * 12 + (current_date.month - 5)
        log_info(f"使用计算的活动ID: {activityId}")

    url = "https://sss-web.tastientech.com/api/sign/member/signV2"
    payload = {"activityId": activityId, "memberName": "", "memberPhone": ""}
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) UnifiedPCWindowsWechat(0xf254032b) XWEB/13655",
        'Content-Type': "application/json",
        'xweb_xhr': "1",
        'user-token': tk,
        'channel': "1"
    }
    
    response = safe_request('POST', url, data=json.dumps(payload), headers=headers)
    if response:
        try:
            data = response.json()
            if data.get("code") == 200:
                # 解析签到结果
                if data['result']['rewardInfoList'][0].get('rewardName'):
                    reward = data['result']['rewardInfoList'][0]['rewardName']
                else:
                    reward = f"{data['result']['rewardInfoList'][0]['point']}积分"
                    
                # 添加到通知
                add_notification(
                    "签到成功", 
                    f"账号: {tk[:10]}...\n"
                    f"结果: 获得 {reward}\n"
                    f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                return True, f"签到成功，获得: {reward}"
            else:
                add_notification(
                    "签到失败", 
                    f"账号: {tk[:10]}...\n"
                    f"原因: {data.get('msg', '未知错误')}\n"
                    f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                return False, data.get("msg", f"签到失败: {response.text}")
        except Exception as e:
            add_notification(
                "签到异常", 
                f"账号: {tk[:10]}...\n"
                f"错误: {str(e)}\n"
                f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            return False, f"解析签到响应异常: {str(e)}"
    else:
        add_notification(
            "签到请求失败", 
            f"账号: {tk[:10]}...\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        return False, "请求失败"

def qdsj(ck):
    """获取签到活动ID"""
    headers = {
        'user-token': ck,
        'channel': '1'
    }
    data = {"shopId": "", "birthday": "", "gender": 0, "nickName": None, "phone": ""}
    response = safe_request('POST', 'https://sss-web.tastientech.com/api/minic/shop/intelligence/banner/c/list', 
                            json=data, headers=headers)
    
    if not response:
        return ''
    
    try:
        dl = response.json()
        activityId = ''
        for i in dl['result']:
            if '每日签到' in i['bannerName'] or '签到' in i['bannerName']:
                qd = i['jumpPara']
                activityId = json.loads(qd)['activityId']
                log_info(f"获取到本月签到代码：{activityId}")
                return activityId
    except Exception as e:
        log_error(f"解析签到活动ID异常: {str(e)}")
    
    return ''

def filter_lines(input_string):
    """过滤有效账号行"""
    lines = input_string.splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip()
    ]

def start():
    """主启动函数"""
    global notification_list
    
    # 环境变量处理
    env = os.getenv('tst_tk_env', '')
    accounts = filter_lines(env)
    if not accounts:
        log_error("未找到有效账号配置")
        add_notification("配置错误", "未找到有效账号配置，请检查环境变量tst_tk_env")
        return
    
    log_info(f"===== 开始执行签到，共 {len(accounts)} 个账号 =====")
    
    # 处理每个账号
    for account in accounts:
        try:
            tk = account.split('|')[0].strip()  # 只取token部分
            log_info(f"处理账号: {tk[:10]}...")
            
            # 签到
            success, message = checkin(tk)
            log_info(f"签到结果: {message}")
        except Exception as e:
            log_error(f"处理账号异常: {str(e)}")
    
    # 发送所有通知
    send_notification()
    log_info("===== 签到执行结束 =====")

if __name__ == '__main__':
    start()