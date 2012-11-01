"""
Parser for Penn WSJ trees.  

It is basically a dumbed-down version of the S-expression parser provided as
an example of the pyparsing module.  This example is available at:
    http://pyparsing.wikispaces.com/file/view/sexpParser.py
"""
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

TOTAL = float('NaN')

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

def extract_rules(tree_collection):
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
    pcfg = {}
    queue = list(tree_collection)
    while queue:
        node = queue.pop()
        # Skip leafs/terminal nodes
        if len(node) <= 1:
            continue

        node_label = node[0]
        child_labels = []
        for child in node[1:]:
            if isinstance(child, basestring):
                child_labels.append(child)
            else:
                child_labels.append(child[0])
                queue.append(child)
        child_labels = tuple(child_labels)
        if node_label not in pcfg:
            pcfg[node_label] = {TOTAL: 0}
        if child_labels not in pcfg[node_label]:
            pcfg[node_label][child_labels] = 0
        pcfg[node_label][child_labels] += 1
        pcfg[node_label][TOTAL] += 1
        # TODO post-process frequencies?
    return pcfg
