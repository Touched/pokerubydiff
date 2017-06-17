from . import elf

class Symbols:
    def __init__(self, file):
        """
        Create a symbol table from the ELF file
        """

        for symbol in elf.symbols(file):
            print(symbol)
