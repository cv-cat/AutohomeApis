import json
import time

import requests

from utils.car_home_creator_utils import get_common_headers, get_post_headers, get_upload_image_headers
from utils.car_home_utils import trans_cookies


class CarApis:
    def __init__(self):
        self.serveice = '汽车之家'


    def get_detail(self, q, cookies_str):
        headers = get_common_headers()
        cookies = trans_cookies(cookies_str)
        url = "https://sou.api.autohome.com.cn/v2/topicentry/search"
        params = {
            "_appid": "club",
            "q": q,
            "_callback": "__jp8"
        }
        response = requests.get(url, headers=headers, cookies=cookies, params=params)
        res_text = response.text
        res_text = res_text.replace("__jp8(", "").replace(")", "")
        res_json = eval(res_text)
        return res_json


    def upload_img(self, file, cookies_str):
        headers = get_upload_image_headers()
        cookies = trans_cookies(cookies_str)
        url = "https://club-open-api.autohome.com.cn/upload/uploadMultiClubImg"
        params = {
            "_appid": "club",
            "t": str(int(time.time() * 1000)),
        }
        files = {
            'file': ('image.jpg', file, 'image/jpeg'),
            "biztype": (None, '1', None)

        }
        response = requests.post(url, headers=headers, cookies=cookies, params=params, files=files)
        res_json = response.json()
        return res_json

    def post(self, note_info, cookies_str):
        headers = get_post_headers()
        cookies = trans_cookies(cookies_str)
        url = "https://club-open-api.autohome.com.cn/topic/topicAdd"
        params = {
            "t": str(int(time.time() * 1000))
        }
        res_json = car.get_detail(note_info['bbsname'], cookies_str)
        bbs_id, bbs = res_json['result']['hitlist'][0]['id'], res_json['result']['hitlist'][0]['data']['bbs']
        image_urls = []
        for img in note_info['images']:
            res_json = car.upload_img(img, cookies_str)
            image_urls.append(res_json['result'][0]['url'])

        json_Content = {
            "root": {
                "children": [

                    {
                        "children": [
                            {
                                "detail": 0,
                                "format": 0,
                                "mode": "normal",
                                "style": "",
                                "text": "我的第一个帖子111",
                                "type": "text",
                                "version": 1
                            }
                        ],
                        "direction": "ltr",
                        "format": "",
                        "indent": 0,
                        "type": "paragraph",
                        "version": 1
                    }
                ],
                "direction": "ltr",
                "format": "",
                "indent": 0,
                "type": "root",
                "version": 1
            }
        }
        for image_url in image_urls:
            json_Content['root']['children'].append({
                "src": image_url,
                "width": 640,
                "height": 427,
                "caption": "image",
                "attributes": [],
                "type": "image",
                "version": 1
            })
        data = {
            "_appid": "club",
            "source": "pc",
            "title": note_info['title'],
            "htmlContent": "<p class=\"editor-paragraph\"><span>" + note_info['desc'] + "</span></p>",
            "jsonContent": json.dumps(json_Content),
            "bbs": str(bbs),
            "bbsId": str(bbs_id),
            "extendObj": "",
            "topicId": "0",
            "videoType": "0",
            "tIsPoll": "0"
        }
        response = requests.post(url, headers=headers, cookies=cookies, params=params, data=data)
        res_json = response.json()
        return res_json




if __name__ == '__main__':
    q = '江'
    cookies_str = ''
    car = CarApis()

    noteInfos = [
        {
            # 标题
            "title": "第一个帖子，11111",
            # 描述
            "desc": "第一个帖子，111112222",
            # 论坛名字
            "bbsname": "江淮iEV论坛",
            # 13位时间戳 数字类型
            "postTime": None,
            # 设置地点 "河海大学"
            "location": '南京',
            # 0:公开 1:私密
            "type": 1,
            "media_type": "image",
            # 设置话题
            "topics": ["雀魂", "麻将"],
            # 图片路径 最多15张
            "images": [
                open(r"C:\Users\99282\Downloads\istockphoto-157284494-1024x1024.jpg", 'rb').read(),
                open(r"C:\Users\99282\Downloads\istockphoto-157284494-1024x1024.jpg", 'rb').read(),
                open(r"C:\Users\99282\Downloads\istockphoto-157284494-1024x1024.jpg", 'rb').read(),
            ],
        },
        # {
        #     "title": "dwadaw20240815",
        #     "desc": "dwadawd20240815",
        #     "postTime": None,
        #     "location": '河海大学',
        #     "topics": ["北京"],
        #     "type": 1,
        #     "media_type": "video",
        #     "video": open(r"D:\data\Videos\2024-05-02 21-14-45.mkv", 'rb').read(),
        # }
    ]
    for noteInfo in noteInfos:
        res_json = car.post(noteInfo, cookies_str)
        print(res_json)



    # res_json = car.get_detail(q, cookies_str)
    # for i in res_json['result']['hitlist']:
    #     # print(i['id'], i['data']['bbsname'], i['data']['bbs'])
    #     print(i)

    # title = '测试测试测试测试测试'
    # content = '测试测试测试测试12132'
    # car.post(title, content, cookies_str)


    # file = open('D:\Desktop\Snipaste_2025-01-14_14-53-27.jpg', 'rb')
    # car.upload_img(file, cookies_str)
