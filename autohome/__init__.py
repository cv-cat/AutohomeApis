# -*- coding: utf-8 -*-
"""AutohomeApis —— 汽车之家全接口 SDK（游客 + 登录态）。

用法::

    from autohome import AutohomeClient

    # 游客模式（无 Cookie）
    ah = AutohomeClient()
    cards = ah.search.search_topics('迈腾')
    thread = ah.detail.get_thread(116675148)

    # 登录模式（浏览器复制 Cookie）
    ah = AutohomeClient(cookies='clubwzuser=xxx; sessionid=xxx; ...')
    print(ah.auth.check_login())
    ah.publish.publish_with_images('标题', '正文', '迈腾', ['a.jpg'])
"""

from .auth import AuthManager
from .base import BaseClient, AutohomeAPIError
from .search import SearchAPI
from .detail import DetailAPI
from .forum import ForumAPI
from .user import UserAPI
from .publish import PublishAPI

__all__ = ['AutohomeClient', 'AuthManager', 'AutohomeAPIError',
           'SearchAPI', 'DetailAPI', 'ForumAPI', 'UserAPI', 'PublishAPI']


class AutohomeClient:
    """聚合入口：一个实例同时持游客读与登录写能力。

    :param cookies: 登录 Cookie（dict 或浏览器复制的字符串）。传 None 即游客模式。
    """

    def __init__(self, cookies=None, timeout=15, proxies=None):
        kw = dict(timeout=timeout, proxies=proxies)
        self.auth = AuthManager(cookies=cookies, **kw)
        self.search = SearchAPI(cookies=cookies, **kw)
        self.detail = DetailAPI(cookies=cookies, **kw)
        self.forum = ForumAPI(cookies=cookies, **kw)
        self.user = UserAPI(cookies=cookies, **kw)
        self.publish = PublishAPI(cookies=cookies, **kw)

    @property
    def is_logged(self):
        return self.auth.is_logged
