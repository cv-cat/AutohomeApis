import json
import os
import random
import shutil
import time

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

from common_utils.utils import validate_text, check_time_in_7_days
from utils.CarHomeUtils import trans_cookies, get_headers, get_time, is_n_days_ago, timestamp_to_str
from loguru import logger

logger.add("qichezhijia.log", rotation="10 MB")
CURRENT_SPIDER_TIME = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
from common_utils.utils import check_time_in_7_days_and_recent, check_time_in_yesterday

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

    def get_user_posted(self, user, user_url, yesterday_uploads, cookies_str, time_sleep, recent_days):
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

                    if check_time_in_yesterday(CURRENT_SPIDER_TIME, upload_time):
                        yesterday_uploads['count'] += 1
                    if not recent_days == -1:
                        flag = check_time_in_7_days(CURRENT_SPIDER_TIME, upload_time)
                        if not flag:
                            # if note['interact_info']['sticky']:
                            #     continue
                            msg = 'end'
                            break

                    work_id = link.split('/')[-1].split('-')[0]
                    detail = self.get_detail(work_id, cookies_str)
                    replys = detail['allreplys']
                    views = detail['views']
                    item = user.copy()
                    work_info = self.get_work_info(link, cookies_str)
                    item_other = {
                        '账号昵称': '未知',
                        '发布账号KEY': '未知',
                        '标题': title,
                        '正文内容': work_info['作品内容'],
                        '话题标签': '未知',
                        '展现量': '未知',
                        '阅读量': views,
                        '点赞量': '未知',
                        '评论量': replys,
                        '收藏量': '未知',
                        '转发量': '未知',
                        '回链': link,
                        '内容类型': '未知',
                        '发布时间': upload_time,
                        '采集时间': timestamp_to_str(int(time.time() * 1000)),
                    }
                    item.update(item_other)
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
            '账号昵称': nickname,
            '头像地址URL': user_avatar,
            '账号KEY': user_id,
            '粉丝数量': user_fans,
            '总发布量': TopicCount,
            '阅读/曝光数量': '未知',
            '点赞数量': '未知',
            '评论数量': '未知',
            '收藏数量': '未知',
            '昨天发布数量': '未知',
            '采集时间': timestamp_to_str(int(time.time() * 1000)),
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


    def get_user_all_posted(self, user, yesterday_uploads, cookies_str, time_sleep, recent_days):
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
        while True:
            user_url = f"https://iservice.autohome.com.cn/clubapp/OtherTopic-{user_id}-all-{index}.html"
            res, msg = self.get_user_posted(user, user_url, yesterday_uploads, cookies_str, time_sleep, recent_days)
            if not res:
                break
            if msg == 'end':
                break
            all_res.extend(res)
            index += 1
        return all_res

    def save_to_excel(self, user_save_path, work_save_path, res):
        user_res = res['user_res']
        note_list = res['note_list']
        df1 = pd.DataFrame([user_res])
        df2 = pd.DataFrame(note_list)
        df1.to_excel(user_save_path, index=False)
        df2.to_excel(work_save_path, index=False)

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
        user_res = user.copy()
        spider_user_info = self.get_user_info(user_id, cookies_str)
        yesterday_uploads = {'count': 0}
        cookies_str = random.choice(cookies_strs)
        res = self.get_user_all_posted(user, yesterday_uploads, cookies_str, time_sleep, recent_days)
        spider_user_info['昨天发布数量'] = yesterday_uploads['count']
        user_res.update(spider_user_info)
        return {
            'user_res': user_res,
            'note_list': res
        }

    def main(self, spider_files, cookies_strs, time_sleep, recent_days, print_error=False):
        error_users = []
        for spider_index, file_name in enumerate(spider_files):
            logger.info(f'开始爬取第 {spider_index + 1} 项目 {file_name} 的所有用户的所有发帖信息')
            # simple_file_name = validate_text(file_name)
            simple_file_name = '.'.join(file_name.split('.')[:-1])
            work_dir = os.path.abspath(os.path.dirname(__file__))
            base_path = os.path.abspath(os.path.join(work_dir, '..'))
            save_base_path = os.path.abspath(os.path.join(base_path, 'data', 'qichezhijia', simple_file_name))
            user_save_base_path = os.path.abspath(os.path.join(save_base_path, 'user'))
            work_save_base_path = os.path.abspath(os.path.join(save_base_path, 'work'))
            if not os.path.exists(user_save_base_path):
                os.makedirs(user_save_base_path, exist_ok=True)
            if not os.path.exists(work_save_base_path):
                os.makedirs(work_save_base_path, exist_ok=True)
            logger.info(f'已经创建 {user_save_base_path} 和 {work_save_base_path} 文件夹')
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
                    user_save_path = f'{user_save_base_path}/{user_id}.xlsx'
                    work_save_path = f'{work_save_base_path}/{user_id}.xlsx'
                    if os.path.exists(user_save_path) and os.path.exists(work_save_path):
                        logger.info(f'用户 {user_url} 的所有发帖信息已经爬取过')
                        continue
                    logger.info('-----------------------------------')
                    logger.info(f'开始爬取第 {spider_index + 1} 项目 {simple_file_name} 的第{index + 1}个用户 {user_url} 的所有发帖信息')
                    res = self.spider_one(user, cookies_strs, time_sleep, recent_days)
                    self.save_to_excel(user_save_path, work_save_path, res)
                    logger.info(f'第 {spider_index + 1} 项目 {simple_file_name} 剩余用户数: {len(users) - index - 1}')
                except Exception as e:
                    logger.error(f'爬取用户 {user} 的所有发帖信息失败: {e}')
                    error_users.append({
                        'file_name': simple_file_name,
                        'user': user
                    })

            self.combine(user_save_base_path, simple_file_name, is_work=False)
            self.combine(work_save_base_path, simple_file_name, is_work=True)
        if print_error:
            logger.info(f'{CURRENT_SPIDER_TIME} 总结: 爬取失败用户数 {len(error_users)}')
            for error_user in error_users:
                logger.error(f'总结: 爬取用户 {error_user} 失败')
            logger.info(f'开始检查所有cookies是否有效')

    def check_cookies_alive(self, cookies_strs):
        user_url = f"https://iservice.autohome.com.cn/clubapp/OtherTopic-286695895-all-1.html"

        for cookie_index, cookies_str in enumerate(cookies_strs):
            try:
                res, msg = self.get_user_posted({}, user_url, {'count': 0}, cookies_str, 0, -1)
                if not res:
                    logger.error(f'第 {cookie_index + 1} 个cookies失效，请手动替换')
                else:
                    logger.info(f'第 {cookie_index + 1} 个cookies有效')
            except Exception as e:
                logger.error(f'第 {cookie_index + 1} 个cookies失效，请手动替换')


    def combine(self, save_base_path, simple_file_name, is_work):
        if is_work:
            all_file_path = f'{save_base_path}/{simple_file_name}_all_work.xlsx'
            if os.path.exists(all_file_path):
                os.remove(all_file_path)
            columns = ['账号编号', '序号', '平台', '赛道（一类）', '赛道（二类）', '账号链接', '账号昵称', '发布账号KEY',
                       '标题',
                       '正文内容', '话题标签', '展现量', '阅读量', '点赞量', '评论量', '收藏量', '转发量', '回链', '内容类型',
                       '发布时间', '采集时间']
        else:
            all_file_path = f'{save_base_path}/{simple_file_name}_all_user.xlsx'
            if os.path.exists(all_file_path):
                os.remove(all_file_path)
            columns = ['账号编号', '序号', '平台', '赛道（一类）', '赛道（二类）', '账号链接', '账号昵称', '头像地址URL',
                       '账号KEY', '粉丝数量',
                       '总发布量', '阅读/曝光数量', '点赞数量', '评论数量', '收藏数量', '昨天发布数量', '采集时间']
        all_excel = os.listdir(save_base_path)
        all_res = []
        for excel in all_excel:
            if excel.endswith('.xlsx'):
                df = pd.read_excel(f'{save_base_path}/{excel}', dtype=str)
                res = df.to_numpy().tolist()
                all_res.extend(res)

        df = pd.DataFrame(all_res, columns=columns)
        df.to_excel(all_file_path, index=False)

def job(print_error=False):
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
    car.main(spider_files, cookies_strs, time_sleep, recent_days, print_error=print_error)
    if print_error:
        car.check_cookies_alive(cookies_strs)


def schedule_job():
    global CURRENT_SPIDER_TIME
    CURRENT_SPIDER_TIME = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
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
    job(print_error=True)


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