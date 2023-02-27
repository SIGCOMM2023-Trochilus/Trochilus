# encoding: utf-8

import warnings
import numpy as np
import pandas as pd
from SoftTree import *
import time
import random
import math
import pickle
import os
from collections import Counter

warnings.filterwarnings('ignore')


def ProduceBinaryInput(data_vec):
    BV = []
    for v in data_vec:
        if v >= 2**7:
            BV.append(1)
            v -= 2**7
        else:
            BV.append(0)
        if v >= 2**6:
            BV.append(1)
            v -= 2**6
        else:
            BV.append(0)
        if v >= 2**5:
            BV.append(1)
            v -= 2**5
        else:
            BV.append(0)
        if v >= 2**4:
            BV.append(1)
            v -= 2**4
        else:
            BV.append(0)
        if v >= 2**3:
            BV.append(1)
            v -= 2**3
        else:
            BV.append(0)
        if v >= 2**2:
            BV.append(1)
            v -= 2**2
        else:
            BV.append(0)
        if v >= 2**1:
            BV.append(1)
            v -= 2**1
        else:
            BV.append(0)
        if v >= 2**0:
            BV.append(1)
            v -= 2**0
        else:
            BV.append(0)
    return BV


def str2int(num_str):
    return int(num_str, 16)


def parse_dataset(x_, y_, y_soft):
    t = 50
    x = []
    y = []
    l_out = []
    y_soft = list(y_soft)
    for j, r in enumerate(x_):
        x.append(list(map(str2int, r.split(' '))))
        y_label = [0]*len(list(y_soft[j]))
        y_label[y_[j]] = 1

        y_soft_row = [np.e**(t*l/np.mean([abs(_) for _ in y_soft[j]]))/
                      sum([np.e**(t*l2/np.mean([abs(_) for _ in y_soft[j]])) for l2 in y_soft[j]]) for l in y_soft[j]]

        for _ in range(len(list(y_soft[j]))):
            y_label[_] = (y_label[_] + y_soft_row[_])/2
        y.append(y_label)
        l_out.append(y_[j])
    return x, y, l_out


def construct_tree(x_train, y_train, feature_attr, x_test, label_test, saved_name, tree_num=1, mode='train'):
    if mode == 'train':
        clf = SoftTreeClassifier(n_features='all', min_sample_leaf=20)
        clf.fit(x_train, y_train, feature_attr)
        if not os.path.exists(saved_name):
            os.mkdir(saved_name)
        with open(saved_name+f'/tree{tree_num}.pkl', 'wb') as f:
            pickle.dump(clf, f)
        if os.path.exists(saved_name+f'/tree{tree_num}.txt'):
            os.remove(saved_name+f'/tree{tree_num}.txt')
        clf.show_tree(saved_name+f'/tree{tree_num}.txt')
    if mode == 'test':
        with open(saved_name+f'/tree{tree_num}.pkl', 'rb') as f:
            clf = pickle.load(f)
        res = clf.predict(x_test)
        T = 0
        F = 0
        for i, r in enumerate(res):
            if label_test[i] == res[i]:
                T += 1
            else:
                F += 1
        return res, T/(T+F)


def random_forest(x, y, label, train_num, saved_name, tree_num=5, ratio=0.8):
    from multiprocessing import Process, Pool
    p = Pool(tree_num)
    fea_list = []
    for i in range(tree_num):
        ind = random.sample(range(train_num), k=int(train_num*ratio))
        x_train, y_train = x[ind], y[ind]
        ind_f = random.sample(range(x_train.shape[1]), k=int(x_train.shape[1] * 1))
        ind_f.sort()
        x_train = x_train[:,ind_f]
        feature_attr = ['d'] * x_train.shape[1]
        p.apply_async(construct_tree, args=(x_train, y_train, feature_attr, [], [], saved_name, i, 'train'))
        fea_list.append((ind_f, i))
    p.close()
    p.join()
    print('start test')
    x_test = x[train_num:]
    label_test = label[train_num:]
    res = [[] for _ in range(x_test.shape[0])]
    for i in range(tree_num):
        ind_f = fea_list[i][0]
        x_test_ = x_test[:, ind_f]
        predicted_res, _ = construct_tree([], [], [], x_test_, label_test, saved_name, i, 'test')
        for j, r in enumerate(predicted_res):
            res[j].append(r)
    from collections import Counter
    T, N = 0, 0
    for i, r in enumerate(res):
        c = Counter(r)
        if c.most_common(1)[0][0] == label_test[i]:
            T += 1
        else:
            N += 1
    print('random_forest accuracy')
    print(T/(T+N))


def SMF(x, y, label, train_num, saved_name, tree_num=5, thre_w=0.5):
    alpha = []
    x_train, y_train, label_train = x[0:train_num], y[0:train_num], label[0:train_num]
    w = [1 for _ in range(train_num)]
    print('start train')
    for t in range(tree_num):
        # print(w[0:100])
        y_train_ = np.array([w[i]*y_per for i, y_per in enumerate(y_train)])
        x__, y__ = [], []
        for ii, y_ in enumerate(y_train_):
            if w[ii] >= thre_w:
                x__.append(x_train[ii])
                y__.append(y_train_[ii])
        x__, y__ = np.array(x__), np.array(y__)
        feature_attr = ['d'] * x.shape[1]
        construct_tree(x__, y__, feature_attr, [], [], saved_name, t, 'train')
        res, et = construct_tree([], [], [], x_train, label_train, saved_name, t, 'test')

        et = 1 - et
        if et == 0:
            et = 0.00001
        if et > 0.5:
            break

        alpha.append(0.5 * math.log((1 - et) / et))
        for i in range(train_num):
            if res[i] == label_train[i]:
                w[i] *= math.exp(-alpha[t])
            else:
                w[i] *= math.exp(alpha[t])

        w = [ww/sum(w)*train_num for ww in w]

    print('start test')
    x_test = x[train_num:]
    label_test = label[train_num:]
    res = [[] for _ in range(x_test.shape[0])]
    for i in range(tree_num):
        predicted_res, _ = construct_tree([], [], [], x_test, label_test, saved_name, i, 'test')
        for j, r in enumerate(predicted_res):
            res[j].append(r)
    T, N = 0, 0
    TN, FP = 0, 0
    for i, r in enumerate(res):
        c = Counter(r)
        if c.most_common(1)[0][0] == label_test[i]:
            T += 1
            if label_test[i] == 0:
                TN += 1
        else:
            N += 1
            if label_test[i] == 1:
                FP += 1
    print('SMF accuracy')
    print(T/(T+N))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rulename', default='test', type=str, help='saved rule name')
    parser.add_argument('--train_num', default=5000, type=int, help='train number')
    parser.add_argument('--dttype', default='binary', type=str, help='decision tree type')
    parser.add_argument('--ensemble', default='SMF', type=str, help='type of ensemble model')
    parser.add_argument('--target', type=str, help='target type')
    args = parser.parse_args()
    saved_name = args.rulename
    train_num = args.train_num
    dttype = args.dttype
    ensemble = args.ensemble
    target = args.target

    dataset = pd.read_csv(os.path.join('multi_classification.csv'))
    dataset = dataset.values.tolist()
    x, y, label = [], [], []

    for row in dataset:
        if row[0] == 'else':
            y.append([1, 0])
            label.append(0)
            x.append(row[1])
        elif row[0] == target:
            y.append([0, 1])
            label.append(1)
            x.append(row[1])
    random.seed(2020)
    random.shuffle(x)
    random.seed(2020)
    random.shuffle(label)
    random.seed(2020)
    random.shuffle(y)
    print(len(x), len(y), len(label))
    x, y, label = parse_dataset(x, label, y)

    if dttype == 'binary':
        x = [ProduceBinaryInput(v) for v in list(x)]
        feature_attr = ['d'] * 66 * 8
    else:
        feature_attr = ['d'] * 66
    x, y, label, = np.array(x), np.array(y), np.array(label)
    if ensemble == 'RF':
        random_forest(x, y, label, train_num, saved_name)
    elif ensemble == 'SMF':
        SMF(x, y, label, train_num, saved_name)