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


def _fmt_regs(registers):
    """Devuelve una cadena legible con los 32 registros."""
    return ", ".join(f"x{i}=0x{registers[i]:08x}" for i in range(32))


def _print_expected_vs_actual(name, expected, actual, ok=True):
    """Imprime en consola el valor esperado vs el obtenido."""
    status = "OK" if ok else "FALLO"
    print(
        f"    [{status}] {name}: esperado=0x{expected:08x}, obtenido=0x{actual:08x}",
        flush=True,
    )


class TestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity=0)
        self.test_number = 0

    def startTest(self, test):
        super().startTest(test)
        self.test_number += 1
        title = test.shortDescription() or test._testMethodName
        self.stream.writeln(f"\n=== Prueba #{self.test_number}: {title} ===")
        self.stream.flush()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.writeln("  Resultado: OK (APROBADO)")
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.writeln("  Resultado: FALLIDO")
        self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.writeln("  Resultado: ERROR")
        self.stream.flush()


class TestRunner(unittest.TextTestRunner):
    resultclass = TestResult


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
        pc_val = int(pc.group(1), 16)
        print(f"  Simics({target_script}, {program.name}): "
              f"PC=0x{pc_val:08x} | Ciclos={counts.group(1)}, Pasos={counts.group(2)}", flush=True)
        print(f"    Registros: {_fmt_regs(registers)}", flush=True)
        return registers, pc_val, tuple(map(int, counts.groups()))

    def _compare_cores(self, atomic_regs, atomic_pc, atomic_counts,
                       pipe_regs, pipe_pc, pipe_counts, prog_name):
        """Compara los resultados del core atómico vs el pipeline."""
        print(f"  Comparación ATOMICO vs PIPELINE ({prog_name}):", flush=True)
        all_ok = True
        for i in range(32):
            ok = atomic_regs[i] == pipe_regs[i]
            if not ok:
                all_ok = False
            _print_expected_vs_actual(
                f"x{i}", atomic_regs[i], pipe_regs[i], ok
            )
        pc_ok = atomic_pc == pipe_pc
        if not pc_ok:
            all_ok = False
        _print_expected_vs_actual("PC", atomic_pc, pipe_pc, pc_ok)
        cycles_ok = atomic_counts[0] != pipe_counts[0]
        print(f"    Ciclos: ATOMICO={atomic_counts[0]} vs PIPELINE={pipe_counts[0]} "
              f"(esperado: pipeline >= atomico)", flush=True)
        steps_ok = atomic_counts[1] == pipe_counts[1]
        if not steps_ok:
            all_ok = False
        _print_expected_vs_actual("Pasos", atomic_counts[1], pipe_counts[1], steps_ok)
        return all_ok

    def test_assembler_encodings_and_rejection(self):
        """Codificaciones del ensamblador y rechazo de inválidos"""
        source = (ATOMIC_TESTS_DIR / "known-encodings.txt").read_text(encoding="utf-8")
        expected = [0x123450b7, 0x06400193, 0x40320733, 0x40125613,
                    0x01028463, 0x00800cef, 0x00dd0de7, 0x00100073]
        print("  Ensamblador(Codificaciones generadas):", flush=True)
        print(f"    {len(loader.assemble(source))} bytes", flush=True)
        self.assertEqual(loader.assemble(source),
                         b"".join(w.to_bytes(4, "little") for w in expected))

        with mock.patch.object(loader, "mem_write8") as write:
            with self.assertRaises(ValueError):
                loader.load_program(None, str(ATOMIC_TESTS_DIR / "invalid-program.txt"), 0)
            write.assert_not_called()
            print("  Ensamblador(Escrituras en memoria en fallo): 0 (esperado)", flush=True)

    def test_stage_fill_latency_on_single_step(self):
        """Latencia de llenado del pipeline con stepi 1"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        result = self.invoke_simics(
            "rv32-pipeline.simics", prog, "stepi 1", "pregs",
            "@print(conf.cosim0.iface.cycle.get_cycle_count(),"
            "conf.cosim0.iface.step.get_step_count())",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        x1_match = re.search(r"x1\s*=\s*(0x[0-9a-fA-F]+)", result.stdout)
        pc_match = re.search(r"pc\s*=\s*(0x[0-9a-fA-F]+)", result.stdout)
        x1_val = int(x1_match.group(1), 16) if x1_match else None
        pc_val = int(pc_match.group(1), 16) if pc_match else None
        print(f"  Simics(paso único pipeline): x1={hex(x1_val) if x1_val else '?'}, "
              f"pc={hex(pc_val) if pc_val else '?'}", flush=True)
        self.assertRegex(result.stdout, r"x1\s*=\s*0x12345000")
        self.assertRegex(result.stdout, r"pc\s*=\s*0x00000004")
        self.assertRegex(result.stdout, r"(?m)^4 1$")
        print("    Ciclos=4 (latencia de llenado), Pasos=1 (una instrucción retirada)", flush=True)

    def test_equivalence_all_instructions(self):
        """Equivalencia: todos los instructions (atómico vs pipeline)"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        a_regs, a_pc, a_cnt = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self._compare_cores(a_regs, a_pc, a_cnt, p_regs, p_pc, p_cnt, "todas las instrucciones")
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        self.assertEqual(a_cnt, (46, 46))
        self.assertEqual(p_cnt, (65, 46))

    def test_equivalence_control_flow(self):
        """Equivalencia: control de flujo (atómico vs pipeline)"""
        prog = ATOMIC_TESTS_DIR / "control-flow.txt"
        a_regs, a_pc, a_cnt = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self._compare_cores(a_regs, a_pc, a_cnt, p_regs, p_pc, p_cnt, "control de flujo")
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        self.assertEqual(a_cnt, (20, 20))
        self.assertEqual(p_cnt, (31, 20))

    def test_nonzero_load_address(self):
        """Dirección de carga distinta de cero (0x100)"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog, 0x100)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog, 0x100)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, 0x1d4)
        self.assertEqual(p_cnt, (65, 46))
        print("  Registros clave (dirección base 0x100):", flush=True)
        for reg in (2, 25, 26, 27):
            ok = p_regs[reg] == a_regs[reg]
            _print_expected_vs_actual(f"x{reg}", a_regs[reg], p_regs[reg], ok)
        _print_expected_vs_actual("PC", 0x1d4, p_pc, p_pc == 0x1d4)

    def test_data_hazards_and_forwarding(self):
        """Peligros de datos y adelantamiento (forwarding)"""
        prog = PIPE_TESTS_DIR / "forwarding-hazards.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        expected = {3: 35, 4: 10, 6: 400, 9: 0, 10: 0, 13: 165, 15: 0}
        print("  Registros clave (forwarding):", flush=True)
        for reg, exp_val in sorted(expected.items()):
            ok = p_regs[reg] == exp_val
            _print_expected_vs_actual(f"x{reg}", exp_val, p_regs[reg], ok)
        self.assertEqual(p_cnt, (24, 19))

    def test_branch_shadow_squashing(self):
        """Anulación de instrucciones en sombra de rama"""
        prog = PIPE_TESTS_DIR / "branch-shadow.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, _ = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        expected = {10: 0, 11: 0, 12: 0, 13: 0, 6: 88}
        print("  Registros clave (sombra de rama):", flush=True)
        for reg, exp_val in sorted(expected.items()):
            ok = p_regs[reg] == exp_val
            _print_expected_vs_actual(f"x{reg}", exp_val, p_regs[reg], ok)

    def test_corner_cases(self):
        """Casos extremos (corner cases)"""
        prog = PIPE_TESTS_DIR / "corner-cases.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, p_cnt = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        self.assertEqual(p_cnt, (14, 11))

    def test_wb_stage_writeback_timing(self):
        """Etapa WB: escritura de resultado en 4 ciclos / 1 paso"""
        prog = PIPE_TESTS_DIR / "stage-wb.txt"
        result = self.invoke_simics(
            "rv32-pipeline.simics", prog, "stepi 1", "pregs",
            "@print(conf.cosim0.iface.cycle.get_cycle_count(),"
            "conf.cosim0.iface.step.get_step_count())",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"x1\s*=\s*0x0000002a")
        self.assertRegex(result.stdout, r"pc\s*=\s*0x00000004")
        self.assertRegex(result.stdout, r"(?m)^4 1$")
        print("  Simics(etapa WB): x1=0x0000002a (42), pc=0x00000004, ciclos=4, pasos=1", flush=True)

    def test_id_stage_rtype_funct7_decode(self):
        """Etapa ID: funct7 distingue sub de add con mismos operandos"""
        prog = PIPE_TESTS_DIR / "stage-id-decode.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, _ = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        _print_expected_vs_actual("x3 (add)", 13, p_regs[3], p_regs[3] == 13)
        _print_expected_vs_actual("x4 (sub)", 7, p_regs[4], p_regs[4] == 7)
        self.assertEqual(p_regs[3], 13)
        self.assertEqual(p_regs[4], 7)

    def test_ex_stage_forwarding_from_ex_wb(self):
        """Etapa EX: adelantamiento desde EX/WB a consumidor en EX"""
        prog = PIPE_TESTS_DIR / "stage-ex-forwarding.txt"
        a_regs, a_pc, _ = self.run_core("rv32-atomic.simics", prog)
        p_regs, p_pc, _ = self.run_core("rv32-pipeline.simics", prog)
        self.assertEqual(p_regs, a_regs)
        self.assertEqual(p_pc, a_pc)
        _print_expected_vs_actual("x1", 10, p_regs[1], p_regs[1] == 10)
        _print_expected_vs_actual("x2 (adelantado)", 20, p_regs[2], p_regs[2] == 20)
        self.assertEqual(p_regs[1], 10)
        self.assertEqual(p_regs[2], 20)

    def test_misaligned_jump_and_illegal_instruction(self):
        """Salto desalineado e instrucción ilegal"""
        misaligned = ATOMIC_TESTS_DIR / "misaligned-jump.txt"
        res_m = self.invoke_simics("rv32-pipeline.simics", misaligned, "run", "pregs")
        self.assertIn("misaligned instruction address", res_m.stdout + res_m.stderr)
        self.assertRegex(res_m.stdout, r"x1\s*=\s*0x00000007")
        self.assertRegex(res_m.stdout, r"pc\s*=\s*0x00000004")
        print(f"  Simics(salto desalineado): Detenido con 'misaligned instruction address'", flush=True)
        print(f"    x1=0x00000007, pc=0x00000004 (esperados)", flush=True)

        illegal = ATOMIC_TESTS_DIR / "illegal.txt"
        res_i = self.invoke_simics("rv32-pipeline.simics", illegal, "run", "pregs")
        self.assertIn("illegal or unsupported instruction", res_i.stdout + res_i.stderr)
        self.assertRegex(res_i.stdout, r"x1\s*=\s*0x00000007")
        self.assertRegex(res_i.stdout, r"pc\s*=\s*0x00000004")
        print(f"  Simics(instrucción ilegal): Detenido con 'illegal or unsupported instruction'", flush=True)
        print(f"    x1=0x00000007, pc=0x00000004 (esperados)", flush=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
