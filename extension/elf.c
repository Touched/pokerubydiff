#include <Python.h>

PyObject *ElfError;

PyObject *elf_symbols(PyObject *self, PyObject *args);

extern PyTypeObject elf_SymbolType;

static PyMethodDef ElfMethods[] = {
    {"symbols",  elf_symbols, METH_VARARGS,
     "Get all the symbols from the ELF."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef elfmodule = {
   PyModuleDef_HEAD_INIT,
   "elf",
   NULL,
   -1,
   ElfMethods
};

PyMODINIT_FUNC
PyInit_elf(void)
{
    PyObject *m;

    if (PyType_Ready(&elf_SymbolType) < 0)
        return NULL;

    m = PyModule_Create(&elfmodule);
    if (m == NULL)
        return NULL;

    ElfError = PyErr_NewException("elf.error", NULL, NULL);
    Py_INCREF(ElfError);
    PyModule_AddObject(m, "error", ElfError);

    Py_INCREF(&elf_SymbolType);
    PyModule_AddObject(m, "Symbol", (PyObject *) &elf_SymbolType);

    return m;
}
