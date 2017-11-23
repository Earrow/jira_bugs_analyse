# coding=utf-8

import logging
import sys
from datetime import datetime

from analyse import Analyse

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '[%(asctime)s][%(levelname)s] %(message)s')
ch.setFormatter(formatter)

logger.addHandler(ch)

user_name = sys.argv[1]
user_pwd = sys.argv[2]
url = sys.argv[3]

start = datetime.now()
a = Analyse(user_name, user_pwd, url)
end = datetime.now()
print('新增缺陷数：{}, 未关闭缺陷数：{}, 缺陷周期大于7天数：{}, 低级缺陷数：{}, 低级缺陷率: {}, '
      '严重缺陷数: {}, 严重缺陷率：{}， 验证不通过缺陷数：{}'.format(a.get_bugs_new(), a.get_bugs_open(), a.get_bugs_more_than_7days(),
                                                *a.get_bugs_small(), *a.get_bugs_big(), a.get_bugs_verified_nopass()))
print(end - start)
