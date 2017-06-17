import os.path
import glob
from clang.cindex import Index, CursorKind

def location_to_function_name(filename, location):
    """
    Return the name of the function at `location` in the C file `filename`.
    `location` is a tuple containing the line number and column. If there is no function
    at this point, return None.
    """

    index = Index.create()
    tu = index.parse(None, [filename])

    def find_node(node, depth=0):
        start = (node.extent.start.line, node.extent.start.offset)
        end = (node.extent.end.line, node.extent.end.offset)

        if start < location < end:
            if node.kind == CursorKind.FUNCTION_DECL:
                return node
            else:
                for c in node.get_children():
                    result = find_node(c, depth + 1)
                    if result: return result

    node = find_node(tu.cursor)
    if node: return node.spelling


def find_location_of_change(filename, file_cache):
    """
    Given a dictionary mapping of { filename: file_content }, and a filename,
    find the line, column tuple of the change.
    """

    try:
        original = file_cache[filename]
    except KeyError:
        return None

    with open(filename) as modified:
        line = 0
        column = 1

        for a, b in zip(original, modified.read()):
            if a != b:
                return (line, column)

            if a == '\n':
                line += 1
                column = 1
            else:
                column += 1


def cache_files(directory, pattern):
    """
    Create the file cache for find_location_of_change.
    """

    cache = {}

    # TODO: Support Python < 3.5
    for filename in glob.glob(os.path.join(directory, pattern), recursive=True):
        with open(filename) as f:
            cache[filename] = f.read()

    return cache


def find_changed_function_name(filename, file_cache):
    """
    Get the name of the first changed function in C file `filename` or None on failure.
    """
    location = find_location_of_change(filename, file_cache)
    if location: return location_to_function_name(filename, location)
