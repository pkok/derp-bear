"""
Parser for Penn WSJ trees.  

It is basically a dumbed-down version of the S-expression parser provided as
an example of the pyparsing module.  This example is available at:
    http://pyparsing.wikispaces.com/file/view/sexpParser.py
"""
import collections

import pyparsing

# Define punctuation literals
LPAR, RPAR, LBRK, RBRK, LBRC, RBRC = map(pyparsing.Suppress, "()[]{}")

# The symbols a token can contain
token = pyparsing.Word(pyparsing.alphanums + "-./_:;*+=!<>@&`',?%#$\\")

display = LBRK + token + RBRK
string_ = pyparsing.Optional(display) + token

sexp = pyparsing.Forward()
sexpList = pyparsing.Group(LPAR + pyparsing.ZeroOrMore(sexp) + RPAR)
sexp << (string_ | sexpList)

class TOTAL: 
    """Used as a symbolic value in the rule table of probabilistic grammars.
    """
    pass


def get_tree(text_tree):
    """Returns a nested list of strings representing the textual parse tree.

    The tokens are not interpreted.  For example, numerical-valued leaf nodes
    are still represented as strings in the tree.
    
    Args:
        text_tree: a string representation of a single parse tree. These are
            defined by the Penn WSJ database.  A sample input is:
                "(TOP (INTJ (UH damn) (. !)) )"
    
    Returns:
        The parse tree of the input, represented in a list datastructure.  For
        example:
            ['TOP', ['INTJ', ['UH, 'damn'], ['.', '!']]]
    """
    return sexp.parseString(text_tree, parseAll=True).asList()[0]


def parse_tree_file(tree_file):
    """Parse every line of the given file into a nested list of strings.

    This returns a generator of nested lists of strings.  Each element
    represents a single tree from the input file.

    Args:
        tree_file: a file where every line contains an s-expression,
            representing a parse tree.

    Returns: 
        A generator which contains a nested list representation of the
        tree/s-expression which is on each single line of the file.
    """
    for text_tree in tree_file:
        yield get_tree(text_tree)


def deduce_grammar(tree_collection):
    """Extracts the frequency of node transitions.
    
    Args:
        tree_collection: an iterable of syntax trees, such as those outputted
        by get_tree.

    Returns:
        A ``2D'' dictionary, where the first entry represents the starting node, and
        the second key refers to the set of child nodes.  The associated value
        is the frequency of this transition.

        Each starting node entry contains a special entry, which contains the
        total frequency of the starting node.
    """
    queue = list(tree_collection)

    terminal_symbols = []
    nonterminal_symbols = []
    rules = {} #collections.defaultdict(lambda: collections.defaultdict(float))
    start_symbol = queue[0][0]
    while queue:
        node = queue.pop()
        # Skip leafs/terminal nodes
        if len(node) <= 1:
            continue

        node_label = node[0]
        nonterminal_symbols.append(node_label)
        child_labels = []
        if isinstance(node[1], basestring):
            child_labels = node[1]
            terminal_symbols.append(child_labels)
        else:
            for child in node[1:]:
                child_labels.append(child[0])
                queue.append(child)
            child_labels = tuple(child_labels)
        if node_label not in rules:
            rules[node_label] = {TOTAL: 0.0}
        if child_labels not in rules[node_label]:
            rules[node_label][child_labels] = 0
        rules[node_label][child_labels] += 1
        rules[node_label][TOTAL] += 1.0
    for node_label in rules:
        for child_labels in rules[node_label]:
            if child_labels != TOTAL:
                rules[node_label][child_labels] /= rules[node_label][TOTAL]
    grammar = {'terminals': set(terminal_symbols), 
        'nonterminals': set(nonterminal_symbols), 'rules': rules, 
        'start_symbol': start_symbol}
    return grammar


"""Keeps returning only {}... p is never updated. Implementation according to Jurafsky and Martin, but unsure how to initialize p.
def cyk_parser(grammar, tokens):
    p = collections.defaultdict(float)
    pi = collections.defaultdict(float)
    backpointers = {}

    nonterminals = grammar['nonterminals']
    rules = grammar['rules']

    for (index, token) in enumerate(tokens):
        for symbol in nonterminals:
            if token in rules[symbol]:
                pi[index, index, symbol] = rules[symbol][token]

    for j in xrange(1, len(tokens)):
        for i in xrange(len(tokens)-j):
            for k in xrange(j-2):
                for A in nonterminals:
                    for B in nonterminals:
                        for C in nonterminals:
                            prob = pi[i, k, B] * p[i+k, j-k, C] * \
                                rules[A].get((B, C), 0.0)
                            if p[i+k, j-k, C] > 0.0:
                                print 'p[i+k, j-k, C] = %f' % pi[i+k, j-k, C]
                            if prob > 0.0: 
                                print 'prob = %f' % prob
                            if prob > pi[i, j, A]:
                                pi[i, j, A] = prob
                                backpointers[i, j, A] = (k, A, B)
    return backpointers
"""

def cyk_parser(grammar, tokens):
    score = collections.defaultdict(float)
    back = {}
    rules = grammar['rules']
    nonterminals = grammar['nonterminals']
    for index, token in enumerate(tokens):
        for nonterminal in nonterminals:
            if token in rules[nonterminal]:
                score[index, index+1, nonterminal] = rules[nonterminal][token]
        added = True
        while added:
            added = False
            for A in nonterminals:
                for B in nonterminals:
                    if score[index, index+1, B] > 0 and B in rules[A]:
                        prob = rules[A][B] * score[index, index+1, B]
                        if prob > score[index, index+1, A]:
                            score[index, index+1, A] = prob
                            back[index, index+1, A] = B
                            added = True
    for span in xrange(2, len(tokens)):
        for begin in xrange(0, len(tokens) - span):
            end = begin + span
            for split in xrange(begin+1, end-1):
                for A in nonterminals:
                    for B in nonterminals:
                        for C in nonterminals:
                            prob = score[begin, split, B]
                            prob *= score[split, end, C]
                            prob *= rules[A].get((B, C), 0.0)
                            if prob > score[begin, end, A]:
                                score[begin, end, A] = prob
                                back[begin, end, A] = (split, B, C)
                added = True
                while added:
                    added = False
                    for A in nonterminals:
                        for B in nonterminals:
                            prob = rules[A].get((B, ), 0.0)
                            prob *= score[begin, end, B]
                            if prob > score[begin, end, A]:
                                score[begin, end, A] = prob
                                back[begin, end, A] = B
                                added = True
    return score, back
