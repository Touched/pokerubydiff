import bisect
import operator
from . import elf

ST_FUNCTION = 2

class SymbolLookup:
    def __init__(self, address, symbol):
        start = symbol.value & 0xFFFFFFFE if symbol.type == ST_FUNCTION else symbol.value
        self.disp = address - start
        self.symbol = symbol


class Symbols:
    def __init__(self, file):
        """
        Create a symbol table from the ELF file
        """

        self._by_name = {}
        by_address = []

        for symbol in elf.symbols(file):
            # Exclude THUMB bit
            start = symbol.value & 0xFFFFFFFE if symbol.type == ST_FUNCTION else symbol.value
            end = start + symbol.size

            self._by_name[symbol.name] = symbol
            by_address.append((start, end, symbol))

        # Create parallel arrays, sorted by start address
        self._start_address, self._end_address, self._symbols = zip(*sorted(
            by_address,
            key=operator.itemgetter(0),
        ))

    def lookup_name(self, name, default=None):
        return self._by_name.get(name, default)

    def lookup(self, address, default=None):
        i = bisect.bisect_right(self._start_address, address)

        if i:
            end_address = self._end_address[i - 1]
            symbol = self._symbols[i - 1]

            if symbol.size == 0 or address < end_address:
                return SymbolLookup(address, symbol)

        return default
