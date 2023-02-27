#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from automata_tools import NFAtoDFA
import re
from my_dfa_from_rule import NFAFromRegex
from fsa_to_tensor import Automata, drawGraph
import pandas as pd
from MinDFA import MinDFA
from utils.utils import preprocess_pcre, reverse_pcre, file_name_walk
import pickle
import numpy as np
from datetime import datetime
from pydash.arrays import compact
import os
from config import MyLogging
myLogger = MyLogging()
import argparse


punctuations = [
    ',', '，', ':', '：', '!', '！', '《', '》', '。', '；', '.', '(', ')', '（', '）',
    '|', '?', '"'
]


def merge_all_automata(automaton, total_language, dataset, rule_type, mode):
    # merge all automata
    all_automata = Automata()
    all_automata.setstartstate(0)
    state_idx = 1
    for label, automata in automaton.items():
        start_state = automata.startstate
        tok = 'BOS'
        if mode == 'reversed':
            tok = 'EOS'
        all_automata.addtransition(0, state_idx, tok)
        # all_automata.addtransition(0, start_state, tok)
        states = list(automata.states)
        final_states = list(automata.finalstates)
        num_states = len(states)
        used_states = [i for i in range(state_idx, state_idx + num_states)]
        states2idx = {states[i]: used_states[i] for i in range(num_states)}

        for fr_state, to in automata.transitions.items():
            for to_state, to_edges in to.items():
                for edge in to_edges:
                    all_automata.addtransition(states2idx[fr_state], states2idx[to_state], edge)
        all_automata.addfinalstates([states2idx[i] for i in final_states])
        # all_automata.addfinalstates_label([states2idx[i] for i in final_states], rule_type)
        state_idx += (num_states)
    
    # min dfa
    all_automata.language = total_language
    print('before min states:', len(all_automata.states))
    all_automata = MinDFA(all_automata)
    # add $ * for finalstates
    for final_state in all_automata.finalstates:
        # all_automata.addtransition(final_state, final_state, '$_24')
        all_automata.addtransition(final_state, final_state, '$')
    
    # add label for finalstates
    current_label = rule_type
    all_automata.addfinalstates_label(all_automata.finalstates, current_label)
    # all_automata = DFAtoMinimizedDFA(all_automata)
    print('after min states:', len(all_automata.states))
    print('language len', len(all_automata.language))
    print('finalstates_label', all_automata.finalstates_label)

    merged_automata = all_automata
    merged_automata_dict = all_automata.to_dict
    # merged_automata = all_automata
    # print(merged_automata)

    if len(all_automata.states) < 500:
        path = '../data/{}/imgs/{}_{}_min'.format(dataset, rule_type, mode)
        print("Drawing Graph and save at: {}".format(path))
        drawGraph(all_automata, path)
    dict_path = '../data/{}/automata_dict/{}.{}.pkl'.format(dataset, rule_type, mode)
    pickle.dump(merged_automata_dict, open(dict_path, 'wb'))
    path = '../data/{}/automata/{}.{}.pkl'.format(dataset, rule_type, mode)
    print("Save the automata object at: {}".format(path))
    pickle.dump(merged_automata, open(path, 'wb'))
    merge_res = {'min_states': len(all_automata.states)}
    return merge_res




def pcres2dfa(dataset, rule_type, reversed=False):
    mode = 'reversed' if reversed else 'split'
    file_path = '../data/{}/pcre_rules/{}.csv'.format(dataset, rule_type)
    
    file_name = file_path.split('/')[-1].split('.')[0]
    
    rules = pd.read_csv(file_path, delimiter='\t')

    i = 0
    automaton = {}
    total_language = set()
    state_num = []
    cls_total_state_num = 0
    
    for indexClass, rulesOfAClass in rules.iterrows():
        print('rule', rulesOfAClass)
        original_rule = rulesOfAClass
        if reversed:
            reversed_re = reverse_pcre(rulesOfAClass[0])
            middle_pcre = ''.join(reversed_re)
        else:
            middle_pcre = rulesOfAClass[0]

        pcre_rule = preprocess_pcre(middle_pcre)

        rulesOfAClass = [pcre_rule]
        concatenatedRule = f'(({")|(".join(compact(rulesOfAClass))}))'
        
        nfa = NFAFromRegex().buildNFA(concatenatedRule, reversed=False)

        dfa = NFAtoDFA(nfa)

        # add $ * for startstate
        dfa.addtransition(dfa.startstate, dfa.startstate, '$')
        my_minDFA = MinDFA(dfa)

        automaton[indexClass] = my_minDFA
        total_language.update(my_minDFA.language)
        state_num.append(len(my_minDFA.states))
        cls_total_state_num += len(my_minDFA.states)

        i += 1
        if i >= 10:
            break

    merge_res = merge_all_automata(automaton, total_language, dataset, rule_type, mode)
    print('state num mean:{}, min: {}, max: {}:'.format(np.mean(state_num), np.min(state_num), np.max(state_num)))

def extract_all_cls():
    """
    @description  : convert single class's rules to DFA
    @param        :
    @Returns      :
    """
    dataset = 'snort'
    rule_type_list = ['activex', 'attack_response']
    
    for rule_type in rule_type_list:
        print()
        print('rule_type', rule_type)
        a = datetime.now()
        print('start time', a)
        pcres2dfa(dataset, rule_type)
        b = datetime.now()
        print('end time', b)
        print('duration(s)', (b - a).seconds)

def extract_single_cls(args):
    dataset = 'snort'
    rule_type = args.datasets
    pcres2dfa(dataset, rule_type, args.reversed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--datasets', type=str, default='activex', help="dataset name")
    parser.add_argument('--reversed', type=int, default=0, help="if we reverse the string")

    args = parser.parse_args()

    extract_single_cls(args)


if __name__ == '__main__':
    a = datetime.now()
    print("start time", a)
    main()
    b = datetime.now()
    print("end time", b)
    durn = (b-a).seconds
    print("duration", durn)