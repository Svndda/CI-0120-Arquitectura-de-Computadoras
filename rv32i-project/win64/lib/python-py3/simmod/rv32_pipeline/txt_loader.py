# © 2026 Intel Corporation
#
# This software and the related documents are Intel copyrighted materials, and
# your use of them is governed by the express license under which they were
# provided to you ("License"). Unless the License provides otherwise, you may
# not use, modify, copy, publish, distribute, disclose or transmit this software
# or the related documents without Intel's prior written permission.
#
# This software and the related documents are provided as is, with no express or
# implied warranties, other than those that are expressly stated in the License.

import re

_REG_ALIASES = {
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
    "t0": 5, "t1": 6, "t2": 7, "s0": 8, "fp": 8, "s1": 9,
    **{"a%d" % i: 10 + i for i in range(8)},
    **{"s%d" % i: 16 + i for i in range(2, 12)},
    **{"t%d" % i: 25 + i for i in range(3, 7)},
}
_R = {
    "add": (0, 0), "sub": (0, 0x20), "sll": (1, 0), "slt": (2, 0),
    "sltu": (3, 0), "xor": (4, 0), "srl": (5, 0), "sra": (5, 0x20),
    "or": (6, 0), "and": (7, 0),
}
_I = {"addi": 0, "slti": 2, "sltiu": 3, "xori": 4, "ori": 6, "andi": 7}
_SHIFT = {"slli": (1, 0), "srli": (5, 0), "srai": (5, 0x20)}
_BRANCH = {"beq": 0, "bne": 1, "blt": 4, "bge": 5, "bltu": 6, "bgeu": 7}
_LABEL = re.compile(r"^[A-Za-z_.$][A-Za-z0-9_.$]*$")


def _register(text):
    text = text.lower()
    if text in _REG_ALIASES:
        return _REG_ALIASES[text]
    if re.fullmatch(r"x(?:[0-9]|[12][0-9]|3[01])", text):
        return int(text[1:])
    raise ValueError("invalid register: %s" % text)


def _number(text, minimum, maximum):
    try:
        value = int(text, 0)
    except ValueError:
        raise ValueError("invalid integer: %s" % text) from None
    if not minimum <= value <= maximum:
        raise ValueError("immediate %s outside [%d, %d]" % (text, minimum, maximum))
    return value


def _offset(text, labels, pc, bits):
    value = labels[text] - pc if text in labels else _number(
        text, -(1 << (bits - 1)), (1 << (bits - 1)) - 1)
    if value & 1 or not -(1 << (bits - 1)) <= value < (1 << (bits - 1)):
        raise ValueError("branch/jump offset out of range or not 2-byte aligned: %s" % text)
    return value & ((1 << bits) - 1)


def _encode(text, labels, pc):
    parts = text.split(None, 1)
    op = parts[0].lower()
    args = [arg.strip() for arg in parts[1].split(",")] if len(parts) == 2 else []
    if any(not arg for arg in args):
        raise ValueError("empty operand")
    if op == "ebreak" and not args:
        return 0x00100073
    if op == "nop" and not args:
        return 0x00000013
    if op == ".word" and len(args) == 1:
        return _number(args[0], -(1 << 31), 0xffffffff) & 0xffffffff
    if op in ("lui", "auipc") and len(args) == 2:
        rd = _register(args[0])
        imm = _number(args[1], -(1 << 19), (1 << 20) - 1) & 0xfffff
        return (imm << 12) | (rd << 7) | (0x37 if op == "lui" else 0x17)
    if op in _R and len(args) == 3:
        rd, rs1, rs2 = map(_register, args)
        funct3, funct7 = _R[op]
        return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0x33
    if op in _I and len(args) == 3:
        rd, rs1 = map(_register, args[:2])
        imm = _number(args[2], -2048, 2047) & 0xfff
        return (imm << 20) | (rs1 << 15) | (_I[op] << 12) | (rd << 7) | 0x13
    if op in _SHIFT and len(args) == 3:
        rd, rs1 = map(_register, args[:2])
        shift = _number(args[2], 0, 31)
        funct3, funct7 = _SHIFT[op]
        return ((funct7 << 25) | (shift << 20) |
                (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0x13)
    if op in _BRANCH and len(args) == 3:
        rs1, rs2 = map(_register, args[:2])
        imm = _offset(args[2], labels, pc, 13)
        return ((((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3f) << 25)
                | (rs2 << 20) | (rs1 << 15) | (_BRANCH[op] << 12)
                | (((imm >> 1) & 0xf) << 8) | (((imm >> 11) & 1) << 7) | 0x63)
    if op == "jal" and len(args) == 2:
        rd = _register(args[0])
        imm = _offset(args[1], labels, pc, 21)
        return ((((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3ff) << 21)
                | (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xff) << 12)
                | (rd << 7) | 0x6f)
    if op == "jalr" and len(args) in (2, 3):
        rd = _register(args[0])
        if len(args) == 2:
            match = re.fullmatch(r"\s*([^()\s]+)\s*\(\s*([^()\s]+)\s*\)\s*", args[1])
            if not match:
                raise ValueError("expected jalr rd, offset(rs1)")
            imm_text, base = match.groups()
        else:
            base, imm_text = args[1:]
        rs1 = _register(base)
        imm = _number(imm_text, -2048, 2047) & 0xfff
        return (imm << 20) | (rs1 << 15) | (rd << 7) | 0x67
    raise ValueError("unsupported instruction or incorrect operands: %s" % text)


def assemble(source, address=0):
    """Assemble the supported RV32I subset into little-endian bytes."""
    if not 0 <= address <= 0xffffffff or address & 3:
        raise ValueError("load address must be a 4-byte aligned RV32 address")
    labels = {}
    instructions = []
    pc = address
    for line_number, line in enumerate(source.splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        try:
            while ":" in line:
                label, line = (part.strip() for part in line.split(":", 1))
                if not _LABEL.fullmatch(label) or label in labels:
                    raise ValueError("invalid or duplicate label: %s" % label)
                labels[label] = pc
            if line:
                if pc > 0xfffffffc:
                    raise ValueError("program exceeds RV32 address space")
                instructions.append((line_number, pc, line))
                pc += 4
        except ValueError as exc:
            raise ValueError("line %d: %s" % (line_number, exc)) from exc
    result = bytearray()
    for line_number, pc, line in instructions:
        try:
            result.extend(_encode(line, labels, pc).to_bytes(4, "little"))
        except ValueError as exc:
            raise ValueError("line %d: %s" % (line_number, exc)) from exc
    return bytes(result)


def mem_write8(core, addr, value):
    """Write the byte value (0..255) to address addr of the core's memory."""
    import simics
    simics.SIM_write_phys_memory(core, addr, value, 1)


def load_program(core, path, address):
    """Read the assembly program in the text file path and write the machine
    code of its instructions into memory, the first one at address."""
    with open(path, encoding="utf-8") as program:
        code = assemble(program.read(), address)
    for offset, byte in enumerate(code):
        mem_write8(core, address + offset, byte)
