import difflib
import re
import math

JUNK = re.compile(r'^[0-8a-f]+ (.+:)?|@.+', flags=re.IGNORECASE)

def tabs2spaces(line, spaces=8):
    """
    Converts tabs to spaces.
    """

    res = ''
    n = 0
    for c in line:
        if c == '\t':
            next_tab_stop = n + spaces - (n % spaces)
            distance_to_next = next_tab_stop - n
            res += ' ' * distance_to_next
            n = next_tab_stop
        else:
            res += c
            n += 1

    return res


def prepare_line(line):
    return JUNK.sub(lambda x: len(x.group(0)) * '.', tabs2spaces(line))


def prepare_lines(s):
    return [prepare_line(l) for l in s.splitlines(keepends=True)]


def diff(original, modified):
    # TODO: tabs2spaces

    a = prepare_lines(original)
    b = prepare_lines(modified)
    return difflib.HtmlDiff().make_file(a, b)


# return Differ(linejunk, charjunk).compare(a, b)
