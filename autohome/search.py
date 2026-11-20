# -*- coding: utf-8 -*-
"""汽车之家搜索接口（游客可用，无需 Cookie）。

两个入口：

- **综合搜索** `sou.api.autohome.com.cn/v1/search`：全站内容卡片流，
  含帖子/新闻/车系/二手车/经销商等卡片类型，分页 offset/size。
- **论坛名搜索** `sou.api.autohome.com.cn/v2/topicentry/search`：
  关键词 → 论坛 bbsId/bbs 名，发帖时用它拿目标论坛。
"""

import json
import urllib.parse
import uuid

from .base import BaseClient, AutohomeAPIError

SOU_HOST = 'sou.api.autohome.com.cn'


class SearchAPI(BaseClient):
    """全站搜索 + 论坛名搜索。游客可用。"""

    def __init__(self, cookies=None, **kw):
        super().__init__(cookies=cookies, **kw)
        self._uuid = str(uuid.uuid4())

    @staticmethod
    def _ext(kw, offset, size):
        # ext 为搜索页固有结构，字段缺失也能搜，但带上与真实请求一致
        return json.dumps({
            'chl': '', 'plat': 'pc', 'pf': 'pc', 'bbsId': '', 'q': kw,
            'offset': offset, 'size': size, 'modify': '0',
            'cityid': 110100, 'version': '1.0.1', 'box_count': 0,
        }, ensure_ascii=False, separators=(',', ':'))

    def search(self, kw, page=1, size=20):
        """全站综合搜索。

        :param kw: 关键词
        :param page: 页码（内部换算 offset = (page-1)*size）
        :return: 卡片列表 dict，returncode!=0 时抛 AutohomeAPIError
        """
        offset = (page - 1) * size
        res = self.get(f'{SOU_HOST}/v1/search', params={
            'uuid': self._uuid, 'source': 'pc', 'is_base_exp': '0',
            'modify': '0', 'q': kw, 'entry': '42', 'error': '0',
            'pid': '90300024', 'offset': offset, 'size': size, 'page': page,
            'ext': self._ext(kw, offset, size),
        }, referer='https://sou.autohome.com.cn/')
        return self.ensure_ok('v1/search', res)

    # ---------- 卡片解析 ----------
    @staticmethod
    def parse_topic_cards(res):
        """把 v1/search 响应解析成扁平内容列表。

        两种卡片（实测结构）：

        - 内容卡：``iteminfo.data.{show,other,hot}``，帖子/新闻/视频混排，
          落地链接在 ``show.jump_url``，``other.detail_url`` 为兜底
        - 论坛盒：``iteminfo.type=luntan_box_topic``，内层
          ``data.data.list`` 为相关论坛 bbsid/bbsname
        """
        cards = []
        for item in res.get('result', {}).get('itemlist', []):
            info = item.get('iteminfo', {})
            data = info.get('data', {}) or {}
            # 内容卡
            show = data.get('show', {})
            if show and show.get('jump_url'):
                other = data.get('other', {}) or {}
                hot = data.get('hot', {}) or {}
                jump = show.get('jump_url')
                m_id = jump.rstrip('.html').rsplit('/', 1)[-1].split('-')[0]
                cards.append({
                    'biz_type': info.get('biz_type'),
                    'title': (show.get('title') or '').replace('<em>', '').replace('</em>', ''),
                    'author': show.get('author'),
                    'author_id': str(show.get('author_id') or ''),
                    'img_url': show.get('img_url'),
                    'jump_url': jump,
                    'topic_id': m_id if m_id.isdigit() else str(info.get('biz_id') or ''),
                    'bbs_id': other.get('bbs_id'),
                    'bbs_name': other.get('bbs_name'),
                    'publish_time': show.get('publish_time'),
                    'view': hot.get('view'), 'reply': hot.get('reply'),
                    'like': hot.get('like'),
                })
        return cards

    @staticmethod
    def parse_forum_boxes(res):
        """v1/search 里的相关论坛盒 → [{bbs_id, bbs_name}]。"""
        forums = []
        for item in res.get('result', {}).get('itemlist', []):
            info = item.get('iteminfo', {})
            if info.get('type') != 'luntan_box_topic':
                continue
            for f in (info.get('data', {}).get('data', {}) or {}).get('list', []):
                d = f.get('data', {})
                forums.append({
                    'bbs_id': d.get('bbsid'),
                    'bbs_name': d.get('bbsname'),
                    'bbs': d.get('bbs'),
                    'topic_count': d.get('topiccount') or d.get('bbsTopicCount'),
                })
        return forums

    def search_topics(self, kw, pages=1, size=20):
        """搜索并解析论坛帖卡片，自动翻页。"""
        out = []
        for page in range(1, pages + 1):
            res = self.search(kw, page=page, size=size)
            cards = self.parse_topic_cards(res)
            if not cards:
                break
            out.extend(cards)
        return out

    # ---------- 论坛名搜索 ----------
    def search_forum(self, kw):
        """关键词 → 论坛列表 [{bbs_id, bbs_name, ...}]。发帖前置步骤。"""
        res = self.get(f'{SOU_HOST}/v2/topicentry/search', params={
            '_appid': 'club', 'q': kw, '_callback': '__jp8',
        }, referer='https://club.autohome.com.cn/')
        # jsonp：__jp8({...})
        if isinstance(res, str):
            res = self.parse_jsonp(res)
        hits = res.get('result', {}).get('hitlist', [])
        forums = []
        for h in hits:
            d = h.get('data', {})
            forums.append({
                'bbs_id': d.get('bbsid') or h.get('id'),
                'bbs_name': d.get('bbsname'),
                'bbs': d.get('bbs'),
                'person_num': d.get('person_num'),
                'topic_count': d.get('topic_count'),
            })
        return forums
