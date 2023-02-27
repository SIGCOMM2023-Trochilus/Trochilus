#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from automata_tools.Automata import Automata
import random
from copy import deepcopy

def move(dfa, src, token):
    reachable_states = dfa.getReachableStates(src, token)
    

def getAllSouceSet(dfa):
    # {dst: {token: (src)}}
    reverse_transitions = {}
    for src_state in dfa.transitions:
        for cur_dst_state in dfa.transitions[src_state]:
            if cur_dst_state not in reverse_transitions:
                reverse_transitions[cur_dst_state] = {}
            for token in dfa.transitions[src_state][cur_dst_state]:
                if token not in reverse_transitions[cur_dst_state]:
                    reverse_transitions[cur_dst_state][token] = set([src_state])
                else:
                    reverse_transitions[cur_dst_state][token].add(src_state)
    return reverse_transitions

def getSourceSet(target_set, token, reverse_transitions):
    source_set = set()
    for target_state in target_set:
        if target_state in reverse_transitions and token in reverse_transitions[target_state]:
            source_set.update(reverse_transitions[target_state][token])
    return source_set

def MinDFA(dfa: Automata) -> Automata:
    # Hopcroft algorithm
    # dfa.transitions: {srcState: {dstState1: (char1, char2), dstState2: (char1, char2)}, ...}
    dfaStateLength = len(dfa.states)
    cins = set(dfa.language)
    termination_states = set(dfa.finalstates)
    total_states = set(dfa.states)
    non_termination_states = total_states - termination_states
    
    reverse_transitions = getAllSouceSet(dfa)

    P = [termination_states, non_termination_states]
    W = [termination_states, non_termination_states]

    while W:
        A = random.choice(W)
        W.remove(A)

        for token in cins:
            X = getSourceSet(A, token, reverse_transitions)
            P_tmp = []
            for Y in P:
                R1 = X & Y
                R2 = Y - X

                if len(R1) and len(R2):
                    P_tmp.append(R1)
                    P_tmp.append(R2)

                    if Y in W:
                        W.remove(Y)
                        W.append(R1)
                        W.append(R2)
                    else:
                        if len(R1) <= len(R2):
                            W.append(R1)
                        else:
                            W.append(R2)
                else:
                    P_tmp.append(Y)
            P = deepcopy(P_tmp)

    # get partitionOfStates
    start_state = dfa.startstate
    for idx, equal_states in enumerate(P):
        if start_state in equal_states:
            P[0], P[idx] = P[idx], P[0]
            break
    state2partition = {}
    for idx, equal_states in enumerate(P):
        for state in equal_states:
            state2partition[state] = idx
    
    # print('my partion of states', state2partition)

    if len(P) == dfaStateLength:
        minDFA = dfa
    else:
        # rebuild DFA
        minDFA = dfa.newBuildFromEquivalentStates({},
                                                  state2partition)
    return minDFA