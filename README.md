# pokerubydiff

# Requirements

- Python 3.6
- Node.js and NPM (for building static assets)
- Clang

# Installation

Clone the repo and build the web client:

First, install the dependencies - `yarn` (recommended) or `npm` is required.

```
yarn install
```

or

```
npm install
```

After this has completed, package the static assets:

```
npm run build
```

Now you can install the Python server:

```
python setup.py install
```

# Usage

Navigate to your pokeruby directory. Perform a clean, matching build and ensure that both the ELF and the GBA files have been created.

Rename the `pokeruby.elf` and `pokeruby.gba` files to `basepokeruby.elf` and `basepokeruby.gba` respectively. The ELF file is used to get debugging information such as symbol names for a better ASM output.

After doing this, you can then just start the diff client to watch your `src/`, `asm/` and `include/` files for changes:

```
pokerubydiff
```

Navigate to the URL logged to the console and make a change.

The diff client will use clang to parse any C files you edit in order to find the symbol name of the function you last edited. It will log to the console if it was unable to find a changed function, or use the last function. If this is not working, you can specify an initial function to diff using

```
pokerubydiff --function NameOfTheFunction
```

# Notes

The disassembler is a custom disassembler based on the Capstone engine. It is incredibly basic, and makes many assumptions (e.g. that the stack will be aligned) in order to find the return location of a function and to identify data and alignment regions. At present, it can only handle THUMB and it is not equipped to handle many branch types, such as `mov pc, rX` or long jumps via `bx rX`. This means it will be unable to handle jump tables for now.
