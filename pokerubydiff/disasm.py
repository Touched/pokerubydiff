import io
import itertools
import collections
import operator
import capstone
import capstone.arm

# FIXME: Convert mnemonic checks to: "if i.id in (ARM_INS_BL, ARM_INS_CMP)"
# TODO: Handle switches

register_names = collections.OrderedDict({
    capstone.arm.ARM_REG_R0: 'r0',
    capstone.arm.ARM_REG_R1: 'r1',
    capstone.arm.ARM_REG_R2: 'r2',
    capstone.arm.ARM_REG_R3: 'r3',
    capstone.arm.ARM_REG_R4: 'r4',
    capstone.arm.ARM_REG_R5: 'r5',
    capstone.arm.ARM_REG_R6: 'r6',
    capstone.arm.ARM_REG_R7: 'r7',
    capstone.arm.ARM_REG_R8: 'r8',
    capstone.arm.ARM_REG_R9: 'r9',
    capstone.arm.ARM_REG_R10: 'r10',
    capstone.arm.ARM_REG_R11: 'r11',
    capstone.arm.ARM_REG_R12: 'r12',
    capstone.arm.ARM_REG_SP: 'sp',
    capstone.arm.ARM_REG_LR: 'lr',
    capstone.arm.ARM_REG_PC: 'pc',
})

def build_reglist(reglist):
    prev = None
    result = ''
    keys = list(register_names.keys())

    for reg in reglist:
        if prev == None:
            result = register_names[reg]
        else:
            # If the register is adjacent
            if abs(keys.index(prev) - keys.index(reg)) == 1:
                if not result.endswith('-'): result += '-'
            else:
                if result.endswith('-'): result += register_names[prev]
                result += ', ' + register_names[reg]

        prev = reg

    if result.endswith('-'): result += register_names[prev]
    return '{{{}}}'.format(result)


def build_imm(imm):
    return '#' + (hex(imm) if imm > 9 else str(imm))


def address_to_offset(address):
    # TODO: Check for other waitstates
    if 0x08000000 <= address <= 0x09FFFFFF:
        return address - 0x08000000
    else:
        raise ValueError('Address is not in ROM')


def generate_label(address, prefix):
    return '{}_{:X}'.format(prefix, address)


class Stack:
    def __init__(self, stack=[]):
        self._stack = stack

    def push(self, item):
        self._stack.append(item)

    def pop(self):
        return self._stack.pop()

    def clone(self):
        return Stack(list(self._stack))


class Registers:
    registers = [
        'r0',
        'r1',
        'r2',
        'r3',
        'r4',
        'r5',
        'r6',
        'r7',
        'r8',
        'r9',
        'r10',
        'r11',
        'r12',
        'sp',
        'lr',
        'pc'
    ]

    def __init__(self, registers={}):
        self._registers = dict(zip(self.registers, itertools.repeat(None)))
        self._registers.update(registers)

    def clone(self):
        return Registers(self._registers)

    def __getitem__(self, key):
        if key not in self.registers:
            raise ValueError('Invalid register name: {}'.format(key))

        return self._registers[key]

    def __setitem__(self, key, value):
        if key not in self.registers:
            raise ValueError('Invalid register name: {}'.format(key))

        self._registers[key] = value


# needs a better name
class Unit:
    def size(self):
        raise NotImplementedError

    def address(self):
        raise NotImplementedError


class AlignItem:
    def __init__(self, address, size):
        self._address = address
        self._size = size

    def size(self):
        return self._size

    def address(self):
        return self._address

    def __str__(self):
        return '.align {}'.format(self.size())


class Data(Unit):
    def __init__(self, data, address, size, symbols):
        offset = address_to_offset(address)
        self._data = data
        self._address = address
        self._size = size
        self.value = int.from_bytes(self._data[offset:offset+size], 'little')

    def size(self):
        return self._size

    def address(self):
        return self._address

    def __str__(self):
        # TODO: Lookup symbol
        return '.word 0x{:08X}'.format(self.value)


class Insn(Unit):
    def __init__(self, data, cs_insn, stack, registers, symbols):
        self._insn = cs_insn
        self._data = data
        self._symbols = symbols

        # Modify the stack
        if self._insn.mnemonic == 'push':
            for op in reversed(self._insn.operands):
                stack.push(self._insn.reg_name(op.reg))
        elif self._insn.mnemonic == 'pop':
            for op in self._insn.operands:
                reg_name = self._insn.reg_name(op.reg)
                prev_reg_name = stack.pop()
                registers[reg_name] = prev_reg_name

        self.stack = stack
        self.registers = registers

        # Detect literal pool loads
        self._datarefs = []

        if self._insn.mnemonic == 'ldr':
            assert len(self._insn.operands) == 2
            base = self._insn.reg_name(self._insn.operands[1].mem.base)

            if base == 'pc':
                disp = self._insn.operands[1].mem.disp

                # FIXME: Negative displacement
                assert disp > 0

                address = self._insn.address + disp + (4 if self._insn.address % 4 == 0 else 2)
                size = 4
                self._datarefs.append(Data(self._data, address, size, self._symbols))

    def size(self):
        return self._insn.size

    def address(self):
        return self._insn.address

    def data_references(self):
        return self._datarefs

    def is_return(self):
        if self._insn.mnemonic == 'bx':
            assert len(self._insn.operands) == 1
            reg_name = self._insn.reg_name(self._insn.operands[0].reg)

            if reg_name == 'lr':
                # Detect 'bx lr' return
                return True
            elif self.registers[reg_name] == 'lr':
                # Detect arm-thumb interworking return
                return True
            else:
                return False
        elif self._insn.mnemonic == 'pop':
            # Detect non arm-thumb interworking return
            return self.registers['pc'] == 'lr'

        return False

    def is_jump(self):
        # FIXME: Use constants
        return 'jump' in [self._insn.group_name(x) for x in self._insn.groups]

    def is_unconditional_jump(self):
        return self._insn.id == capstone.arm.ARM_INS_B and self._insn.cc == capstone.arm.ARM_CC_AL

    def jump_address(self):
        assert self.is_jump()
        assert self._insn.mnemonic != 'bx' # Can't get the address for a BX
        assert len(self._insn.operands) == 1
        return self._insn.operands[0].imm

    def is_call(self):
        # FIXME: Detect BX/BL as long jump

        if self._insn.mnemonic == 'bx':
            # Detect long-call
            return not self.is_return()
        if self._insn.mnemonic == 'bl':
            return True

        return False

    def __str__(self):
        mnemonic = self._insn.mnemonic
        op_str = self._insn.op_str
        id = self._insn.id
        groups = self._insn.groups

        # TODO: Other reglists (LDMIA, etc.)
        if id in (capstone.arm.ARM_INS_POP, capstone.arm.ARM_INS_PUSH):
            reglist = self._insn.operands
            operands = []
        else:
            reglist = []
            operands = self._insn.operands

        ops = []

        # Pseudo instructions
        if id == capstone.arm.ARM_INS_ADD:
            if len(operands) == 3:
                if operands[2].reg == 0 and operands[2].imm == 0:
                    mnemonic = 'mov'
                    operands = operands[:2]
        elif id == capstone.arm.ARM_INS_MOV:
            if operands[0].reg == operands[1].reg and operands[0].reg == capstone.arm.ARM_REG_R8:
                mnemonic = 'nop'
                operands = []
        elif id == capstone.arm.ARM_INS_LDR:
            if operands[1].mem.base == capstone.arm.ARM_REG_PC:
                # TODO: Get symbol in the middle
                lookup = self._symbols.lookup(self._datarefs[0].value)

                if lookup:
                    if lookup.disp > 0:
                        ops.append('={}+{}'.format(lookup.symbol.name, lookup.disp))
                    else:
                        ops.append('={}'.format(lookup.symbol.name))
                else:
                    ops.append('=0x{:08x}'.format(self._datarefs[0].value))

                operands = []

        # TODO: ADR (ADR rX,imm == ADD r4,pc,#nn)

        # TODO: Check extra features: Writeback, ...

        for op in operands:
            if op.type == capstone.arm.ARM_OP_MEM:
                if op.mem.index != 0:
                    disp = register_names[op.mem.index]
                else:
                    disp = build_imm(op.mem.disp)
                ops.append('[{}, {}]'.format(register_names[op.mem.base], disp))
            elif op.type == capstone.arm.ARM_OP_REG:
                ops.append(register_names[op.reg])
            elif op.type == capstone.arm.ARM_OP_IMM:
                if capstone.arm.ARM_GRP_JUMP in groups:
                    ops.append(generate_label(op.imm, 'loc'))
                elif id == capstone.arm.ARM_INS_BL:
                    # Lookup THUMB function
                    lookup = self._symbols.lookup(op.imm)

                    if lookup:
                        ops.append(lookup.symbol.name)
                    else:
                        ops.append('0x{:08x}'.format(op.imm))
                else:
                    ops.append(build_imm(op.imm))

        # Build register list
        if len(reglist) > 0: ops.append(build_reglist(op.reg for op in reglist))

        return '{}\t{}'.format(mnemonic, ', '.join(ops))


class CodePath:
    def __init__(self, md, data, address, stack, registers, symbols):
        offset = address_to_offset(address)

        data_slice = data[offset:]
        self._md = md
        self._data = data
        self._disasm = md.disasm(data_slice, address)
        self._stopped = False
        self._symbols = symbols

        self.address = address
        self.stack = stack.clone()
        self.registers = registers.clone()

    def __iter__(self):
        return self

    def __next__(self):
        if self._stopped:
            raise StopIteration

        try:
            insn = Insn(self._data, next(self._disasm), self.stack, self.registers, self._symbols)
        except StopIteration:
            raise RuntimeError('Unexepected EOF')

        # Stop next iteration for non-call jumps and returns
        if insn.is_return() or (insn.is_jump() and not insn.is_call()):
            self._stopped = True

        return insn

    def branch(self, address):
        """
        Branch this code path.
        """
        return CodePath(
            self._md,
            self._data,
            address,
            self.stack.clone(),
            self.registers.clone(),
            self._symbols,
        )


class Disassembler:
    def __init__(self, data):
        self.data = data
        self.md = capstone.Cs(
            capstone.CS_ARCH_ARM,
            capstone.CS_MODE_THUMB | capstone.CS_MODE_LITTLE_ENDIAN
        )
        self.md.detail = True

    def disassemble(self, address, symbols):
        queue = [CodePath(self.md, self.data, address, Stack(), Registers(), symbols)]
        visited = set()

        items = {}
        labels = {
            # TODO: Use name
            address: generate_label(address, 'sub'),
        }

        # Pass over data
        while len(queue):
            code_path = queue.pop()
            visited.add(code_path.address)

            for insn in code_path:
                items[insn.address()] = insn

                for dataref in insn.data_references():
                    labels[dataref.address()] = generate_label(dataref.address(), 'off')
                    items[dataref.address()] = dataref

                if not insn.is_return() and (insn.is_jump() and not insn.is_call()):
                    # Enqueue both branch paths
                    jump_address = insn.jump_address()

                    # Don't cotinue past unconditional jumps
                    if insn.is_unconditional_jump():
                        addresses = (jump_address,)
                    else:
                        addresses = (insn.address() + insn.size(), jump_address)

                    for address in addresses:
                        if address not in visited:
                            queue.append(code_path.branch(address))

                    # Only the jump target gets a label
                    labels[jump_address] = generate_label(jump_address, 'loc')

        # Sort by address
        items = map(operator.itemgetter(1), sorted(items.items(), key=operator.itemgetter(0)))

        # Uncover holes in output and label the instructions
        predicted_next_address = None
        for item in items:
            if predicted_next_address != None and predicted_next_address != item.address():
                # A hole in the output will always occur after the predicted next address
                # if not, the size of the item was incorrect
                assert item.address() >= predicted_next_address
                size = item.address() - predicted_next_address
                yield AlignItem(predicted_next_address, size)

            # Label the items
            item.label = labels.get(item.address())

            predicted_next_address = item.address() + item.size()
            yield item
