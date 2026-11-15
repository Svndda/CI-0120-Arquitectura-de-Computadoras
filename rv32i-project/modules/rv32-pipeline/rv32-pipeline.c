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

/* Inter-layer Register Struct: IF -> ID*/
typedef struct {
	bool valid;
	uint32 pc;
	uint32 instr;
	bool is_fetch_fault;
	const char *fault_reason;
} if_id_reg_t;

/* Inter-layer Register Struct: ID -> EX */
typedef struct {
	bool valid;
	uint32 pc;
	uint32 instr;

	uint32 opcode;
	unsigned rd;
	unsigned funct3;
	unsigned rs1;
	unsigned rs2;
	unsigned funct7;

	uint32 val_a;
	uint32 val_b;
	uint32 imm;

	bool uses_rs1;
	bool uses_rs2;
	bool write_rd;
	bool is_ebreak;
	bool is_illegal;
	bool is_fetch_fault;
	const char *fault_reason;
} id_ex_reg_t;

/* Inter-layer Register Struct: EX -> WB */
typedef struct {
	bool valid;
	uint32 pc;
	uint32 next_pc;
	uint32 instr;

	unsigned rd;
	uint32 result;
	bool write_rd;
	bool is_ebreak;
	bool is_illegal;
	bool is_fetch_fault;
	const char *fault_reason;
} ex_wb_reg_t;

/* Inter-layer Register Struct: WB -> Forwarding queue */
typedef struct {
	bool valid;
	bool write_rd;
	unsigned rd;
	uint32 result;
} wb_fwd_reg_t;

typedef struct rv32 {
	// Passed through from cosim_core_t
	cosim_core_t *core;
	// Pointer to the corresponding Simics object
	conf_object_t *obj;

	uint32 pc;
	uint32 x[RV32_NUM_REGS];

	uint32 arch_pc;
	// Internal pipeline registers
	uint32 fetch_pc;	/// The PC of the instruction currently in the fetch stage
	if_id_reg_t if_id;	// Speculative PC and instruction in the IF/ID pipeline register.
	id_ex_reg_t id_ex;
	ex_wb_reg_t ex_wb;
} rv32_t;

void
execute(rv32_t *cpu)
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
