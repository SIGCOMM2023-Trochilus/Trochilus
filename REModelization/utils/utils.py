import numpy as np
import random
import torch
import os
import datetime, time
import re

from config import MyLogging
myLogger = MyLogging()

blank_chars = ['\f', '\n', '\r', '\t', '\v']


def recursive_search(res, pat, text, pos=0):
    chars = [']']
    m = re.search(pat, text[pos:])  # pos: begin index
    if m:
        span = (m.span()[0] + pos, m.span()[1] + pos)
        # res.append({'result':m.group(0),'span':span})
        res.append(m.group(2))
        start_index = span[1]
        # if pat[-1] in chars:
        start_index = span[1] - 1
        return recursive_search(res, pat, text, pos=start_index)
    else:
        return res


def preprocess_pcre(pcre_rule):
    myLogger.debug_logger('before preprocess, len: {}, rule: {}'.format(len(pcre_rule), pcre_rule))

    # replace \$ with \x24
    pcre_rule = pcre_rule.replace('\$', '\\x24')

    # replace $ with \x24
    pcre_rule = pcre_rule.replace('$', '\\x24')

    # replace . with $
    pcre_rule = pcre_rule.replace('\\.', '\\$')
    pcre_rule = pcre_rule.replace('.', '$')
    pcre_rule = pcre_rule.replace('\\$', '\\.')

    # replace [\r\n\s] with \s
    any_blank_str = '(\\x0c|\\x0a|\\x0d|\\x09|\\x0b)'
    pcre_rule = pcre_rule.replace('[\\r\\n\s]', any_blank_str)

    # 2023.1.4 add
    # replace \r with \x0d
    pcre_rule = pcre_rule.replace('\r', '\\x0d')
    # replace \n with \x0a
    pcre_rule = pcre_rule.replace('\n', '\\x0a')

    # replace *? with *, replace +? with +
    pcre_rule = pcre_rule.replace('*?', '*')
    pcre_rule = pcre_rule.replace('+?', '+')

    myLogger.debug_logger('after replace basic: {}'.format(pcre_rule))
    # replace[a-z]
    # pattern = re.compile(r'[^\\]\[([^\[\]]*)\]')
    # pattern = re.compile(r'?=[^\\]\[[^\[\]]*\]')
    # pattern = re.compile(r'\[([^\[\]]*)\]')
    # match_obj = pattern.findall(pcre_rule)
    pattern = re.compile(r'([^\\]|^)\[([^\[\]]*)\]')
    match_obj = recursive_search([], pattern, pcre_rule, 0)
    myLogger.debug_logger('match_obj: {}'.format(match_obj))
    for match_str in match_obj:
        replace_str = parse_square_content(match_str)
        pcre_rule = pcre_rule.replace('[{}]'.format(match_str), replace_str)
    myLogger.debug_logger('after square: {}'.format(pcre_rule))

    # replace \s with (\x0c|\x0a|\x0d|\x09|\x0b)
    pcre_rule = pcre_rule.replace('\\s', any_blank_str)

    # replace \d with (0|1...|9)
    add_tokens = f'({"|".join([str(num) for num in range(0, 10)])})'
    pcre_rule = pcre_rule.replace('\d', add_tokens)

    myLogger.debug_logger('after preprocess: {}'.format(pcre_rule))
    return pcre_rule


def parse_square_content(square_tokens):
    # process content of []

    token_len = len(square_tokens)
    res = []
    ans = []
    range_flag = False
    idx = 0
    while idx < token_len:
        # print('idx', idx)
        token = square_tokens[idx]
        if token == '-':
            if len(res) > 0 and idx + 1 < token_len:
                range_flag = True
            else:
                res.append(token)
            idx += 1
        else:
            if token == '\\':
                if square_tokens[idx + 1] == 'x':
                    cur_token = ''.join(square_tokens[idx + 2: idx + 4])
                    res.append('\\x{}'.format(cur_token))
                    idx += 4
                elif square_tokens[idx + 1] == 's':
                    # \s
                    # blank_char_list = ['\\x0c', '\\x0a', '\\x09', '\\x0b']
                    blank_char_list = ['\\x0c', '\\x0a', '\\x09', '\\x0b', '\\x0d']
                    ans.extend(blank_char_list)
                    idx += 2
                elif square_tokens[idx + 1] == 'd':
                    ans.extend([str(i) for i in range(10)])
                    idx += 2
                else:
                    cur_token = square_tokens[idx + 1]
                    # if cur_token == '.':
                    #     cur_token = '\.'
                    cur_token = '\\{}'.format(cur_token)
                    res.append(cur_token)
                    idx += 2
            else:
                cur_token = token
                res.append(cur_token)
                idx += 1
            if range_flag:
                range_flag = False
                right = res.pop()
                left = res.pop()
                if len(left) > 1:
                    # [\x20-\x7f]
                    for i in range(int(left[-2:], base=16), int(right[-2:], base=16) + 1):
                        ans.append('\\x{:02x}'.format(i))
                else:
                    if left.isdigit():
                        # 0-9
                        for i in range(int(left), int(right) + 1):
                            ans.append(str(i))
                    elif left.islower() or left.isupper():
                        # a-z or A-Z
                        for i in range(ord(left), ord(right) + 1):
                            ans.append(chr(i))
                    else:
                        res.append(left)
                        res.append(right)
                while res:
                    ans.insert(0, res.pop())
    while res:
        ans.append(res.pop())
    ans = ['\\{}'.format(data) if data == '+' else data for data in ans]
    ans_str = f'({"|".join(ans)})'
    return ans_str


def get_blank_chrs():
    blank_chars_hex = []
    for ch in blank_chars:
        blank_chars_hex.append('\\x{:02x}'.format(ord(ch)))

    res = f'({"|".join(blank_chars_hex)})'
    print('black chars', blank_chars, blank_chars_hex, res)
    return res


# for reverse pcre
def split_rule(pcre_rule):
    idx = 0
    token_len = len(pcre_rule)
    unit_list = []
    while idx < token_len:
        token = pcre_rule[idx]
        if token == '\\':
            if pcre_rule[idx + 1] == 'x':
                # \x2a
                token = pcre_rule[idx: idx + 4]
                idx += 4
            else:
                token = pcre_rule[idx: idx + 2]
                idx += 2
        else:
            idx += 1
        unit_list.append(token)
    return unit_list


def reverse_pcre(pcre_rule):
    # split rule
    # print('before reverse:', pcre_rule)
    myLogger.debug_logger('before reverse: {}'.format(pcre_rule))
    unit_list = split_rule(pcre_rule)
    # print(unit_list)

    unit_list.reverse()

    operator = {'*', '+', '?'}
    reversed_re = []
    stack = []  # for operator
    prev = None
    temp_stack = []  # for {}
    square_stack = []  # for []
    set_begin = False
    square_begin = False
    unfinished_range = False
    unfinished_operator = False

    for i in unit_list:
        # print()
        # print('current: {}, pre: {}'.format(i, prev))
        # print('temp_stack', temp_stack)
        # print('square_stack', square_stack)
        # print('reversed_re', reversed_re)
        # print('square_begin', square_begin)
        # print('set_begin', set_begin)
        # print('unfinished_operator', unfinished_operator)

        if i == '}':
            set_begin = True

        if set_begin:
            temp_stack.append(i)
            if i == '{':
                set_begin = False
            prev = i
            continue

        if prev == '{':

            if i == ')' or i == ']':
                # 判断{}的前面是否是[]或者()
                unfinished_range = True
                prev = i
            else:
                temp_stack.append(i)
                temp_stack.reverse()
                reversed_re += temp_stack
                temp_stack = []
                prev = i
                continue

        if i == ']':
            square_begin = True

        if square_begin and i != '[':
            square_stack.append(i)
            if i == '[':
                square_begin = False
            prev = i
            continue

        if i == '[':
            square_stack.append(i)
            square_stack.reverse()

            if unfinished_range:
                temp_stack.reverse()
                square_stack = square_stack + temp_stack
                unfinished_range = False
                temp_stack = []
            if unfinished_operator:
                square_stack.append(stack.pop())
                unfinished_operator = False
            reversed_re += square_stack
            prev = i
            square_stack = []

            square_begin = False
            continue

        if i == '(':
            # pop from stack
            reversed_re.append(')')
            pop_tok = stack.pop(-1)
            if pop_tok != '':
                reversed_re.append(pop_tok)

        elif i == ')':
            # add to stack
            if prev in operator:
                stack.append(prev)
            else:
                stack.append('')

            reversed_re.append('(')

        elif i in operator:
            unfinished_operator = True
            stack.append(i)

        else:
            reversed_re.append(i)
            if prev in operator:
                reversed_re.append(prev)
                stack.pop()
                unfinished_operator = False

        prev = i

    return reversed_re


def file_name_walk(file_dir, file_type='.csv'):
    file_list = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == file_type:
                file_list.append("{}/{}".format(root, file))
    return file_list


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def len_stats(query):
    max_len = 0
    avg_len = 0
    for q in query:
        max_len = max(len(q), max_len)
        avg_len += len(q)
    avg_len /= len(query)

    print("max_len: {}, avg_len: {}".format(max_len, avg_len))


def pad_dataset(query, config, pad_idx):
    lengths = []
    new_query = []
    new_query_inverse = []
    for q in query:
        length = len(q)
        q_inverse = q[::-1]

        if length > config.seq_max_len:
            q = q[: config.seq_max_len]
            q_inverse = q_inverse[: config.seq_max_len]
            length = config.seq_max_len
        else:
            remain = config.seq_max_len - length
            remain_arr = np.repeat(pad_idx, remain)
            q = np.concatenate((q, remain_arr))
            q_inverse = np.concatenate((q_inverse, remain_arr))
            assert len(q) == config.seq_max_len

        new_query.append(q)
        new_query_inverse.append(q_inverse)
        lengths.append(length)

    return new_query, new_query_inverse, lengths


def pad_dataset_1(query, seq_max_len, pad_idx):
    lengths = []
    new_query = []
    new_query_inverse = []
    for q in query:
        length = len(q)

        if length <= 0:
            continue

        q_inverse = q[::-1]

        if length > seq_max_len:
            q = q[: seq_max_len]
            q_inverse = q_inverse[: seq_max_len]
            length = seq_max_len
        else:
            remain = seq_max_len - length
            remain_arr = np.repeat(pad_idx, remain)
            q = np.concatenate((q, remain_arr))
            q_inverse = np.concatenate((q_inverse, remain_arr))
            assert len(q) == seq_max_len

        new_query.append(q)
        new_query_inverse.append(q_inverse)
        lengths.append(length)

    return new_query, new_query_inverse, lengths


def mkdir(path):
    if not os.path.exists(path):
        os.mkdir(path)


def create_datetime_str():
    datetime_dt = datetime.datetime.today()
    datetime_str = datetime_dt.strftime("%m%d%H%M%S")
    datetime_str = datetime_str + '-' + str(time.time())
    return datetime_str


class Args():
    def __init__(self, data):
        self.data = data
        for k, v in data.items():
            setattr(self, k, v)


class Logger():
    def __init__(self):
        self.record = []  # recored strings

    def add(self, string):
        assert type(string) == str
        self.record.append(string + ' \n')

    def save(self, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(self.record)

def relu_normalized_NLLLoss(input, target):
    relu = torch.nn.ReLU()
    loss = torch.nn.NLLLoss()
    input = relu(input)
    input += 1e-4  # add small positive offset to prevent 0
    input = input / torch.sum(input)
    input = torch.log(input)
    loss_val = loss(input, target)
    return loss_val


def even_select_from_portion(L, portion):
    final_nums = int(L * portion)
    interval = 1 / portion
    idxs = [int(i * interval) for i in range(final_nums)]
    return np.array(idxs)


def evan_select_from_total_number(L, N):
    assert L >= N
    if N > 0:
        portion = N / L
        interval = 1 / portion
        idxs = [int(i * interval) for i in range(N)]
    else:
        idxs = []
    return np.array(idxs)
