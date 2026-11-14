import importlib.util
import pathlib
import re
import subprocess
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests" / "rv32-atomic"
LOADER_PATH = ROOT / "modules" / "rv32-atomic" / "txt_loader.py"
spec = importlib.util.spec_from_file_location("rv32_assembler", LOADER_PATH)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


class TestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity=0)
        self.test_number = 0

    def startTest(self, test):
        super().startTest(test)
        self.test_number += 1
        title = test.shortDescription() or test._testMethodName
        self.stream.writeln(f"\nTest #{self.test_number}: {title}")
        self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.writeln("  Result: OK")
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.writeln("  Result: FAILED")
        self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.writeln("  Result: ERROR")
        self.stream.flush()


class TestRunner(unittest.TextTestRunner):
    resultclass = TestResult


class AssemblerTests(unittest.TestCase):
    def test_known_encodings(self):
        """Known instruction encodings"""
        source = (TESTS_DIR / "known-encodings.txt").read_text(encoding="utf-8")
        expected = [0x123450b7, 0x06400193, 0x40320733, 0x40125613,
                    0x01028463, 0x00800cef, 0x00dd0de7, 0x00100073]
        assembled = loader.assemble(source)
        print(f"  Assembler(Generated encodings):\n    {len(assembled)} bytes, {assembled.hex()} hex", flush=True)
        self.assertEqual(assembled,
                         b"".join(word.to_bytes(4, "little") for word in expected))

    def test_labels_and_aliases(self):
        """Label and register alias resolution"""
        source = (TESTS_DIR / "labels-and-aliases.txt").read_text(encoding="utf-8")
        assembled = loader.assemble(source)
        print(f"  Assembler(Assembled labels and aliases): {assembled.hex()}", flush=True)
        self.assertEqual(assembled, bytes.fromhex("93021000e39e02fe"))

    def test_invalid_programs_are_rejected(self):
        """Rejection of invalid programs"""
        content = (TESTS_DIR / "invalid-programs.txt").read_text(encoding="utf-8")
        cases = [block.strip() for block in content.split("---") if block.strip()]
        print(f"  Assembler(Validating {len(cases)} invalid programs):", flush=True)
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "line") as ctx:
                    loader.assemble(source)
                print(f"    Invalid '{source.replace(chr(10), ' / ')}' -> {ctx.exception}", flush=True)

    def test_invalid_program_does_not_write_memory(self):
        """Memory protection on assembly failure"""
        with mock.patch.object(loader, "mem_write8") as write:
            with self.assertRaises(ValueError) as ctx:
                loader.load_program(None, str(TESTS_DIR / "invalid-program.txt"), 0)
            write.assert_not_called()
            print(f"  Assembler(Memory writes):\n    {write.call_count} {ctx.exception}", flush=True)


class SimicsTests(unittest.TestCase):
    def invoke_simics(self, program, *commands, address=0):
        command = [str(ROOT / "simics.bat"), "--batch-mode", "--no-win",
                   str(ROOT / "targets" / "rv32i" / "rv32-atomic.simics"),
                   "program=" + str(program), "load_address=" + str(address)]
        for item in commands:
            command.extend(["-e", item])
        return subprocess.run(command, cwd=ROOT, capture_output=True,
                              text=True, timeout=60)

    def run_program(self, program, address=0):
        result = self.invoke_simics(
            program, "run", "pregs",
            "@print(conf.cosim0.iface.cycle.get_cycle_count(),"
            "conf.cosim0.iface.step.get_step_count())", address=address)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ebreak", result.stdout)
        registers = {int(name): int(value, 16) for name, value in
                     re.findall(r"x(\d+)\s*=\s*0x([0-9a-fA-F]+)", result.stdout)}
        pc = re.search(r"pc\s*=\s*0x([0-9a-fA-F]+)", result.stdout)
        self.assertEqual(len(registers), 32, result.stdout)
        self.assertIsNotNone(pc, result.stdout)
        counts = re.search(r"^(\d+) (\d+)\s*$", result.stdout, re.MULTILINE)
        self.assertIsNotNone(counts, result.stdout)
        return registers, int(pc.group(1), 16), tuple(map(int, counts.groups()))

    def test_all_instructions(self):
        """Full RV32I instruction set execution"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        registers, pc, counts = self.run_program(prog)
        print(f"  Simics({prog.name}): PC=0x{pc:08x} | Cycles={counts[0]}, Steps={counts[1]}", flush=True)
        print("    Registers:", ", ".join(f"x{i}=0x{registers[i]:x}" for i in range(32)), flush=True)
        expected = [0, 0x12345000, 4, 100, 0xfffffff9, 1, 0, 0x9b,
                    0x764, 0xf0, 0x640, 15, 0xfffffffc, 93, 0xffffff95,
                    200, 1, 0, 0xffffff9d, 0x7ffffffc, 0xfffffffc,
                    0xf4, 0x60, 6, 0, 0xbc, 0xc0, 0xc8, 100, 0, 0, 0]
        self.assertEqual([registers[i] for i in range(32)], expected)
        self.assertEqual(pc, 0xd4)
        self.assertEqual(counts, (46, 46))

    def test_backward_branch_and_jump(self):
        """Backward branches and control flow"""
        prog = TESTS_DIR / "control-flow.txt"
        registers, pc, counts = self.run_program(prog)
        subset = {r: f"0x{registers[r]:x}" for r in (0, 1, 5, 6, 10, 11, 12, 13, 14, 15)}
        print(f"  Simics({prog.name}): PC=0x{pc:08x} | Cycles={counts[0]}, Steps={counts[1]} | Subset={subset}", flush=True)
        for register, value in {0: 0, 1: 44, 5: 0, 6: 3, 10: 0xffffffff,
                                11: 0, 12: 0xffffffff, 13: 1, 14: 7, 15: 56}.items():
            self.assertEqual(registers[register], value, "x%d" % register)
        self.assertEqual(pc, 60)
        self.assertEqual(counts, (20, 20))

    def test_nonzero_load_address(self):
        """Non-zero base load address execution (0x100)"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        registers, pc, counts = self.run_program(prog, 0x100)
        print(f"  Simics(load_address=0x100): PC=0x{pc:08x} | Cycles={counts[0]}, Steps={counts[1]} | "
              f"x2=0x{registers[2]:x}, x25=0x{registers[25]:x}, x26=0x{registers[26]:x}, x27=0x{registers[27]:x}", flush=True)
        self.assertEqual(registers[2], 0x104)
        self.assertEqual(registers[25], 0x1bc)
        self.assertEqual(registers[26], 0x1c0)
        self.assertEqual(registers[27], 0x1c8)
        self.assertEqual(pc, 0x1d4)
        self.assertEqual(counts, (46, 46))

    def test_single_step(self):
        """Single-step execution (stepi 1) and memory check"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        result = self.invoke_simics(
            prog, "stepi 1", "pregs",
            "@print(conf.cosim0.iface.cycle.get_cycle_count(),"
            "conf.cosim0.iface.step.get_step_count())",
            "@print(simics.SIM_read_phys_memory(conf.core0,0,4))")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        x1_match = re.search(r"x1\s*=\s*(0x[0-9a-fA-F]+)", result.stdout)
        pc_match = re.search(r"pc\s*=\s*(0x[0-9a-fA-F]+)", result.stdout)
        print(f"  Simics(single_step): x1={x1_match.group(1) if x1_match else '?'}, "
              f"pc={pc_match.group(1) if pc_match else '?'}", flush=True)
        self.assertRegex(result.stdout, r"x1\s*=\s*0x12345000")
        self.assertRegex(result.stdout, r"pc\s*=\s*0x00000004")
        self.assertRegex(result.stdout, r"(?m)^1 1$")
        self.assertRegex(result.stdout, r"(?m)^305418423$")

    def test_misaligned_jump_does_not_write_link_register(self):
        """Halt on misaligned jump without overwriting link register"""
        prog = TESTS_DIR / "misaligned-jump.txt"
        result = self.invoke_simics(prog, "run", "pregs")
        combined = result.stdout + result.stderr
        msg = next((line.strip() for line in combined.splitlines() if "misaligned instruction address" in line), "")
        print(f"  Simics({prog.name}): Halted with: '{msg}'", flush=True)
        self.assertIn("misaligned instruction address", combined)
        self.assertRegex(result.stdout, r"x1\s*=\s*0x00000007")
        self.assertRegex(result.stdout, r"pc\s*=\s*0x00000004")

    def test_illegal_instruction_stops(self):
        """Halt on illegal or unsupported instruction"""
        prog = TESTS_DIR / "illegal.txt"
        result = self.invoke_simics(prog, "run", "pregs")
        combined = result.stdout + result.stderr
        msg = next((line.strip() for line in combined.splitlines() if "illegal or unsupported instruction" in line), "")
        print(f"  Simics({prog.name}): Halted with: '{msg}'", flush=True)
        self.assertIn("illegal or unsupported instruction", combined)
        self.assertNotIn("ebreak", result.stdout)


if __name__ == "__main__":
    unittest.main(testRunner=TestRunner)