import re
#split string with 2 delimiters
my_str = 'z0`z1@x1`x2`x3@x4ff\r\n'#  'one,two-three,four'
my_list = re.split(r'`|@', my_str)
# split on comma or hyphen
print(my_list)