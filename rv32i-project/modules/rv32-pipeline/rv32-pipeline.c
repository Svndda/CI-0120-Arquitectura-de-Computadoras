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

static bool
signed_less(uint32 a, uint32 b)
{
        return (a ^ 0x80000000u) < (b ^ 0x80000000u);
}

static uint32
arithmetic_shift_right(uint32 value, unsigned amount)
{
        if (amount == 0)
                return value;
        return (value >> amount) | ((value & 0x80000000u) ? (~0u << (32 - amount)) : 0);
}

static void
stage_if(rv32_t *cpu, bool flush, uint32 redirect_pc, if_id_reg_t *next_if_id)
{       
        // Clear the next IF/ID register
        memset(next_if_id, 0, sizeof(*next_if_id));

        if (flush) {
                cpu->fetch_pc = redirect_pc;
                return;
        }

        // Fetch the instruction at the current fetch PC
        uint32 pc = cpu->fetch_pc;
        next_if_id->valid = true;
        next_if_id->pc = pc;

        // Check for misaligned instruction address
        if (pc & 3u) {
                next_if_id->is_fetch_fault = true;
                next_if_id->fault_reason = "misaligned instruction address";
                return;
        }

        // Read 4 bytes from memory at the fetch PC
        uint8 bytes[4];
        if (!read_simics_memory(cpu, pc, bytes, sizeof bytes)) {
                next_if_id->is_fetch_fault = true;
                next_if_id->fault_reason = "instruction fetch failed";
                return;
        }

        // Combine the bytes into a 32-bit instruction
        next_if_id->instr = (uint32)bytes[0]
                          | ((uint32)bytes[1] << 8)
                          | ((uint32)bytes[2] << 16)
                          | ((uint32)bytes[3] << 24);
        cpu->fetch_pc = pc + 4;
}


void execute(rv32_t *cpu)
{
        /* TODO */
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
