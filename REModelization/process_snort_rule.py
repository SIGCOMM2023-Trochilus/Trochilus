#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import re
import pandas as pd
import os

special_rules = ['[^', '\w', '\W', '(?:', '(?=', '(?!', '(?<=', '(?<!', '(?<', '(?#', '\S', '(?P']
special_res = []



def file_name_walk(file_dir, file_type='.csv'):
    file_list = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == file_type:
                file_list.append("{}/{}".format(root, file))
    return file_list

def extract_pcre_rules(file_path, rule_type='snort'):
    """
    @description  : extract pcre patterns
    @param        :
    @Returns      : DataFrame([original, rule, condition])
    """
    
    
    file_name = file_path.split('/')[-1].split('.')[0]
    if '-' in file_name:
        file_name = file_name.split('-')[1]
    print('rule name', file_name)
    i = 0
    res = []
    

    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if 'pcre' in line:
                skip_flag = False
                for special_rule in special_rules:
                    if special_rule in line:
                        skip_flag  = True
                        break
                if skip_flag:
                    continue
                try:
                    pattern = re.compile(r'pcre:"/([^;]*)/([a-zA-Z]*)"; ')
                    match_obj = pattern.findall(line)
                    if match_obj:
                        pcre_rule = rule_parser(match_obj[0][0])
                        res.append([match_obj[0][0], pcre_rule, match_obj[0][1]])
                except Exception as e:
                    print(e)
                    print(line)
                    print('match obj', match_obj)
    df = pd.DataFrame(res, columns=['original', 'rule', 'condition'])
    save_path = '../data/{}/pcre_rules/{}.csv'.format(rule_type, file_name)
    df.drop_duplicates(subset=['original'], inplace=True)
    if df.shape[0] > 0:
        df.loc[:, ['original', 'condition']].to_csv(save_path, index=False, sep='\t')
    
def rule_parser(rule):
    rule = rule.strip()
    idx = 0
    res = []
    while idx < len(rule):
        cur = rule[idx]
        if rule[idx] == '\\':
            if rule[idx + 1] == 'x':
                cur = rule[idx + 2: idx + 4]
                idx += 4
            else:
                cur = rule[idx + 1]
                idx += 2
        else:
            idx += 1
        res.append(cur)

    return res

def extract_all_rules():
    rule_path = '../data/snort/rules'
    file_list = file_name_walk(rule_path, file_type='.rules')
    print(file_list)
    for file_name in file_list:
        if 'rule' in file_name:
        # if 'activex' in file_name:
            extract_pcre_rules(file_name, 'snort')


def main():
    extract_all_rules()
    # read_rules()

if __name__ == '__main__':
    main()
