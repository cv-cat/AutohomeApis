<div align="center">
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
    </a>
    <a href="https://www.autohome.com.cn/">
        <img src="https://img.shields.io/badge/汽车之家-autohome-orange" alt="autohome">
    </a>
</div>

# 🚗 汽车之家 Platform

**✨ 专业的汽车之家用户数据采集解决方案，支持用户信息、帖子内容的全量抓取**

当你需要让 AI Agent 感知汽车之家内容生态——自动采集用户发帖、分析内容数据、驱动运营策略——第一道墙往往不是模型能力，而是**平台数据获取能力的缺失**。

本项目做的事很简单：把这道墙拆掉。

**⚠️ 严禁用于爬取用户隐私、违规商业用途！本项目仅供学习与技术研究使用，后果自负。**

## 🌟 功能特性

- ✅ **用户信息采集**
  - 用户头像、昵称、关注数、粉丝数、位置
  - 用户精华帖数、总发帖数、注册时间、性别
- ✅ **帖子全量采集**
  - 支持按天数范围过滤（`recent_days`），`-1` 表示不限制
  - 自动翻页，获取用户全部历史发帖
  - 采集帖子标题、正文、图片、视频、回复数、浏览数、上传位置
- 🔐 **Cookie 鉴权**
  - 使用浏览器登录态 Cookie 透传，适配汽车之家接口鉴权
  - 支持多 Cookie 轮换，降低风控风险
- 🚀 **简洁接口**
  - 纯 Python 模块，直接调用，无需额外服务

## 🛠️ 快速开始

### ⛳ 运行环境

- Python 3.10+

### 🎯 安装依赖

```bash
pip install -r requirements.txt
```

### 🎨 Cookie 配置

在浏览器中打开 [www.autohome.com.cn](https://www.autohome.com.cn)，**登录账号**后按 `F12` 打开开发者工具，点击「网络」→ 找任意一个 API 请求 → 复制请求头中的 `Cookie` 字段值。

将获取到的 Cookie 字符串作为 `cookies_str` 参数传入接口，格式如下：

```
autohome_ci=xxx; sessionID=xxx; ...
```

> ⚠️ 注意：必须登录后获取的 Cookie 才有效，Cookie 失效后需重新获取。

## 📡 接口说明

所有接口均通过实例化 `CarApis` 类调用。

```python
from car_home_apis import CarApis

car = CarApis()
```

---

### `get_user_info(user_id, cookies_str)`

获取指定用户的**个人信息**。

**参数**

| 参数            | 类型  | 说明                                      |
|---------------|-----|-------------------------------------------|
| `user_id`     | str | 用户 ID（用户主页 URL 中的数字部分）         |
| `cookies_str` | str | 汽车之家登录 Cookie 字符串                  |

**返回示例**

```python
{
    "用户头像": "https://x.autoimg.cn/...",
    "用户名称": "昵称",
    "user_id": "12345678",
    "用户关注数": "100",
    "用户粉丝数": "200",
    "用户位置": "上海",
    "用户精华帖数": 5,
    "用户发帖数": 80,
    "用户注册时间": "2018-06-01",
    "性别": 1
}
```

---

### `get_work_info(work_url, cookies_str)`

获取指定帖子的**详细内容**（正文、图片、视频、发布位置）。

**参数**

| 参数            | 类型  | 说明              |
|---------------|-----|-------------------|
| `work_url`    | str | 帖子完整 URL       |
| `cookies_str` | str | 登录 Cookie 字符串 |

**返回示例**

```python
{
    "作品图片": ["https://...", "https://..."],
    "作品视频": [],
    "作品内容": "帖子正文内容...",
    "上传位置": "上海"
}
```

---

### `get_user_all_posted(user, spider_user_info, cookies_str, time_sleep, recent_days)`

获取指定用户的**全部历史发帖**，自动翻页。

**参数**

| 参数                | 类型  | 说明                                         |
|-------------------|-----|----------------------------------------------|
| `user`            | dict | 包含 `账号链接` 字段的用户基础信息字典           |
| `spider_user_info`| dict | `get_user_info` 返回的用户信息                |
| `cookies_str`     | str | 登录 Cookie 字符串                            |
| `time_sleep`      | int | 翻页间隔（秒）                                |
| `recent_days`     | int | 采集最近 N 天的帖子，`-1` 表示全量采集         |

---

### `spider_one(user, cookies_strs, time_sleep, recent_days)`

**一键采集**单个用户的完整数据（用户信息 + 全部发帖）。

**参数**

| 参数             | 类型       | 说明                                     |
|----------------|----------|------------------------------------------|
| `user`         | dict     | 包含 `账号链接` 字段的用户基础信息字典        |
| `cookies_strs` | list[str]| Cookie 字符串列表，每次请求随机选取一个      |
| `time_sleep`   | int      | 翻页间隔（秒）                             |
| `recent_days`  | int      | 采集最近 N 天，`-1` 表示全量                |

**调用示例**

```python
from car_home_apis import CarApis

car = CarApis()

user = {"账号链接": "https://i.autohome.com.cn/12345678"}
cookies_strs = ["autohome_ci=xxx; sessionID=xxx; ..."]

result = car.spider_one(user, cookies_strs, time_sleep=1, recent_days=7)
# result: [{"账号链接": ..., "作品标题": ..., "用户粉丝数": ..., ...}, ...]
```

## 🐳 Docker 部署

```bash
docker build -t qichezhijia-platform .
docker run -d qichezhijia-platform
```

## 🍥 日志

| 日期       | 说明                                    |
|----------|-----------------------------------------|
| 26/04/11 | 项目初始化，完成用户信息与全量发帖采集接口封装 |

## 🤝 欢迎贡献 PR

本项目欢迎任何形式的贡献！如果你有新功能想法、Bug 修复或文档改进，欢迎提交 PR。

- Fork 本仓库并在新分支上开发
- 保持代码风格与现有代码一致
- PR 描述中请简要说明改动内容和目的
- 也欢迎通过 Issue 提出建议或报告问题

## 🧸 额外说明
1. 感谢 star⭐ 和 follow📰！不时更新
2. 作者的联系方式在主页里，有问题可以随时联系我
3. 可以关注下作者的其他项目，欢迎 PR 和 issue
4. 感谢赞助！如果此项目对您有帮助，请作者喝一杯奶茶~~ （开心一整天😊😊）
5. thank you~~~
