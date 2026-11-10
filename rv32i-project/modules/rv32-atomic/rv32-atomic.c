/*
  © 2026 Intel Corporation

  This software and the related documents are Intel copyrighted materials, and
  your use of them is governed by the express license under which they were
  provided to you ("License"). Unless the License provides otherwise, you may
  not use, modify, copy, publish, distribute, disclose or transmit this software
  or the related documents without Intel's prior written permission.

  This software and the related documents are provided as is, with no express or
  implied warranties, other than those that are expressly stated in the License.
*/

#include <simics/util/strbuf.h>
#include "cosim.h"
#include "rv32-core.h"
#include "rv32-helpers.h"

static uint32
sign_extend(uint32 value, unsigned bits)
{
        uint32 sign = 1u << (bits - 1);
        return (value ^ sign) - sign;
}

void
execute(rv32_t *cpu)
{
        // Save the current PC and prepare to fetch instruction bytes
        uint32 pc = cpu->pc;
        uint8 bytes[4];

        // Fetch Phase
        if (pc & 3) {
                rv32_halt(cpu, "misaligned instruction address");
                return;
        }

        // Read the instruction bytes from memory
        if (!read_simics_memory(cpu, pc, bytes, sizeof bytes)) {
                rv32_halt(cpu, "instruction fetch failed");
                return;
        }

        // Reconstruct 32-bit instruction word
        uint32 ins = (uint32)bytes[0] | ((uint32)bytes[1] << 8)
                | ((uint32)bytes[2] << 16) | ((uint32)bytes[3] << 24);

        // Decode Phase

        // Extract standard RISC-V instruction fields
        uint32 opcode = ins & 0x7f;
        unsigned rd     = (ins >> 7) & 31;
        unsigned funct3 = (ins >> 12) & 7;
        unsigned rs1    = (ins >> 15) & 31;
        unsigned rs2    = (ins >> 20) & 31;
        unsigned funct7 = ins >> 25;

        // Read the values of the source registers
        uint32 val_rs1 = reg_read_x(cpu, rs1);
        uint32 val_rs2 = reg_read_x(cpu, rs2);

        // Immediate values for I-type instructions
        uint32 imm = sign_extend(ins >> 20, 12);
        // R-type instruction result
        uint32 result = 0;
        // The next program counter value, default to sequential execution
        uint32 next_pc = pc + 4;

        // Control flags for instruction execution
        bool write_rd = false;
        bool branch = false;

        // Switch on the opcode to determine instruction type
        switch (opcode) {
        // LUI - Load Upper Immediate
        case 0x37:
                result = ins & 0xfffff000u;
                write_rd = true;
                break;
        // AUIPC - Add Upper Immediate to PC
        case 0x17:
                result = pc + (ins & 0xfffff000u);
                write_rd = true;
                break;
        // JAL - Jump and Link
        case 0x6f:
                imm = ((ins >> 31) << 20) | (((ins >> 12) & 0xff) << 12)
                        | (((ins >> 20) & 1) << 11)
                        | (((ins >> 21) & 0x3ff) << 1);
                next_pc = pc + sign_extend(imm, 21);
                result = pc + 4;
                write_rd = true;
                break;
        // JALR - Jump and Link Register
        case 0x67:
                if (funct3 != 0)
                        goto illegal;
                next_pc = (val_rs1 + imm) & ~1u;
                result = pc + 4;
                write_rd = true;
                break;
        // B-type conditional branches
        case 0x63:
                // Determine the branch condition based on funct3
                switch (funct3) {
                case 0: branch = a == b; break;
                case 1: branch = a != b; break;
                case 4: branch = signed_less(a, b); break;
                case 5: branch = !signed_less(a, b); break;
                case 6: branch = a < b; break;
                case 7: branch = a >= b; break;
                default: goto illegal;
                }
                imm = ((ins >> 31) << 12) | (((ins >> 7) & 1) << 11)
                        | (((ins >> 25) & 0x3f) << 5)
                        | (((ins >> 8) & 0xf) << 1);
                if (branch)
                        next_pc = pc + sign_extend(imm, 13);
                break;
        // I-type arithmetic instructions
        case 0x13:
                // Determine the operation based on funct3 and funct7
                switch (funct3) {
                case 0: result = a + imm; break;
                case 2: result = signed_less(a, imm); break;
                case 3: result = a < imm; break;
                case 4: result = a ^ imm; break;
                case 6: result = a | imm; break;
                case 7: result = a & imm; break;
                case 1:
                        if (funct7 != 0) {
                                goto illegal;
                        }
                        result = a << rs2;
                        break;
                case 5:
                        if (funct7 == 0) {
                                result = a >> rs2;
                        }
                        else if (funct7 == 0x20) {
                                result = arithmetic_shift_right(a, rs2);
                        }
                        else goto illegal;
                        break;
                }
                write_rd = true;
                break;
        // R-type arithmetic instructions
        case 0x33:
                // Validate funct7 and funct3 for R-type instructions
                if (funct7 != 0 && funct7 != 0x20) {
                        goto illegal;
                }
                if (funct7 == 0x20 && funct3 != 0 && funct3 != 5) {
                        goto illegal;
                }
                switch (funct3) {
                case 0: result = funct7 ? a - b : a + b; break;
                case 1: result = a << (b & 31); break;
                case 2: result = signed_less(a, b); break;
                case 3: result = a < b; break;
                case 4: result = a ^ b; break;
                case 5: result = funct7 ? arithmetic_shift_right(a, b & 31): a >> (b & 31);
                        break;
                case 6: result = a | b; break;
                case 7: result = a & b; break;
                }
                write_rd = true;
                break;
        // ECALL and EBREAK instructions
        case 0x73:
                // Handle EBREAK instruction specifically
                if (ins != 0x00100073u) {
                        goto illegal;
                }
                // Increment cycle and step counters before halting
                increment_cycle(cpu);
                increment_step(cpu);
                // Halt the CPU
                ebreak(cpu);
                return;
        default:
                goto illegal;
        }

        if (next_pc & 3) {
                rv32_halt(cpu, "misaligned instruction address");
                return;
        }
        
        if (write_rd) {
                reg_write_x(cpu, rd, result);
        }
        // Update the program counter and increment cycle/step counters
        cpu->pc = next_pc;
        increment_cycle(cpu);
        increment_step(cpu);
        // Return to the caller after executing the instruction
        return;

        // Handle any illegal instruction case
illegal:
        illegal_instruction(cpu, pc, ins);
}

/* Text for Simics' disassemble CLI command (e.g. "disassemble 0x0 10")
   for the instruction word instr. Return a string allocated with Simics'
   allocators, e.g. MM_STRDUP() or a strbuf as below; Simics frees it. */
char *
rv32_disassemble(uint32 instr)
{
        strbuf_t b = SB_INIT;
        sb_addfmt(&b, ".word 0x%08x", instr);
        return sb_detach(&b);
}
