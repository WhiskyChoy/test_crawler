# 这是用来测试的文件
import re

from craw_cy import make_suitable_for_file

test_str = '<div class="location">\n<span>广东省</span>\n<span>东莞市</span>\n</div>'
# . 匹配任意字符，除了换行符，当re.DOTALL标记被指定时，则可以匹配包括换行符的任意字符。
result = re.match(r'<div.*?class="location".*?>.*?</div>', test_str, re.DOTALL)

list_test = ['s', 'd', 'c']
a, b, c = list_test


print('"sadfadsf"sdfsdf"'.replace('"', '""'))

print(make_suitable_for_file('&quot; \x00 \x0b / \\ : * " < > | ?'))
print('test'[0:0])
print(result.group())
print(a, b, c)
