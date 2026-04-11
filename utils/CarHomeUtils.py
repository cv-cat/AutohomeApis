import time
def trans_cookies(cookies):
    return {i.split('=')[0]: i.split('=')[1] for i in cookies.split('; ')}

def get_time():
    timestamp_ms = int(time.time() * 1000)
    timestamp_s = timestamp_ms / 1000
    formatted_time = time.strftime("%a %b %d %Y %H:%M:%S GMT+0800 (中国标准时间)", time.localtime(timestamp_s))
    return str(timestamp_ms), str(formatted_time)
# 判断日期与当前日期是否在n天内
def is_n_days_ago(date, n):
    now = time.time()
    date = str_to_timestamp(date)
    if now - date > n * 24 * 60 * 60:
        return False
    return True

def get_headers(referer="https://iservice.autohome.com.cn/"):
    return {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": referer,
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "sec-ch-ua": "\"Microsoft Edge\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }
def timestamp_to_str(timestamp):
    time_local = time.localtime(timestamp / 1000)
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
    return dt

# %Y-%m-%d %H:%M:%S 转时间戳 10位
def str_to_timestamp(str):
    time_array = time.strptime(str, "%Y-%m-%d %H:%M:%S")
    timestamp = int(time.mktime(time_array))
    return timestamp

# 判断日期与当前日期是否在n天内
def is_n_days_ago(date, n):
    now = time.time()
    date = str_to_timestamp(date)
    if now - date > n * 24 * 60 * 60:
        return False
    return True
if __name__ == '__main__':

    print(get_time())