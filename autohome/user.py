# -*- coding: utf-8 -*-
"""汽车之家用户接口（游客可用）。

- `frontapi/getUserInfoByIds`：昵称/注册时间/性别
- `i.autohome.com.cn/ajax/home/GetUserInfo`：精华帖数/发帖总数
- `iservice OtherTopic-<uid>-all-<page>.html`：用户历史发帖表（HTML 表格）
- `i.autohome.com.cn/<uid>`：会员页（关注/粉丝/位置）
"""

import re

from .base import BaseClient

CLUB_HOST = 'club.autohome.com.cn'


class UserAPI(BaseClient):
    """用户信息与历史发帖。游客可用。"""

    def get_user_info(self, user_id):
        """昵称/注册时间/性别等基础信息。"""
        res = self.get(f'{CLUB_HOST}/frontapi/getUserInfoByIds',
                       params={'userids': user_id})
        result = res.get('result') or []
        return result[0] if result else {}

    def get_user_counts(self, user_id):
        """发帖总量（iservice 表计数）。会员页 i.autohome 有 JS 挑战，不走。"""
        total = 0
        for page in range(1, 51):
            try:
                resp = self.get_user_posted_html(user_id, page)
            except Exception:
                break
            rows = self.parse_posted_rows(resp.text)
            if not rows:
                break
            total += len(rows)
        return {'topic_count': total}

    def get_user_page_stats(self, user_id):
        """会员页关注/粉丝数（解析 HTML）。"""
        text = self.get(f'i.autohome.com.cn/{user_id}',
                        referer='https://i.autohome.com.cn/')
        if not isinstance(text, str):
            return {}
        stats = {}
        m = re.findall(r'state-mes[^>]*><span[^>]*>([\d\.,万]+)</span>', text)
        if len(m) >= 2:
            stats['follows'], stats['fans'] = m[0], m[1]
        ip = re.search(r'IP属地[^<]*<[^>]*>([^<]+)', text)
        if ip:
            stats['ip_location'] = ip.group(1).strip()
        return stats

    def get_user_posted_html(self, user_id, page=1):
        """用户历史发帖列表页（iservice HTML 表格）。"""
        return self.session.get(
            f'https://iservice.autohome.com.cn/clubapp/OtherTopic-{user_id}-all-{page}.html',
            headers=self._headers('https://iservice.autohome.com.cn/'),
            timeout=self.timeout)

    @staticmethod
    def parse_posted_rows(html):
        """发帖表格 → [{title, link, topic_id, upload_time}]。"""
        rows = []
        for m in re.finditer(
                r"<p class=\"cp1\">\s*<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", html, re.S):
            link = m.group(1)
            if link.startswith('//'):
                link = 'https:' + link
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip().replace('\n', '')
            tid = link.rstrip('.html').rsplit('/', 1)[-1].split('-')[0]
            rows.append({'title': title, 'link': link,
                         'topic_id': tid if tid.isdigit() else None})
        # 时间在每行第二个 txtCen td：<td class="txtCen"> YYYY-MM-DD<br/>HH:MM
        times = re.findall(r'([\d\-]{10})<br\s*/?>\s*([\d:]{5})', html)
        for row, t in zip(rows, times):
            row['upload_time'] = f'{t[0]} {t[1]}:00'
        # 论坛名（发布在 xxx论坛）
        bbsnames = [b.strip() for b in re.findall(r'发布在[^<]*<a[^>]*>\s*([^<]+)', html)]
        for row, b in zip(rows, bbsnames):
            row['bbs_name'] = b.strip()
        return rows

    def get_user_all_posted(self, user_id, max_pages=50):
        """翻页拉全量历史发帖。"""
        out = []
        for page in range(1, max_pages + 1):
            try:
                resp = self.get_user_posted_html(user_id, page)
                rows = self.parse_posted_rows(resp.text)
            except Exception:
                break
            if not rows:
                break
            out.extend(rows)
        return out
