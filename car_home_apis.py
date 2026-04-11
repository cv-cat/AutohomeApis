import json
import random
import time

import requests
from bs4 import BeautifulSoup

from utils.car_home_utils import trans_cookies, get_headers, get_time, is_n_days_ago


class CarApis:
    def __init__(self):
        self.service = '汽车之家'

    def get_detail(self, work_id, cookies_str):
        headers = get_headers()
        url = "https://clubajax.autohome.com.cn/topic/rv"
        _, r = get_time()
        params = {
            "fun": "jsonprv",
            "callback": "jsonprv",
            "ids": work_id + ",",
            "r": r,
            "_": _
        }
        cookies = trans_cookies(cookies_str)
        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        res_text = response.text
        res = res_text[8:-1]
        res = json.loads(res)
        return res[0]

    def get_user_posted(self, user, user_url, user_info, cookies_str, time_sleep, recent_days):
        try:
            if 'club' in user_url:
                user_id = user_url.split('/club')[0].split('/')[-1]
            else:
                user_id = user_url.split('/')[-1].split('#')[0]
        except Exception:
            return
        try:
            headers = get_headers(user_url)
            cookies = trans_cookies(cookies_str)
            response = requests.get(user_url, headers=headers, cookies=cookies)
            res_text = response.text
            if '没有发布过任何帖子' in res_text:
                return [], ''
            soup = BeautifulSoup(res_text, "html.parser")
            trs = soup.find("table", attrs={'class': 'topicList'}).find_all("tr")
            tr_len = len(trs)
            res = []
            msg = ''
            if tr_len > 1:
                for tr in trs[1:]:
                    main = tr.find_all('p', attrs={'class': 'cp1'})[0]
                    title = main.text.replace('\n', '').replace(' ', '')
                    link = 'https:' + main.a['href'] if main.a['href'].startswith('//') else main.a['href']
                    upload_time = tr.find_all('td', attrs={'class': 'txtCen'})[1].text.replace('\n', '').replace('\r', '').replace(' ', '')
                    upload_time = upload_time[:10] + ' ' + upload_time[10:] + ':00'
                    if not recent_days == -1:
                        if not is_n_days_ago(upload_time, recent_days):
                            msg = 'end'
                            break
                    work_id = link.split('/')[-1].split('-')[0]
                    detail = self.get_detail(work_id, cookies_str)
                    replys = detail['allreplys']
                    views = detail['views']
                    item = user.copy()
                    item_other = {
                        '用户主页': f'https://i.autohome.com.cn/{user_id}',
                        '作品标题': title,
                        '作品链接': link,
                        '作品回复数': replys,
                        '作品浏览数': views,
                        '作品上传时间': upload_time,
                    }
                    item.update(item_other)
                    work_info = self.get_work_info(link, cookies_str)
                    item.update(work_info)
                    item.update(user_info)
                    res.append(item)
            return res, msg
        except Exception:
            return False, 'end'

    def get_user_info(self, user_id, cookies_str):
        headers = get_headers()
        cookies = trans_cookies(cookies_str)

        url = f"https://i.autohome.com.cn/{user_id}"
        response = requests.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, "html.parser")
        user_avatar = 'https:' + soup.find("div", attrs={'class': 'userHead'}).find('img')['src']
        user_info = soup.find("div", attrs={'class': 'user-lv'})
        user_follows = user_info.find_all('a', attrs={'class': 'state-mes'})[0].find('span').text
        user_fans = user_info.find_all('a', attrs={'class': 'state-mes'})[1].find('span').text
        iplocation = user_info.find_all('span')[-1].text

        url = "https://i.autohome.com.cn/ajax/home/GetUserInfo"
        params = {
            "userid": user_id,
            "r": "0.46471182146932577",
            "_": str(time.time() * 1000)
        }
        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        res_json = response.json()
        jh_topic_count = res_json['JHTopicCount']
        topic_count = res_json['TopicCount']

        url = "https://club.autohome.com.cn/frontapi/getUserInfoByIds"
        params = {"userids": user_id}
        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        res_json = response.json()
        res = res_json['result'][0]
        nickname = res['Nickname']
        register_time = res.get('AddDate', 'None')
        sex = res.get('Sex', 'None')

        return {
            '用户头像': user_avatar,
            '用户名称': nickname,
            'user_id': user_id,
            '用户关注数': user_follows,
            '用户粉丝数': user_fans,
            '用户位置': iplocation,
            '用户精华帖数': jh_topic_count,
            '用户发帖数': topic_count,
            '用户注册时间': register_time,
            '性别': sex
        }

    def get_work_info(self, work_url, cookies_str):
        headers = get_headers(work_url)
        cookies = trans_cookies(cookies_str)
        response = requests.get(work_url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, "html.parser")
        upload_iplocation = soup.find("span", attrs={'class': 'post-handle-publish'}).find('strong').text
        info = soup.find("div", attrs={'class': 'post-container'})
        images = []
        videos = []
        for image in info.find_all('img'):
            src = 'https:' + image['src'] if image['src'].startswith('//') else image['src']
            images.append(src)
        for video in info.find_all('video'):
            videos.append(video['src'])
        content = info.text
        return {
            '作品图片': images,
            '作品视频': videos,
            '作品内容': content,
            '上传位置': upload_iplocation
        }

    def get_user_all_posted(self, user, spider_user_info, cookies_str, time_sleep, recent_days):
        index = 1
        all_res = []
        user_url = user['账号链接']
        try:
            if 'club' in user_url:
                user_id = user_url.split('/club')[0].split('/')[-1]
            else:
                user_id = user_url.split('/')[-1].split('#')[0]
        except Exception:
            return
        while True:
            page_url = f"https://iservice.autohome.com.cn/clubapp/OtherTopic-{user_id}-all-{index}.html"
            res, msg = self.get_user_posted(user, page_url, spider_user_info, cookies_str, time_sleep, recent_days)
            if not res:
                break
            if msg == 'end':
                break
            all_res.extend(res)
            index += 1
        return all_res

    def spider_one(self, user, cookies_strs, time_sleep, recent_days):
        user_url = user['账号链接']
        try:
            if 'club' in user_url:
                user_id = user_url.split('/club')[0].split('/')[-1]
            else:
                user_id = user_url.split('/')[-1].split('#')[0]
        except Exception:
            return
        cookies_str = random.choice(cookies_strs)
        spider_user_info = self.get_user_info(user_id, cookies_str)
        res = []
        try:
            cookies_str = random.choice(cookies_strs)
            res = self.get_user_all_posted(user, spider_user_info, cookies_str, time_sleep, recent_days)
            for item in res:
                item['作品数量'] = len(res)
            if len(res) == 0:
                one_item = user.copy()
                one_item.update({
                    '用户主页': f'https://i.autohome.com.cn/{user_id}',
                    '作品标题': '该用户没有发布过任何帖子',
                    '作品链接': 'None',
                    '作品回复数': 'None',
                    '作品浏览数': 'None',
                    '作品上传时间': 'None',
                    '作品图片': 'None',
                    '作品视频': 'None',
                    '作品内容': 'None',
                    '上传位置': 'None',
                    '用户头像': 'None',
                    '用户名称': 'None',
                    'user_id': user_id,
                    '用户关注数': 'None',
                    '用户粉丝数': 'None',
                    '用户位置': 'None',
                    '用户精华帖数': 'None',
                    '用户发帖数': 'None',
                    '用户注册时间': 'None',
                    '性别': 'None',
                    '作品数量': 0
                })
                one_item.update(spider_user_info)
                res.append(one_item)
        except Exception:
            pass
        return res
