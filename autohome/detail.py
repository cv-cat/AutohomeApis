# -*- coding: utf-8 -*-
"""汽车之家帖子详情（游客可用）。

详情主体是服务端渲染 HTML（`club.autohome.com.cn/bbs/thread/<hash>/<topicid>-<page>.html`），
老格式 `bbs/thread-c-<bbsid>-<topicid>-<page>.html` 会 302 到新格式，需跟随。
楼层在 `js-reply-floor-container` 容器内，带 data-floor / data-reply-id /
data-member-id 属性；翻页总数在 `data-page-count`。

配套接口：

- `clubajax topic/rv`：浏览/回复统计（jsonprv）
- `frontapi/getclicksandreplys`：点击/回复数
- `Detail/GetVideoDetailRightV2` + `p-vp gpi`：视频信息与直链
- `club-open-api club/zan/list`：点赞列表
"""

import re

from .base import BaseClient

CLUB_HOST = 'club.autohome.com.cn'


class DetailAPI(BaseClient):
    """帖子详情页 + 统计 + 视频直链。游客可用。"""

    def get_thread_html(self, topic_id, page=1):
        """拉帖子页 HTML（自动跟随 302）。topic_id 数字或完整 URL 均可。"""
        url = (topic_id if str(topic_id).startswith('http')
               else f'https://{CLUB_HOST}/bbs/thread/a/{topic_id}-{page}.html')
        return self.session.get(url, headers=self._headers(f'https://{CLUB_HOST}/'),
                                timeout=self.timeout, allow_redirects=True)

    def parse_thread(self, html):
        """解析帖子页 HTML → dict（标题/正文/楼层/翻页数）。"""
        soup_title = (re.search(r'<h1[^>]*title="([^"]+)"', html)
                      or re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
                      or re.search(r'<title>[^|]*\|([^|<]+)', html))
        title = ''
        if soup_title:
            title = re.sub(r'<[^>]+>', '', soup_title.group(1)).strip()
        # 正文容器（新版 ssr 帖）
        content = ''
        m = re.search(r'class="topic-detail[^"]*"[^>]*>(.*?)<!--', html, re.S)
        if m:
            content = re.sub(r'<[^>]+>', '', m.group(1)).strip()[:5000]
        # 页数
        pc = re.findall(r'data-page-count="(\d+)"', html)
        page_count = int(pc[0]) if pc else 1
        return {
            'title': title,
            'content_text': content,
            'page_count': page_count,
            'floors': self.parse_floors(html),
        }

    @staticmethod
    def parse_floors(html):
        """解析楼层列表（服务端渲染部分，每页默认 20/15 楼）。"""
        floors = []
        for m in re.finditer(r'<li[^>]*js-reply-floor-container[^>]*>(.*?)</li>', html, re.S):
            block = m.group(0)
            def attr(name):
                a = re.search(rf'data-{name}="([^"]*)"', block)
                return a.group(1) if a else None
            tm = re.search(r'<strong>\s*(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s*</strong>', block)
            dm = re.search(r'reply-detail[^>]*>(.*?)(?:</div>\s*<div class="reply-handle"|</li>)', block, re.S)
            text = re.sub(r'<[^>]+>', '', dm.group(1)).strip() if dm else ''
            floors.append({
                'floor': attr('floor'),
                'reply_id': attr('reply-id'),
                'member_id': attr('member-id'),
                'quote_id': attr('quote-id'),
                'time': tm.group(1) if tm else None,
                'text': text[:2000],
            })
        return floors

    def get_thread(self, topic_id, pages=1):
        """帖子全文 + 楼层，多页自动翻。"""
        first = self.get_thread_html(topic_id, 1)
        html = first.text
        data = self.parse_thread(html)
        all_floors = data['floors']
        total = data['page_count']
        for page in range(2, min(pages, total) + 1):
            try:
                nxt = self.get_thread_html(topic_id, page)
                all_floors.extend(self.parse_floors(nxt.text))
            except Exception:
                break
        data['floors'] = all_floors
        data['floor_count'] = len(all_floors)
        return data

    # ---------- 统计 ----------
    def get_topic_stats(self, topic_id):
        """浏览/回复统计（clubajax jsonprv，游客可用）。"""
        res = self.get('clubajax.autohome.com.cn/topic/rv',
                       params={'fun': 'jsonprv', 'callback': 'jsonprv',
                               'ids': f'{topic_id},'},
                       referer=f'https://{CLUB_HOST}/')
        if isinstance(res, list):
            return res[0] if res else {}
        if isinstance(res, dict):
            return res
        return self.parse_jsonp(res)[0]

    def get_clicks_replys(self, topic_ids):
        """点击/回复数（frontapi）。topic_ids: list 或逗号串。"""
        if isinstance(topic_ids, (list, tuple)):
            topic_ids = ','.join(str(t) for t in topic_ids)
        return self.get(f'{CLUB_HOST}/frontapi/getclicksandreplys',
                        params={'topicids': topic_ids})

    def add_topic_click(self, topic_id):
        """上报浏览（frontapi，游客可调用）。"""
        return self.get(f'{CLUB_HOST}/frontapi/addtopicclick',
                        params={'topicid': topic_id})

    def get_zan_list(self, topic_id, member_id=''):
        """点赞列表（club-open-api，游客可用）。"""
        return self.get('club-open-api.autohome.com.cn/club/zan/list',
                        params={'_appid': 'club',
                                'input': f'{topic_id}-0',
                                'memberId': member_id})

    # ---------- 视频 ----------
    def get_video_right(self, topic_id, video_id, member_id=0):
        """视频帖右侧信息（作者、播放数等）。"""
        return self.get(f'{CLUB_HOST}/Detail/GetVideoDetailRightV2',
                        params={'topicId': topic_id, 'videoId': video_id,
                                'memberId': member_id},
                        referer=f'https://{CLUB_HOST}/')

    def get_video_url(self, video_id, ft='mp4', strategy=1):
        """视频播放直链（p-vp gpi）。"""
        res = self.get('p-vp.autohome.com.cn/api/gpi',
                       params={'mid': video_id, 'ft': ft, 'strategy': strategy},
                       referer=f'https://{CLUB_HOST}/')
        return res

    def get_thread_video_url(self, topic_id):
        """帖子 → 视频 mp4 直链（视频帖专用）。

        链路：thread HTML 内嵌 vid（hash 型 id，非数字）→ p-vp gpi → qualities mp4。
        图文帖返回空列表。
        """
        html = self.get_thread_html(topic_id, 1).text
        m = re.search(r'"(?:videoId|videoid|vid|video_id)"\s*:\s*"([\w+\-]+)"', html)
        if not m:
            return []
        res = self.get_video_url(m.group(1))
        media = (res.get('result') or {}).get('media') or {}
        urls = []

        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str) and '.mp4' in o:
                urls.append(o)

        walk(media.get('qualities'))
        walk(media.get('extqualities'))
        return urls
