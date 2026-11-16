import importlib.util
import pathlib
import re
import subprocess
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
ATOMIC_TESTS_DIR = ROOT / "tests" / "rv32-atomic"
PIPE_TESTS_DIR = ROOT / "tests" / "rv32-pipeline"
LOADER_PATH = ROOT / "modules" / "rv32-pipeline" / "txt_loader.py"

spec = importlib.util.spec_from_file_location("rv32_pipeline_loader", LOADER_PATH)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


class PipelineVerificationTests(unittest.TestCase):
    def invoke_simics(self, target_script, program, *commands, address=0):
        command = [
            str(ROOT / "simics.bat"), "--batch-mode", "--no-win",
            str(ROOT / "targets" / "rv32i" / target_script),
            "program=" + str(program), "load_address=" + str(address),
        ]
        for item in commands:
            command.extend(["-e", item])
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)

    def run_core(self, target_script, program, address=0):
        result = self.invoke_simics(
            target_script, program, "run", "pregs",
            "@print(conf.cosim0.iface.cycle.get_cycle_count(),"
            "conf.cosim0.iface.step.get_step_count())",
            address=address,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ebreak", result.stdout)
        registers = {
            int(name): int(value, 16)
            for name, value in re.findall(r"x(\d+)\s*=\s*0x([0-9a-fA-F]+)", result.stdout)
        }
        pc = re.search(r"pc\s*=\s*0x([0-9a-fA-F]+)", result.stdout)
        counts = re.search(r"^(\d+) (\d+)\s*$", result.stdout, re.MULTILINE)
        self.assertEqual(len(registers), 32)
        self.assertIsNotNone(pc)
        self.assertIsNotNone(counts)
        return registers, int(pc.group(1), 16), tuple(map(int, counts.groups()))

    def test_assembler_encodings_and_rejection(self):
        source = (ATOMIC_TESTS_DIR / "known-encodings.txt").read_text(encoding="utf-8")
        expected = [0x123450b7, 0x06400193, 0x40320733, 0x40125613,
                    0x01028463, 0x00800cef, 0x00dd0de7, 0x00100073]
        self.assertEqual(loader.assemble(source),
                         b"".join(w.to_bytes(4, "little") for w in expected))

        with mock.patch.object(loader, "mem_write8") as write:
            with self.assertRaises(ValueError):
                loader.load_program(None, str(ATOMIC_TESTS_DIR / "invalid-program.txt"), 0)
            write.assert_not_called()

    def test_stage_fill_latency_on_single_step(self):
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        result = self.invoke_simics(
            "rv32-pipeline.simics", prog, "stepi 1", "pregs",
            "@print(conf.cosim0.iface.cycle.get_cycle_count(),"
            "conf.cosim0.iface.step.get_step_count())",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"x1\s*=\s*0x12345000")
        self.assertRegex(result.stdout, r"pc\s*=\s*0x00000004")
        self.assertRegex(result.stdout, r"(?m)^4 1$")

    def test_equivalence_all_instructions(self):
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        a_regs, a_pc, a_cnt = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        self.assertEqual(a_cnt, (46, 46))
        self.assertEqual(p_cnt, (65, 46))

    def test_equivalence_control_flow(self):
        prog = ATOMIC_TESTS_DIR / "control-flow.txt"
        a_regs, a_pc, a_cnt = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        self.assertEqual(a_cnt, (20, 20))
        self.assertEqual(p_cnt, (31, 20))

    def test_nonzero_load_address(self):
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog, 0x100)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog, 0x100)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, 0x1d4)
        self.assertEqual(p_cnt, (65, 46))

    def test_data_hazards_and_forwarding(self):
        prog = PIPE_TESTS_DIR / "forwarding-hazards.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        self.assertEqual(p_regs[3], 35)
        self.assertEqual(p_regs[4], 10)
        self.assertEqual(p_regs[6], 400)
        self.assertEqual(p_regs[9], 0)
        self.assertEqual(p_regs[10], 0)
        self.assertEqual(p_regs[13], 165)
        self.assertEqual(p_regs[15], 0)
        self.assertEqual(p_cnt, (24, 19))

    def test_branch_shadow_squashing(self):
        prog = PIPE_TESTS_DIR / "branch-shadow.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, _ = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        for r in (10, 11, 12, 13):
            self.assertEqual(p_regs[r], 0)
        self.assertEqual(p_regs[6], 88)

    def test_corner_cases(self):
        prog = PIPE_TESTS_DIR / "corner-cases.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        self.assertEqual(p_cnt, (14, 11))

    def test_misaligned_jump_and_illegal_instruction(self):
        misaligned = ATOMIC_TESTS_DIR / "misaligned-jump.txt"
        res_m = self.invoke_simics("rv32-pipeline.simics", misaligned, "run", "pregs")
        self.assertIn("misaligned instruction address", res_m.stdout + res_m.stderr)
        self.assertRegex(res_m.stdout, r"x1\s*=\s*0x00000007")
        self.assertRegex(res_m.stdout, r"pc\s*=\s*0x00000004")

        illegal = ATOMIC_TESTS_DIR / "illegal.txt"
        res_i = self.invoke_simics("rv32-pipeline.simics", illegal, "run", "pregs")
        self.assertIn("illegal or unsupported instruction", res_i.stdout + res_i.stderr)
        self.assertRegex(res_i.stdout, r"x1\s*=\s*0x00000007")
        self.assertRegex(res_i.stdout, r"pc\s*=\s*0x00000004")


if __name__ == "__main__":
    unittest.main(verbosity=2)