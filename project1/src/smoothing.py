def no_smoothing(grammar, *parameters):
    return grammar

def laplace_smoothing(grammar, *parameters):
    raise NotImplementedError("Laplace smoothing")

def good_turing_smoothing(grammar, *parameters):
    raise NotImplementedError("Good Turing smoothing")

functions = {"none": no_smoothing,
             "laplace": laplace_smoothing,
             "good_turing": good_turing_smoothing}
