import pandas as pd
from automata_tools import get_word_to_index

def load_dataset():
    DATASET_PATH = 'YourDatasetPath'
    totalDF = pd.read_csv(DATASET_PATH).reset_index(drop=True)
    used_cols = ['self', 'else']
    totalDF = totalDF[totalDF['class'].isin(used_cols)]
    totalDF.reset_index(drop=True, inplace=True)
    tmp = totalDF.iloc[0, :]

    train_size, valid_size, test_size = 0.7, 0.1, 0.2
    totalDF = totalDF.sample(frac=1.0, random_state=2)  # shaffle
    totalDF.iloc[0, :] = tmp
    total_len = totalDF.shape[0]

    trainDf = totalDF.iloc[:int(total_len * train_size), :].reset_index(drop=True)
    trainDf['mode'] = 'train'
    validDf = totalDF.iloc[int(total_len * train_size): int(total_len * (train_size + valid_size)), :].reset_index(
        drop=True)
    validDf['mode'] = 'valid'
    testDf = totalDF.iloc[
             int(total_len * (train_size + valid_size)): int(total_len * (train_size + valid_size + test_size)),
             :].reset_index(drop=True)
    testDf['mode'] = 'test'
    df = pd.concat([trainDf, validDf, testDf], ignore_index=True)
    # indexToWord, wordToIndex = get_word_to_index(map(lambda text: tokenizer(text) + text.split(' '), list(df['text'])))
    indexToWord, wordToIndex = get_word_to_index(map(lambda text: text.split(' '), list(df['text'])))
    return {
        'rules': [],
        'data': df,
        'indexToWord': indexToWord,
        'wordToIndex': wordToIndex
    }