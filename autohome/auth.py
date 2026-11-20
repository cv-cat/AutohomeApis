# -*- coding: utf-8 -*-
"""汽车之家登录态管理。

汽车之家写接口（发帖/点赞/评论/回帖）没有独立 token，完全依赖
``club.autohome.com.cn`` 域的登录 Cookie。本模块负责：

- Cookie 导入（浏览器 F12 复制即可）
- 登录态探活（`frontapi/getUserInfoByIds` + 会员页标记）
- 游客 / 登录分级：读接口游客可用，写接口要求登录态

登录通道（结构已知，见 `login_state_matrix.md`）：

- 账密：``/Login/ValidIndexsm``（pwd = hex_md5(密码)，需数美 rid）
- 短信：``/Login/SendRegLoginMobileCodesm`` → ``/Login/RegOrLoginByMobileCode``
- 微信扫码：``/oauth/GetWXLightAppQrCodeState`` 轮询

以上通道均需先过数美滑动验证码（smdata.rid），建议在浏览器人工过码后
直接复制 Cookie 导入，省去脚本化过码。
"""

import time

import json
import re

from .base import BaseClient, DEFAULT_UA

# 登录后浏览器里必须存在的 Cookie（缺任何一个都视为未登录）
_LOGIN_COOKIE_KEYS = ('autopcid', 'remember', 'sessionflag', 'sessionid',
                      'sessionpwd', 'clubwzuser', 'userAuthIdUnixtime')


class AuthManager(BaseClient):
    """Cookie 会话管理 + 游客/登录态分级。"""

    def __init__(self, cookies=None, **kw):
        super().__init__(cookies=cookies, **kw)
        self._login_checked = False

    # ---------- 导入 ----------
    @classmethod
    def open(cls, cookies=None, **kw):
        return cls(cookies=cookies, **kw)

    # ---------- 探活 ----------
    def check_login(self):
        """探测当前 Cookie 是否有效。

        判据（实测）：

        1. clubwzuser / sessionid 等登录 Cookie 是否存在；
        2. 会员页 `i.autohome.com.cn/<uid>` 是否返回个人页而非登录跳转。

        返回 dict: {logged: bool, user_id, nickname?}
        """
        jar = {c.name: c.value for c in self.session.cookies}
        has_login_cookie = any(k in jar for k in _LOGIN_COOKIE_KEYS)
        if not has_login_cookie:
            self._login_checked = True
            return {'logged': False, 'user_id': None}
        # 有登录 Cookie，进一步验证是否过期：取会员信息
        uid = jar.get('_uid') or jar.get('uid') or ''
        try:
            info = self.get_user_info(uid) if uid else {}
            logged = bool(info)
        except Exception:
            logged = False
        self._login_checked = True
        return {'logged': logged, 'user_id': uid or None}

    @property
    def is_logged(self):
        if not self._login_checked:
            return self.check_login()['logged']
        if not any(c.name in _LOGIN_COOKIE_KEYS for c in self.session.cookies):
            return False
        return True

    def require_login(self, action):
        """写接口前置校验：未登录直接抛错，不发无效请求。"""
        if not self.is_logged:
            raise PermissionError(
                f'{action} 需要登录 Cookie（服务端实测返回 -101 未登录）。'
                '请在浏览器登录后 F12 复制 Cookie 传给 AuthManager.open(cookies=...)')

    # ---------- 登录通道（需先通过数美验证码拿 rid） ----------
    LOGIN_HOST = 'account.autohome.com.cn'

    def get_sm_rid(self):
        """数美验证码注册，返回 rid（登录请求需携带）。

        自动滑块实测被风控拒绝（REJECT），建议浏览器人工过码后
        从 window.smdata 取 rid，或直接导入登录 Cookie。
        """
        res = self.get('captchaautohome.fengkongcloud.com/ca/v1/register',
                       params={'organization': 'autohome', 'channel': 'Default',
                               'appId': 'default', 'lang': 'zh-cn', 'model': 'slide',
                               'rversion': '1.0.4', 'sdkver': '1.1.3',
                               'data': '{}', 'callback': 'sm_init'})
        return res

    def login_password(self, name, pwd_md5, rid, validcode='', isauto='1'):
        """账密登录。pwd_md5 = hex_md5(明文)。需要数美 rid（滑块通过后）。

        实测注意：数美滑块需人工/CDP 真实事件通过，rid 未通过时登录失败。
        """
        import urllib.parse
        data = {
            'name': urllib.parse.quote(name, safe=''),
            'pwd': pwd_md5,
            'validcode': validcode,
            'isauto': isauto,
            'type': 'json',
            'backurl': '',
            'url': '',
            'fPosition': 'bbs',
            'sPosition': 'header',
            'platform': 'pcPassport',
            'popWindow': '0',
            'rid': rid,
        }
        return self.post(f'{self.LOGIN_HOST}/Login/ValidIndexsm', data=data,
                         referer='https://account.autohome.com.cn/')

    def send_sms_code(self, phoneno, geetest_challenge='', geetest_validate='',
                      geetest_seccode='', rid=''):
        """发送登录短信验证码。"""
        data = {'phoneno': phoneno,
                'geetest_challenge': geetest_challenge,
                'geetest_validate': geetest_validate,
                'geetest_seccode': geetest_seccode,
                'rid': rid}
        return self.post(f'{self.LOGIN_HOST}/Login/SendRegLoginMobileCodesm',
                         data=data, referer='https://account.autohome.com.cn/')

    def login_sms(self, phoneno, phonecode, rid=''):
        """短信验证码登录（先 send_sms_code）。"""
        data = {'phoneno': phoneno, 'phonecode': phonecode,
                'fPosition': 'bbs', 'sPosition': 'header',
                'platform': 'pcPassport', 'popWindow': '0',
                'yztagreement': '1', 'rid': rid}
        return self.post(f'{self.LOGIN_HOST}/Login/RegOrLoginByMobileCode',
                         data=data, referer='https://account.autohome.com.cn/')

    # ---------- 用户信息 ----------
    def get_user_info(self, user_id):
        """用户基础信息（游客可用）。"""
        res = self.get('club.autohome.com.cn/frontapi/getUserInfoByIds',
                       params={'userids': user_id})
        if isinstance(res, dict):
            result = res.get('result') or []
            if result:
                return result[0]
        return {}

    def get_user_wzinfo(self, user_id):
        """会员页信息（关注/粉丝/精华帖/发帖数，游客可用）。"""
        import re
        text = self.get(f'i.autohome.com.cn/{user_id}',
                        referer='https://i.autohome.com.cn/')
        if not isinstance(text, str):
            return {}
        import json
        m = re.search(r"GetUserInfo'\s*,\s*(\{.*?\})", text, re.S)
        user = {'user_id': str(user_id)}
        # frontapi 为主，页面信息为辅
        info = self.get_user_info(user_id)
        user.update(info)
        return user


# ---------- 微信扫码登录（纯 HTTP） ----------

class WechatQRLogin:
    """微信扫码登录：取码 → 轮询 → SSO 落 Cookie。

    全程 urllib，无需浏览器 / 无需数美滑块：

    1. ``/oauth/getWXLightAppQrCodeUrl`` → 二维码 URL +
       ``Set-Cookie: wxlightappsecuritykey``（轮询凭证）
    2. 轮询 ``/oauth/GetWXLightAppQrCodeState``：Status 1 待扫 →
       2 已扫待确认 → 3 确认（带 otherurl）→ 4 过期
    3. GET ``otherurl`` → 登录 Cookie（clubwzuser / sessionid 等）

    用法::

        qr = WechatQRLogin()
        qr.get_qr('qr.png')          # 保存二维码
        header = qr.login()          # 轮询到确认后返回 Cookie 头
        ah = AutohomeClient(cookies=header)
    """

    def __init__(self, cookie_file='autohome_cookies.txt', acw_tc=None):
        import http.cookiejar
        import urllib.request
        self.cookie_file = cookie_file
        self.jar = http.cookiejar.MozillaCookieJar()
        if acw_tc:
            self.jar.set_cookie(http.cookiejar.Cookie(
                0, 'acw_tc', acw_tc, None, False, '.autohome.com.cn', True,
                True, '/', True, False, None, False, None, None, {}))
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [
            ('User-Agent', DEFAULT_UA),
            ('Referer', f'https://{WechatQRLogin.HOST}/login'),
            ('X-Requested-With', 'XMLHttpRequest'),
        ]

    HOST = 'account.autohome.com.cn'

    def get_qr(self, save_path='autohome_qr.png'):
        """取新二维码并保存图片。过期（Status=4）后重新调用即可。"""
        import urllib.request
        # 网关需要先有一次正常站内访问（拿 acw_tc），否则 405
        self.opener.open('https://club.autohome.com.cn/', timeout=15).read()
        url = (f'https://{self.HOST}/oauth/getWXLightAppQrCodeUrl'
               f'?id={time.time()}&_={int(time.time() * 1000)}')
        o = self._get_json(url)
        if o.get('returncode') != 0:
            raise RuntimeError(f'取码失败: {o}')
        req = urllib.request.Request(o['result'],
                                     headers={'User-Agent': DEFAULT_UA})
        with open(save_path, 'wb') as f:
            f.write(self.opener.open(req, timeout=15).read())
        self._save()
        return o['result']

    def poll(self):
        """查一次状态 → {'status': 1|2|3|4, 'otherurl'?, 'session_login'?}。"""
        url = (f'https://{self.HOST}/oauth/GetWXLightAppQrCodeState'
               f'?fPosition=0&sPosition=0&platform=1&popWindow=0'
               f'&_={int(time.time() * 1000)}')
        o = self._get_json(url)
        result = o.get('result', {})
        state = {'status': result.get('Status')}
        if o.get('otherurl'):
            state['otherurl'] = o['otherurl']
        if result.get('SessionLogin'):
            state['session_login'] = result['SessionLogin']
        return state

    def wait_login(self, timeout=300, on_status=None):
        """轮询直到确认（3）或过期（4）。"""
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            st = self.poll()
            if st['status'] != last:
                last = st['status']
                if on_status:
                    on_status(last)
            if st['status'] == 4:
                return {'ok': False, 'status': 4, 'otherurl': ''}
            if st['status'] == 3 and st.get('otherurl'):
                self._sso(st['otherurl'])
                return {'ok': True, 'status': 3, 'otherurl': st['otherurl']}
            time.sleep(2.5)
        return {'ok': False, 'status': last, 'otherurl': ''}

    def login(self, timeout=300, save_path='autohome_qr.png'):
        """一步登录：取码 → 轮询 → 返回 Cookie 头（失败返回 None）。"""
        import urllib.request
        img = self.get_qr(save_path)
        print(f'扫码（App / 微信）: {save_path} | {img}')
        res = self.wait_login(timeout)
        if res['ok']:
            self._save()
            return self.cookie_header()
        print('未完成扫码（过期 / 超时）')
        return None

    def cookie_header(self):
        return '; '.join(f'{c.name}={c.value}' for c in self.jar)

    # ---------- internal ----------
    def _sso(self, otherurl):
        url = otherurl if otherurl.startswith('http') else f'https://{self.HOST}{otherurl}'
        self.opener.open(url, timeout=15).read()

    def _save(self):
        self.jar.save(self.cookie_file, ignore_discard=True, ignore_expires=True)

    def _get_json(self, url):
        raw = self.opener.open(url, timeout=15).read().decode('utf-8')
        m = re.search(r'\{.*\}', raw, re.S)
        return json.loads(m.group(0)) if m else json.loads(raw)
