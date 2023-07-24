"""
This file defines span_parse, which takes a string and parses it into a tree which can be put into a LARPTextField.
The tree then has the following important methods:
.raw(): output the source html with all the markup
.render(writer): output pretty html with all the markup resolved. writer is a boolean that affects printing of stnotes.
.mark_unresolved_keywords(keywords): Search for the given GenderizedKeyword objects in the text,
    and flag them for correction
"""

import re
import garhdony_app.utils as utils
from django.db.models import get_model
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
import logging
import HTMLParser
html_parser = HTMLParser.HTMLParser()
logger = logging.getLogger(__name__)

############################################################
####################### Little Utils #######################
############################################################

class ProblemLogger():
    """
    Basically just a wrapper for the global variable 'had_problem'
    which records whether span_parser had a problem.
    """
    def __init__(self):
        self.had_problem = False
        self.problems = []

    def reset(self):
        self.had_problem = False
        self.problems = []

    def log(self, string):
        """
        For badly formed string,s we want to not ethe problem, but don't want to actually raise an error
        Since badly formed LARPstrings might actually arise in the wild.
        """
        self.had_problem = True
        self.problems+=[string]
        logger.debug("SPAN PARSE PROBLEM: "+string)

the_problem_logger = ProblemLogger()

class InvalidGenderSwitch(Exception):
    pass

class MalformedLarpStringException(Exception):
    pass

def make_regex(keywords):
    """
    Takes a list of GenderizedKeyword objects
    And makes a regex that searches for all matches to any of them ignoring case.
    So if keywords are [he/she, his/her], it will match "He", "her", "his", etc.
    """
    expr = '('+utils.regex_join([k.regex for k in keywords])+')'
    return re.compile(expr, re.IGNORECASE)

def add_tag(string, open, close):
    """
    Adds html tag formatting to arbitrary string.

    If everything is simple, surrounds string with open/close tags. But string might have tags, and might be the middle
    of a longer string, so the tags might be imbalanced.
    If string has tags in it, then we wrap every text node in string with open/close.
    So e.g. add_tag("text <br> stuff </i> <p> other stuff</p> more", "<b>","</b>") is:
    <b>text </b><br><b> stuff </b></i><b> </b><p><b> other stuff</b></p><b> more</b>
    """
    def recurse(so_far, split_left):
        if split_left == []:
            return so_far
        tag = split_left.pop(0)
        text = split_left.pop(0)
        if text=="":
            return recurse(so_far+tag, split_left)
        else:
            return recurse(so_far+tag+open+text+close, split_left)
    split_string = re.split("(<.+?>)", string)
    split_string.insert(0,"") #Add an empty tag at the beginning to match the first bit of text.
    return recurse("",split_string)


############################################################
######################## Span Parse ########################
############################################################

def span_parse(string):
    """
    This is the main function, that takes an html string and returns a tree of nodes
    It ignores all tags other than spans, since our markup is all spans.

    It tries to be super robust, since the database could wind up with all sorts of junk in it.

    bits_left is a list of things that are either:
        * regular text that wasn't part of a span tag
        * "/" or "" indicating how the span tag started (<span>="", </span>="/")
        * the list of attributes of a span tag (will be empty for closing tags)

        So it goes:
            A <span attrs1> B </span> C <span attrs2> D <span attrs3> E </span> F </span>
        becomes:
            ["A", "", attrs1, "B", "/", "", "C", "", attrs2, "D", "", attrs3, "E", "/", "", "F", "/", ""]


    open_nodes is a list of Nodes which we've begun but haven't found a closing tag for yet.
    expecting_flag: because of the period-3 structure of bits_left,
                    we know if the next bit is text or a flag ("" or "/").
                    this should never get called if the next bit is an attrs,
                    since that got read with the previous flag.
    """

    ''' This is for timing-debugging.
    time1=0
    time2=0
    time3=0
    popping_duration = 0
    first_third_time_breakdown = [0,0,0]
    second_third_time_breakdown = [0,0,0]
    last_third_time_breakdown = [0,0,0]
    '''

    the_problem_logger.reset() # Don't want to be remembering problems from old runs.

    began_time = datetime.now()

    bits_left_backwards = re.split("<(/?) *span *([^>]*)>", string)
    bits_left_backwards.reverse()
    # logger.debug("Bits Left: "+str(bits_left_backwards))
    open_nodes = [SpanRootNode()]
    expecting_flag = False

    #total_num_bits = len(bits_left_backwards)
    #split_time = datetime.now()
    while len(bits_left_backwards)>0:

        '''
        This chunk was used for timing. It now seems not to be doing anything inefficient,
        and the timing itself was on the same timescale as the actual work.
        if total_num_bits>1000:
             numleft = len(bits_left_backwards)
             if numleft==2*int(total_num_bits/3):
                 first_third_time = (datetime.now()-began_time).total_seconds()*1000
                 logger.debug("First third done: "+str((datetime.now()-began_time).total_seconds()*1000))
                 first_third_time_breakdown = [time1, time2, time3]
                 logger.debug("Times were: "+str(first_third_time_breakdown))
                 logger.debug("Popping_time: "+str(popping_duration))
             if numleft==int(total_num_bits/3):
                 second_third_time = (datetime.now()-began_time).total_seconds()*1000
                 logger.debug("Second third done: "+str(second_third_time))
                 second_third_time_breakdown = [time1, time2, time3]
                 logger.debug("Times were: "+str([x-y for x,y in zip(second_third_time_breakdown, first_third_time_breakdown)]))
                 logger.debug("Popping_time: "+str(popping_duration))
             if numleft==1:
                 last_third_time = (datetime.now()-began_time).total_seconds()*1000
                 logger.debug("Last third done: "+str(last_third_time))
                 last_third_time_breakdown = [time1, time2, time3]
                 logger.debug("Times were: "+str([x-y for x,y in zip(last_third_time_breakdown, second_third_time_breakdown)]))
                 logger.debug("Popping_time: "+str(popping_duration))
        '''

        #bit_left_start_time = datetime.now()
        bit = bits_left_backwards.pop()
        #popping_time = datetime.now()
        #popping_duration += (popping_time-bit_left_start_time).total_seconds()*1000
        if not expecting_flag:
            # bit is text, so add it as a child of the lowest-level open node.
            if bit!='':
                try:
                    open_nodes[-1].add(TextNode(bit))
                except IndexError:
                    # There are not open nodes. We will just not add the bit at all.
                    the_problem_logger.log("No open nodes when adding TextNode!")
            #time1+=(datetime.now()-popping_time).total_seconds()*1000
        else:
            # bit is a flag, either "" or "/".
            # First get the next bit, which is either the attrs or "", depending on whether this tag opened or closed.
            try:
                other_regex_arg = bits_left_backwards.pop()
            except:
                # Somehow there are no more bits left
                other_regex_arg = ""
                the_problem_logger.log("incorrect number of bits: tag had nothing after it.")
            bit = bit.strip()
            if bit == '':
                # bit comes from <span>, starting a new node.

                # Construct the attrs from other_regex_arg
                # TODO: this fails if there are quotes inside the quotes, like "class='stupid' blah".
                # It will parse correctly, but it will forget what kind of quotes were on the outside
                # and so might put the wrong ones when redisplaying.
                args_list = re.findall(r"\b(\S+?)=(?P<quote>['\"])(.*?)(?P=quote)", other_regex_arg)
                attrs={k:v for k,q,v in args_list}

                # This is where lots of magic is, in MakeSpanNode
                # MakeSpanNode makes a node of the appropriate type depending on the data-larp-action
                # And applies the dict of attrs.
                current_node = MakeSpanNode(attrs)
                # Then add it as a child to the lowest-level open node,
                # and also add it as the new lowest-level open node.
                try:
                    open_nodes[-1].add(current_node)
                    open_nodes.append(current_node)
                except IndexError:
                    the_problem_logger.log("No open nodes when adding span node!")
                #time2+=(datetime.now()-popping_time).total_seconds()*1000
            elif bit =='/':
                # bit is from '</span>'
                if len(open_nodes)==1:
                    # If there's only one open node, then it's the RootNode,
                    # which was artificial and should not be closed by </span> in the string.
                    # We will ignore it and just not close anything.
                    the_problem_logger.log("Mismatched flags in middle")
                if other_regex_arg != '':
                    # </span> should always produce "/", "", since you should never have </span class=''>
                    # We'll log the problem and then ignore it.
                    the_problem_logger.log("argument to </span>?: %s" % other_regex_arg)

                # Close off the last open node
                # done_parsing is any __init__ type stuff that the node wants to do after it's got all its children.
                try:
                    open_nodes[-1].done_parsing()
                    open_nodes = open_nodes[0:-1]
                except IndexError:
                    the_problem_logger.log("No open nodes when finishing span node!")
                #time3+=(datetime.now()-popping_time).total_seconds()*1000
            else:
                # Dunno how you got here; bit must not have been '' or '/' when you were expecting a flag.
                the_problem_logger.log("Strange consistency problem. Received '" + bit + "' when expecting <span> flag")
        expecting_flag = not expecting_flag

    time = ((datetime.now() - began_time).total_seconds())*1000
    if time > 1:
        logger.debug(str(datetime.now())+": Done span_parse; took " + str(time) + " milliseconds")#, of which "+ str((split_time-began_time).total_seconds()*1000) + " were splitting/reversing and "+str(popping_duration)+" were popping.")
        #logger.debug("Times were: "+str([time1, time2, time3]))

    # End while loop; now len(bits_left)==0
    # The Root Nodes is still open, since it didn't come from an actual tag.
    # So open_nodes should be a list of one entry, namely the root.
    if len(open_nodes)>1:

        # There are still open nodes. We'll just close them all now, at the end.
        the_problem_logger.log("Mismatched flags at end")
        [node.done_parsing() for node in open_nodes]
    elif len(open_nodes)==0:
        # Panic and return the original thing as a singel text node.
        the_problem_logger.log("Lost Root Node!")
        root = SpanRootNode()
        theTextNode = TextNode(string)
        root.append(theTextNode)
    else:
        root = open_nodes[0]
    if not isinstance(root, SpanRootNode):
        the_problem_logger.log("Last node isn't root!")
        new_root = SpanRootNode()
        new_root.append(root)
        return new_root

    return root, the_problem_logger.problems



#############################################################
####################### Generic Nodes #######################
#############################################################


class Node(object):
    """
    The main class of our tree.
    First of all, it's a tree, so it has a pointer to a parent node.
    Also, it knows how to display itself in two ways:
        raw(): the raw text, for the editor and the database
        render(writer): for players and non-editing writers (boolean argument tells which).
    """
    def __init__(self):
        self.parent = None
    def render(self, writer=False):
        '''For displaying to players and in non-edit mode'''
        raise NotImplementedError('Node did not override render.')
    def raw(self):
        '''For sending to the editor for edit mode, and for storing in the database.'''
        raise NotImplementedError('Node did not override raw.')
    def cleanup_temporary_markup(self):
        '''Remove things like merge crossouts.'''
        pass
    def done_parsing(self):
        '''Any processing that has to be done after all children are added.'''
        pass
    def regex_replace(self, regex, replacement):
        pass
    def mark_unresolved_keywords(self, keywords, regex):
        """
        For validating forms.
        This is the heart of the gender-problem-catcher; each node calls mark_unresolved_keywords.
        The argument keywords is a list of GenderizedKeyword objects to match against.
        Regex is a regex constructed at the beginning which matches any of the keywords.
        Generally, this should scan the text (for TextNodes) and iterate to children for non-leaf Nodes.
        For some nodes this expands them into bigger, more complicated nodes like BrokenGenderNodes.
        Returns True if there were any unresolved keywords.
        """
        return False
    def split(self, new_nodes):
        """Replace this node with the list new_nodes."""
        parent = self.parent
        my_index = parent.children.index(self)
        earlier_siblings = parent.children[:my_index]
        later_siblings = parent.children[my_index+1:]
        parent.children = earlier_siblings + new_nodes + later_siblings
        for node in new_nodes:
            node.parent = parent

class TextNode(Node):
    """
    The simplest Node, which just contains fixed text.
    This does all the work of looking for new gender switches in mark_unresolved_keywords
    """
    def __init__(self, text):
        super(TextNode, self).__init__()
        self.text = text
    def raw(self):
        return self.text
    def render(self, writer=False):
        # For rendering in non-edit mode, Remove any contentEditable flags.
        regex = r"contentEditable=\w*"
        cleaned = re.sub(regex,'',self.text, flags=re.I)
        # Also render 1 space after every period.
        regex = r"\.( |&nbsp;)( |&nbsp;)"
        cleaned = re.sub(regex,'. ',self.text, flags=re.I)
        return cleaned # match contenteditable=[], ignoring case.
    def __repr__(self):
        return "[T: " + self.text + "]"
    def unescape_html(self):
        self.text = html_parser.unescape(self.text)
    def mark_unresolved_keywords(self, keywords, regex):
        """
        Check if any text in here matches keywords.
        """
        split_text = re.split(regex, self.text) # re.split returns a list [filler, match, filler, match, filler]

        if len(split_text)==1:
            # It's all one big filler, so didn't match anything, so there's no problems.
            return False
        else:
            # the zeroth and all even entries in the split list are regular text; the odd entries matched the regex and are thus keywords

            # List comprehensions are great .... but not for understanding.
            # This goes through the entries in split_text that are not ''.
            # For each one it gives [problems?, newNode]
            # If n is even they are filler, so there was no problem and we make a TextNode out of them.
            # If n is odd they are a match, so we make a newMaybeBrokenGenderSwitchNode out of them.
            # That function takes some text and the list of keywords and decides if it can resolve it on its own
            # And makes a GenderSwitchNode or BrokenGenderSwitchNode as appropriate.
            # It returns [problems? newNode] as we need.
            nodes_and_problems = [[False, TextNode(split_text[n])] if n%2==0 else newMaybeBrokenGenderSwitchNode(split_text[n], keywords) for n in range(len(split_text)) if split_text[n]!='']

            # Then we unzip that list we had into just the list of nodes.
            new_nodes = [lst[1] for lst in nodes_and_problems]

            # And see if there were any problems.
            problem = any([lst[0] for lst in nodes_and_problems])

            # Replace this big TextNode with the list of new ones.
            self.split(new_nodes)

            #return whether there were any problems.
            return problem
    def regex_replace(self, regex, replacement):
        re.sub(regex, replacement, self.text)


class SpanNode(Node):
    """A span. has a dict of attrs like {'class':'some_class', 'data-stuff':'stuff'} and a list of children nodes"""
    def __init__(self, attrs):
        super(SpanNode, self).__init__()
        self.children = []
        self.attrs = attrs

    def add(self, node):
        self.children.append(node)
        node.parent = self
        return node

    def span_tagify(self, inside, removeEditable=False):
        """
        adds this node's span tag (with all attrs) around the string inside.
        If removeEditable, then it will not put contentEditable.
        """
        attrs_lst = [k+"='"+self.attrs[k]+"'" for k in self.attrs if ((not removeEditable) or k.strip().lower()!='contenteditable')] # TODO: use build_attrs or some other built in thing that will do more processing here?
        return "<span "+" ".join(attrs_lst) + ">" + inside + "</span>"

    def raw(self, tagify = True):
        """
        Output my children's raws concatenated.
        With my tag around it (or not, if tagify is false)
        """
        string = "".join([n.raw() for n in self.children])
        if tagify:
            string = self.span_tagify(string)
        return string

    def render(self, tagify = True, writer=False):
        """
        Output my children's renders concatenated.
        With my tag around it (or not, if tagify is false, as for the RootNode)
        """
        string = "".join([n.render(writer=writer) for n in self.children])
        if tagify:
            string = self.span_tagify(string, removeEditable=True)
        return string

    def cleanup_temporary_markup(self):
        """Remove things like merge crossouts. Just passes it on to its children."""
        for child in self.children:
            child.cleanup_temporary_markup()

    def mark_unresolved_keywords(self, *args):
        """Ask all my children to resolve, and then return whether any of them had a problem."""
        children_resolved = [c.mark_unresolved_keywords(*args) for c in self.children]
        return any(children_resolved)

    def __repr__(self):
        return "[S: " + ','.join([str(n) for n in self.children]) + "]"

    def regex_replace(self, regex, replacement):
        [child.regex_replace(regex, replacement) for child in self.children]

class SpanRootNode(SpanNode):
    """A node that's not particularly special except that it should never tagify, and has no attrs."""
    def __init__(self):
        super(SpanRootNode, self).__init__({})
        self.resolved = False
    def raw(self):
        return super(SpanRootNode, self).raw(False)
    def render(self, writer=False):
        return super(SpanRootNode, self).render(tagify=False, writer=writer)
    def mark_unresolved_keywords(self, keywords):
        return super(SpanRootNode, self).mark_unresolved_keywords(keywords, make_regex(keywords))

##############################################################
######################## MakeSpanNode ########################
##############################################################

def node_class(data_larp_action_attribute):
    larp_action_nodes = {
        # This is the dictionary that MakeSpanNode uses to decide what Node class to make based
        # on the data-larp-action attribute of a given span in the input string.
        # All these classes are defined below.
        'remove-label':RemoveTagNode,
        'remove': RemoveNode,
        'unescape': UnescapeNode,
        'temporary-ignore': TemporaryIgnoreNode,
        'gender-switch': GenderSwitchNode,
        'gender-static': GenderStaticNode,
        'alt-gender':GenderAlternateNode,
        'broken-gender-switch':BrokenGenderSwitchNode,
        'alt-possibility':AltPossibilityNode,
        'writers-bubble':WritersNode, #Not used, but worth supporting.
        'stnote':WritersNode,
        'todo':WritersNode,
        'gender': ComplexGenderSwitchNode,
        'hidden':HiddenNode,
        'writers-bubble-inner':WritersBubbleInnerNode
    }
    return larp_action_nodes[data_larp_action_attribute]

def MakeSpanNode(attrs):
    """
    This is used by span_parse to make a SpanNode of the appropriate type
    out of a given string based on the data-larp-action attribute.
    """
    if 'data-larp-action' in attrs:
        try:
            node= node_class(attrs['data-larp-action'])(attrs)
            return node
        except InvalidGenderSwitch:
            # This gets raised if a gender switch didn't get a character or keyword that it recognizes.
            # TODO: Not sure if it should really try to make a normal brokengenderswitch. Probably it should do something more panicky.
            the_problem_logger.log("Broken data-larp-action: "+attrs['data-larp-action'])
            return BrokenGenderSwitchNode(attrs)
        except KeyError:
            the_problem_logger.log("Invalid data-larp-action: "+attrs['data-larp-action'])
            return SpanNode(attrs)
    else:
        return SpanNode(attrs)

##############################################################
################## Simple LARP markup Nodes ##################
##############################################################

class LarpActionNode(SpanNode):
    """All nodes that are our special markup should be one of these."""
    def __init__(self, attrs, resolved=True):
        """Resolved decides whether the mark_unresolved_keywords should look inside this span or not."""
        super(LarpActionNode, self).__init__(attrs)
        self.resolved = resolved

    def mark_unresolved_keywords(self, *args):
        if self.resolved:
            return False
        else:
            return super(LarpActionNode, self).mark_unresolved_keywords(*args)

    def render(self, tagify=False, writer=False):
        """
        By default tagify is False (hide the span tag markup)
        Because players don't want to see our gender-switches and stnotes.
        """
        return super(LarpActionNode, self).render(tagify, writer)

class RemoveTagNode(SpanNode):
    """
    This is data-larp-action:'remove'
    It's for temporary things like merging markup and the tag gets removed immediately.
    """
    def cleanup_temporary_markup(self):
        """Replace it with its children."""
        super(RemoveTagNode, self).cleanup_temporary_markup()
        self.split(self.children)


class RemoveNode(SpanNode):
    """
    This is data-larp-action:'remove'
    It's for temporary things like merging markup and gets removed immediately.
    """
    def cleanup_temporary_markup(self):
        """Delete it."""
        self.split([])

class UnescapeNode(SpanNode):
    """
    This is data-larp-action:'unescape'
    It's for merge-view, which displays to the user fully escaped.
    The view puts this tag around the whole thing, and this tags job is to unescape the html
    After all the merging markup (remove and remove-label) spans are gone.
    It assumes that all spans inside it are remove-tags.
    So after running cleanup, there are no span children left.
    """
    def cleanup_temporary_markup(self):
        super(UnescapeNode, self).cleanup_temporary_markup()
        for child in self.children:
            if isinstance(child, TextNode):
                child.unescape_html()
            else:
                # Shouldn't get here unless there was a span child of the unescape node
                # That was not remove or remove-label
                # If this happens, just let it by without touching it.
                the_problem_logger.log("Unescape Node had a span child!")
        reparsed, problems = span_parse(self.raw()) # Reparse the string to detect the tags. This will have Root and Unescape surrounding the relevant things.
        self.split(reparsed.children[0].children) # Replace this tag with the top-level children (inside the RootNode and the UnescapeNode).

class TemporaryIgnoreNode(RemoveTagNode):
    """
    data-larp-action='temporary-ignore'
    For when users don't want to deal with a gendered word now, but it does need resolving eventually.
    It doesn't look inside itself for unresolved words.
    But removes itself upon saving to the database (inherits from RemoveTagNode).
    """
    def mark_unresolved_keywords(self, *args):
        return False


class GenderStaticNode(LarpActionNode):
    """
    For words that are already resolved but need no other markup (the STATIC gender option).
    They have to be this not TextNodes, so that they don't get flagged again in mark_unresolved_keywords.
    """
    pass

class GenderNode(LarpActionNode):
    """
    A node that changes based on something. Before outputting anything, always update yourself.
    """
    def update(self):
        raise NotImplementedError('GenderNode subclass did not override update.')

    def render(self, tagify=False, writer=False):
        self.update()
        return super(GenderNode, self).render(tagify=tagify, writer=writer)

    def raw(self):
        self.update()
        return super(GenderNode, self).raw()


##############################################################
################# Normal Gender Switch Nodes #################
##############################################################


class GenderSwitchNode(GenderNode):
    """
    The standard {{he-she | Tamas Kazka }} node. It has the keyword and character encoded in the attributes (pks), the
    current actual text as its first child, and the alternate possibility as a GenderAlternateNode as its second child.
    <span contenteditable="false" data-default-gender="M" data-larp-action="gender-switch" data-keyword="121" data-character="80" class="gender-switch">
        he
        <span data-larp-action="alt-gender" class="alt-gender">
            she
        </span>
    </span>

    self.reverse: It can be reversed if it has attribute data-gender-reversed='true'
    self.keyword_bound: determines if it's bound to a particular keyword (e.g. someone's name, or he/she),
            or if it's free text. Free text is not currently implemented in the javascript. 4/15
    self.default_gender: The gender of the text currently in the main area (i.e. not in the alternate span)
    """
    def __init__(self, attrs):
        # If we're constructing one of these from a string, it was presumably made correctly.
        # attrs.update({'data-larp-action':'gender-switch', 'class':'gender-switch'})
        self.keyword_bound =  'data-keyword' in attrs # If we already know what keyword to use, then it's resolved.
        self.reversed = 'data-gender-reversed' in attrs
        if self.reversed:
            # having data-gender-reversed=[anything else] is an error.

            if attrs['data-gender-reversed']!='true':
                the_problem_logger.log("Invalid argument to data-gender-reversed: "+attrs['data-gender-reversed']+"; assuming 'true'")
                attrs['data-gender-reversed'] = 'true'

        super(GenderSwitchNode, self).__init__(attrs, self.keyword_bound) # The argument here becomes self.resolved

        # Find the character and keyword objects from the database:
        try:
            character_id = self.attrs['data-character']
            self.default_gender = self.attrs['data-default-gender']
        except KeyError:
            # TODO: Do something smarter here.
            raise InvalidGenderSwitch("Didn't receive required arguments.")
        try:
            self.character = get_model('garhdony_app', 'Character').objects.get(id=character_id)
            if 'data-keyword' in self.attrs:
                self.keyword =  get_model('garhdony_app', 'GenderizedKeyword').objects.get(id=self.attrs['data-keyword'])
        except ObjectDoesNotExist:
            # TODO: Do something smarter here.
            raise InvalidGenderSwitch("Invalid character or keyword")

        # Construct two children, for the two possible genders. When rendering we'll display the appropriate one.
        self.gender_children = {'M':[],'F':[]}

    def get_alt_gender_node(self):
        """Returns a node whose children are the stuff for the alternate gender"""
        #the last sub-span contains the alternate gender version
        # Overridden by ComplexGenderNode
        alt = self.children[-1]
        if isinstance(alt, GenderAlternateNode):
            return alt
        else:
            the_problem_logger.log("Malformed Gender Switch: Alternate Gender tag not found!")
            # Oh dear. Our gender alternate node is not in the right place!
            # Let's remove this tag.
            self.split(self.children)
            raise MalformedLarpStringException



    def get_current_children(self):
        """Returns a list of children nodes that correspond to the current gender."""
        # children for default gender are all but the last.
        # If the LARPstring is malformed this will be wrong but won't break anything.
        return self.children[:-1]

    def done_parsing(self):
        """After we have children, finish the init-type stuff."""

        try:
            alt_gender_node = self.get_alt_gender_node()
            assert(alt_gender_node.attrs['data-larp-action']=='alt-gender')

            self.gender_children[utils.other_gender(self.default_gender)] = alt_gender_node.children

            self.gender_children[self.default_gender] = self.get_current_children()

        except (MalformedLarpStringException, AssertionError):
            the_problem_logger.log("Malformed GenderSwitch: AltGender no good!")
    def update(self):
        """
        According to GenderNode, this will get called before displaying anything.
        It has to decide which gender to display.
        """
        if self.keyword_bound:
            # In this case I have a keyword that I know.
            # So I'm a simple word and should match case to the current version.
            try:
                case_source = self.children[0].render()
                self.gender_children['M'] = [TextNode(utils.matchcase(case_source, self.keyword.male))]
                self.gender_children['F'] = [TextNode(utils.matchcase(case_source, self.keyword.female))]
            except IndexError:
                # Somehow I have no children. May as well delete me.
                the_problem_logger.log("Empty keyword-bound GenderSwitch")
                self.split([])
                return
        else:
            # Don't need to modify the capitalizaton if I'm not keyword bound.
            pass
        # Figure out what gender to display.
        new = self.character.gender()
        if self.reversed:
            new = utils.other_gender(new)
        if new != self.default_gender or \
                (self.keyword_bound and self.gender_children[self.default_gender] != self.get_current_children()[0].raw()):
            # If it's the other gender, or the keyword text has changed:
            # Set new metadata:
            self.default_gender = new
            self.attrs['data-default-gender'] = self.default_gender

            # And put the appropriate children into self.children and self.alt_gender_node.children:
            self.put_children_in_place()

    def put_children_in_place(self):
        """
        Put current text (self.gender_children[self.default_gender]) in right place
        And put alternate text in right place.
        """
        try:
            alt_node = self.get_alt_gender_node()
            alt_node.children = self.gender_children[utils.other_gender(self.default_gender)]
            main_list = self.gender_children[self.default_gender]
            self.children = main_list + [alt_node]
        except MalformedLarpStringException:
            # If I can't find my alt_gender_node(), just don't do anything.
            # No need to log, because whatever raised the Exception will log it.
            pass

class GenderAlternateNode(LarpActionNode):
    """
    The inside tag of a GenderSwitchNode. Always invisible. Looks like this:
        <span data-larp-action="alt-gender" class="alt-gender">
            //This GenderAlternateNode lists all the possible keywords it could be, each in their own AltPossibilityNode
            <span data-keyword="122" data-larp-action="alt-possibility">her</span>
        </span>
    """
    # Do we want to do things like this where we delete orphans?
    #def done_parsing(self):
    #    if not (isinstance(self.parent, BrokenGenderSwitchNode) or isinstance(self.parent, GenderSwitchNode) or isinstance(self.parent, WritersBubbleInnerNode)):
    #        the_problem_logger.log("Orphaned alt-gender")
    #        if len(self.raw(tagify=False))>100:
    #            # That's a lot of text for an alternate-possibility-node ... try to preserve it.
    #            self.split(self.children)
    #        else:
    #            self.split([])


    def render(self, writer=False):
        return ''

def newGenderAlternateNode():
    """
    Generally Nodes are made by span-parser when it reads a string.
    They call its __init__ function, which automatically puts in the attrs the span actually has in the string.
    But sometimes in the processing of GenderNodes we want to make our own, so that's what this is for.
    """
    # TODO: Make these secondary-init functions be methods inside the appropriate classes
    attrs = {'data-larp-action':'alt-gender', 'class':'alt-gender'}
    return GenderAlternateNode(attrs)


def newGenderSwitchNode(name, gender):
    """ See newGenderAlternateNode """
    attrs = {'class':'gender-switch', 'data-larp-action':'gender-switch', 'contenteditable':'false', 'data-keyword':str(name.id), 'data-default-gender':gender, 'data-character':str(name.character.id)}
    node =  GenderSwitchNode(attrs)
    main = node.add(TextNode(name.resolve(gender)))
    alt = node.add(newGenderAlternateNode())
    alt.add(TextNode(name.resolve(utils.other_gender(gender))))
    node.done_parsing()
    return node

##############################################################
################# Broken Gender Switch Nodes #################
##############################################################

class BrokenGenderSwitchNode(LarpActionNode):
    """
    A keyword that has been flagged for the user to fix.
    It looks like this:
    <span data-default-gender="M" contenteditable="false" data-larp-action="broken-gender-switch" class="broken-gender-switch", data-names='#-#-#'> # Names is present if all matches are names, and lists the character IDs.
        him //What the user put originally goes here.
        <span data-larp-action="alt-gender" class="alt-gender">
            //This GenderAlternateNode lists all the possible keywords it could be, each in their own AltPossibilityNode
            <span data-keyword="122" data-larp-action="alt-possibility">her</span>
        </span>
    </span>
    """
    def __init__(self, attrs, resolved=True):
        # Broken nodes are automatically resolved, since we already know they're broken).
        # TODO: What if the set of keywords changed?
        attrs.update({'data-larp-action':'broken-gender-switch', 'class':'broken-gender-switch'})
        super(BrokenGenderSwitchNode, self).__init__(attrs, resolved)

    def main_child(self):
        """ The text node containing the content the user entered."""
        return self.children[0]
    def alt_child(self):
        """ The GenderAlternateNode containing the list of possible resolutions. """
        alt = self.children[1]
        if not isinstance(alt, GenderAlternateNode):
            the_problem_logger.log("Bad BrokenGenderSwitch; invalid Alternate.")
        return alt

    def mark_unresolved_keywords(self, *args):
        return True
    #    # It should re-resolve itself, in case the set of keywords has changed.

    #    # First remove itself; replace itself with its main child.
    #    self.split([self.main_child()])

    #    #Have the child mark itself up.
    #    self.main_child().mark_unresolved_keywords(*args)

    #    #There is a broken gender-switch node, namely this one.
    #    # TODO: What if the set of keywords changed?
    #    return True


class AltPossibilityNode(LarpActionNode):
    """These go inside GenderAlternateNodes in BrokenGenderSwitches."""
    # Do we want to do things like this?
    #def done_parsing(self):
    #    """Check that we're inside a gender-alternate-node"""
    #    if not isinstance(self.parent, GenderAlternateNode):
    #        the_problem_logger.log("Orphaned AltPossibilityNode")
    #        if len(self.raw(tagify=False))>20:
    #            # That's a lot of text for an alt-possibility-node ... try to preserve it.
    #            self.split(self.children)
    #        else:
    #            self.split([])


def newAltPossibilityNode(word, id):
    """ See newGenderAlternateNode """
    attrs = {'data-larp-action':'alt-possibility', 'data-keyword':id}
    node = AltPossibilityNode(attrs)
    node.add(TextNode(word))
    return node

def newBrokenGenderSwitchNode(gender, word, possible_matches, all_matches_are_names=None):
    """ See newGenderAlternateNode """
    attrs = {'data-larp-action':'broken-gender-switch', 'class':'broken-gender-switch', 'contenteditable':'false', 'data-default-gender':gender}
    if all_matches_are_names: attrs['data-names']='-'.join([str(m['keyword'].character.id)+'.'+str(m['id']) for m in possible_matches])
    # data-names is like '13.15-17.23' if it could be character 13, keyword 15 or character 17, keyword 23

    main_child = TextNode(word)

    alt_child = newGenderAlternateNode()
    for m in possible_matches:
        alt_child.add(newAltPossibilityNode(m['alt'], str(m['id'])))

    node = BrokenGenderSwitchNode(attrs)
    node.add(main_child)
    node.add(alt_child)
    node.done_parsing()
    return node

def newMaybeBrokenGenderSwitchNode(word, keywords):
    """
    Takes a word which matches keywords and makes a new GenderSwitch,
    which may or may not be broken depending on how many possibilities it finds.

    returns [isItBroken?, newNode]
    """
    if word == "":
        the_problem_logger.log("Problem in function newMaybeBrokenGenderSwitchNode; word is empty.")
        return [False, TextNode(word)]
    possible_matches = [k.match(word) for k in keywords if k.match(word) is not None]
    # match(word) returns None if word cannot match this keyword, or:
    # {'gender':'M', 'alt':'she', 'id':'3', 'keyword':keyword-object}
    # if it can be the male version of keyword 3 with alternate version 'she'

    if len(possible_matches)==0:
        the_problem_logger.log("Problem in function newMaybeBrokenGenderSwitchNode; no possible_matches:\n  word: %s\n  keywrods%s"%(word, keywords))
        return [False, TextNode(word)]
        # assert(len(possible_matches)>0) # It had better have a match, or else why was it flagged?

    genders = [m['gender'] for m in possible_matches]
    assert(len(set(genders))==1)        # All matches should have the same gender. TODO: What if they don't?
    my_gender = genders[0]


    if len(possible_matches)==1:
        # Then we can resolve the keyword automatically.
        match = possible_matches[0]
        keyword = match['keyword']
        all_names=False
        if keyword.is_name:
            # It's a name; autoguess the right character.
            # Make a new GenderSwitchNode, and report that it's not broken
            return [False, newGenderSwitchNode(keyword, gender=match['gender'])]
    else:
        all_names = all([hasattr(m['keyword'], 'character') for m in possible_matches])

    # Otherwise assemble a new BrokenGenderSwitchNode
    return [True, newBrokenGenderSwitchNode(my_gender, word, possible_matches, all_names)]


#############################################################
################### Writer's Markup Nodes ###################
#############################################################

class WritersNode(SpanNode):
    """
    A Writer's node is some markup (generally a <span class="something">)
    that should only be displayed to writers.
    So whether we tagify (print the span tag) is determined by whether we're displaying to a writer.

    Currently these are stnote and todo. These two also have some extra internal structure, which looks like this:
    <span data-larp-action="todo" class="writers-bubble todo" contenteditable="false">
        [&nbsp; for looking nice and for letting cursors get everywhere.]
        <span contenteditable="true">
            [text] //This is the actual text.
        </span>
        <span data-larp-action="writers-bubble-inner" class="writers-bubble-inner">
            //This is a WritersBubbleInnerNode, which never displays to non-writers.
            //The comment is somewhere deep in the following table, but the span_parser doesn't need to care about that.
            <table class="todo triangle-pointer" contenteditable="true"><tbody><tr><th colspan="2">To Do</th><th class="button-cell" style="text-align:right"></th></tr><tr><td colspan="3" class="writers-bubble-content">I am a new To Do</td></tr><tr><th>david</th><th width="40"></th><th style="text-align:right">Wed Apr 15 2015</th></tr></tbody></table>
        </span>
        [&nbsp; for looking nice and for letting cursors get everywhere.]
    </span>
    """
    def render(self, writer=False):
        """Only put the tag if user is a writer."""
        if writer:
            return super(WritersNode,self).render(tagify=writer, writer=writer)
        else:
            # Only render the span that actually has the stuff; that's entry 1 (after the placeholder space)
            try:
                span_node = self.children[1]
                assert(isinstance(span_node, SpanNode))
                return span_node.render(tagify=False, writer=False)
            except TypeError:
                # TypeError: span_node's render takes different arguments
                # This could be because it doesn't have the spaces around the content.
                if len(self.children)==2:
                    the_problem_logger.log("Rendering malformed WritersBubble (maybe no surrounding spaces?): "+self.raw())
                    self.children = [TextNode("&nbsp;")]+self.children+[TextNode("&nbsp;")]
                    return self.render(writer)
                else:
                    the_problem_logger.log("Rendering malformed WritersBubble: "+self.raw())
                    return ""
            except AssertionError:
                # My index-1 child wasn't a span somehow.
                # Panic and render empty string.
                the_problem_logger.log("Rendering malformed WritersBubble: "+self.raw())
                return ""
            except IndexError:
                # I didn't have enough children somehow.
                the_problem_logger.log("Rendering WritersBubble without enough children: "+self.raw())
                if len(self.children)==0:
                    self.split([])
                    return ""
                else:
                    return self.children[0]


class WritersBubbleInnerNode(WritersNode):
    """The secret part of an stnote or todo, this never appears to non-writers."""
    def render(self, writer=False):
        if writer:
            naive_version = super(WritersBubbleInnerNode, self).render(writer)
            # The table in naive_version might have contenteditable=true
            split_parts = re.split('''contenteditable=['"]true['"]''', naive_version)
            return 'contenteditable="false"'.join(split_parts)
        else:
            return ""

    def mark_unresolved_keywords(self, *args):
        """Don't look inside inner bubbles for markup, since it would be really awkward to find in the editor."""
        return False

    def done_parsing(self):
        """Check that we're inside a gender-alternate-node"""
        if not (isinstance(self.parent, WritersNode) or isinstance(self.parent, ComplexGenderSwitchNode)):
            # Hopefully nothing bad will come of just ignoring it.
            the_problem_logger.log("Orphaned WritersBubbleInnerNode")



class HiddenNode(WritersNode):
    """
    data-larp-action='hidden'

    This is like a WritersNode, but even writers don't want to see it unless they're editing.
    """
    def render(self, writer=False):
        return ""


############################################################
################### Complex Gender Nodes ###################
############################################################

# These are both WritersNodes and LARPAction Nodes...

class ComplexGenderSwitchNode(GenderSwitchNode):
    def get_alt_gender_node(self):
        """
        It looks like:
        <span complexGenderSwitchNode>
            [placeholder space]
            <span>
                Tex
            </span>
            <span WritersBubbleInner>
                [table-stuff that span-parser treats as text]
                <span AltGender>
                </span>
                [table-stuff that span-parser treats as text]
            </span>
            [placeholder space]
        </span>
        """
        try:
            inner_bubble = self.children[-2]
            return inner_bubble.children[1]
        except (IndexError, AttributeError):
            the_problem_logger.log("Malformed Complex Gender Switch: Alternate Gender tag not found!")
            # Oh dear. Our gender alternate node is not in the right place!
            # Let's remove this tag.
            self.split(self.children)
            raise MalformedLarpStringException

    def main_span(self):
        # Where the stuff for the current gender version lives.
        try:
            span = self.children[1]
            assert(isinstance(span, SpanNode))
            return span
        except AssertionError:
            # My main_children node is in the wrong place, because this thing is a textnode.
            the_problem_logger.log("Complex Gender Switch can't find appropriate children.")
            # Let's not do anything here, since this might be an arbitrarily complicated problem.
            raise MalformedLarpStringException
        except IndexError:
            # I don't have 2 children.
            the_problem_logger.log("Complex Gender Switch with only one child.")
            self.split([self.children])
            raise MalformedLarpStringException


    def put_children_in_place(self):
        try:
            alt_gender_node = self.get_alt_gender_node()
            alt_gender_node.children = self.gender_children[utils.other_gender(self.default_gender)]
            main_children_node = self.main_span()
            main_children_node.children = self.gender_children[self.default_gender]
        except MalformedLarpStringException:
            pass

    def get_current_children(self):
        return self.main_span().children

    def render(self, tagify=False, writer=False):
        # Only render the span tht actually has the stuff; that's entry 1 (after the placeholder space).
        # Otherwise it displays extra spaces.
        self.update() # Need to do this like a good GenderNode
        return self.main_span().render(tagify=False, writer=writer)

