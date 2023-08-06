def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

def regex_join(lst):
    """
    Joins a bunch fo regexes with or's ('|'), ignoring any that are the empty string.

    Used for constructing the big regex for searching through LARPStrings to find possible gendered words.
    :param lst: A list of regexes
    :return: a single regex
    """
    return '|'.join([r for r in lst if r != ''])

def matchcase(source, target):
    """
    Tries to match the case of target to source, so for instane if source is "He" and target is "she", returns "She"
    """
    if source.islower():
        return target.lower()
    if source.isupper():
        return target.upper()
    if source.istitle():
        return target.title()
    #If it's capitalized weirdly, return the original
    return target

def remove_duplicates(seq, num=None, idfun=None):
    # order preserving
    if idfun is None:
        def idfun(x): return x
    if num is None:
        num = len(seq)
    seen = {}
    result = []
    for item in seq:
        if len(result)==num: break
        marker = idfun(item)
        if marker in seen: continue
        seen[marker] = 1
        result.append(idfun(item))
    return result

genders = ['M','F']
def other_gender(g):
    if g == 'M':
        return 'F'
    elif g=='F':
        return 'M'
    else:
        raise ValueError("Garhdony is too gender-normative for you")

from diff_match_patch import diff_match_patch
def double_diff(base, version1, version2):
    """
    The double diff of what version1 and version2 each did to base.

    Returns a list of trios, each of which is [v1_operation, v2_operation, text]
    """
    # TODO: Comment this function
    dmp = diff_match_patch()
    rev1 = dmp.diff_compute(base, version1, True, 2)
    rev2 = dmp.diff_compute(base, version2, True, 2)
    res = []

    while len(rev1)>0 and len(rev2)>0:
        (op1, next1) = rev1[0]
        (op2, next2) = rev2[0]
        if op1 == diff_match_patch.DIFF_INSERT:
            if next1 != "":
                res.append([diff_match_patch.DIFF_INSERT, None, next1])
            rev1.pop(0)
            continue
        if op2 == diff_match_patch.DIFF_INSERT:
            if next2 !="":
                res.append([None, diff_match_patch.DIFF_INSERT, next2])
            rev2.pop(0)
            continue

        if len(next1)>len(next2):
            rev2.pop(0)
            rev1[0] = (op1, next1[len(next2):])
            res.append([op1, op2, next2])
        elif len(next2)>len(next1):
            rev2[0] = (op2, next2[len(next1):])
            res.append([op1, op2, next1])
            rev1.pop(0)
        else:
            rev1.pop(0)
            rev2.pop(0)
            res.append([op1, op2, next1])

    rest1 = [(op, None, next) for (op, next) in rev1]
    rest2 = [(None, op, next) for (op, next) in rev2]
    res = res + rest1 + rest2
    return res
