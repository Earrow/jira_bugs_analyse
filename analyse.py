# coding=utf-8

from parse import ParsePage

from datetime import date


class Analyse:
    def __init__(self, username, password, rooturl):
        self.__parser = ParsePage(username, password)
        self.__parser.parse_root(rooturl)
        self._issues = self.__parser.issues

    def get_bugs_new(self):
        """获取本月新增缺陷数。
        统计规则：类型=缺陷，当前月份=创建月份

        :return: 本月新增缺陷数。
        """
        num = 0
        current_date = date.today()
        for issue in self._issues:
            created_date = date(*(int(item) for item in issue.created_time.split('/')))
            if issue.type == '缺陷' and created_date.month == current_date.month:
                num += 1

        return num

    def get_bugs_open(self):
        """获取未关闭缺陷数。
        统计规则：类型=缺陷，状态!=关闭

        :return: 未关闭缺陷数。
        """
        num = 0
        for issue in self._issues:
            if issue.type == '缺陷' and issue.status != '关闭':
                num += 1

        return num

    def get_bugs_more_than_7days(self):
        """获取周期大于7天的缺陷数。
        统计规则：类型=缺陷，状态!=关闭，当前日期-创建日期>7

        :return: 周期大于7天的缺陷数。
        """
        num = 0
        current_date = date.today()
        for issue in self._issues:
            if issue.type == '缺陷' and issue.status != '关闭':
                created_date = date(*(int(item) for item in issue.created_time.split('/')))
                if (current_date - created_date).days > 7:
                    num += 1

        return num

    def get_bugs_small(self):
        """获取低级缺陷数和低级缺陷率。
        统计规则：类型=缺陷，创建日期=本月，严重性=细微|一般

        :return: 低级缺陷数和低级缺陷率。
        """
        num = 0
        current_date = date.today()
        for issue in self._issues:
            created_date = date(*(int(item) for item in issue.created_time.split('/')))
            if issue.type == '缺陷' and created_date.month == current_date.month and \
                    (issue.severity == '细微缺陷' or issue.severity == '一般缺陷'):
                num += 1

        return num, '{:0.2f}'.format(num / self.get_bugs_new())

    def get_bugs_big(self):
        """获取严重缺陷数和严重缺陷率。
        统计规则：类型=缺陷，创建日期=本月，严重性=严重|致命

        :return: 严重缺陷数和严重缺陷率。
        """
        num = 0
        current_date = date.today()
        for issue in self._issues:
            created_date = date(*(int(item) for item in issue.created_time.split('/')))
            if issue.type == '缺陷' and created_date.month == current_date.month and \
                    (issue.severity == '严重缺陷' or issue.severity == '致命缺陷'):
                num += 1

        return num, '{:0.2f}'.format(num / self.get_bugs_new())

    def get_bugs_verified_nopass(self):
        """获取验证不通过的缺陷数。
        统计规则：类型=缺陷，本月验证不通过

        :return: 验证不通过的缺陷数。
        """
        num = 0
        for issue in self._issues:
            if issue.type == '缺陷' and issue.is_verified_nopass:
                num += 1

        return num
