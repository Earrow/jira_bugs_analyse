# coding=utf-8


"""
解析页面，提取出问题类型、名称、时间等信息。
"""

import requests
from lxml import html
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

import time
import datetime
import logging
from collections import namedtuple

# 问题描述，包括类型（需求、缺陷...）、标题、创建时间、更新时间、严重性、本月是否有过验证不通过
ISSUE = namedtuple('ISSUE', 'type title status severity created_time updated_time is_verified_nopass')


class ParsePage:
    def __init__(self, username, password):
        """初始化issue列表，保存JIRA账号。

        :param username: 登录JIRA的用户名
        :type username: string
        :param password: username对应的登录密码
        :type password: string
        """
        # 保存实例解析出的所有issue。
        # parse方法会返回对特定url的解析结果，该集合中会保存parse方法解析出的所有结果。
        self._issues = set()
        # 页面内容缓存
        self.__html_doc_cache = {}
        self._username = username
        self._password = password
        self._logger = logging.getLogger(__name__)

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6',
            'Host': '***',
            'User-Agent': 'Mozilla / 5.0(WindowsNT10.0;Win64;x64) AppleWebKit / 537.36(KHTML, likeGecko) '
                          'Chrome / 61.0.3163.100Safari / 537.36'
        }

        # 登录JIRA
        self._session = requests.Session()
        self._session.headers.update(headers)
        self._session.post('http://***', data={
            'os_username': self._username,
            'os_password': self._password
        })

    @property
    def issues(self):
        return list(self._issues)

    def _get_html_doc(self, url, params=None):
        """获取页面内容。

        :param url: 页面地址。
        :type url: string
        :params: http请求参数。
        :type params: dict
        :return: 页面内容。
        :rtype: string
        """
        if url in self.__html_doc_cache:
            # 如果该页面被访问过，则直接返回页面内容
            self._logger.debug('get {url} page content in cache'.format(url=url))
            return self.__html_doc_cache[url]
        else:
            r = self._session.get(url, params=params)
            self.__html_doc_cache.update({url: r.text})
            return r.text

    def is_verified_nopass(self, issue_url, **kwargs):
        """判断某个问题是否在本月内有验证未通过的情况。
        判断规则：该问题本月有操作，且操作字段=状态，原值=待验证，新值=待修复

        :param issue_url: 问题链接。
        :type issue_url: string
        :param html_doc_path: （可选）html内容文本路径字符串，供测试该函数使用。
        :return: True if 本月内该问题有验证不通过的记录 else False
        :rtype: bool
        """
        # 对问题url和该参数一起调用get请求可以获取该问题的改动记录
        payload = {
            'page': 'com.atlassian.jira.plugin.system.issuetabpanels:changehistory-tabpanel',
            '_': str(round(time.time(), 3)).replace('.', '')
        }

        if 'html_doc_path' in kwargs:
            # 测试该函数
            with open(kwargs['html_doc_path']) as fp:
                html_doc = fp.read()
        else:
            html_doc = self._get_html_doc(issue_url, payload)
        tree = html.fromstring(html_doc)

        # 操作用户、操作时间、操作字段都放在一个id包含'changehistory-<id>'的div中
        # 因此遍历网页中的所有此div，即可获取各次操作
        for action in tree.xpath('//div[contains(./@id, "changehistory-")]'):
            # 操作人
            change_user = action.xpath('.//a[contains(./@id, "changehistoryauthor")]')[0].xpath('./text()')[0].strip()
            # 操作时间
            change_date = action.xpath('.//span[@class="date"]/time')[0].text.strip()
            # 操作字段，一次操作中修改了哪些内容，可能有多条
            change_actions = [(action[0].text.strip(), action[1].text.strip(), action[2].text.strip())
                              for action in zip(
                    action.xpath('.//td[@class="activity-name"]'),
                    action.xpath('.//td[@class="activity-old-val"]'),
                    action.xpath('.//td[@class="activity-new-val"]')
                )]

            date = datetime.datetime.strptime(change_date, '%Y/%m/%d %H:%M')
            current_date = datetime.date.today()
            if date.month == current_date.month:
                for name, old_val, new_val in change_actions:
                    if name == '状态' and old_val == '待验证' and new_val == '待修复':
                        return True

        return False

    def parse(self, url):
        """解析某个页面中的issue，存入集合中返回，并存入实例的总issues集合中。

        :param url: 要解析的html页面url
        :type url: string
        :return: url参数对应页面中的issue集合
        :rtype: set
        """
        tree = html.fromstring(self._get_html_doc(url))
        types = tree.xpath('//td[@class="issuetype"]//img/@alt')
        titles = [a.text for a in tree.xpath('//td[@class="summary"]//a[@class="issue-link"]')]
        status_list = [span.text for span in tree.xpath('//td[@class="status"]/span')]
        severities = [td.text.strip() if td.text is not None else None
                      for td in tree.xpath('//td[@class="customfield_10121"]')]
        created_times = [time_tag.text for time_tag in tree.xpath('//td[@class="created"]//time')]
        updated_times = [time_tag.text for time_tag in tree.xpath('//td[@class="updated"]//time')]

        with ThreadPoolExecutor(max_workers=10) as executor:
            is_verified_nopass = list(executor.map(self.is_verified_nopass, ('http://***' + url for url in tree.xpath('//a[@class="issue-link"][count(./text())=1]/@href'))))

        issues = {ISSUE(type, title, status, severity, created_time, updated_time, is_nopass)
                  for type, title, status, severity, created_time, updated_time, is_nopass
                  in zip(types, titles, status_list, severities, created_times, updated_times, is_verified_nopass)}

        self._issues = self._issues | issues
        return issues

    def parse_root(self, root_url, issues=set()):
        """解析某个页面中的issue，如果有下一页，会继续往下解析，直到解析完所有页面。

        :param root_url: 解析的起始页面，传入问题列表的第一页则可以解析完所有问题
        :type root_url: string
        :param issues: 存放解析出的issue的集合
        :type issues: set
        :return: 从root_url开始的所有页面中的issue集合
        :rtype: set
        """
        issues.update(self.parse(root_url))
        time.sleep(3)

        tree = html.fromstring(self._get_html_doc(root_url))
        # 当前页显示的最大问题序号
        count_end = int(tree.xpath('//span[@class="results-count-end"]')[0].text)
        # 总问题数
        count_total = int(tree.xpath('//span[contains(./@class, "results-count-total")]')[0].text)

        if count_end < count_total:
            # 获取下一页的链接，递归解析每一页。
            # '&'之前的url为问题列表第一页的路径，每次翻页都会在该url的基础上增加'&startIndexStr='后缀，
            # 且其跟的值为上一页的'results-count-end'值。
            root_url = root_url.split('&')[0]
            root_url += '&startIndex=' + str(count_end)

            self.parse_root(root_url, issues)
        else:
            self._issues.update(issues)
            return issues

    def filter(self, **kwargs):
        """根据type、status字段对全issues进行过滤。

        :param kwargs: 过滤的字段、值
        :return: 过滤后的issues子列表
        :rtype: set

        Usage::
            >>> ParsePage.filter(type='需求', statue='关闭')
        """
        sub_issues = set()
        sub_issues.update(self._issues)
        for issue in self._issues:
            for key in kwargs:
                # 如果过滤条件是issue的属性并且值匹配，则将该issue删掉
                if key in issue._fields and not kwargs[key] == issue.__getattribute__(key):
                    sub_issues.remove(issue)
                    break

        return sub_issues

    def __len__(self):
        return len(self._issues)

    def __repr__(self):
        return str(self._issues)
