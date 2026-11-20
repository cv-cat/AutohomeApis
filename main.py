# coding=utf-8
"""汽车之家全链路采集 / 发布入口。

用法::

    python main.py search  迈腾                 # 游客：综合搜索
    python main.py forum   3075                 # 游客：论坛帖子流（bbs_id=3075 速腾）
    python main.py thread  116675148            # 游客：帖子详情+楼层
    python main.py user    8597646              # 游客：用户信息+历史发帖
    python main.py publish "标题" "正文" "迈腾" img1.jpg   # 登录：发帖（需 AUTOHOME_COOKIES）
"""

import json
import os
import sys
import time

from dotenv import load_dotenv
from loguru import logger

from autohome import AutohomeClient


def load_auth():
    """读 .env 的 AUTOHOME_COOKIES；没有则游客模式。"""
    load_dotenv()
    cookies = os.getenv('AUTOHOME_COOKIES')
    ah = AutohomeClient(cookies=cookies)
    state = ah.auth.check_login()
    if state['logged']:
        logger.info(f'登录态有效 user_id={state["user_id"]}')
    else:
        logger.info('游客模式（读接口全可用；写接口需配置 AUTOHOME_COOKIES）')
    return ah


def cmd_search(ah, kw):
    cards = ah.search.search_topics(kw, pages=1)
    logger.info(f'搜索"{kw}" 论坛帖卡片 {len(cards)} 条')
    for c in cards[:10]:
        logger.info(f'  [{c["biz_type"]}] {c["title"]} | {c["author"]} '
                    f'| view={c["view"]} reply={c["reply"]} | {c["jump_url"]}')
    forums = ah.search.parse_forum_boxes(ah.search.search(kw))
    for f in forums[:5]:
        logger.info(f'  相关论坛: {f["bbs_name"]} (bbs_id={f["bbs_id"]})')
    return cards


def cmd_forum(ah, bbs_id):
    topics = ah.forum.iter_topic_list(bbs_id, pages=1)
    logger.info(f'论坛 {bbs_id} 帖子 {len(topics)} 条')
    for t in topics[:10]:
        logger.info(f'  [{t["topic_id"]}] {t["title"]} reply={t["reply_count"]}')
    return topics


def cmd_thread(ah, topic_id):
    data = ah.detail.get_thread(topic_id, pages=1)
    logger.info(f'《{data["title"]}》 页数={data["page_count"]} 楼层={data["floor_count"]}')
    for f in data['floors'][:5]:
        logger.info(f'  #{f["floor"]} {f["time"]} {f["text"][:40]}')
    stats = ah.detail.get_topic_stats(topic_id)
    logger.info(f'统计: {stats}')
    return data


def cmd_user(ah, user_id):
    info = ah.user.get_user_info(user_id)
    logger.info(f'用户: {info.get("Nickname")} 注册={info.get("AddDate")} 性别={info.get("Sex")}')
    counts = ah.user.get_user_counts(user_id)
    logger.info(f'发帖总数(iservice 全量计数): {counts.get("topic_count")}')
    posted = ah.user.get_user_all_posted(user_id, max_pages=2)
    logger.info(f'历史发帖（前2页）: {len(posted)} 条')
    for p in posted[:5]:
        logger.info(f'  {p.get("upload_time")} {p["title"]}')
    return {'info': info, 'counts': counts, 'posted': posted}


def cmd_publish(ah, title, text, kw, *imgs):
    if not ah.is_logged:
        logger.error('发帖需要登录 Cookie：.env 里配 AUTOHOME_COOKIES=<浏览器复制的Cookie>')
        return None
    res = ah.publish.publish_with_images(title, text, kw, list(imgs) or None)
    logger.info(f'发布结果: {json.dumps(res, ensure_ascii=False)[:300]}')
    return res


def cmd_zan(ah, topic_id):
    if not ah.is_logged:
        logger.error('点赞需要登录 Cookie')
        return None
    res = ah.publish.zan_add(topic_id)
    logger.info(f'点赞结果: {res}')
    return res


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    ah = load_auth()
    if cmd == 'search':
        cmd_search(ah, rest[0])
    elif cmd == 'forum':
        cmd_forum(ah, rest[0])
    elif cmd == 'thread':
        cmd_thread(ah, rest[0])
    elif cmd == 'user':
        cmd_user(ah, rest[0])
    elif cmd == 'publish':
        cmd_publish(ah, rest[0], rest[1], rest[2], *rest[3:])
    elif cmd == 'zan':
        cmd_zan(ah, rest[0])
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
