import numpy as np


def create_mat_and_bias_with_empty_PCRE(automata, in2i, i2in,additional_state=0):
    mat = np.zeros((len(automata['states']) + additional_state , len(i2in)))
    bias = np.zeros((len(i2in),))

    # extract final states, for multiple final states, use OR gate
    # finalstates_label: {label: states}
    for lab, states in automata['finalstates_label'].items():
        lab_idx = in2i[lab]
        for state in states:
            mat[state, lab_idx] = 1

    return mat, bias
