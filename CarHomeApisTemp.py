import json
import os
import random
import shutil
import time

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from common_utils.utils import validate_text
from utils.CarHomeUtils import trans_cookies, get_headers, get_time, is_n_days_ago
from loguru import logger

logger.add("qichezhijia.log", rotation="10 MB", retention="10 days", compression="zip")

class CarApis:
    def __init__(self):
        self.serveice = '汽车之家'

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
        except Exception as e:
            logger.info(f'用户url解析失败: {user_url}')
            return
        try:
            headers = get_headers(user_url)
            cookies = trans_cookies(cookies_str)
            response = requests.get(user_url, headers=headers, cookies=cookies)
            res_text = response.text
            if '没有发布过任何帖子' in res_text:
                logger.info('该用户没有发布过任何帖子')
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
                    upload_time = tr.find_all('td', attrs={'class': 'txtCen'})[1].text.replace('\n', '').replace('\r','').replace(' ', '')
                    upload_time = upload_time[:10] + ' ' + upload_time[10:] + ':00'
                    if not recent_days == -1:
                        if not is_n_days_ago(upload_time, recent_days):
                            # if note['interact_info']['sticky']:
                            #     continue
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
                    logger.info(f'爬取信息 {item}')
                    res.append(item)
            return res, msg
        except Exception as e:
            logger.info(f'爬取用户发帖信息失败: {e}')
            return False, 'end'

    def get_user_info(self, user_id, cookies_str):
        url = f"https://i.autohome.com.cn/{user_id}"
        headers = get_headers()
        cookies = trans_cookies(cookies_str)
        response = requests.get(url, headers=headers, cookies=cookies)
        res_text = response.text
        soup = BeautifulSoup(res_text, "html.parser")
        user_avatar = 'https:' + soup.find("div", attrs={'class': 'userHead'}).find('img')['src']
        user_info = soup.find("div", attrs={'class': 'user-lv'})
        user_follows = user_info.find_all('a', attrs={'class': 'state-mes'})[0].find('span').text
        user_fans = user_info.find_all('a', attrs={'class': 'state-mes'})[1].find('span').text
        iplocation = user_info.find_all('span')[-1].text
        url = "https://i.autohome.com.cn/ajax/home/GetUserInfo"
        params = {
            "userid": "286704319",
            "r": "0.46471182146932577",
            "_": str(time.time() * 1000)
        }
        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        res_json = response.json()
        JHTopicCount = res_json['JHTopicCount']
        TopicCount = res_json['TopicCount']

        url = "https://club.autohome.com.cn/frontapi/getUserInfoByIds"
        params = {
            "userids": user_id
        }
        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        res_json = response.json()
        res = res_json['result'][0]
        nickname = res['Nickname']
        if 'AddDate' in res:
            register_time = res['AddDate']
        else:
            register_time = 'None'
        if 'Sex' in res:
            sex = res['Sex']
        else:
            sex = 'None'
        res = {
            '用户头像': user_avatar,
            '用户名称': nickname,
            'user_id': user_id,
            '用户关注数': user_follows,
            '用户粉丝数': user_fans,
            '用户位置': iplocation,
            '用户精华帖数': JHTopicCount,
            '用户发帖数': TopicCount,
            '用户注册时间': register_time,
            '性别': sex
        }
        return res

    def get_work_info(self, work_url, cookies_str):
        # work_id = work_url.split('/')[-1].split('-')[0]
        # headers = get_headers(work_url)
        # cookies = trans_cookies(cookies_str)
        # url = "https://club.autohome.com.cn/frontapi/getclicksandreplys"
        # params = {
        #     "topicids": work_id
        # }
        # response = requests.get(url, headers=headers, cookies=cookies, params=params)
        # res_json = response.json()
        headers = get_headers(work_url)
        cookies = trans_cookies(cookies_str)
        response = requests.get(work_url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, "html.parser")
        upload_iplocation = soup.find("span", attrs={'class': 'post-handle-publish'}).find('strong').text
        info = soup.find("div", attrs={'class': 'post-container'})
        images = []
        videos = []
        images_ele = info.find_all('img')
        for image in images_ele:
            src = 'https:' + image['src'] if image['src'].startswith('//') else image['src']
            images.append(src)
        videos_ele = info.find_all('video')
        for video in videos_ele:
            videos.append(video['src'])
        content = info.text
        res = {
            '作品图片': images,
            '作品视频': videos,
            '作品内容': content,
            '上传位置': upload_iplocation
        }
        return res


    def get_user_all_posted(self, user, spider_user_info, cookies_str, time_sleep, recent_days):
        index = 1
        all_res = []
        user_url = user['账号链接']
        try:
            if 'club' in user_url:
                user_id = user_url.split('/club')[0].split('/')[-1]
            else:
                user_id = user_url.split('/')[-1].split('#')[0]
        except Exception as e:
            logger.info(f'用户url解析失败: {user_url}')
            return
        user_info = spider_user_info
        while True:
            user_url = f"https://iservice.autohome.com.cn/clubapp/OtherTopic-{user_id}-all-{index}.html"
            res, msg = self.get_user_posted(user, user_url, user_info, cookies_str, time_sleep, recent_days)
            if not res:
                break
            if msg == 'end':
                break
            all_res.extend(res)
            index += 1
        return all_res

    def save_to_excel(self, save_path, res):
        df = pd.DataFrame(res)
        df.to_excel(save_path, index=True)

    def all_all_users(self, path):
        df = pd.read_excel(path)
        datas = df.to_numpy().tolist()
        users = []
        for data in datas:
            url = str(data[5])
            if 'i.autohome' in url:
                users.append({
                    '账号编号': str(data[0]),
                    '序号': str(data[1]),
                    '平台': str(data[2]),
                    '赛道（一类）': data[3],
                    '赛道（二类）': data[4],
                    '账号链接': url
                })
        return users

    def spider_one(self, user, cookies_strs, time_sleep, recent_days):
        user_url = user['账号链接']
        res = []
        try:
            if 'club' in user_url:
                user_id = user_url.split('/club')[0].split('/')[-1]
            else:
                user_id = user_url.split('/')[-1].split('#')[0]
        except Exception as e:
            logger.info(f'用户url解析失败: {user_url}')
            return
        cookies_str = random.choice(cookies_strs)
        spider_user_info = self.get_user_info(user_id, cookies_str)
        try:
            cookies_str = random.choice(cookies_strs)
            res = self.get_user_all_posted(user, spider_user_info, cookies_str, time_sleep, recent_days)
            for item in res:
                item['作品数量'] = len(res)
            if len(res) == 0:
                one_item = user.copy()
                one_item_other = {
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
                }
                one_item.update(one_item_other)
                one_item.update(spider_user_info)
                res.append(one_item)
        except Exception as e:
            logger.error(f'爬取用户 {user_url} 的所有发帖信息失败: {e}')
        return res

    def main(self, spider_files, cookies_strs, time_sleep, recent_days):
        for spider_index, file_name in enumerate(spider_files):
            logger.info(f'开始爬取第 {spider_index} 项目 {file_name} 的所有用户的所有发帖信息')
            # simple_file_name = validate_text(file_name)
            simple_file_name = '.'.join(file_name.split('.')[:-1])
            work_dir = os.path.abspath(os.path.dirname(__file__))
            base_path = os.path.abspath(os.path.join(work_dir, '..'))
            save_base_path = os.path.abspath(os.path.join(base_path, 'data', 'qichezhijia', simple_file_name))
            if not os.path.exists(save_base_path):
                os.makedirs(save_base_path)
            spider_file_path = os.path.abspath(os.path.join(base_path, 'input', file_name))
            users = self.all_all_users(spider_file_path)
            for index, user in enumerate(users):
                try:
                    user_url = user['账号链接']
                    try:
                        if 'club' in user_url:
                            user_id = user_url.split('/club')[0].split('/')[-1]
                        else:
                            user_id = user_url.split('/')[-1].split('#')[0]
                    except Exception as e:
                        logger.error(f'用户url解析失败: {user_url}')
                        continue
                    save_path = f'{save_base_path}/{user_id}.xlsx'
                    if os.path.exists(save_path):
                        logger.info(f'用户 {user_url} 的所有发帖信息已经爬取过')
                        continue
                    logger.info('-----------------------------------')
                    logger.info(
                        f'开始爬取第 {spider_index} 项目 {simple_file_name} 的第{index + 1}个用户 {user_url} 的所有发帖信息')
                    res = self.spider_one(user, cookies_strs, time_sleep, recent_days)
                    self.save_to_excel(save_path, res)
                    logger.info(f'第 {spider_index} 项目 {simple_file_name} 剩余用户数: {len(users) - index - 1}')
                except Exception as e:
                    logger.error(f'爬取用户 {user} 的所有发帖信息失败: {e}')
            self.combine(save_base_path)

    def combine(self, save_base_path):
        if os.path.exists(f'{save_base_path}/all.xlsx'):
            os.remove(f'{save_base_path}/all.xlsx')
        all_excel = os.listdir(save_base_path)
        all_res = []
        for excel in all_excel:
            if excel.endswith('.xlsx'):
                df = pd.read_excel(f'{save_base_path}/{excel}', dtype=str).iloc[:, 1:]
                res = df.to_numpy().tolist()
                all_res.extend(res)
        columns = ['账号编号', '序号', '平台', '赛道（一类）', '赛道（二类）', '账号链接', '用户主页', '作品标题', '作品链接', '作品回复数', '作品浏览数', '作品上传时间', '作品图片', '作品视频', '作品内容', '上传位置', '用户头像', '用户名称', 'user_id', '用户关注数', '用户粉丝数', '用户位置', '用户精华帖数', '用户发帖数', '用户注册时间', '性别', '作品数量']
        df = pd.DataFrame(all_res, columns=columns)
        df.to_excel(f'{save_base_path}/all.xlsx', index=True)

def job():
    car = CarApis()
    work_dir = os.path.abspath(os.path.dirname(__file__))
    env_path = os.path.join(work_dir, '..', 'env.yaml')
    env_path = os.path.abspath(env_path)
    with open(env_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    car_config = config['platform']['qichezhijia']
    cookies_strs = car_config['cookies_strs']
    time_sleep = car_config['timesleep']
    recent_days = car_config['recent_days']
    spider_files = car_config['spider_files']
    car.main(spider_files, cookies_strs, time_sleep, recent_days)


def schedule_job():
    work_dir = os.path.abspath(os.path.dirname(__file__))
    base_path = os.path.abspath(os.path.join(work_dir, '..'))
    save_base_path = os.path.abspath(os.path.join(base_path, 'data', 'qichezhijia'))
    logger.info(f'清理 {save_base_path} 下的所有文件和文件夹')
    # 清理save_base_path下的所有文件和文件夹
    for filename in os.listdir(save_base_path):
        file_path = os.path.join(save_base_path, filename)
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
    job()
    job()


if __name__ == '__main__':
    # job()
    schedule_job()

    # schedule.every().monday.at("00:05").do(schedule_job)
    # schedule.every().tuesday.at("00:05").do(schedule_job)
    # schedule.every().wednesday.at("00:05").do(schedule_job)
    # schedule.every().thursday.at("00:05").do(schedule_job)
    # schedule.every().friday.at("00:05").do(schedule_job)
    #
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)