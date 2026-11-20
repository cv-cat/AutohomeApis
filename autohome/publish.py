# -*- coding: utf-8 -*-
"""汽车之家发布接口（需要登录 Cookie）。

发布链路：

1. `v2/topicentry/search` 关键词 → 目标论坛 bbsId/bbs
2. `uploadMultiClubImg` 上传图片，拿 CDN URL
3. `topic/topicAdd` 提交帖子（htmlContent + jsonContent 双写）

点赞 / 评论 / 回帖同属登录态写接口，见本类 `zan_add` / `comment_add` /
`reply_add`。

游客直接调这些接口服务端返回 ``-101 未登录`` / ``403``，因此全部带
`require_login` 前置校验，避免无效请求。
"""

import json
import time

from .auth import AuthManager

CLUB_OPEN_HOST = 'club-open-api.autohome.com.cn'
CLUB_HOST = 'club.autohome.com.cn'
CREATOR_HOST = 'creator.autohome.com.cn'


class PublishAPI(AuthManager):
    """发帖 / 点赞 / 评论 / 回帖。需要登录 Cookie。"""

    # ---------- 图片上传 ----------
    def upload_img(self, file_path_or_bytes, filename='image.jpg'):
        """上传图片到帖子图床，返回 CDN URL。"""
        self.require_login('图片上传')
        if isinstance(file_path_or_bytes, (bytes, bytearray)):
            content = bytes(file_path_or_bytes)
        else:
            with open(file_path_or_bytes, 'rb') as f:
                content = f.read()
        url = f'https://{CLUB_OPEN_HOST}/upload/uploadMultiClubImg'
        resp = self.session.post(
            url,
            params={'_appid': 'club', 't': self.now_ms()},
            headers=self._headers(f'https://{CREATOR_HOST}/',
                                   origin=f'https://{CREATOR_HOST}'),
            files={'file': (filename, content, 'image/jpeg'),
                   'biztype': (None, '1', None)},
            timeout=self.timeout)
        return resp.json()

    # ---------- 发帖 ----------
    @staticmethod
    def build_json_content(text, images=None):
        """构造编辑器 jsonContent（Lexical 风格树）。"""
        children = [{
            'children': [{'detail': 0, 'format': 0, 'mode': 'normal',
                          'style': '', 'text': text, 'type': 'text',
                          'version': 1}],
            'direction': 'ltr', 'format': '', 'indent': 0,
            'type': 'paragraph', 'version': 1,
        }]
        for img in (images or []):
            children.append({
                'src': img, 'width': 640, 'height': 427,
                'caption': 'image', 'attributes': [], 'type': 'image',
                'version': 1,
            })
        return {'root': {'children': children, 'direction': 'ltr',
                         'format': '', 'indent': 0, 'type': 'root',
                         'version': 1}}

    def publish_topic(self, title, text, bbs_id, bbs_name, images=None,
                      extend_obj=''):
        """发帖。需先 search_forum 拿 bbs_id/bbs_name。

        :param images: 已上传的 CDN URL 列表（先 upload_img）
        """
        self.require_login('发帖')
        html_content = f'<p class="editor-paragraph"><span>{text}</span></p>'
        for img in (images or []):
            html_content += f'<p class="editor-paragraph"><img src="{img}"></p>'
        data = {
            '_appid': 'club',
            'source': 'pc',
            'title': title,
            'htmlContent': html_content,
            'jsonContent': json.dumps(
                self.build_json_content(text, images), ensure_ascii=False),
            'bbs': str(bbs_name),
            'bbsId': str(bbs_id),
            'extendObj': extend_obj,
            'topicId': '0',
            'voteId': '',
            'videoType': '0',
            'tIsPoll': '0',
            'multibbsid': '',
            'nobbs': '',
            'workStatementIds': '',
        }
        resp = self.session.post(
            f'https://{CLUB_OPEN_HOST}/topic/topicAdd',
            params={'t': self.now_ms(), '_appid': 'club'},
            headers=self._headers(f'https://{CREATOR_HOST}/',
                                  origin=f'https://{CREATOR_HOST}'),
            data=data, timeout=self.timeout)
        return resp.json()

    def publish_with_images(self, title, text, kw, image_paths=None):
        """一步发帖：搜论坛 → 传图 → 提交。"""
        from .search import SearchAPI
        s = SearchAPI()
        forums = s.search_forum(kw)
        if not forums:
            raise ValueError(f'找不到论坛: {kw}')
        bbs_id, bbs_name = forums[0]['bbs_id'], forums[0]['bbs_name']
        urls = []
        for p in (image_paths or []):
            res = self.upload_img(p)
            urls.append(res['result'][0]['url'])
        return self.publish_topic(title, text, bbs_id, bbs_name, urls)

    # ---------- 互动 ----------
    def zan_add(self, topic_id, reply_id=0, source=9):
        """点赞（creator openapi，jsonp）。"""
        self.require_login('点赞')
        resp = self.session.get(
            f'https://{CREATOR_HOST}/openapi/club/web/zan/add',
            params={'topicid': topic_id, 'replyid': reply_id, 'source': source,
                    '_appid': 'creator', 'cb': 'ZanAddOK', '_': self.now_ms()},
            headers=self._headers(f'https://{CLUB_HOST}/'),
            timeout=self.timeout)
        return self.parse_jsonp(resp.text)

    def comment_add(self, topic_id, text, reply_id=0):
        """评论 / 楼中楼（club-open-api rout）。"""
        self.require_login('评论')
        data = {
            '_appid': 'club',
            'topicid': str(topic_id),
            'replyid': str(reply_id),
            'content': text,
            't': self.now_ms(),
        }
        resp = self.session.post(
            f'https://{CLUB_OPEN_HOST}/api/rout/club/comment/add',
            params={'_appid': 'club'},
            headers=self._headers(f'https://{CLUB_HOST}/',
                                  origin=f'https://{CLUB_HOST}'),
            data=data, timeout=self.timeout)
        return resp.json()

    def reply_add(self, topic_id, text, quote_reply_id=''):
        """回帖（frontapi）。"""
        self.require_login('回帖')
        data = {
            'topicid': str(topic_id),
            'bbsid': '',
            'content': text,
            'quotereplyid': str(quote_reply_id),
            't': self.now_ms(),
        }
        resp = self.session.post(
            f'https://{CLUB_HOST}/frontapi/reply/add',
            headers=self._headers(f'https://{CLUB_HOST}/',
                                  origin=f'https://{CLUB_HOST}'),
            data=data, timeout=self.timeout)
        return resp.json()

    # ---------- 创作平台内容接口 ----------
    def check_publish(self):
        """创作平台权限自检（gc/checkPublish）。403 = 无权限/未登录。"""
        return self.get(f'{CREATOR_HOST}/content-api/gc/checkPublish',
                        params={'_appid': 'creator'},
                        referer=f'https://{CREATOR_HOST}/')
