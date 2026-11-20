# coding=utf-8
"""游客态全链路端到端验证（无 Cookie）。

跑通：搜索 → 论坛列表 → 帖子详情(楼层/统计) → 视频直链 → 用户信息 →
历史发帖。每步打 PASS/FAIL，输出 JSON 汇总。

用法::

    python e2e.py
"""

import json
import sys

from autohome import AutohomeClient

results = []


def check(name, ok, detail=''):
    results.append({'step': name, 'ok': bool(ok), 'detail': str(detail)[:120]})
    print(f'[{"PASS" if ok else "FAIL"}] {name}' + (f' — {str(detail)[:100]}' if not ok else ''))


def main():
    ah = AutohomeClient()

    # 1. 综合搜索
    try:
        cards = ah.search.search_topics('迈腾', pages=1)
        check('search.v1', len(cards) >= 5, f'{len(cards)} cards')
        topic_id = cards[0]['topic_id']
    except Exception as e:
        check('search.v1', False, e)
        topic_id = '116675148'

    # 2. 论坛名搜索
    try:
        forums = ah.search.search_forum('迈腾')
        check('search.topicentry', forums and str(forums[0]['bbs_id']) == '496', forums[:1])
        bbs_id = forums[0]['bbs_id']
    except Exception as e:
        check('search.topicentry', False, e)
        bbs_id = '496'

    # 3. 论坛帖子流
    try:
        topics = ah.forum.iter_topic_list(bbs_id, pages=1)
        check('forum.getClubTopicList', len(topics) >= 20, f'{len(topics)} topics')
    except Exception as e:
        check('forum.getClubTopicList', False, e)

    # 4. 置顶帖 + 论坛人数
    try:
        tops = ah.forum.get_top_topics(bbs_id)
        cnt = ah.forum.get_bbs_user_count(bbs_id)
        check('forum.top+count', isinstance(tops, dict) and isinstance(cnt, dict), '')
    except Exception as e:
        check('forum.top+count', False, e)

    # 5. 帖子详情（楼层+翻页）
    try:
        data = ah.detail.get_thread(topic_id, pages=1)
        ok = data['title'] and len(data['floors']) >= 1
        check('detail.thread+floors', ok, f"{data['title'][:20]} floors={data['floor_count']}")
    except Exception as e:
        check('detail.thread+floors', False, e)

    # 6. 帖子统计
    try:
        stats = ah.detail.get_topic_stats(topic_id)
        check('detail.topicStats', 'views' in stats, stats)
    except Exception as e:
        check('detail.topicStats', False, e)

    # 7. 视频帖直链
    try:
        urls = ah.detail.get_thread_video_url(112650837)
        check('detail.videoUrl', len(urls) >= 3 and '.mp4' in urls[0], f'{len(urls)} urls')
    except Exception as e:
        check('detail.videoUrl', False, e)

    # 8. 用户信息
    try:
        info = ah.user.get_user_info('8597646')
        check('user.getUserInfoByIds', info.get('Nickname') == '南回归线以南', info.get('Nickname'))
    except Exception as e:
        check('user.getUserInfoByIds', False, e)

    # 9. 用户历史发帖
    try:
        posted = ah.user.get_user_all_posted('8597646', max_pages=2)
        first = posted[0] if posted else {}
        check('user.posted', len(posted) >= 5 and first.get('upload_time'), first.get('title', '')[:30])
    except Exception as e:
        check('user.posted', False, e)

    # 10. auth 游客态
    try:
        st = ah.auth.check_login()
        check('auth.guest', st == {'logged': False, 'user_id': None}, st)
    except Exception as e:
        check('auth.guest', False, e)

    # 11. 写接口游客边界（应拒绝）
    try:
        ah.publish.publish_topic('t', 'x', '496', 'c')
        check('publish.guestBlocked', False, '游客发帖竟然成功了')
    except PermissionError:
        check('publish.guestBlocked', True, 'require_login 前置拦截')
    except Exception as e:
        check('publish.guestBlocked', False, e)

    # 12. 登录态（autohome_cookies.txt 存在且含登录 Cookie 时跑点赞冒烟，否则跳过）
    import os
    import http.cookiejar
    if os.path.exists('autohome_cookies.txt'):
        jar = http.cookiejar.MozillaCookieJar('autohome_cookies.txt')
        jar.load(ignore_discard=True, ignore_expires=True)
        names = {c.name for c in jar}
        if 'clubwzuser' in names or 'sessionid' in names:
            try:
                header = '; '.join(f'{c.name}={c.value}' for c in jar)
                ah2 = AutohomeClient(cookies=header)
                st = ah2.auth.check_login()
                zan = ah2.publish.zan_add(116675148)
                check('login.zan', st.get('logged'), str(zan)[:80])
            except Exception as e:
                check('login.zan', False, e)
        else:
            print('[SKIP] login.zan — cookie 文件无登录态（扫码未完成）')

    ok = sum(1 for r in results if r['ok'])
    print(f'\n{ok}/{len(results)} PASS')
    with open('e2e_result.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    sys.exit(0 if ok == len(results) else 1)


if __name__ == '__main__':
    main()
