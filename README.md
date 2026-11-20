<div align="center">
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
    </a>
    <a href="https://www.autohome.com.cn/">
        <img src="https://img.shields.io/badge/汽车之家-autohome-orange" alt="autohome">
    </a>
</div>

# 🚗 AutohomeApis

**✨ 汽车之家全接口 SDK：游客读 + 登录写一站式，搜索 / 论坛 / 详情 / 视频 / 用户 / 发布**

按 [DouyinSpider](https://github.com/cv-cat/DouyinSpider) 的架构重构：`autohome/` 包内按业务域分模块，
`AutohomeClient` 聚合入口，`AuthManager` 统一游客/登录态分级。

**⚠️ 仅供学习与技术研究使用，严禁爬取用户隐私或用于违规商业用途，后果自负。**

## 🌟 能力矩阵

| 模块 | 接口 | 游客 | 登录 |
|---|---|:-:|:-:|
| search | 全站综合搜索 v1（帖子/新闻卡片流） | ✅ | ✅ |
| search | 论坛名搜索 topicentry（→ bbsId） | ✅ | ✅ |
| forum | 论坛帖子流 getClubTopicList（翻页/排序） | ✅ | ✅ |
| forum | 置顶帖 / 论坛成员数 | ✅ | ✅ |
| detail | 帖子详情（SSR 楼层 / 翻页 / 标题） | ✅ | ✅ |
| detail | 浏览回复统计（clubajax rv） | ✅ | ✅ |
| detail | 视频 mp4 直链（vid → p-vp gpi） | ✅ | ✅ |
| user | 用户信息 / 历史发帖全量 | ✅ | ✅ |
| publish | 发帖 topicAdd（图+文） | ❌ | ✅ |
| publish | 图片上传 uploadMultiClubImg | ❌ | ✅ |
| publish | 点赞 zan/add · 评论 comment/add · 回帖 reply/add | ❌ | ✅ |
| auth | 登录通道（账密 md5 / 短信 / 微信扫码结构） | — | 结构已解 |

写接口无独立 token，完全依赖 `club.autohome.com.cn` 域登录 Cookie；
游客直接调用服务端返回 `-101 未登录`，SDK 在客户端做 `require_login` 前置拦截。

## 🛠️ 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### CLI

```bash
python main.py search 迈腾                # 综合搜索 + 相关论坛
python main.py forum  496                 # 论坛帖子流（496=迈腾论坛）
python main.py thread 116675148           # 帖子详情 + 楼层 + 统计
python main.py user   8597646             # 用户信息 + 历史发帖
python main.py publish "标题" "正文" "迈腾" a.jpg   # 发帖（需登录）
python e2e.py                            # 游客态 11 步端到端验证
```

### SDK

```python
from autohome import AutohomeClient

ah = AutohomeClient()                       # 游客模式
cards = ah.search.search_topics('迈腾', pages=2)
forums = ah.search.search_forum('迈腾')     # [{bbs_id, bbs_name, ...}]
topics = ah.forum.iter_topic_list(496, pages=1)
thread = ah.detail.get_thread(cards[0]['topic_id'])
mp4s = ah.detail.get_thread_video_url(112650837)
posted = ah.user.get_user_all_posted('8597646')
```

### 登录态（发布/点赞/评论）

1. 浏览器登录 [club.autohome.com.cn](https://club.autohome.com.cn)，F12 → Network → 复制任意请求的 `Cookie` 头
2. 写入 `.env`（复制 `.env.example`）：

```bash
AUTOHOME_COOKIES=clubwzuser=xxx; sessionid=xxx; remember=xxx
```

3. SDK 自动识别登录态，写接口放行：

```python
ah = AutohomeClient(cookies='clubwzuser=xxx; ...')
print(ah.auth.check_login())                # {'logged': True, 'user_id': ...}

ah.publish.publish_with_images('提车作业', '正文...', '迈腾', ['1.jpg'])
ah.publish.zan_add(116675148)
ah.publish.comment_add(116675148, '写得好')
```

### 登录通道

| 通道 | 状态 | 说明 |
|---|---|---|
| **微信扫码** | ✅ 纯 HTTP 闭环 | `WechatQRLogin`：取码 → 轮询 → SSO 落 Cookie，无需浏览器 |
| 账密 / 短信 | 结构已解 | 需先过数美滑块拿 rid（合成事件会被风控拒，需人工） |
| 浏览器导 Cookie | ✅ | 任何方式登录后 F12 复制，`.env` 或构造参数直接给 |

扫码登录（推荐，无需浏览器）::

    from autohome.auth import WechatQRLogin
    qr = WechatQRLogin()
    header = qr.login(timeout=300)   # 终端展示二维码，扫码确认后返回 Cookie 头
    ah = AutohomeClient(cookies=header)

账密（`/Login/ValidIndexsm`，pwd=hex_md5）/ 短信（`SendRegLoginMobileCodesm`→`RegOrLoginByMobileCode`）
结构已在 `autohome/auth.py` 实现，但登录前置的数美滑动验证码（`smdata.rid`）对合成事件返回 REJECT，
需浏览器人工过码——**推荐扫码或直接导入 Cookie**，脚本侧零过码。

## 📁 结构

```
autohome/
├── __init__.py    # AutohomeClient 聚合入口
├── base.py        # 请求基座：UA/Referer/Cookie 注入 + JSON/JSONP 解析
├── auth.py        # AuthManager：Cookie 导入、探活、游客/登录分级、登录通道
├── search.py      # v1/search 综合搜索 + topicentry 论坛名搜索
├── forum.py       # getClubTopicList 论坛帖子流 + 置顶 + 成员数
├── detail.py      # 帖子 SSR 楼层解析 + 统计 + 视频 mp4 直链
├── user.py        # 用户信息 + iservice 历史发帖全量
└── publish.py     # topicAdd / uploadMultiClubImg / zan / comment / reply
main.py            # CLI 入口
e2e.py             # 游客态 11 步端到端验证
```

## 📝 接口备注

- 帖子楼层为服务端渲染，在 HTML `js-reply-floor-container` 容器内（带
  `data-floor/reply-id/member-id`），SDK 用正则解析，无需 bs4
- 视频 id 为 hash 型 vid（`"videoId":"9CD3..."`），非数字 topicid；
  p-vp `api/gpi` 返回 qualities mp4 直链数组
- `i.autohome.com.cn` 会员页有 JS 挑战（EdgeOne），发帖统计改走 iservice 表计数
- 用户历史发帖在 `iservice.autohome.com.cn/clubapp/OtherTopic-<uid>-all-<page>.html`，
  GB 编码表格，SDK 已按 UTF-8 容错处理
