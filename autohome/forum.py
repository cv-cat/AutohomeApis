# -*- coding: utf-8 -*-
"""汽车之家论坛列表接口（游客可用）。

- `club-open-api getClubTopicList`：指定论坛的帖子流，按发表时间/热度排序翻页
- `frontapi/topics/getUpListByBbsId`：置顶帖
- `la.autohome club_get_bbs_user_count`：论坛用户数
"""

from .base import BaseClient

CLUB_HOST = 'club.autohome.com.cn'


class ForumAPI(BaseClient):
    """论坛帖子列表。游客可用。"""

    def get_topic_list(self, bbs_id, page_num=1, page_size=50, order=1,
                       bbs_type='c'):
        """论坛帖子流。

        :param bbs_id: 论坛 id（search_forum 拿到）
        :param order: 1=最新发表 2=最新回复 3=热门
        :param bbs_type: c=论坛帖
        :return: dict（含 result.list 帖子数组）
        """
        res = self.get('club-open-api.autohome.com.cn/api/pc/bbs/index/getClubTopicList',
                       params={
                           '_appid': 'club', 'scenes': '1',
                           'page_num': page_num, 'page_size': page_size,
                           'club_bbs_type': bbs_type, 'club_bbs_id': bbs_id,
                           'club_order_type': order,
                       }, referer=f'https://{CLUB_HOST}/')
        return res

    @staticmethod
    def parse_topic_list(res):
        """帖子流 → 扁平列表 [{topic_id, title, author, stats...}]。"""
        lst = res.get('result', {}).get('items', [])
        out = []
        for t in lst:
            out.append({
                'topic_id': str(t.get('biz_id') or t.get('topicid') or ''),
                'title': t.get('title') or t.get('club_title') or '',
                'bbs_id': t.get('club_bbs_id'),
                'bbs_name': t.get('club_bbs_name'),
                'author_id': str(t.get('author_id') or ''),
                'author': t.get('author_name'),
                'reply_count': t.get('reply_count') or t.get('topic_reply_count'),
                'view_count': t.get('pv_count') or t.get('view_count'),
                'publish_time': t.get('publish_time') or t.get('club_publishtime'),
                'url': t.get('url') or '',
            })
        return out

    def iter_topic_list(self, bbs_id, pages=1, page_size=50, order=1):
        """翻页迭代论坛帖子。"""
        out = []
        for page in range(1, pages + 1):
            res = self.get_topic_list(bbs_id, page_num=page, page_size=page_size,
                                      order=order)
            items = self.parse_topic_list(res)
            if not items:
                break
            out.extend(items)
        return out

    def get_top_topics(self, bbs_id, top=6):
        """置顶帖。"""
        return self.get(f'{CLUB_HOST}/frontapi/topics/getUpListByBbsId',
                        params={'fields': 'url,title', 'bbsid': bbs_id, 'top': top})

    def get_bbs_user_count(self, bbs_id):
        """论坛成员数。"""
        return self.get('la.autohome.com.cn/club/club_get_bbs_user_count',
                        params={'_appid': 'club', 'bbsId': bbs_id},
                        referer=f'https://{CLUB_HOST}/')
