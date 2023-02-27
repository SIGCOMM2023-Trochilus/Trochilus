# Trochilus
Regular Expression in the Data Plane

## Code Architecture
```
-- RE Modelization
   -- create_logic_mat_bias.py
   -- create_automata.py
   -- decompose_automata.py
   -- dfa_from_rule.py
   -- fsa_to_tensor.py
   -- load_dataset.py
   -- RE.py
   -- config.py
   -- reverse_regex.py
   -- RE2DFA.py
   -- process_snort_rule.py
   -- MinDFA.py
   -- run_dfa2brnn.py
   -- train_brnn.py
   -- val.py
   -- models
      -- BRNN.py
      -- BRNN_O.py
      -- Baseline.py
      -- net.py
   -- utils
      -- data.py
      -- utils.py
-- SSKD
  -- DecisionNode.py
  -- SSPKD.py
  -- SoftTree.py
  -- utils.py
-- P4
   -- common
      -- headers.p4
      -- utils.p4
  -- Trochilus.p4
-- README.md
-- requirements.txt
```




## Run Code
### RE Modelization
#### Run DFA extraction
Download Snort rules and unzip them to "./data/snort/rules/".
```
https://rules.emergingthreats.net/OPEN_download_instructions.html
```
Process Snort rules.
```
python3 process_snort_rule.py
```
Create m-DFA based on Snort rules.
```
python3 RE2DFA.py --dataset "category_name"
```
Merge all category automaton to one automaton.
```
python3 merge_automaton.py
```
#### Run DFA Modelization
Train a BRNN.
```
# to train a BRNN based on "category_name", see more parameters in our source code.
python3 run_dfa2BRNN --dataset "category_name" --model_type Onehot
```
Train other baselines (e.g., LSTM).
```
# to train a LSTM based on "category_name", see more parameters in our source code.
python3 run_dfa2BRNN --dataset "category_name" --model_type MarryUp -rnn LSTM
```

### Run SSKD
This code is a sample code for training and testing SMF.
Besides, we provide a sample dataset (multi_classification.csv) for testing.
Note that the sample dataset only includes hard labeled data. 
If you want to test the complete SSKD process, you need to run RNN first to get the soft labels.
```
# to train SMF with labeled data for certain target
python3 SSKD --target "target type"
```

### Run P4 Program

compile P4 code: Trochilus.p4 under your p4 path

```
cd $SDE/pkgsrc/p4-build
./configure --prefix=$SDE_INSTALL --with-tofino --with-bf-runtime P4_NAME=Trochilus P4_PATH= <your p4 path> P4_VERSION=p4-16 P4C=p4c --enable-thrift
make
make install
```

run

```
cd $SDE
./run_switchd.sh -p Trochilus
```



