import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(_project_root)
sys.path.append('../')
sys.path.append('../../')

import time
import re
from typing import Set, Dict, Optional, List, cast, Tuple

from automata_tools import BuildAutomata, Automata, DFAtoMinimizedDFA, NFAtoDFA, isInstalled, drawGraph, WFA, get_word_to_index
from pydash import uniq

from reverse_regex import reverse_regex

from config import MyLogging
myLogger = MyLogging()

punctuations = [
    ',', '，', ':', '：', '!', '！', '《', '》', '。', '；', '.', '(', ')', '（', '）',
    '|', '?', '"'
]


def padPunctuations(shortString: str):
    # add space to every punctuation
    for punctuation in punctuations:
        shortString = re.sub(f'[{punctuation}]', f' {punctuation} ',
                             shortString)
    return shortString


def tokenizer(input: str):
    inputWithPunctuationsPaddedWithSpace = padPunctuations(input)
    tokens = inputWithPunctuationsPaddedWithSpace.split(' ')
    return [item for item in tokens if item]


IAvailableTransitions = Dict[int, Set[str]]

SymbolWord = 'SymbolWord'
SymbolNumeric = 'SymbolNumeric'
SymbolPunctuation = 'SymbolPunctuation'
SymbolWildcard = 'SymbolWildcard'


def matchTokenInSet(token: Optional[str], acceptTokens: Set[str]):
    if token == None:
        return None
    if token in acceptTokens:
        return SymbolWord
    elif '%' in acceptTokens and token.replace('.', '', 1).isdigit():
        return SymbolNumeric
    elif '&' in acceptTokens and token in punctuations:
        return SymbolPunctuation
    elif '$' in acceptTokens and not token.replace('.', '', 1).isdigit() and token not in punctuations:
        return SymbolWildcard
    return None


def tryConsumeNonWildCard(availableTransitions: IAvailableTransitions,
                          currentToken: Optional[str], currentTokens: List[str]
                          ) -> Optional[Tuple[int, Optional[str], List[str]]]:
    # search available transition in the first pass
    for nextState, pathSet in availableTransitions.items():
        if matchTokenInSet(currentToken, pathSet) == SymbolWord:
            nextToken = currentTokens.pop(0) if len(currentTokens) > 0 else None
            return (nextState, nextToken, currentTokens)
    return None


def tryConsumeWildCard(availableTransitions: IAvailableTransitions,
                       currentToken: Optional[str], currentTokens: List[str]
                       ) -> Optional[Tuple[int, Optional[str], List[str]]]:
    # non-greedy wild card, we only use it when there is no other choice
    for nextState, pathSet in availableTransitions.items():
        if matchTokenInSet(currentToken, pathSet) == SymbolNumeric:
            nextToken = currentTokens.pop(0) if len(currentTokens) > 0 else None
            return (nextState, nextToken, currentTokens)
        elif matchTokenInSet(currentToken, pathSet) == SymbolPunctuation:
            nextToken = currentTokens.pop(0) if len(currentTokens) > 0 else None
            return (nextState, nextToken, currentTokens)
        elif matchTokenInSet(currentToken, pathSet) == SymbolWildcard:
            nextToken = currentTokens.pop(0) if len(currentTokens) > 0 else None
            return (nextState, nextToken, currentTokens)
    return None


def executor(tokens, startState, finalStates,
             transitions: Dict[int, IAvailableTransitions]):
    currentState: int = startState
    currentToken: Optional[str] = tokens.pop(0)
    while currentState not in finalStates:
        availableTransitions = transitions[currentState]
        # count if we have ambiguous situation, since wildcard can make DFA sometimes actually a NFA
        availablePathCount = 0
        for _, pathSet in availableTransitions.items():
            if matchTokenInSet(currentToken, pathSet):
                availablePathCount += 1
        # try consume a non wildcard matcher in rule first
        matchingResult = tryConsumeNonWildCard(transitions[currentState],
                                               currentToken, tokens)
        if matchingResult and matchingResult[0] in finalStates:
            return True
        if availablePathCount > 1 and matchingResult != None:
            # it is ambiguous now
            # try go on, and see if consume a non wildcard matcher is a right choice
            # (currentState, currentToken, tokens) = matchingResult
            if matchingResult[1] == None:
                return False
            initialStateToTry = matchingResult[0]
            tokensToTry = [cast(str, matchingResult[1])] + matchingResult[2]
            if executor(tokensToTry, initialStateToTry, finalStates,
                        transitions):
                return True
            else:
                matchingResult = None
        if matchingResult == None:
            matchingResult = tryConsumeWildCard(transitions[currentState],
                                                currentToken, tokens)
            if matchingResult == None:
                return False  # sadly, no available transition for current token
        (currentState, currentToken, tokens) = matchingResult
    return True


def token2byte(token):
    # token = token.lower()
    if len(token) == 1:
        if token == '$':
            # wildcard
            ans = token
        else:
            # ans = '\\x{:02x}'.format(ord(token))
            ans = '{:02x}'.format(ord(token))
    else:
        # ans = '\\x{}'.format(token)
        ans = '{}'.format(token)
    # ans = '{}_{}'.format(token, ans)
    # print('token to byte', token, ans)
    ans = ans.lower()
    return ans

class NFAFromRegex:
    """
    class for building e-nfa from regular expressions
    """

    stack: List[str] = []
    automata: List[Automata] = []

    starOperator = '*'
    plusOperator = '+'
    questionOperator = '?'
    concatOperator = '.'
    orOperator = '|'
    initOperator = '::e::'
    openingBracket = '('
    closingBracket = ')'
    openingBrace = '{'
    closingBrace = '}'
    openingSquare = '['
    closingSquare = ']'
    maxRepeatTime = 20
    reapeatRange = [0, 0]

    binaryOperators = [orOperator, concatOperator]
    unaryOperators = [starOperator, plusOperator, questionOperator]
    openingBrackets = [openingBracket, openingBrace]
    closingBrackets = [closingBracket, closingBrace]
    allOperators = [
        initOperator
    ] + binaryOperators + unaryOperators + openingBrackets + closingBrackets

    def __init__(self):
        pass

    @staticmethod
    def displayNFA(nfa: Automata):
        nfa.display()

    def buildNFA(self, rule: str, reversed: bool=False) -> Automata:
        language = set()
        self.stack = []
        self.automata = []
        previous = self.initOperator
        # ruleTokens = ruleParser(rule)
        # ruleTokens = rule.split()
        ruleTokens = list(rule)
        myLogger.debug_logger('begin buildNFA')
        myLogger.debug_logger('ruleTokens: {}'.format(ruleTokens))

        if reversed:
            ruleTokens = reverse_regex(ruleTokens)

        index = 0
        while index < len(ruleTokens):
            token = ruleTokens[index]
            # print(index, token)
            if token not in self.allOperators:
                isAnyNumber = False
                if token == '\\':
                    if ruleTokens[index + 1] == 'x':
                        # \x
                        token = ''.join(ruleTokens[index + 2: index + 4])
                        index += 3
                    elif ruleTokens[index + 1] == 'd':
                        # \d
                        isAnyNumber = True
                        token = 'd'
                        curState = self.processAnyNumber()
                        index += 1
                    elif ruleTokens[index + 1] == '(' or ruleTokens[index + 1] == ')':
                        token = '{:02x}'.format(ord(ruleTokens[index + 1]))
                        index += 1
                    else:
                        # \.
                        # token = token2byte(ruleTokens[index + 1])
                        token = '{:02x}'.format(ord(ruleTokens[index + 1]))
                        # token = '2E' if token == '.' else token
                        index += 1
                token_byte = token2byte(token)
                # language.add(token)
                language.add(token_byte)
                # if previous automata is standalong (char or a group or so), we concat current automata with previous one
                if ((previous not in self.allOperators)
                        or previous in [self.closingBracket] +
                        self.unaryOperators):
                    self.addOperatorToStack(self.concatOperator)
                if isAnyNumber:
                    self.automata.append(curState)
                else:
                    
                    # self.automata.append(BuildAutomata.characterStruct(token))
                    self.automata.append(BuildAutomata.characterStruct(token_byte))
            elif token == self.openingBracket:
                # concat current automata with previous one, same as above
                if ((previous not in self.allOperators)
                        or previous in [self.closingBracket] +
                        self.unaryOperators):
                    self.addOperatorToStack(self.concatOperator)
                self.stack.append(token)
            elif token == self.closingBracket:
                if previous in self.binaryOperators:
                    raise BaseException(
                        f"Error processing {token} after {previous}")
                while (1):
                    if len(self.stack) == 0:
                        raise BaseException(
                            f"Error processing {token}. Empty stack")
                    o = self.stack.pop()
                    if o == self.openingBracket:
                        break
                    elif o in self.binaryOperators:
                        self.processOperator(o)
            elif token == self.openingBrace:
                end_pos = index + 1
                while ruleTokens[end_pos] != '}':
                    end_pos += 1
                range_content = ''.join(ruleTokens[index + 1: end_pos])
                range_list = range_content.split(',')
                if len(range_list) > 1:
                    if len(range_list[1]) > 0:
                        #{a,b}
                        self.reapeatRange = [int(range_list[0]), int(range_list[1])]
                    else:
                        # {a,}
                        self.reapeatRange = [int(range_list[0]), self.maxRepeatTime]
                else:
                    # {a}
                    self.reapeatRange = [int(range_list[0]), int(range_list[0])]
                index = end_pos
                continue
            elif token == self.closingBrace:
                # to handle { 0 , 2 } , we get "0" and "2"
                # repeatRangeStart = ruleTokens[index - 3]
                # repeatRangeEnd = ruleTokens[index - 1]
                repeatRangeStart = min(int(self.reapeatRange[0]), self.maxRepeatTime)
                repeatRangeEnd = min(int(self.reapeatRange[1]), self.maxRepeatTime)
                myLogger.debug_logger('repeat range: [{}, {}]'.format(repeatRangeStart, repeatRangeEnd))
                payload = (repeatRangeStart, repeatRangeEnd)
                self.processOperator(self.closingBrace, payload)
                index += 1
                continue
            elif token in self.unaryOperators:
                if previous in self.binaryOperators + self.openingBrackets + self.unaryOperators:
                    raise BaseException(
                        f"Error processing {token} after {previous}")
                self.processOperator(token)
            elif token in self.binaryOperators:
                if previous in self.binaryOperators or previous == self.openingBracket:
                    raise BaseException(
                        f"Error processing {token} after {previous}")
                self.addOperatorToStack(token)
            else:
                raise BaseException(f"Symbol {token} is not allowed")
            previous = token
            index += 1
            # print('token', token)
            # print('stack', self.stack)
            # print('self.automa', self.automata)
            # print('language', language)
            # print()
        while len(self.stack) != 0:
            op = self.stack.pop()
            self.processOperator(op)
        if len(self.automata) > 1:
            # print(self.automata)
            raise BaseException("Regex could not be parsed successfully")
        nfa = self.automata.pop()
        nfa.language = language
        
        # print('self.automa', self.automata)
        # print('language', language)
        return nfa

    def addOperatorToStack(self, char: str):
        while (1):
            if len(self.stack) == 0:
                break
            top = self.stack[len(self.stack) - 1]
            if top == self.openingBracket:
                break
            if top == char or top == self.concatOperator:
                op = self.stack.pop()
                self.processOperator(op)
            else:
                break
        self.stack.append(char)

    def processOperator(self,
                        operator,
                        payload: Optional[Tuple[str, str]] = None):
        if len(self.automata) == 0:
            raise BaseException(
                f"Error processing operator {operator}. Stack is empty")
        if operator == self.starOperator:
            a = self.automata.pop()
            self.automata.append(BuildAutomata.starStruct(a))
        elif operator == self.questionOperator:
            a = self.automata.pop()
            self.automata.append(BuildAutomata.skipStruct(a))
        elif operator == self.plusOperator:
            a = self.automata.pop()
            moreA = BuildAutomata.starStruct(a)
            self.automata.append(BuildAutomata.concatenationStruct(a, moreA))
        elif operator == self.closingBrace:
            if payload == None:
                raise BaseException(
                    f"Error processing operator {operator}. payload is None")
            repeatRangeStart, repeatRangeEnd = payload
            # magic code
            repeatRangeStart = max(repeatRangeStart, 2)
            repeatRangeEnd = max(repeatRangeEnd, repeatRangeStart)
            automataToRepeat = self.automata.pop()
            myLogger.debug_logger('repeatRange:[{}, {}]'.format(repeatRangeStart, repeatRangeEnd))
            repeatedAutomata = BuildAutomata.repeatRangeStruct(
                automataToRepeat, int(repeatRangeStart), int(repeatRangeEnd))
            self.automata.append(repeatedAutomata)
        elif operator in self.binaryOperators:
            if len(self.automata) < 2:
                raise BaseException(
                    f"Error processing operator {operator}. Inadequate operands"
                )
            a = self.automata.pop()
            b = self.automata.pop()
            if operator == self.orOperator:
                self.automata.append(BuildAutomata.unionStruct(b, a))
            elif operator == self.concatOperator:
                self.automata.append(BuildAutomata.concatenationStruct(b, a))
    def processSquareRange(self):
        pass
    def processAnyNumber(self, ruleTokens, index):
        # process \d
        # ans = BuildAutomata.characterStruct('0')
        # for num in range(1, 10):
        #     cur = BuildAutomata.characterStruct(str(num))
        #     ans = BuildAutomata.unionStruct(ans, cur)
        # return ans
        add_tokens = f'({"|".join([str(num) for num in range(0, 10)])})'
        print(add_tokens)


def mergeWordToIndex(listOfWordToIndex: List[Dict[str, int]]) -> Tuple[Dict[int, str], Dict[str, int]]:
    vocabList = []
    for wordToIndex in listOfWordToIndex:
        vocabList += wordToIndex.keys()
    vocabList = uniq(vocabList)
    wordToIndex = {vocab: idx for idx, vocab in enumerate(vocabList)}
    indexToWord = {idx: vocab for idx, vocab in enumerate(vocabList)}

    return indexToWord, wordToIndex