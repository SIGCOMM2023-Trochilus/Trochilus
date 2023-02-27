import os
import pickle
from rules.load_data_and_rules import load_TREC_dataset, load_SMS_dataset, load_rule
from pydash.arrays import compact
from automata_tools import NFAtoDFA, DFAtoMinimizedDFA
from rules.dfa_from_rule import NFAFromRegex
from rules.fsa_to_tensor import Automata, drawGraph
from utils.utils import mkdir, create_datetime_str
import argparse
from rules.MinDFA import MinDFA


def create_dataset_automata(args):
    automaton = {}
    all_automata = Automata()
    all_automata.setstartstate(0)
    state_idx = 0
    flag = True

    for i in range(len(args.datasets)):
        print('rule type', args.datasets[i])
        automata_path = '/home/dgl/P4/RE_P4/RE-P4/baseline/RE2RNN-master/data/Automata/{}/{}.{}.pkl'.format(
            'Snort_delete', args.datasets[i], 'split')
        # automaton[i] = pickle.load(open(automata_path, 'rb'))
        automaton[args.datasets[i]] = pickle.load(open(automata_path, 'rb'))
        # print(automaton[i])

    print('MERGING AUTOMATA')
    for label, automata in automaton.items():

        # if flag:
        #     all_automata.setstartstate(automata.getstartstate())
        #     flag = False
        # states = list(automata.states)
        # final_states = list(automata.finalstates)
        # num_states = len(states)
        # used_states = [i for i in range(state_idx, state_idx + num_states)]
        # states2idx = {states[i]: used_states[i] for i in range(num_states)}
        # continue

        all_start = all_automata.getstartstate()
        # start = 0
        # print("start:", start)
        # print(label)
        # tok = 'BOS'
        # if reversed:
        #     tok = 'EOS'
        # all_automata.addtransition(0, state_idx, tok)  # may cause bug when the RE is accosiate with BOS
        states = list(automata.states)
        final_states = list(automata.finalstates)
        num_states = len(states)
        # print("num_states:", num_states)
        used_states = [i for i in range(state_idx, state_idx + num_states)]
        # print("used_states", used_states)
        states2idx = {states[i]: used_states[i] for i in range(num_states)}
        # print("states2idx：", states2idx)

        for fr_state, to in automata.transitions.items():
            for to_state, to_edges in to.items():
                for edge in to_edges:
                    # print(fr_state)
                    if fr_state == 0 and not flag:
                        # print("all_start:", states2idx[all_start])
                        # print("to state:", to_state)
                        # print("to state:", states2idx[to_state])
                        all_automata.addtransition(all_start, states2idx[to_state], edge)
                    else:
                        all_automata.addtransition(states2idx[fr_state], states2idx[to_state], edge)

        all_automata.addfinalstates([states2idx[i] for i in final_states])
        all_automata.addfinalstates_label([states2idx[i] for i in final_states], label)
        state_idx += (num_states) - 1
        flag = False

    # add $ * for finalstates
    for final_state in all_automata.finalstates:
        all_automata.addtransition(final_state, final_state, '$')

    # print("all states:", all_automata.states)

    # all_automata = DFAtoMinimizedDFA(all_automata)
    # all_automata  = MinDFA(all_automata)
    merged_automata = all_automata.to_dict()
    time_str = create_datetime_str()

    path = '../data/{}/automata/{}'.format('Snort', 'all_single')
    print("Drawing Graph and save at: {}".format(path))
    drawGraph(all_automata, path)
    path = '../data/{}/automata/{}.pkl'.format('Snort', 'all_single')
    print("Save the automata object at: {}".format(path))
    pickle.dump(merged_automata, open(path, 'wb'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    rule_name_list = [
        'activex.csv',
        'attack_response.csv',
        # 'exploit.csv',
        'ftp.csv',
        'info.csv',
        'malware.csv',
        'mobile_malware.csv',
        'policy.csv',
        'shellcode.csv',
        'web_client.csv',
        # 'web_server.csv',
        'current_events.csv', ]
    # datasets = ['web_client', 'current_events']
    datasets = ['policy']
    # datasets = ['activex', 'attack_response', 'ftp', 'shellcode', 'mobile_malware', 'info', 'malware', 'policy', 'web_client', 'current_events']
    # datasets = ['info', 'malware', 'policy', 'web_client', 'current_events']
    datasets = ['self']
    parser.add_argument('--datasets', type=list, default=datasets, help="dataset name")
    parser.add_argument('--automata_name', type=str, default='all', help="automata name prefix")
    parser.add_argument('--reversed', type=int, default=0, help="if we reverse the string")

    args = parser.parse_args()
    # assert args.dataset_name in ['ATIS', 'TREC', 'SMS']

    create_dataset_automata(args)
