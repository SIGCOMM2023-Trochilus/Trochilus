import os
import pickle
from pydash.arrays import compact
from automata_tools import NFAtoDFA, DFAtoMinimizedDFA
from fsa_to_tensor import Automata, drawGraph
from utils.utils import mkdir, create_datetime_str
import argparse
from MinDFA import MinDFA


def create_dataset_automata(args):
    automaton = {}
    all_automata = Automata()
    all_automata.setstartstate(0)
    state_idx = 0
    flag = True

    for i in range(len(args.datasets)):
        print('rule type', args.datasets[i])
        automata_path = 'YourSingleAutomatonPath'
        # automaton[i] = pickle.load(open(automata_path, 'rb'))
        # merge all category automaton
        automaton[args.datasets[i]] = pickle.load(open(automata_path, 'rb'))
        # print(automaton[i])

    print('MERGING AUTOMATA')
    for label, automata in automaton.items():

        all_start = all_automata.getstartstate()
        states = list(automata.states)
        final_states = list(automata.finalstates)
        num_states = len(states)
        used_states = [i for i in range(state_idx, state_idx + num_states)]
        states2idx = {states[i]: used_states[i] for i in range(num_states)}

        for fr_state, to in automata.transitions.items():
            for to_state, to_edges in to.items():
                for edge in to_edges:
                    # print(fr_state)
                    if fr_state == 0 and not flag:
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

    merged_automata = all_automata.to_dict()

    path = 'YourGraphSavePath'
    print("Drawing Graph and save at: {}".format(path))
    drawGraph(all_automata, path)
    path = 'YourAutomatonSavePath'
    print("Save the automata object at: {}".format(path))
    pickle.dump(merged_automata, open(path, 'wb'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # for test
    rule_name_list = [
        'activex.csv',
        'attack_response.csv',
        'ftp.csv',
        'info.csv',
        'malware.csv',
        'mobile_malware.csv',
        'policy.csv',
        'shellcode.csv',
        'web_client.csv',
        'current_events.csv', ]
    # datasets = ['web_client', 'current_events']
    parser.add_argument('--datasets', type=list, default=['activex'], help="dataset name")
    parser.add_argument('--automata_name', type=str, default='all', help="automata name prefix")
    parser.add_argument('--reversed', type=int, default=0, help="if we reverse the string")

    args = parser.parse_args()

    create_dataset_automata(args)
