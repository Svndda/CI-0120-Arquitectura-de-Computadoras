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
        self.stream.writeln("  Resultado: OK")
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


class AssemblerTests(unittest.TestCase):
    def test_known_encodings(self):
        """Codificaciones conocidas de instrucciones"""
        source = (TESTS_DIR / "known-encodings.txt").read_text(encoding="utf-8")
        expected = [0x123450b7, 0x06400193, 0x40320733, 0x40125613,
                    0x01028463, 0x00800cef, 0x00dd0de7, 0x00100073]
        assembled = loader.assemble(source)
        print("  Ensamblador(Codificaciones generadas):", flush=True)
        print(f"    {len(assembled)} bytes, {assembled.hex()} hex", flush=True)
        for i, (exp, got) in enumerate(zip(expected, assembled)):
            _print_expected_vs_actual(
                f"instruccion[{i}]", exp, int.from_bytes(assembled[i*4:i*4+4], "little")
            )
        self.assertEqual(assembled,
                         b"".join(word.to_bytes(4, "little") for word in expected))

    def test_labels_and_aliases(self):
        """Resolución de etiquetas y alias de registros"""
        source = (TESTS_DIR / "labels-and-aliases.txt").read_text(encoding="utf-8")
        assembled = loader.assemble(source)
        print(f"  Ensamblador(Etiquetas y alias ensamblados): {assembled.hex()}", flush=True)
        expected = bytes.fromhex("93021000e39e02fe")
        self.assertEqual(assembled, expected)

    def test_invalid_programs_are_rejected(self):
        """Rechazo de programas inválidos"""
        content = (TESTS_DIR / "invalid-programs.txt").read_text(encoding="utf-8")
        cases = [block.strip() for block in content.split("---") if block.strip()]
        print(f"  Ensamblador(Validando {len(cases)} programas inválidos):", flush=True)
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "line") as ctx:
                    loader.assemble(source)
                print(f"    Inválido '{source.replace(chr(10), ' / ')}' -> {ctx.exception}", flush=True)

    def test_invalid_program_does_not_write_memory(self):
        """Protección de memoria ante fallo de ensamblado"""
        with mock.patch.object(loader, "mem_write8") as write:
            with self.assertRaises(ValueError) as ctx:
                loader.load_program(None, str(TESTS_DIR / "invalid-program.txt"), 0)
            write.assert_not_called()
            print("  Ensamblador(Escrituras en memoria):", flush=True)
            print(f"    {write.call_count} escrituras (esperado: 0)", flush=True)
            print(f"    Excepción: {ctx.exception}", flush=True)


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
        print(f"  Simics({program.name}): PC=0x{int(pc.group(1), 16):08x} | "
              f"Ciclos={counts.group(1)}, Pasos={counts.group(2)}", flush=True)
        print(f"    Registros: {_fmt_regs(registers)}", flush=True)
        return registers, int(pc.group(1), 16), tuple(map(int, counts.groups()))

    def test_all_instructions(self):
        """Ejecución completa del conjunto de instrucciones RV32I"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        registers, pc, counts = self.run_program(prog)
        expected = [0, 0x12345000, 4, 100, 0xfffffff9, 1, 0, 0x9b,
                    0x764, 0xf0, 0x640, 15, 0xfffffffc, 93, 0xffffff95,
                    200, 1, 0, 0xffffff9d, 0x7ffffffc, 0xfffffffc,
                    0xf4, 0x60, 6, 0, 0xbc, 0xc0, 0xc8, 100, 0, 0, 0]
        print("  Comparación registro a registro:", flush=True)
        all_ok = True
        for i in range(32):
            ok = registers[i] == expected[i]
            if not ok:
                all_ok = False
            _print_expected_vs_actual(f"x{i}", expected[i], registers[i], ok)
        self.assertEqual([registers[i] for i in range(32)], expected)
        self.assertEqual(pc, 0xd4)
        self.assertEqual(counts, (46, 46))
        _print_expected_vs_actual("PC", 0xd4, pc, pc == 0xd4)
        _print_expected_vs_actual("Ciclos", 46, counts[0], counts[0] == 46)
        _print_expected_vs_actual("Pasos", 46, counts[1], counts[1] == 46)

    def test_backward_branch_and_jump(self):
        """Ramas hacia atrás y control de flujo"""
        prog = TESTS_DIR / "control-flow.txt"
        registers, pc, counts = self.run_program(prog)
        expected = {0: 0, 1: 44, 5: 0, 6: 3, 10: 0xffffffff,
                    11: 0, 12: 0xffffffff, 13: 1, 14: 7, 15: 56}
        print("  Registros clave esperados vs obtenidos:", flush=True)
        for reg, exp_val in sorted(expected.items()):
            ok = registers[reg] == exp_val
            _print_expected_vs_actual(f"x{reg}", exp_val, registers[reg], ok)
        self.assertEqual(pc, 60)
        self.assertEqual(counts, (20, 20))
        _print_expected_vs_actual("PC", 60, pc, pc == 60)
        _print_expected_vs_actual("Ciclos", 20, counts[0], counts[0] == 20)
        _print_expected_vs_actual("Pasos", 20, counts[1], counts[1] == 20)

    def test_nonzero_load_address(self):
        """Ejecución con dirección de carga distinta de cero (0x100)"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        registers, pc, counts = self.run_program(prog, 0x100)
        expected = {2: 0x104, 25: 0x1bc, 26: 0x1c0, 27: 0x1c8}
        print("  Registros clave (dirección base 0x100):", flush=True)
        for reg, exp_val in sorted(expected.items()):
            ok = registers[reg] == exp_val
            _print_expected_vs_actual(f"x{reg}", exp_val, registers[reg], ok)
        self.assertEqual(pc, 0x1d4)
        self.assertEqual(counts, (46, 46))
        _print_expected_vs_actual("PC", 0x1d4, pc, pc == 0x1d4)

    def test_single_step(self):
        """Ejecución monopaso (stepi 1) y verificación de memoria"""
        prog = ROOT / "targets" / "rv32i" / "programs" / "all-instructions.txt"
        result = self.invoke_simics(
            prog, "stepi 1", "pregs",
            "@print(conf.cosim0.iface.cycle.get_cycle_count(),"
            "conf.cosim0.iface.step.get_step_count())",
            "@print(simics.SIM_read_phys_memory(conf.core0,0,4))")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        x1_match = re.search(r"x1\s*=\s*(0x[0-9a-fA-F]+)", result.stdout)
        pc_match = re.search(r"pc\s*=\s*(0x[0-9a-fA-F]+)", result.stdout)
        x1_val = int(x1_match.group(1), 16) if x1_match else None
        pc_val = int(pc_match.group(1), 16) if pc_match else None
        print(f"  Simics(paso único): x1={hex(x1_val) if x1_val else '?'}, "
              f"pc={hex(pc_val) if pc_val else '?'}", flush=True)
        self.assertRegex(result.stdout, r"x1\s*=\s*0x12345000")
        self.assertRegex(result.stdout, r"pc\s*=\s*0x00000004")
        self.assertRegex(result.stdout, r"(?m)^1 1$")
        self.assertRegex(result.stdout, r"(?m)^305418423$")

    def test_misaligned_jump_does_not_write_link_register(self):
        """Detención por salto desalineado sin sobrescribir registro de enlace"""
        prog = TESTS_DIR / "misaligned-jump.txt"
        result = self.invoke_simics(prog, "run", "pregs")
        combined = result.stdout + result.stderr
        msg = next((line.strip() for line in combined.splitlines()
                    if "misaligned instruction address" in line), "")
        print(f"  Simics({prog.name}): Detenido con: '{msg}'", flush=True)
        self.assertIn("misaligned instruction address", combined)
        self.assertRegex(result.stdout, r"x1\s*=\s*0x00000007")
        self.assertRegex(result.stdout, r"pc\s*=\s*0x00000004")

    def test_illegal_instruction_stops(self):
        """Detención ante instrucción ilegal o no soportada"""
        prog = TESTS_DIR / "illegal.txt"
        result = self.invoke_simics(prog, "run", "pregs")
        combined = result.stdout + result.stderr
        msg = next((line.strip() for line in combined.splitlines()
                    if "illegal or unsupported instruction" in line), "")
        print(f"  Simics({prog.name}): Detenido con: '{msg}'", flush=True)
        self.assertIn("illegal or unsupported instruction", combined)
        self.assertNotIn("ebreak", result.stdout)


if __name__ == "__main__":
    unittest.main(testRunner=TestRunner)
