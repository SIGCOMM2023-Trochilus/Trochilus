import sys
sys.path.append('..')
from typing import List
from utils.utils import preprocess_pcre, reverse_pcre
from pydash.arrays import compact
import pandas as pd


def reverse_regex(tokenized_re: List[str]):
    # ruleString = '($ * abbreviation ( & | $ ) * a{1, 3} )'
    tokenized_re.reverse()
    print('reversed token', tokenized_re)
    operator = {'*', '+', '?'}
    reversed_re = []
    stack = [] # for operator
    prev = None
    temp_stack = [] # for {}
    set_begin = False
    for i in tokenized_re:
        if i == '}':
            set_begin = True

        if set_begin:
            temp_stack.append(i)
            if i == '{':
                set_begin = False
            prev = i
            continue

        if prev == '{':
            temp_stack.append(i)
            temp_stack.reverse()
            reversed_re += temp_stack
            prev = i
            temp_stack = []
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
            pass

        else:
            reversed_re.append(i)
            if prev in operator:
                reversed_re.append(prev)

        prev = i

    return reversed_re



def original_test_param():
    print('original_tets')
    ruleString = '($ * abbreviation ( & | $ ) * a{1, 3} )'
    parseResult = ruleParser(ruleString)
    print(parseResult)
    reversed_re = reverse_regex(parseResult)
    print(reversed_re)
    print()

def reverse_pcre_test():
    file_path = '../data/snort/pcre_rules/activex.csv'
    rules = pd.read_csv(file_path, delimiter='\t')
    i = 0
    for indexClass, rulesOfAClass in rules.iterrows():
        print()
        print('indexClass', indexClass)
        reversed_re = reverse_pcre(rulesOfAClass[0])
        print('after reverse', ''.join(reversed_re))
        reversed_pcre = ''.join(reversed_re)
        reversed_pcre = preprocess_pcre(reversed_pcre)
        rulesOfAClass = [reversed_pcre]
        # print('indexClass', indexClass)
        print('rulesofClass', rulesOfAClass)
        concatenatedRule = f'(({")|(".join(compact(rulesOfAClass))}))'
        # concatenatedRule = f'( ( {")|(".join(compact(rulesOfAClass))} ) )'
        
        print(concatenatedRule)
        

        # i += 1
        # if i >= 10:
        #     break
    


if __name__ == '__main__':

    reverse_pcre_test()