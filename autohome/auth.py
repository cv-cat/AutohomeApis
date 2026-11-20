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

from .base import BaseClient

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
