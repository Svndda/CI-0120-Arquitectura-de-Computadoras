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



static void
stage_id(rv32_t *cpu, bool flush, id_ex_reg_t *next_id_ex)
{       
        // Clear the next ID/EX register
        memset(next_id_ex, 0, sizeof(*next_id_ex));
        const if_id_reg_t *in = &cpu->if_id;

        // If flush is true or the input IF/ID register is not valid
        if (flush || !in->valid)
                return;

        // Set the next ID/EX register fields
        next_id_ex->valid = true;
        next_id_ex->pc = in->pc;
        next_id_ex->instr = in->instr;

        // If there was a fetch fault, propagate it to the next ID/EX register
        if (in->is_fetch_fault) {
                next_id_ex->is_fetch_fault = true;
                next_id_ex->fault_reason = in->fault_reason;
                return;
        }

        // Decode the instruction
        uint32 ins = in->instr;
        uint32 opcode = ins & 0x7fu;
        unsigned rd     = (ins >> 7) & 31u;
        unsigned funct3 = (ins >> 12) & 7u;
        unsigned rs1    = (ins >> 15) & 31u;
        unsigned rs2    = (ins >> 20) & 31u;
        unsigned funct7 = ins >> 25;

        // Set the decoded fields in the next ID/EX register
        next_id_ex->opcode = opcode;
        next_id_ex->rd = rd;
        next_id_ex->funct3 = funct3;
        next_id_ex->rs1 = rs1;
        next_id_ex->rs2 = rs2;
        next_id_ex->funct7 = funct7;

        // Handle different opcodes and set the appropriate fields in the next ID/EX register
        switch (opcode) {
        // LUI
        case 0x37:
        // AUIPC
        case 0x17:
                next_id_ex->imm = ins & 0xfffff000u;
                next_id_ex->write_rd = true;
                break;
        //  JAL instruction
        case 0x6f:
                uint32 raw_imm = ((ins >> 31) << 20)
                               | (((ins >> 12) & 0xffu) << 12)
                               | (((ins >> 20) & 1u) << 11)
                               | (((ins >> 21) & 0x3ffu) << 1);
                next_id_ex->imm = sign_extend(raw_imm, 21);
                next_id_ex->write_rd = true;
                break;
        
        // JALR instruction
        case 0x67:
                if (funct3 != 0) {
                        next_id_ex->is_illegal = true;
                        return;
                }
                next_id_ex->imm = sign_extend(ins >> 20, 12);
                next_id_ex->uses_rs1 = true;
                next_id_ex->val_a = reg_read_x(cpu, rs1);
                next_id_ex->write_rd = true;
                break;
        // Branch instructions
        case 0x63: 
                if (funct3 == 2 || funct3 == 3) {
                        next_id_ex->is_illegal = true;
                        return;
                }
                uint32 raw_imm = ((ins >> 31) << 12)
                               | (((ins >> 7) & 1u) << 11)
                               | (((ins >> 25) & 0x3fu) << 5)
                               | (((ins >> 8) & 0xfu) << 1);
                next_id_ex->imm = sign_extend(raw_imm, 13);
                next_id_ex->uses_rs1 = true;
                next_id_ex->uses_rs2 = true;
                next_id_ex->val_a = reg_read_x(cpu, rs1);
                next_id_ex->val_b = reg_read_x(cpu, rs2);
                break;
        
        // I-type ALU instructions
        case 0x13:
                if (funct3 == 1 && funct7 != 0) {
                        next_id_ex->is_illegal = true;
                        return;
                }
                if (funct3 == 5 && funct7 != 0 && funct7 != 0x20) {
                        next_id_ex->is_illegal = true;
                        return;
                }
                next_id_ex->imm = sign_extend(ins >> 20, 12);
                next_id_ex->uses_rs1 = true;
                next_id_ex->val_a = reg_read_x(cpu, rs1);
                next_id_ex->write_rd = true;
                break;
        // R-type ALU instructions
        case 0x33:
                if (funct7 != 0 && funct7 != 0x20) {
                        next_id_ex->is_illegal = true;
                        return;
                }
                if (funct7 == 0x20 && funct3 != 0 && funct3 != 5) {
                        next_id_ex->is_illegal = true;
                        return;
                }
                next_id_ex->uses_rs1 = true;
                next_id_ex->uses_rs2 = true;
                next_id_ex->val_a = reg_read_x(cpu, rs1);
                next_id_ex->val_b = reg_read_x(cpu, rs2);
                next_id_ex->write_rd = true;
                break;
        // EBREAK instruction
        case 0x73:
                if (ins != 0x00100073u) {
                        next_id_ex->is_illegal = true;
                        return;
                }
                next_id_ex->is_ebreak = true;
                break;
        // illegal instructions
        default:
                next_id_ex->is_illegal = true;
                break;
        }
}

static bool
stage_ex(rv32_t *cpu, const wb_fwd_reg_t *wb_fwd,
         ex_wb_reg_t *next_ex_wb, bool *flush_pipeline, uint32 *redirect_pc)
{       
        // Clear the next EX/WB register and initialize flush_pipeline and redirect_pc
        memset(next_ex_wb, 0, sizeof(*next_ex_wb));
        *flush_pipeline = false;
        *redirect_pc = 0;

        // Get the input ID/EX register
        const id_ex_reg_t *in = &cpu->id_ex;
        if (!in->valid)
                return true;

        // Set the next EX/WB register fields
        next_ex_wb->valid = true;
        next_ex_wb->pc = in->pc;
        next_ex_wb->next_pc = in->pc + 4;
        next_ex_wb->instr = in->instr;
        next_ex_wb->rd = in->rd;
        next_ex_wb->write_rd = in->write_rd;
        next_ex_wb->is_ebreak = in->is_ebreak;
        next_ex_wb->is_illegal = in->is_illegal;
        next_ex_wb->is_fetch_fault = in->is_fetch_fault;
        next_ex_wb->fault_reason = in->fault_reason;

        // If there was a fetch fault, illegal instruction, or EBREAK, just propagate it to the next EX/WB register
        if (in->is_fetch_fault || in->is_illegal || in->is_ebreak) {
                return true;
        } 

        // Forwarding logic for source registers
        uint32 op_a = in->val_a;
        uint32 op_b = in->val_b;

        // Forwarding for rs1
        if (in->uses_rs1 && in->rs1 != 0) {
                if (cpu->ex_wb.valid && cpu->ex_wb.write_rd && cpu->ex_wb.rd == in->rs1) {
                        op_a = cpu->ex_wb.result;
                } else if (wb_fwd->valid && wb_fwd->write_rd && wb_fwd->rd == in->rs1) {
                        op_a = wb_fwd->result;
                }
        }

        // Forwarding for rs2
        if (in->uses_rs2 && in->rs2 != 0) {
                if (cpu->ex_wb.valid && cpu->ex_wb.write_rd && cpu->ex_wb.rd == in->rs2) {
                        op_b = cpu->ex_wb.result;
                } else if (wb_fwd->valid && wb_fwd->write_rd && wb_fwd->rd == in->rs2) {
                        op_b = wb_fwd->result;
                }
        }

        // Execute the instruction based on the opcode and funct3/funct7 fields
        uint32 result = 0;
        uint32 target_pc = in->pc + 4;
        bool take_redirect = false;

        switch (in->opcode) {
        // LUI
        case 0x37:
                result = in->imm;
                break;
        // AUIPC
        case 0x17:
                result = in->pc + in->imm;
                break;
        // J-type jumps 
        case 0x6f:
                target_pc = in->pc + in->imm;
                result = in->pc + 4;
                take_redirect = true;
                break;
        case 0x67:
                target_pc = (op_a + in->imm) & ~1u;
                result = in->pc + 4;
                take_redirect = true;
                break;
        // B-type conditional branches
        case 0x63: {
                // Determine if the branch should be taken based on funct3
                bool branch = false;
                switch (in->funct3) {
                case 0: branch = (op_a == op_b); break;
                case 1: branch = (op_a != op_b); break;
                case 4: branch = signed_less(op_a, op_b); break;
                case 5: branch = !signed_less(op_a, op_b); break;
                case 6: branch = (op_a < op_b); break;
                case 7: branch = (op_a >= op_b); break;
                default: break;
                }
                if (branch) {
                        target_pc = in->pc + in->imm;
                        take_redirect = true;
                }
                break;
        }
        // I-type ALU
        case 0x13:
                // Execute I-type ALU operations based on funct3
                switch (in->funct3) {
                case 0: result = op_a + in->imm; break;
                case 2: result = signed_less(op_a, in->imm); break;
                case 3: result = op_a < in->imm; break;
                case 4: result = op_a ^ in->imm; break;
                case 6: result = op_a | in->imm; break;
                case 7: result = op_a & in->imm; break;
                case 1: result = op_a << in->rs2; break;
                case 5: result = (in->funct7 == 0x20)
                                ? arithmetic_shift_right(op_a, in->rs2)
                                : (op_a >> in->rs2);
                        break;
                }
                break;
        // R-type ALU
        case 0x33:
                // R-type ALU operations based on funct3 and funct7
                switch (in->funct3) {
                case 0: result = in->funct7 ? (op_a - op_b) : (op_a + op_b); break;
                case 1: result = op_a << (op_b & 31); break;
                case 2: result = signed_less(op_a, op_b); break;
                case 3: result = op_a < op_b; break;
                case 4: result = op_a ^ op_b; break;
                case 5: result = in->funct7
                                ? arithmetic_shift_right(op_a, op_b & 31)
                                : (op_a >> (op_b & 31));
                        break;
                case 6: result = op_a | op_b; break;
                case 7: result = op_a & op_b; break;
                }
                break;
        default:
                break;
        }

        // Handle pipeline redirection if needed
        if (take_redirect) {
                if (target_pc & 3u) {
                        cpu->pc = in->pc;
                        cpu->arch_pc = in->pc;
                        rv32_halt(cpu, "misaligned instruction address");
                        return false;
                }
                next_ex_wb->next_pc = target_pc;
                *flush_pipeline = true;
                *redirect_pc = target_pc;
        }

        // Set the result in the next EX/WB register
        next_ex_wb->result = result;
        return true;
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
