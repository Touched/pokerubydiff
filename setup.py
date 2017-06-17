from setuptools import setup, find_packages, Extension

elf = Extension('pokerubydiff.elf', sources=['extension/elf.c', 'extension/symbols.c'])

setup(
    name='pokerubydiff',
    version='0.1',
    description='Diffing tools for decompilation',
    packages=find_packages(),
    scripts=['bin/pokerubydiff'],
    ext_modules=[elf],
    install_requires=['libclang-py3', 'watchdog', 'flask', 'flask-socketio'],
    include_package_data=True,
)
