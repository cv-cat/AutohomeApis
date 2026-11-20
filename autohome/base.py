# -*- coding: utf-8 -*-
"""汽车之家请求基座。

统一 UA / Referer / Cookie 注入与 JSON / JSONP / HTML 三种响应解析。
接口分两级：

- **游客接口**：不登录即可用（搜索、帖子详情、用户信息、统计数据）。
- **登录接口**：需要浏览器登录 Cookie（发帖、点赞、评论、回帖），
  未登录时服务端返回 ``-101 未登录``。
"""

import json
import re
import time

import requests

requests.packages.urllib3.disable_warnings()

DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


class AutohomeAPIError(RuntimeError):
    """业务码非 0 / 解析失败；保留端点与原始响应供调用方处理。"""

    def __init__(self, endpoint, response, message=None):
        self.endpoint = endpoint
        self.response = response
        code = None
        if isinstance(response, dict):
            code = response.get('returncode', response.get('code'))
        super().__init__(message or f'{endpoint}: returncode={code}')


class BaseClient:
    """所有 API 模块的公共底座。"""

    def __init__(self, cookies=None, timeout=15, proxies=None):
        # cookies: dict 或 "k=v; k2=v2" 字符串（浏览器直接复制）
        self.session = requests.Session()
        self.session.verify = False
        if proxies:
            self.session.proxies.update(proxies)
        self.timeout = timeout
        if cookies:
            self.set_cookies(cookies)

    # ---------- cookie ----------
    def set_cookies(self, cookies):
        """导入登录 Cookie。支持 dict 或浏览器复制的原始 Cookie 头字符串。"""
        if isinstance(cookies, str):
            cookies = dict(kv.strip().split('=', 1) for kv in cookies.split(';') if '=' in kv)
        for k, v in cookies.items():
            self.session.cookies.set(k, v, domain='.autohome.com.cn')

    @property
    def cookie_header(self):
        return '; '.join(f'{c.name}={c.value}' for c in self.session.cookies)

    # ---------- 请求 ----------
    def _headers(self, referer='https://club.autohome.com.cn/', origin=None):
        referer = referer or 'https://club.autohome.com.cn/'
        return {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': referer,
            'Origin': origin or referer.rstrip('/'),
            'User-Agent': DEFAULT_UA,
        }

    def get(self, endpoint, params=None, referer=None, **kw):
        url = endpoint if endpoint.startswith('http') else f'https://{endpoint}'
        resp = self.session.get(url, params=params, headers=self._headers(referer),
                                timeout=self.timeout, **kw)
        return self._parse(url, resp)

    def post(self, endpoint, data=None, json_body=None, params=None,
             referer=None, **kw):
        url = endpoint if endpoint.startswith('http') else f'https://{endpoint}'
        headers = self._headers(referer)
        if json_body is not None:
            resp = self.session.post(url, params=params, headers=headers,
                                     json=json_body, timeout=self.timeout, **kw)
        else:
            resp = self.session.post(url, params=params, headers=headers,
                                     data=data, timeout=self.timeout, **kw)
        return self._parse(url, resp)

    # ---------- 解析 ----------
    def _parse(self, url, resp):
        text = resp.text
        ct = resp.headers.get('Content-Type', '')
        if 'javascript' in ct or text[:6] == '__jp8(' or text.startswith('__jp'):
            return self.parse_jsonp(text)
        if 'json' in ct:
            return resp.json()
        # 兜底：自动探测
        st = text.lstrip()
        if st[:1] in ('{', '['):
            return json.loads(st)
        return text

    @staticmethod
    def parse_jsonp(text):
        """`__jp8({...})` / `jsonprv([...])` → dict/list。"""
        st = text.strip()
        m = re.match(r'^[\w.$]+\((.*)\)\s*;?\s*$', st, re.S)
        if m:
            return json.loads(m.group(1))
        return json.loads(st)

    # ---------- 业务码 ----------
    def ensure_ok(self, endpoint, res, ok_code=0):
        if isinstance(res, dict):
            code = res.get('returncode')
            if code is not None and code != ok_code:
                raise AutohomeAPIError(endpoint, res)
        return res

    @staticmethod
    def now_ms():
        return str(int(time.time() * 1000))
