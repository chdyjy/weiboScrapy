import requests
from bs4 import BeautifulSoup
import json
import re
import time

# 配置
USER_AGENT = 'PostmanRuntime/7.29.2'
COOKIE = 'SINAGLOBAL=4206599047525.141.1682342743826; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFGmzaq-i7x1wZ-nyEFeahM5JpX5KMhUgL.Foz01KzfShnce0M2dJLoI0YLxKqL1-BLBKnLxK-L1h-L1hnLxKML1KBL1-qLxKBLBonL1h.LxK-LBo.LBoBLxKBLB.2L12eLxKML12qLB-Bt; UOR=,,login.sina.com.cn; ULV=1691029680380:6:1:2:4491541635858.181.1691029680350:1690724475571; XSRF-TOKEN=2azpGKz5OSnOe1vgkRENHGBg; ALF=1694846877; SSOLoginState=1692254877; SCF=Ani60_CJV5f7LwiVnTMTmd3RbiX0qs1kXgEmHV81LS_d1FlKj_lQ-nolst_eUcMlHDf3XkiQsEfu6QRxUSwBD2Y.; SUB=_2A25J2bLNDeRhGeRN4lAU9CbKyDuIHXVqrqMFrDV8PUNbmtANLVTZkW9NU2xvJCUkiDdARs9eNWISanzanfnbtlvu; WBPSESS=bXjQXCqFck1xasUtx3ZoUakbBFLPsC8eyeSfg1nzrDaedQ5g6muQPf53BfMS6Max63fNkjacYLVTMXLQhQF_CQcZX1Ky-rxi0f6f5s6Ju4RDcXUEJH6aJkYKUcQQBp_AHxwBc4V9LWLZRDohl98MbA=='
HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Connection': 'keep-alive',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cookie': COOKIE
}
BASE_URL = "https://weibo.com/ajax/side/hotSearch"
SAVE_FILE = "hotSearch.json"


def fetch_base_hot_search_data(limit=50):
    response = requests.get(BASE_URL)
    # print(response.content)
    base_json_data = response.json()
    base_hot_search_data = base_json_data['data']['realtime']
    return base_hot_search_data[:limit] if len(base_hot_search_data) > limit else base_hot_search_data


def fetch_hot_search_details(title):
    item_url = "https://s.weibo.com/weibo?q=%23" + title + "%23" + "&Refer=top"
    response = requests.get(item_url, headers=HEADERS)
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch data from {item_url}. Status code: {response.status_code}. Content: {response.text}")
    return BeautifulSoup(response.content, 'html.parser')


def save_to_file(data, filename=SAVE_FILE):
     with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

# def generate_compact_json(data_list):
#     # 转换每个 item 为紧凑形式的 JSON，然后使用 '\n' 连接，两侧加上方括号
#     return '[\n' + ',\n'.join(json.dumps(item, ensure_ascii=False) for item in data_list) + '\n]'


def get_indices_from_text(search_text, base_hot_search_data):
    """根据文本匹配热搜项并返回它们的序号"""
    matched_indices = []
    for idx, item in enumerate(base_hot_search_data, 1):
        if search_text in item.get('note', ''):
            matched_indices.append(idx)
    return matched_indices


def get_read_discuss_numbers(soup):
    """从soup中提取阅读数和讨论数"""
    span_div = soup.find("div", attrs={"class": "total"})
    span_list = span_div.findChildren("span")
    read_num = span_list[0].text[4:]
    discuss_num = span_list[1].text[4:]
    return read_num, discuss_num


def extract_topic_data_from_details(item):
    """从详情页中提取微博话题的相关数据"""
    hot_data_item = {}

    # 过滤掉广告
    if item.parent()[0].attrs.get("class")[0] != "card-wrap":
        return None

    item_title = item.find("p", attrs={"node-type": "feed_list_content"}).text
    nick_name = item.find("a", attrs={"class": "name"}).text
    item_id = item.attrs['mid']

    card_div = item.find("div", attrs={"class": "card-act"})
    span_list = card_div.findChildren("a")

    repost_num = 0 if "转发" in span_list[0].text else int(span_list[0].text)
    comment_num = 0 if "评论" in span_list[1].text else int(span_list[1].text)
    like_num = 0 if "赞" in span_list[2].text else int(span_list[2].text)

    item_url = "https://weibo.com/ajax/statuses/buildComments?is_reload=1&id=" + \
               item_id + "&is_show_bulletin=2&is_mix=0&count=10"
    item_res = requests.get(item_url, headers=HEADERS).json()

    comments = [
        {
            "nickName": data['user']['screen_name'],
            "content": re.sub(r'<[^>]*>', "", data['text'])
        }
        for data in item_res['data'][:10]
    ]

    return {
        "title": filter_title(re.sub(r'<[^>]*>', "", item_title)),
        "nickName": nick_name,
        "repostNum": repost_num,
        "commentNum": comment_num,
        "likeNum": like_num,
        "content": comments
    }


def extract_hot_search_data(cookie, indices=None, search_text=None):

    HEADERS['Cookie'] = cookie

    base_hot_search_data = fetch_base_hot_search_data()

    # 如果提供了热搜文本，获取对应的序号
    if search_text:
        indices = get_indices_from_text(search_text, base_hot_search_data)

    # 如果没有指定索引，则提取所有热搜数据
    if not indices:
        indices = list(range(1, len(base_hot_search_data) + 1))

    hot_data_list = []
    for idx in indices:
        if idx <= 0 or idx > len(base_hot_search_data):
            print(f"Invalid index {idx}. Skipping...")
            continue

        hot_search_item = base_hot_search_data[idx - 1]
        hot_data = {
            "title": filter_title(hot_search_item.get('note', '')),
            "hot": hot_search_item.get('raw_hot', 0),
            "content": []
        }

        soup = fetch_hot_search_details(hot_data["title"])
        hot_data["readNum"], hot_data["discussNum"] = get_read_discuss_numbers(soup)

        item_div = soup.find("div", attrs={"id": "pl_feedlist_index"})
        item_data_t = item_div.find("div", "m-note")
        item_data = item_data_t.findNextSibling("div")
        item_data_list = item_data.findChildren("div", attrs={"action-type": "feed_list_item"})
        item_data_list = item_data_list[:10]

        for item in item_data_list:
            topic_data = extract_topic_data_from_details(item)
            if topic_data:
                hot_data["content"].append(topic_data)

        hot_data_list.append(hot_data)
        time.sleep(2)  # 增加延迟，防止频繁请求

    return hot_data_list


def get_hot_search_list(cookie, limit=50):
    """
    Returns a list of hot search titles.

    :param cookie: The cookie string to use for requests.
    :param limit: Limit the number of titles returned.
    :return: A list of hot search titles.
    """
    HEADERS['Cookie'] = cookie
    base_hot_search_data = fetch_base_hot_search_data(limit=limit)

    # Extract titles from the fetched data
    titles = [filter_title(item.get('note', '')) for item in base_hot_search_data]

    return titles



def filter_title(text):
    """过滤空格、表情、换行符和其他不可见字符"""
    # 删除字符串开始和结束的空白字符以及换行
    cleaned_text = text.strip().replace('\n', '')
    # 使用正则表达式删除多余的空格和其他不需要的字符
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
    # 使用正则表达式过滤所有的Unicode表情和特殊字符
    cleaned_text = re.sub(r'[\U00010000-\U0010ffff]', '', cleaned_text)
    return cleaned_text





def main():
    try:
        hot_data_list = extract_hot_search_data(search_text='阿斯巴甜换名字了')
        save_to_file(hot_data_list)
        print(json.dumps(hot_data_list, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"出错了：{e}")


if __name__ == '__main__':
    main()
