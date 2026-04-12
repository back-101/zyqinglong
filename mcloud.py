# 脚本名称: [移动云盘]
# 功能描述: [签到 基础任务 果园 云朵大作战]
# 使用说明:
#   - [抓包 Cookie：任意Authorization]
#   - [例: Basic cGMxxxxgzt@Basic cGMxxxxgzra]
# 环境变量设置:
#   - [ydyp_ck]

# 注: 本脚本仅用于个人学习和交流，请勿用于非法用途。作者不承担由于滥用此脚本所引起的任何责任，请在下载后24小时内删除。

# cron: 5 12 * * *
# const $ = new Env('移动云盘')

import os
import random
import re
import time
import json
import base64
from os import path

import requests

ua = 'Mozilla/5.0 (Linux; Android 14; KB2000 Build/UKQ1.230924.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/90.0.4430.210 Mobile Safari/537.36 MCloudApp/10.0.1'

err_accounts = ''  # 异常账号
err_message = ''  # 错误信息
user_amount = ''  # 用户云朵·数量
GLOBAL_DEBUG = False

# Bark推送配置
# ==================== Bark 推送配置 ====================
BARK_ICON = "https://gitee.com/hlt1995/BARK_ICON/raw/main/mcloud.png"     # 自定义图标
BARK_GROUP = "移动云盘"                     # 自定义分组
PUSH_SWITCH = "1"                #推送开关，1开启，0关闭
# =======================================================

os.environ["PUSH_SWITCH"] = PUSH_SWITCH

# 发送通知
def load_send():
    cur_path = path.abspath(path.dirname(__file__))
    notify_file = cur_path + "/notify.py"

    if path.exists(notify_file):
        try:
            from notify import send
            print("加载通知服务成功！")
            return send
        except ImportError:
            print("加载通知服务失败~")
    else:
        print("加载通知服务失败~")

    return False


class YP:
    def __init__(self, cookie):
        self.notebook_id = None
        self.note_token = None
        self.note_auth = None
        self.click_num = 15  # 定义抽奖次数和摇一摇戳一戳次数
        self.draw = 1  # 抽奖次数，首次免费
        self.session = requests.Session()

        self.timestamp = str(int(round(time.time() * 1000)))
        self.cookies = {'sensors_stay_time': self.timestamp}
        
        self.parse_cookie(cookie)
        
        if self.account and len(self.account) >= 7:
            self.encrypt_account = self.account[:3] + "*" * 4 + self.account[7:]
        else:
            self.encrypt_account = self.account or "未知账号"
            
        self.fruit_url = 'https://happy.mail.10086.cn/jsp/cn/garden/'

        self.jwtHeaders = {
            'User-Agent': ua,
            'Accept': '*/*',
            'Host': 'caiyun.feixin.10086.cn:7071',
        }
        self.treeHeaders = {
            'Host': 'happy.mail.10086.cn',
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': ua,
            'Referer': 'https://happy.mail.10086.cn/jsp/cn/garden/wap/index.html?sourceid=1003',
            'Cookie': '',
        }

    def parse_cookie(self, cookie):
        if '#' in cookie:
            parts = cookie.split("#")
            if len(parts) >= 3:
                self.Authorization = parts[0]
                self.account = parts[1]
                self.auth_token = parts[2]
                print(f"使用旧格式账号: {self.account[:3] + '*' * 4 + self.account[7:] if len(self.account) >= 7 else self.account}")
                return
        
        self.Authorization = cookie.strip()
        self.auth_token = "00"  
        
        try:
            if self.Authorization.startswith("Basic "):
                auth_value = self.Authorization[6:]
            else:
                auth_value = self.Authorization
            
            decoded_bytes = base64.b64decode(auth_value)
            decoded_str = decoded_bytes.decode('utf-8')
            
            parts = decoded_str.split(':')
            if len(parts) >= 2:
                self.account = parts[1]
            else:
                raise ValueError("无法从CK中解析手机号")
                
        except Exception as e:
            print(f"解析CK失败: {e}")
            self.account = "13800138000"
            print(f"使用默认手机号: {self.account}")

    # 捕获异常
    
    def catch_errors(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                global err_message
                print("错误:", str(e))
                err_message += f'用户[{self.encrypt_account}]:{e}\n'  # 错误信息
            return None

        return wrapper

    @catch_errors
    def run(self):
        if self.jwt():
            self.signin_status()
            self.click()
            self.get_tasklist(url = 'sign_in_3', app_type = 'cloud_app')
            print(f'\n☁️ 云朵大作战')
            self.cloud_game()
            print(f'\n🌳 果园任务')
            self.fruitLogin()
            print(f'\n📰 公众号任务')
            self.wxsign()
            self.shake()
            self.surplus_num()
            print(f'\n🔥 热门任务')
            self.backup_cloud()
            self.open_send()
            print(f'\n📧 139邮箱任务')
            self.get_tasklist(url = 'newsign_139mail', app_type = 'email_app')
            self.receive()
        else:
            global err_accounts
            # 失效账号
            err_accounts += f'{self.encrypt_account}\n'

    @catch_errors
    def send_request(self, url, headers=None, cookies=None, data=None, params=None, method='GET', debug=None,
                     retries=5):

        debug = debug if debug is not None else GLOBAL_DEBUG

        self.session.headers.update(headers or {})
        if cookies:
            self.session.cookies.update(cookies)
        request_args = {'json': data} if isinstance(data, dict) else {'data': data}

        for attempt in range(retries):
            try:
                response = self.session.request(method, url, params = params, **request_args)
                response.raise_for_status()
                if debug:
                    print(f'\n【{url}】响应数据:\n{response.text}')
                return response
            except (requests.RequestException, ConnectionError, TimeoutError) as e:
                print(f"请求异常: {e}")
                if attempt >= retries - 1:
                    print("达到最大重试次数。")
                    return None
                time.sleep(1)

    # 随机延迟默认1-1.5s
    def sleep(self, min_delay=1, max_delay=1.5):
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    # 日志
    def log_info(self, err_msg=None, amount=None):
        global err_message, user_amount
        if err_msg is not None:
            err_message += f'用户[{self.encrypt_account}]:{err_msg}\n'  # 错误信息
        elif amount is not None:
            user_amount += f'用户[{self.encrypt_account}]:{amount}\n'  # 云朵数量

    # 刷新令牌
    def sso(self):
        sso_url = 'https://orches.yun.139.com/orchestration/auth-rebuild/token/v1.0/querySpecToken'
        sso_headers = {
            'Authorization': self.Authorization,
            'User-Agent': ua,
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'Host': 'orches.yun.139.com'
        }
        sso_payload = {"account": self.account, "toSourceId": "001005"}
        sso_data = self.send_request(sso_url, headers = sso_headers, data = sso_payload, method = 'POST').json()

        if sso_data['success']:
            refresh_token = sso_data['data']['token']
            return refresh_token
        else:
            print(sso_data['message'])
            return None

    # jwt
    def jwt(self):
        # 获取jwttoken
        token = self.sso()
        if token is not None:

            jwt_url = f"https://caiyun.feixin.10086.cn:7071/portal/auth/tyrzLogin.action?ssoToken={token}"
            jwt_data = self.send_request(jwt_url, headers = self.jwtHeaders, method = 'POST').json()
            if jwt_data['code'] != 0:
                print(jwt_data['msg'])
                return False
            self.jwtHeaders['jwtToken'] = jwt_data['result']['token']
            self.cookies['jwtToken'] = jwt_data['result']['token']
            return True
        else:
            print('-ck可能失效了')
            return False

    # 签到查询
    @catch_errors
    def signin_status(self):
        self.sleep()
        check_url = 'https://caiyun.feixin.10086.cn/market/signin/page/info?client=app'
        check_data = self.send_request(check_url, headers = self.jwtHeaders, cookies = self.cookies).json()
        if check_data['msg'] == 'success':
            today_sign_in = check_data['result'].get('todaySignIn', False)

            if today_sign_in:
                print('✅已签到')
            else:
                print('❌ 未签到')
                signin_url = 'https://caiyun.feixin.10086.cn/market/manager/commonMarketconfig/getByMarketRuleName?marketName=sign_in_3'
                signin_data = self.send_request(signin_url, headers = self.jwtHeaders,
                                                cookies = self.cookies).json()

                if signin_data['msg'] == 'success':
                    print('✅签到成功')
                else:
                    print(signin_data['msg'])
                    self.log_info(signin_data['msg'])
        else:
            print(check_data['msg'])
            self.log_info(check_data['msg'])

    # 戳一下
    def click(self):
        url = "https://caiyun.feixin.10086.cn/market/signin/task/click?key=task&id=319"
        successful_click = 0  # 获得次数

        try:
            for _ in range(self.click_num):
                return_data = self.send_request(url, headers = self.jwtHeaders, cookies = self.cookies).json()
                time.sleep(0.2)

                if 'result' in return_data:
                    print(f'✅{return_data["result"]}')
                    successful_click += 1

            if successful_click == 0:
                print(f'❌未获得 x {self.click_num}')
        except Exception as e:
            print(f'错误信息:{e}')

    # 刷新笔记token
    @catch_errors
    def refresh_notetoken(self):
        note_url = 'http://mnote.caiyun.feixin.10086.cn/noteServer/api/authTokenRefresh.do'
        note_payload = {
            "authToken": self.auth_token,
            "userPhone": self.account
        }
        note_headers = {
            'X-Tingyun-Id': 'p35OnrDoP8k;c=2;r=1122634489;u=43ee994e8c3a6057970124db00b2442c::8B3D3F05462B6E4C',
            'Charset': 'UTF-8',
            'Connection': 'Keep-Alive',
            'User-Agent': 'mobile',
            'APP_CP': 'android',
            'CP_VERSION': '3.2.0',
            'x-huawei-channelsrc': '10001400',
            'Host': 'mnote.caiyun.feixin.10086.cn',
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept-Encoding': 'gzip'
        }

        try:
            response = self.send_request(note_url, headers = note_headers, data = note_payload, method = "POST")
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print('出错了:', e)
            return

        self.note_token = response.headers.get('NOTE_TOKEN')
        self.note_auth = response.headers.get('APP_AUTH')

    # 任务列表
    def get_tasklist(self, url, app_type):
        url = f'https://caiyun.feixin.10086.cn/market/signin/task/taskList?marketname={url}'
        return_data = self.send_request(url, headers = self.jwtHeaders, cookies = self.cookies).json()
        self.sleep()
        # 任务列表
        task_list = return_data.get('result', {})

        try:
            for task_type, tasks in task_list.items():
                if task_type in ["new", "hidden", "hiddenabc"]:
                    continue
                if app_type == 'cloud_app':
                    if task_type == "month":
                        print('\n📆 云盘每月任务')
                        for month in tasks:
                            task_id = month.get('id')
                            if task_id in [110, 113, 417, 409]:
                                continue
                            task_name = month.get('name', '')
                            task_status = month.get('state', '')

                            if task_status == 'FINISH':
                                print(f'-已完成: {task_name}')
                                continue
                            print(f'-去完成: {task_name}')
                            self.do_task(task_id, task_type = 'month', app_type = 'cloud_app')
                            time.sleep(2)
                    elif task_type == "day":
                        print('\n📆 云盘每日任务')
                        for day in tasks:
                            task_id = day.get('id')
                            if task_id == 404:
                                continue
                            task_name = day.get('name')
                            task_status = day.get('state', '')

                            if task_status == 'FINISH':
                                print(f'-已完成: {task_name}')
                                continue
                            print(f'-去完成: {task_name}')
                            self.do_task(task_id, task_type = 'day', app_type = 'cloud_app')
                elif app_type == 'email_app':
                    if task_type == "month":
                        print('\n📆 139邮箱每月任务')
                        for month in tasks:
                            task_id = month.get('id')
                            task_name = month.get('name', '')
                            task_status = month.get('state', '')
                            if task_id in [1004, 1005, 1015, 1020]:
                                continue

                            if task_status == 'FINISH':
                                print(f'-已完成: {task_name}')
                                continue
                            print(f'-去完成: {task_name}')
                            self.do_task(task_id, task_type = 'month', app_type = 'email_app')
                            time.sleep(2)
        except Exception as e:
            print(f'错误信息:{e}')

    # 做任务
    @catch_errors
    def do_task(self, task_id, task_type, app_type):
        self.sleep()
        task_url = f'https://caiyun.feixin.10086.cn/market/signin/task/click?key=task&id={task_id}'
        self.send_request(task_url, headers = self.jwtHeaders, cookies = self.cookies)

        if app_type == 'cloud_app':
            if task_type == 'day':
                if task_id == 106:
                    print('-开始上传文件，默认0kb')
                    self.updata_file()
                elif task_id == 107:
                    self.refresh_notetoken()
                    print('-获取默认笔记id')
                    note_url = 'http://mnote.caiyun.feixin.10086.cn/noteServer/api/syncNotebookV3.do'
                    headers = {
                        'X-Tingyun-Id': 'p35OnrDoP8k;c=2;r=1122634489;u=43ee994e8c3a6057970124db00b2442c::8B3D3F05462B6E4C',
                        'Charset': 'UTF-8',
                        'Connection': 'Keep-Alive',
                        'User-Agent': 'mobile',
                        'APP_CP': 'android',
                        'CP_VERSION': '3.2.0',
                        'x-huawei-channelsrc': '10001400',
                        'APP_NUMBER': self.account,
                        'APP_AUTH': self.note_auth,
                        'NOTE_TOKEN': self.note_token,
                        'Host': 'mnote.caiyun.feixin.10086.cn',
                        'Content-Type': 'application/json; charset=UTF-8',
                        'Accept': '*/*'
                    }
                    payload = {
                        "addNotebooks": [],
                        "delNotebooks": [],
                        "notebookRefs": [],
                        "updateNotebooks": []
                    }
                    return_data = self.send_request(url = note_url, headers = headers, data = payload,
                                                    method = 'POST').json()
                    if return_data is None:
                        return print('出错了')
                    self.notebook_id = return_data['notebooks'][0]['notebookId']
                    print('开始创建笔记')
                    self.create_note(headers)
            elif task_type == 'month':
                pass
        elif app_type == 'email_app':
            if task_type == 'month':
                pass

    # 上传文件
    @catch_errors
    def updata_file(self):
        url = 'http://ose.caiyun.feixin.10086.cn/richlifeApp/devapp/IUploadAndDownload'
        headers = {
            'x-huawei-uploadSrc': '1',
            'x-ClientOprType': '11',
            'Connection': 'keep-alive',
            'x-NetType': '6',
            'x-DeviceInfo': '6|127.0.0.1|1|10.0.1|Xiaomi|M2012K10C|CB63218727431865A48E691BFFDB49A1|02-00-00-00-00-00|android 11|1080X2272|zh||||032|',
            'x-huawei-channelSrc': '10000023',
            'x-MM-Source': '032',
            'x-SvcType': '1',
            'APP_NUMBER': self.account,
            'Authorization': self.Authorization,
            'X-Tingyun-Id': 'p35OnrDoP8k;c=2;r=1955442920;u=43ee994e8c3a6057970124db00b2442c::8B3D3F05462B6E4C',
            'Host': 'ose.caiyun.feixin.10086.cn',
            'User-Agent': 'okhttp/3.11.0',
            'Content-Type': 'application/xml; charset=UTF-8',
            'Accept': '*/*'
        }
        payload = '''
                                <pcUploadFileRequest>
                                    <ownerMSISDN>{phone}</ownerMSISDN>
                                    <fileCount>1</fileCount>
                                    <totalSize>1</totalSize>
                                    <uploadContentList length="1">
                                        <uploadContentInfo>
                                            <comlexFlag>0</comlexFlag>
                                            <contentDesc><![CDATA[]]></contentDesc>
                                            <contentName><![CDATA[000000.txt]]></contentName>
                                            <contentSize>1</contentSize>
                                            <contentTAGList></contentTAGList>
                                            <digest>C4CA4238A0B923820DCC509A6F75849B</digest>
                                            <exif/>
                                            <fileEtag>0</fileEtag>
                                            <fileVersion>0</fileVersion>
                                            <updateContentID></updateContentID>
                                        </uploadContentInfo>
                                    </uploadContentList>
                                    <newCatalogName></newCatalogName>
                                    <parentCatalogID></parentCatalogID>
                                    <operation>0</operation>
                                    <path></path>
                                    <manualRename>2</manualRename>
                                    <autoCreatePath length="0"/>
                                    <tagID></tagID>
                                    <tagType></tagType>
                                </pcUploadFileRequest>
                            '''.format(phone = self.account)

        response = requests.post(url = url, headers = headers, data = payload)
        if response is None:
            return
        if response.status_code != 200:
            return print('-上传失败')
        print('-上传文件成功')

    # 创建笔记
    def create_note(self, headers):
        note_id = self.get_note_id(32)  # 获取随机笔记id
        createtime = str(int(round(time.time() * 1000)))
        time.sleep(3)
        updatetime = str(int(round(time.time() * 1000)))
        note_url = 'http://mnote.caiyun.feixin.10086.cn/noteServer/api/createNote.do'
        payload = {
            "archived": 0,
            "attachmentdir": note_id,
            "attachmentdirid": "",
            "attachments": [],
            "audioInfo": {
                "audioDuration": 0,
                "audioSize": 0,
                "audioStatus": 0
            },
            "contentid": "",
            "contents": [{
                "contentid": 0,
                "data": "<font size=\"3\">000000</font>",
                "noteId": note_id,
                "sortOrder": 0,
                "type": "RICHTEXT"
            }],
            "cp": "",
            "createtime": createtime,
            "description": "android",
            "expands": {
                "noteType": 0
            },
            "latlng": "",
            "location": "",
            "noteid": note_id,
            'notestatus': 0,
            "remindtime": "",
            "remindtype": 1,
            "revision": "1",
            "sharecount": "0",
            "sharestatus": "0",
            "system": "mobile",
            "tags": [{
                "id": self.notebook_id,
                "orderIndex": "0",
                "text": "默认笔记本"
            }],
            "title": "00000",
            "topmost": "0",
            "updatetime": updatetime,
            "userphone": self.account,
            "version": "1.00",
            "visitTime": ""
        }
        create_note_data = self.send_request(note_url, headers = headers, data = payload, method = "POST")
        if create_note_data.status_code == 200:
            print('-创建笔记成功')
        else:
            print('-创建失败')

    # 笔记id
    def get_note_id(self, length):
        characters = '19f3a063d67e4694ca63a4227ec9a94a19088404f9a28084e3e486b928039a299bf756ebc77aa4f6bfa250308ec6a8be8b63b5271a00350d136d117b8a72f39c5bd15cdfd350cba4271dc797f15412d9f269e666aea5039f5049d00739b320bb9e8585a008b52c1cbd86970cae9476446f3e41871de8d9f6112db94b05e5dc7ea0a942a9daf145ac8e487d3d5cba7cea145680efc64794d43dd15c5062b81e1cda7bf278b9bc4e1b8955846e6bc4b6a61c28f831f81b2270289e5a8a677c3141ddc9868129060c0c3b5ef507fbd46c004f6de346332ef7f05c0094215eae1217ee7c13c8dca6d174cfb49c716dd42903bb4b02d823b5f1ff93c3f88768251b56cc'
        note_id = ''.join(random.choice(characters) for _ in range(length))
        return note_id

    # 公众号签到
    @catch_errors
    def wxsign(self):
        self.sleep()
        url = 'https://caiyun.feixin.10086.cn/market/playoffic/followSignInfo?isWx=true'
        return_data = self.send_request(url, headers = self.jwtHeaders, cookies = self.cookies).json()

        if return_data['msg'] != 'success':
            return print(return_data['msg'])
        if not return_data['result'].get('todaySignIn'):
            return print('❌签到失败,可能未绑定公众号')
        return print('✅签到成功')

    # 摇一摇
    def shake(self):
        url = "https://caiyun.feixin.10086.cn:7071/market/shake-server/shake/shakeIt?flag=1"
        successful_shakes = 0  # 记录成功摇中的次数

        try:
            for _ in range(self.click_num):
                return_data = self.send_request(url = url, cookies = self.cookies, headers = self.jwtHeaders,
                                                method = 'POST').json()
                time.sleep(1)
                shake_prize_config = return_data["result"].get("shakePrizeconfig")

                if shake_prize_config:
                    print(f"🎉摇一摇获得: {shake_prize_config['name']}")
                    successful_shakes += 1
        except Exception as e:
            print(f'错误信息: {e}')
        if successful_shakes == 0:
            print(f'❌未摇中 x {self.click_num}')

    # 查询剩余抽奖次数
    @catch_errors
    def surplus_num(self):
        self.sleep()
        draw_info_url = 'https://caiyun.feixin.10086.cn/market/playoffic/drawInfo'
        draw_url = "https://caiyun.feixin.10086.cn/market/playoffic/draw"

        draw_info_data = self.send_request(draw_info_url, headers = self.jwtHeaders).json()

        if draw_info_data.get('msg') == 'success':
            remain_num = draw_info_data['result'].get('surplusNumber', 0)
            print(f'剩余抽奖次数{remain_num}')
            if remain_num > 50 - self.draw:
                for _ in range(self.draw):
                    self.sleep()
                    draw_data = self.send_request(url = draw_url, headers = self.jwtHeaders).json()

                    if draw_data.get("code") == 0:
                        prize_name = draw_data["result"].get("prizeName", "")
                        print("✅抽奖成功，获得:" + prize_name)
                    else:
                        print("❌抽奖失败")
            else:
                pass
        else:
            print(draw_info_data.get('msg'))
            self.log_info(draw_info_data.get('msg'))

    # 果园专区
    @catch_errors
    def fruitLogin(self):
        token = self.sso()
        if token is not None:
            print("-果园专区token刷新成功")
            self.sleep()
            login_info_url = f'{self.fruit_url}login/caiyunsso.do?token={token}&account={self.account}&targetSourceId=001208&sourceid=1003&enableShare=1'
            headers = {
                'Host': 'happy.mail.10086.cn',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Referer': 'https://caiyun.feixin.10086.cn:7071/',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            loginInfoData = requests.request("GET", login_info_url, headers = headers)
            treeCookie = loginInfoData.request.headers['Cookie']
            self.treeHeaders['cookie'] = treeCookie

            do_login_url = f'{self.fruit_url}login/userinfo.do'
            doLoginData = self.send_request(do_login_url, headers = self.treeHeaders).json()
            if doLoginData.get('result', {}).get('islogin') != 1:
                return print('❌果园登录失败')
            # 去做果园任务
            self.fruitTask()
        else:
            print("果园专区token刷新失败")

    # 任务查询
    @catch_errors
    def fruitTask(self):
        # 签到任务
        check_sign_data = self.send_request(f'{self.fruit_url}task/checkinInfo.do',
                                            headers = self.treeHeaders).json()
        if check_sign_data.get('success'):
            today_checkin = check_sign_data.get('result', {}).get('todayCheckin', 0)
            if today_checkin == 1:
                print('-果园今日已签到')
            else:
                checkin_data = self.send_request(f'{self.fruit_url}task/checkin.do',
                                                 headers = self.treeHeaders).json()
                if checkin_data.get('result', {}).get('code', '') == 1:
                    print('-果园签到成功')
                self.sleep()
                water_data = self.send_request(f'{self.fruit_url}user/clickCartoon.do?cartoonType=widget',
                                               headers = self.treeHeaders).json()
                color_data = self.send_request(f'{self.fruit_url}user/clickCartoon.do?cartoonType=color',
                                               headers = self.treeHeaders).json()
                given_water = water_data.get('result', {}).get('given', 0)
                print(f'-领取每日水滴: {given_water}')
                print(f'-每日雨滴:{color_data.get("result").get("msg")}')
        else:
            print('-果园签到查询失败:', check_sign_data.get('msg', ''))

        # 获取任务列表
        task_list_data = self.send_request(f'{self.fruit_url}task/taskList.do?clientType=PE',
                                           headers = self.treeHeaders).json()
        task_state_data = self.send_request(f'{self.fruit_url}task/taskState.do', headers = self.treeHeaders).json()
        task_state_result = task_state_data.get('result', [])

        task_list = task_list_data.get('result', [])

        for task in task_list:
            task_id = task.get('taskId', '')
            task_name = task.get('taskName', '')
            water_num = task.get('waterNum', 0)
            if task_id == 2002 or task_id == 2003:
                continue

            task_state = next(
                (state.get('taskState', 0) for state in task_state_result if state.get('taskId') == task_id), 0)

            if task_state == 2:
                print(f'-已完成: {task_name}')
            else:
                self.do_fruit_task(task_name, task_id, water_num)

        # 果树信息
        self.tree_info()

    # 做任务
    @catch_errors
    def do_fruit_task(self, task_name, task_id, water_num):
        print(f'-去完成: {task_name}')
        do_task_url = f'{self.fruit_url}task/doTask.do?taskId={task_id}'
        do_task_data = self.send_request(do_task_url, headers = self.treeHeaders).json()

        if do_task_data.get('success'):
            get_water_url = f'{self.fruit_url}task/givenWater.do?taskId={task_id}'
            get_water_data = self.send_request(get_water_url, headers = self.treeHeaders).json()

            if get_water_data.get('success'):
                print(f'-已完成任务获得水滴: {water_num}')
            else:
                print(f'❌领取失败: {get_water_data.get("msg", "")}')
        else:
            print(f'❌参与任务失败: {do_task_data.get("msg", "")}')

    # 果树信息
    @catch_errors
    def tree_info(self):
        treeinfo_url = f'{self.fruit_url}user/treeInfo.do'
        treeinfo_data = self.send_request(treeinfo_url, headers = self.treeHeaders).json()

        if not treeinfo_data.get('success'):
            error_message = treeinfo_data.get('msg', '获取果园任务列表失败')
            print(error_message)
        else:
            collect_water = treeinfo_data.get('result', {}).get('collectWater', 0)
            tree_level = treeinfo_data.get('result', {}).get('treeLevel', 0)
            print(f'-当前小树等级: {tree_level} 剩余水滴: {collect_water}')
            if tree_level in (2, 4, 6, 8):
                # 开宝箱
                openbox_url = f'{self.fruit_url}prize/openBox.do'
                openbox_data = self.send_request(openbox_url, headers = self.treeHeaders).json()
                print(f'- {openbox_data.get("result").get("msg")}')

            watering_amount = collect_water // 20  # 计算需要浇水的次数
            watering_url = f'{self.fruit_url}user/watering.do?isFast=0'
            if watering_amount > 0:
                for _ in range(watering_amount):
                    watering_data = self.send_request(watering_url, headers = self.treeHeaders).json()
                    if watering_data.get('success'):
                        print('✔️ 浇水成功')
                        time.sleep(3)
            else:
                print('-水滴不足!')

    # 云朵大作战
    @catch_errors
    def cloud_game(self):
        game_info_url = 'https://caiyun.feixin.10086.cn/market/signin/hecheng1T/info?op=info'
        bigin_url = 'https://caiyun.feixin.10086.cn/market/signin/hecheng1T/beinvite'
        end_url = 'https://caiyun.feixin.10086.cn/market/signin/hecheng1T/finish?flag=true'

        game_info_data = self.send_request(game_info_url, headers = self.jwtHeaders, cookies = self.cookies).json()
        if game_info_data and game_info_data.get('code', -1) == 0:
            currnum = game_info_data.get('result', {}).get('info', {}).get('curr', 0)
            count = game_info_data.get('result', {}).get('history', {}).get('0', {}).get('count', '')
            rank = game_info_data.get('result', {}).get('history', {}).get('0', {}).get('rank', '')

            print(f'今日剩余游戏次数: {currnum}\n本月排名: {rank}    合成次数: {count}')

            for _ in range(currnum):
                self.send_request(bigin_url, headers = self.jwtHeaders, cookies = self.cookies).json()
                print('-开始游戏,等待10-15秒完成游戏')
                time.sleep(random.randint(10, 15))
                end_data = self.send_request(end_url, headers = self.jwtHeaders, cookies = self.cookies).json()
                if end_data and end_data.get('code', -1) == 0:
                    print('游戏成功')
        else:
            print("-获取游戏信息失败")

    # 领取云朵
    @catch_errors
    def receive(self):
        receive_url = "https://caiyun.feixin.10086.cn/market/signin/page/receive"
        prize_url = f"https://caiyun.feixin.10086.cn/market/prizeApi/checkPrize/getUserPrizeLogPage?currPage=1&pageSize=15&_={self.timestamp}"
        receive_data = self.send_request(receive_url, headers = self.jwtHeaders, cookies = self.cookies).json()
        self.sleep()
        prize_data = self.send_request(prize_url, headers = self.jwtHeaders, cookies = self.cookies).json()
        result = prize_data.get('result').get('result')
        rewards = ''
        for value in result:
            prizeName = value.get('prizeName')
            flag = value.get('flag')
            if flag == 1:
                rewards += f'-待领取奖品: {prizeName}\n'

        receive_amount = receive_data["result"].get("receive", "")
        total_amount = receive_data["result"].get("total", "")
        print(f'\n-当前待领取:{receive_amount}云朵')
        print(f'-当前云朵数量:{total_amount}云朵')
        msg = f'云朵数量:{total_amount} \n{rewards}'
        self.log_info(amount = msg)

    # 备份云朵
    @catch_errors
    def backup_cloud(self):
        backup_url = 'https://caiyun.feixin.10086.cn/market/backupgift/info'
        backup_data = self.send_request(backup_url, headers = self.jwtHeaders).json()
        state = backup_data.get('result', {}).get('state', '')
        if state == -1:
            print('本月未备份,暂无连续备份奖励')

        elif state == 0:
            print('-领取本月连续备份奖励')
            cur_url = 'https://caiyun.feixin.10086.cn/market/backupgift/receive'
            cur_data = self.send_request(cur_url, headers = self.jwtHeaders).json()
            print(f'-获得云朵数量:{cur_data.get("result").get("result")}')

        elif state == 1:
            print('-已领取本月连续备份奖励')
        self.sleep()
        expend_url = 'https://caiyun.feixin.10086.cn/market/signin/page/taskExpansion'  # 每月膨胀云朵
        expend_data = self.send_request(expend_url, headers = self.jwtHeaders, cookies = self.cookies).json()

        curMonthBackup = expend_data.get('result', {}).get('curMonthBackup', '')  # 本月备份
        preMonthBackup = expend_data.get('result', {}).get('preMonthBackup', '')  # 上月备份
        curMonthBackupTaskAccept = expend_data.get('result', {}).get('curMonthBackupTaskAccept', '')  # 本月是否领取
        nextMonthTaskRecordCount = expend_data.get('result', {}).get('nextMonthTaskRecordCount', '')  # 下月备份云朵
        acceptDate = expend_data.get('result', {}).get('acceptDate', '')  # 月份

        if curMonthBackup:
            print(f'- 本月已备份，下月可领取膨胀云朵: {nextMonthTaskRecordCount}')
        else:
            print('- 本月还未备份，下月暂无膨胀云朵')

        if preMonthBackup:
            if curMonthBackupTaskAccept:
                print('- 上月已备份，膨胀云朵已领取')
            else:
                # 领取
                receive_url = f'https://caiyun.feixin.10086.cn/market/signin/page/receiveTaskExpansion?acceptDate={acceptDate}'
                receive_data = self.send_request(receive_url, headers = self.jwtHeaders,
                                                 cookies = self.cookies).json()
                if receive_data.get("code") != 0:
                    print(f'-领取失败:{receive_data.get("msg")}')
                else:
                    cloudCount = receive_data.get('result', {}).get('cloudCount', '')
                    print(f'- 膨胀云朵领取成功: {cloudCount}朵')
        else:
            print('-上月未备份，本月无膨胀云朵领取')

    # #  开启备份
    # def open_backup(self):

    # 通知云朵
    @catch_errors
    def open_send(self):
        send_url = 'https://caiyun.feixin.10086.cn/market/msgPushOn/task/status'
        send_data = self.send_request(send_url, headers = self.jwtHeaders).json()

        pushOn = send_data.get('result', {}).get('pushOn', '')  # 0未开启，1开启，2未领取，3已领取
        firstTaskStatus = send_data.get('result', {}).get('firstTaskStatus', '')
        secondTaskStatus = send_data.get('result', {}).get('secondTaskStatus', '')
        onDuaration = send_data.get('result', {}).get('onDuaration', '')  # 开启时间

        if pushOn == 1:
            reward_url = 'https://caiyun.feixin.10086.cn/market/msgPushOn/task/obtain'

            if firstTaskStatus == 3:
                print('- 任务1奖励已领取')
            else:
                # 领取任务1
                print('- 领取任务1奖励')
                reward1_data = self.send_request(reward_url, headers = self.jwtHeaders, data = {"type": 1},
                                                 method = "POST").json()
                print(reward1_data.get('result', {}).get('description', ''))

            if secondTaskStatus == 2:
                # 领取任务2
                print('- 领取任务2奖励')
                reward2_data = self.send_request(reward_url, headers = self.jwtHeaders, data = {"type": 2},
                                                 method = "POST").json()
                print(reward2_data.get('result', {}).get('description', ''))

            print(f'- 通知已开启天数: {onDuaration}, 满31天可领取奖励')
        else:
            print('- 通知权限未开启')


if __name__ == "__main__":
    env_name = 'ydyp_ck'
    token = os.getenv(env_name)
    
    if not token:
        print(f'⛔️未获取到ck变量：请检查变量 {env_name} 是否填写')
        exit(0)

    cookies = re.split(r'[@\n]', token)
    print(f"移动云盘共获取到{len(cookies)}个账号")

    for i, account_info in enumerate(cookies, start = 1):
        print(f"\n======== ▷ 第 {i} 个账号 ◁ ========")
        YP(account_info).run()
        print("\n随机等待5-10s进行下一个账号")
        time.sleep(random.randint(5, 10))

    if err_accounts != '':
        print(f"\n失效账号:\n{err_accounts}")
    else:
        print('当前所有账号ck有效')
    
    print(user_amount)
    
    send = load_send()

    if PUSH_SWITCH == '1':
        if send:
            if err_accounts:
                msg = f"⚠️ 失效账号：\n{err_accounts}\n" + user_amount
            else:
                msg = user_amount
            send('☁️ 云朵资产统计', msg)
        else:
            print('通知服务不可用')
    else:
        print("推送开关已关闭，不发送推送通知")
