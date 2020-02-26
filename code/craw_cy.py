import os
import random
import re
import time

import math
# 下面两个库不是自带的，需要额外安装
import requests
from tqdm import trange

from static_data import *

# 数据位置
DATA_PREFIX = '../data/'
# 创业网站平台
URL_PREFIX = 'https://cy.ncss.org.cn/search/'
# 计数API
COUNT_URL = URL_PREFIX + 'projectcount'
# 列表API
LIST_URL = URL_PREFIX + 'projectlist'
# CSV存储位置（所有项目放在一个CSV）
DATA_FILE_PATH = DATA_PREFIX + 'data.csv'
INDEX_FILE_PATH = DATA_PREFIX + 'index.txt'
# 每页的项目数
PAGE_SIZE = 15
# 红色字符头
RED_CMD_CODE = '\033[1;31;m'
# 默认颜色
NORMAL_CMD_CODE = '\033[0m'
# 起始项目指针，小于等于0则会从当前爬取的项目开始
START_PROJECT_NUM = 0
# 终止项目指针，小于等于0则会爬取到网站提供的最后一个项目
END_PROJECT_NUM = 50000
# 每个项目放一个文件，该文件的行分隔符
CUSTOMIZED_SEP = '\n\n'
LF = '\n'
CR = '\r'
# CSV每项的分隔符
CSV_ELEMENT_SEP = ','
# CSV囊括一项的符号
CSV_ELEM_WRAPPER = '"'
# 文件标号与文件名的分隔符
NUM_SEP = '_'
# 以下是睡眠时间，避免被强行关闭连接
# 单位是秒，0.001秒=1毫秒，1000毫秒=1秒
MILLISECOND = 1 / 1000
# 每页请求的暂停时间
SLEEP_TIME_FOR_PAGE = 0 * MILLISECOND
# 每个项目的暂停时间
SLEEP_TIME_FOR_PROJECT = 50 * MILLISECOND
# 单个请求不成功，再次尝试的间隔时间
SLEEP_TIME_FOR_TRIAL = 10 * MILLISECOND
# 请求重试暂停时间的增长率
TRIAL_PROLONG_RATE = 0.1
# 重复单个请求的最大次数
MAX_SAFE_COUNTER = 5
# CSV文件的表头
CSV_HEADER = CSV_ELEMENT_SEP.join(['"题目"', '"所在省"', '"所在市"', '"行业"', '"项目概述"',
                                   '"项目进展"', '"团队信息"', '"专利情况"', '"网址"'])


def get_headers():
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Referer': 'https://cy.ncss.org.cn/search/projects',
        'User-Agent': random.choice(USER_LIST)
    }
    return headers


def get_proxies():
    proxies = {
        'https': 'https://' + random.choice(PROXY_LIST),
    } if len(PROXY_LIST) > 0 else None
    return proxies


def print_warning_sentence(sentence):
    print(RED_CMD_CODE, sentence, NORMAL_CMD_CODE)


def safe_get_request_text_getter(url, params=None, headers=None, proxies=None, max_safe_counter=MAX_SAFE_COUNTER):
    req = None
    for safe_counter in range(0, max_safe_counter):
        try:
            req = requests.get(url, params=params, headers=headers, proxies=proxies)
        # 这里最可能是ConnectionAbortedError，建议看看Exception的树
        except Exception as e:
            print('Error show at [' + str(safe_counter) + '] trial, the error is: ', e)
        if req.status_code == 200:
            break
        else:
            time.sleep((1 + safe_counter * TRIAL_PROLONG_RATE) * SLEEP_TIME_FOR_TRIAL)
        if safe_counter == max_safe_counter - 1:
            print_warning_sentence('Completely failed to finished getting url %s' % url)

    return req.text


def write_str_file(file_content_str, file_path):
    output_file = open(file_path, 'w', encoding='utf-8')
    output_file.write(file_content_str)
    output_file.close()


def add_zeros_before_str(input_num, digit_len):
    result = str(input_num)
    zeros_num = digit_len - len(result)
    for i in range(0, zeros_num):
        result = '0' + result
    return result


def strip_str(str_list):
    for i in range(0, len(str_list)):
        if hasattr(str_list[i], 'strip'):
            str_list[i] = str_list[i].strip()


def to_csv_element(str_list):
    for i in range(0, len(str_list)):
        if hasattr(str_list[i], 'replace'):
            replaced_str = str_list[i].replace(LF, CR).replace(CSV_ELEM_WRAPPER, CSV_ELEM_WRAPPER + CSV_ELEM_WRAPPER)
            str_list[i] = CSV_ELEM_WRAPPER + replaced_str + CSV_ELEM_WRAPPER


def get_project_detail(data_link):
    browse_url = URL_PREFIX + data_link
    project_detail_content = safe_get_request_text_getter(browse_url)
    title = re.findall(r'<h4>(.*?)</h4>', project_detail_content)[0]
    # . 匹配任意字符，除了换行符，当re.DOTALL标记被指定时，则可以匹配包括换行符的任意字符。
    location_html = re.findall(r'<div.*?class="location".*?>(.*?)</div>', project_detail_content, re.DOTALL)[0]
    locations = re.findall(r'<span>(.*?)</span>', location_html)
    location_province = locations[0]
    location_city = locations[1]
    industry_html = re.findall(r'<div.*?class="industry".*?>(.*?)</div>', project_detail_content, re.DOTALL)[0]
    industry = re.findall(r'<span>(.*?)</span>', industry_html)[0]
    description = re.findall(r'项目概述.*?<p.*?>(.*?)</p>', project_detail_content, re.DOTALL)[0]
    progress = re.findall(r'项目进展.*?<p.*?>(.*?)</p>', project_detail_content, re.DOTALL)[0]
    # 上面也有href链接到下面的，所以会先找到上面的，加个</h5>就可以避免这个问题，虽然很丑陋
    # 再加上丑陋的strip
    team = re.findall(r'团队信息</h5>.*?<p.*?>(.*?)</p>', project_detail_content, re.DOTALL)[0]
    patent = re.findall(r'专利情况</h5>.*?<p.*?>(.*?)</p>', project_detail_content, re.DOTALL)[0]
    arg_list = [title, location_province, location_city, industry, description, progress, team, patent,
                browse_url]
    strip_str(arg_list)
    # ProjectDetail(title, location_province, location_city, industry, description,
    # progress, team, patent, browse_url)没有用，因为被改的是list里的
    return ProjectDetail(*arg_list)


class ProjectDetail(object):
    def __init__(self, title, location_province, location_city, industry, description, progress, team, patent,
                 browse_url):
        self.title = title
        self.location_province = location_province
        self.location_city = location_city
        self.industry = industry
        self.description = description
        self.progress = progress
        self.team = team
        self.patent = patent
        self.browse_url = browse_url

    def to_string(self):
        return CUSTOMIZED_SEP.join(['题目', self.title, '所在省', self.location_province, '所在市', self.location_city,
                                    '行业', self.industry, '项目概述', self.description, '项目进展', self.progress,
                                    '团队信息', self.team, '专利情况', self.patent, '网址', self.browse_url])

    def to_csv_line(self):
        str_list = [self.title, self.location_province, self.location_city, self.industry, self.description,
                    self.progress, self.team, self.patent, self.browse_url]
        to_csv_element(str_list)
        return CSV_ELEMENT_SEP.join(str_list)


def make_suitable_for_file(input_str):
    reg = re.compile(r'[\x00-\x1f\x7F/\\:*"<>|?]')
    result = reg.sub('_', input_str)
    return result


def get_current_project_index():
    if not os.path.exists(INDEX_FILE_PATH):
        return 0
    else:
        index_file = open(INDEX_FILE_PATH, 'r', encoding='utf-8', newline='\n')
        index_line = index_file.readline()
        if index_line == '':
            return 0
        index = re.findall(r'Current Project Index: (.*)', index_line)
        if len(index) == 0:
            return 0
        return int(index[0])


def main():
    if not os.path.exists(DATA_PREFIX):
        os.makedirs(DATA_PREFIX)

    total_project_num = int(safe_get_request_text_getter(COUNT_URL))

    print("Total project number is read from the website as [%d]." % total_project_num)

    digit_len_max_project_num = len(str(total_project_num))

    if END_PROJECT_NUM > 0:
        total_project_num = min(END_PROJECT_NUM, total_project_num)
    smallest_project_num = START_PROJECT_NUM if START_PROJECT_NUM >= 1 else get_current_project_index() + 1

    page_start_num = math.floor(smallest_project_num / PAGE_SIZE)
    page_end_num = math.ceil(total_project_num / PAGE_SIZE)

    project_index = page_start_num * PAGE_SIZE + 1

    expected_num = total_project_num - smallest_project_num + 1
    actual_num = total_project_num - project_index + 1
    delta_num = actual_num - expected_num
    print("The number of projects expected to get is [%d]." % expected_num)
    print("When consider the old page refreshed, there are [%d] project(s) rewritten." % delta_num)
    print("The final projects number is %d." % actual_num)

    # 创建进度条，trange与range相似，前两个参数是起始值和终止值，这里的leave是留下继续显示的意思
    # project_index这里从1开始，不从0开始，所以total_project_num要加1
    progress_bar = trange(project_index, total_project_num + 1, desc='爬取进度')

    lines = []
    if os.path.exists(DATA_FILE_PATH):
        data_file = open(DATA_FILE_PATH, 'r', encoding='utf-8', newline='\n')
        lines = data_file.readlines()
        data_file.close()

    data_file = open(DATA_FILE_PATH, 'w', encoding='utf-8', newline='\n')
    index_file = open(INDEX_FILE_PATH, 'w', encoding='utf-8', newline='\n')

    len_lines = len(lines)
    if len_lines == 0:
        data_file.write(CSV_HEADER + LF)
    else:
        data_file.writelines(lines[0:min(project_index + 1, len_lines)])
    for page_index in range(page_start_num, page_end_num):
        # 查询字符串
        params = {
            # api页面从0记起
            'pageIndex': str(page_index),
            'pageSize': PAGE_SIZE
        }
        table_content = safe_get_request_text_getter(LIST_URL, params=params, headers=get_headers(),
                                                     proxies=get_proxies())
        # print(table_content)
        data_links = re.findall(r'<tr.*?data-link="(.*?)".*?>', table_content)
        # print(data_links)
        for data_link in data_links:
            project_detail = get_project_detail(data_link)
            # 这里从1开始编号文件，如果不想从1开始编号就把project_counter + 1后面的+ 1去掉
            output_filename_prefix = add_zeros_before_str(project_index, digit_len_max_project_num)
            output_filename = output_filename_prefix + NUM_SEP + make_suitable_for_file(project_detail.title)
            output_file_path = DATA_PREFIX + output_filename
            write_str_file(project_detail.to_string(), output_file_path)
            data_file.write(project_detail.to_csv_line() + LF)
            progress_bar.update(1)
            index_file.truncate(0)
            index_file.seek(0, 0)
            index_file.write('Current Project Index: %d' % project_index)
            project_index += 1
            if project_index == total_project_num + 1:
                break
            time.sleep(SLEEP_TIME_FOR_PROJECT)

        time.sleep(SLEEP_TIME_FOR_PAGE)

    progress_bar.close()
    data_file.close()
    index_file.close()


if __name__ == '__main__':
    main()
