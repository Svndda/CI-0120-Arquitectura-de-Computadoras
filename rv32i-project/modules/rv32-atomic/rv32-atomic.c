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
        uint32 imm_i = sign_extend(ins >> 20, 12);

        // Always increment the PC and cycle/step counters
        // after executing the instruction
        cpu->pc = pc + 4;
        increment_cycle(cpu);
        increment_step(cpu);
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
