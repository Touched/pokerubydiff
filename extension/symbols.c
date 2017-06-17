#include <Python.h>
#include <structmember.h>
#include <elf.h>
#include <stdio.h>

extern PyObject *ElfError;

struct Symbol
{
    PyObject_HEAD
    PyObject *name;
    PyObject *value;
    PyObject *size;
    int type;
    int bind;
};

static void Symbol_dealloc(struct Symbol* self)
{
    Py_XDECREF(self->name);
    Py_TYPE(self)->tp_free((PyObject*) self);
}

static PyMemberDef Symbol_members[] = {
    {"name", T_OBJECT_EX, offsetof(struct Symbol, name), READONLY, "The name of the symbol"},
    {"value", T_OBJECT_EX, offsetof(struct Symbol, value), READONLY, "The symbol value"},
    {"size", T_OBJECT_EX, offsetof(struct Symbol, size), READONLY, "The symbol size if known"},
    {"type", T_INT, offsetof(struct Symbol, type), READONLY, "The type of symbol"},
    {"bind", T_INT, offsetof(struct Symbol, bind), READONLY, "The binding of symbol"},
    {NULL}  /* Sentinel */
};

PyTypeObject elf_SymbolType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "elf.Symbol",
    .tp_basicsize = sizeof(struct Symbol),
    .tp_itemsize = 0,
    .tp_dealloc = (destructor) Symbol_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_members = Symbol_members,
};

FILE *load_elf(PyObject *file, Elf32_Ehdr *ehdr)
{
    int fd = PyObject_AsFileDescriptor(file);

    if (fd == 0)
    {
        return NULL;
    }

    FILE *fp = fdopen(fd, "rb");

    if (fread(ehdr, sizeof(Elf32_Ehdr), 1, fp) != 1)
    {
        PyErr_SetString(PyExc_OSError, strerror(errno));
        return NULL;
    }

    if (ehdr->e_ident[EI_MAG0] != ELFMAG0
        || ehdr->e_ident[EI_MAG1] != ELFMAG1
        || ehdr->e_ident[EI_MAG2] != ELFMAG2
        || ehdr->e_ident[EI_MAG3] != ELFMAG3)
    {
        PyErr_SetString(ElfError, "Invalid ELF header");
        return NULL;
    }

    if (ehdr->e_ident[EI_CLASS] != ELFCLASS32)
    {
        PyErr_SetString(ElfError, "Not a 32-bit ELF");
        return NULL;
    }

    if (ehdr->e_ident[EI_DATA] != ELFDATA2LSB)
    {
        PyErr_SetString(ElfError, "Not a little-endian ELF");
        return NULL;
    }

    if (ehdr->e_ident[EI_VERSION] != EV_CURRENT || ehdr->e_version != EV_CURRENT)
    {
        PyErr_SetString(ElfError, "Unsupported ELF version");
        return NULL;
    }

    if (ehdr->e_ident[EI_OSABI] != ELFOSABI_NONE)
    {
        PyErr_SetString(ElfError, "Unsupported ABI");
        return NULL;
    }


    if (ehdr->e_machine != EM_ARM)
    {
        PyErr_SetString(ElfError, "Unsupported architecture");
        return NULL;
    }

    if (!ehdr->e_shoff)
    {
        PyErr_SetString(ElfError, "Failed to find section header");
        return NULL;
    }

    return fp;
}

Elf32_Shdr *load_shdrs(FILE* fp, Elf32_Ehdr *ehdr)
{
    Elf32_Shdr *shdrs = malloc(sizeof(Elf32_Shdr) * ehdr->e_shnum);

    if (!shdrs)
        return NULL;

    if (fseek(fp, ehdr->e_shoff, SEEK_SET))
        return NULL;

    for (int i = 0; i < ehdr->e_shnum; i++)
    {
        if (fread(&shdrs[i], sizeof(Elf32_Shdr), 1, fp) != 1)
            return NULL;
    }

    return shdrs;
}

PyObject *elf_symbols(PyObject *self, PyObject *args)
{
    PyObject *file = NULL;
    PyObject *result = NULL;
    char *strtab = NULL;
    char *syms = NULL;
    Elf32_Shdr *shdrs = NULL;
    FILE *fp = NULL;
    Elf32_Ehdr ehdr;

    struct Symbol *symbol = NULL;
    PyObject* symbols = PyList_New(0);

    if (!symbols)
        goto error;

    if (!PyArg_ParseTuple(args, "O", &file))
        goto error;

    fp = load_elf(file, &ehdr);

    if (!fp)
        goto error;

    shdrs = load_shdrs(fp, &ehdr);

    if (!shdrs)
        goto error;

    // Load the symbols
    for (size_t i = 0; i < ehdr.e_shnum; i++)
    {
        if (shdrs[i].sh_type == SHT_SYMTAB)
        {
            // Load the string table for the symbol table
            uint32_t strndx = shdrs[i].sh_link;
            size_t strtabsize = shdrs[strndx].sh_size;
            strtab = malloc(strtabsize);

            if (!strtab)
                goto error;

            if (fseek(fp, shdrs[strndx].sh_offset, SEEK_SET))
                goto error;

            if (fread(strtab, 1, strtabsize, fp) != strtabsize)
                goto error;

            if (strtab[strtabsize - 1] != '\0')
                strtab[strtabsize - 1] = '\0';

            // Read the section into memory
            size_t symtabsize = shdrs[i].sh_size;
            size_t symnum = symtabsize / shdrs[i].sh_entsize;
            syms = malloc(symtabsize);

            if (!syms)
                goto error;

            if (fseek(fp, shdrs[i].sh_offset, SEEK_SET))
                goto error;

            if (fread(syms, 1, shdrs[i].sh_size, fp) != shdrs[i].sh_size)
                goto error;

            // Build the symbols
            for (size_t j = 0; j < symnum; j++)
            {
                Elf32_Sym *sym = (Elf32_Sym *) syms + j;
                struct Symbol *symbol;

                symbol = PyObject_New(struct Symbol, &elf_SymbolType);

                if (!symbol)
                    goto error;

                symbol->name = PyUnicode_FromString(&strtab[sym->st_name]);
                symbol->value = PyLong_FromLong(sym->st_value);
                symbol->size = PyLong_FromLong(sym->st_size);
                symbol->type = ELF32_ST_TYPE(sym->st_info);
                symbol->bind = ELF32_ST_BIND(sym->st_info);

                if (!symbol->name || !symbol->value || !symbol->size)
                {
                    Py_XDECREF(symbol->name);
                    Py_XDECREF(symbol->value);
                    Py_XDECREF(symbol->size);
                    goto error;
                }

                PyList_Append(symbols, (PyObject*) symbol);
            }
        }
    }

    return symbols;

error:
    if (errno == ENOMEM)
        result = PyErr_NoMemory();
    else if (errno)
        PyErr_SetString(PyExc_OSError, strerror(errno));

    Py_XDECREF(symbol);
    Py_XDECREF(symbols);

    if (fp)
        fclose(fp);

    if (shdrs)
        free(shdrs);

    if (syms)
        free(syms);

    if (strtab)
        free(strtab);

    return result;
}
