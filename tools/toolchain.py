#!/usr/bin/env python3
"""Small offline launch/check helpers; only setup may initialize from remotes."""
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "zookeeper-tla-spec"
RUNNER = SPEC / "low-level-spec/zk-3.7/check_connecting_quorum.py"
JAR = ROOT / "tla-bin/tla2tools.jar"
ARCHIVE = ROOT / "apalache.tgz"
APALACHE = ROOT / ".tools/apalache/lib/apalache.jar"
HASHES = {
    JAR: "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88",
    ARCHIVE: "95746f11062b2dea716052c8f03258496a194afc4e9dd29e985f488ea3e90b76",
    APALACHE: "079b6c2320252469dcf79afec6886b8255d3dd1b34a9484433c88986752efaa8",
}


def checked(path):
    if not path.is_file():
        raise RuntimeError(f"Missing tool payload: {path}; run task setup")
    with path.open("rb") as stream:
        if stream.read(100).startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise RuntimeError(f"Git LFS pointer, not a tool: {path}; run task setup to hydrate")
        stream.seek(0)
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != HASHES[path]:
        raise RuntimeError(f"Checksum mismatch: {path}; expected {HASHES[path]}, got {actual}. "
                           "Preserve/inspect local changes before restoring the pinned payload.")
    return path


def run(command, **kwargs):
    print("+ " + repr([str(arg) for arg in command]), flush=True)
    return subprocess.run(command, check=True, **kwargs)


def prerequisites():
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12+ required")
    for program in ("git", "java", "task"):
        if not shutil.which(program):
            raise RuntimeError(f"Missing prerequisite on PATH: {program}; install it separately")
    for command in (["git", "--version"], ["git", "lfs", "version"],
                    ["task", "--version"], ["java", "-version"]):
        run(command)
    print(sys.version)


def submodule():
    if not (SPEC / ".git").exists() or not RUNNER.is_file():
        raise RuntimeError("Missing verification submodule/runner; run task setup")
    expected = subprocess.check_output(
        ["git", "rev-parse", "HEAD:zookeeper-tla-spec"], cwd=ROOT, text=True).strip()
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SPEC, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=SPEC, text=True)
    print(f"Spec HEAD: {actual}; parent pin: {expected}")
    if dirty or actual != expected:
        print("WARNING: preserving existing submodule edits/commit drift; results use this working tree.")


def setup():
    prerequisites()
    # Configure only this repository's filters. Do not replace custom hooks.
    run(["git", "lfs", "install", "--local", "--skip-repo"], cwd=ROOT)
    hydrate = []
    for path in (JAR, ARCHIVE):
        if not path.exists():
            hydrate.append(path.relative_to(ROOT).as_posix())
        else:
            with path.open("rb") as stream:
                pointer = stream.read(100).startswith(b"version https://git-lfs.github.com/spec/v1")
            if pointer:
                hydrate.append(path.relative_to(ROOT).as_posix())
            else:
                checked(path)  # Never overwrite corrupt or intentionally modified payloads.
    if hydrate:
        run(["git", "lfs", "pull", "--include=" + ",".join(hydrate), "--exclude="], cwd=ROOT)
    checked(JAR)
    checked(ARCHIVE)
    if not (SPEC / ".git").exists():
        if SPEC.exists() and any(SPEC.iterdir()):
            raise RuntimeError("Uninitialized submodule directory is nonempty; preserve it and resolve manually")
        run(["git", "submodule", "update", "--init", "--", "zookeeper-tla-spec"], cwd=ROOT)
    submodule()  # Existing initialized submodules are never updated/reset.
    destination = ROOT / ".tools/apalache"
    if destination.exists():
        checked(APALACHE)
    else:
        destination.parent.mkdir(exist_ok=True)
        # Validate the exact small package layout, and publish only complete extraction.
        files = {"apalache/bin/apalache-mc", "apalache/bin/apalache-mc.bat",
                 "apalache/LICENSE", "apalache/lib/apalache.jar"}
        dirs = {"apalache", "apalache/bin", "apalache/lib"}
        with tempfile.TemporaryDirectory(dir=destination.parent, prefix="unpack-") as work:
            with tarfile.open(ARCHIVE, "r:gz") as archive:
                members = archive.getmembers()
                if ({m.name for m in members if m.isfile()} != files
                        or any(not ((m.isfile() and m.name in files) or
                                    (m.isdir() and m.name.rstrip("/") in dirs)) for m in members)):
                    raise RuntimeError("Unexpected Apalache archive layout")
                archive.extractall(work, filter="data")
            Path(work, "apalache").rename(destination)
        checked(APALACHE)
    print("Setup complete (no model checking; Remix is not needed or initialized).")


def java_command(tool, arguments, scratch):
    java = ["java", "-Xmx512m", "-XX:+UseParallelGC", f"-Djava.io.tmpdir={scratch}"]
    if tool == "apalache":
        checked(APALACHE)
        # The supplied launcher's unquoted temp path breaks with spaces; use argv,
        # retaining its Java compatibility probe and a bounded heap instead.
        probe = subprocess.run(["java", "--sun-misc-unsafe-memory-access=allow", "-version"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode == 0:
            java.append("--sun-misc-unsafe-memory-access=allow")
        output = [] if arguments == ["version"] else [f"--out-dir={ROOT / '.tool-results/apalache'}"]
        return java + ["-jar", str(APALACHE), *output, *arguments]
    checked(JAR)
    return java + ["-cp", str(JAR), {"tlc": "tlc2.TLC", "sany": "tla2sany.SANY"}[tool], *arguments]


def scratch_base():
    path = Path(os.environ.get("TMPDIR") or Path.home() / "tmp" / "pi").expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def tool(tool_name, arguments, cwd=ROOT, timeout=None):
    if not shutil.which("java"):
        raise RuntimeError("Java required on PATH")
    with tempfile.TemporaryDirectory(prefix="tla-java-", dir=scratch_base()) as scratch:
        command = java_command(tool_name, arguments, scratch)
        print("+ " + repr(command), flush=True)
        process = subprocess.Popen(command, cwd=cwd, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise RuntimeError(f"{tool_name} interrupted or exceeded {timeout}s limit")
        # This pinned TLC prints successful help with exit 1 (not a model result).
        if code and not (tool_name == "tlc" and arguments == ["-help"] and code == 1):
            raise subprocess.CalledProcessError(code, command)


def smoke():
    results = ROOT / ".tool-results"
    results.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="smoke-", dir=results) as work:
        work = Path(work)
        for name in ("ToolSmoke.tla", "ToolSmoke.cfg"):
            shutil.copy2(ROOT / "tools" / name, work / name)
        tool("sany", ["ToolSmoke.tla"], cwd=work, timeout=30)
        tool("tlc", ["-workers", "1", "-fp", "0", "-cleanup", "-checkpoint", "0",
                     "-config", "ToolSmoke.cfg", "ToolSmoke"], cwd=work, timeout=60)
        tool("apalache", ["check", "--length=3", "--timeout-smt=10", "--inv=TypeOK",
                          "ToolSmoke.tla"], cwd=work, timeout=120)


def main():
    command, *arguments = sys.argv[1:]
    if command == "setup":
        setup()
    elif command == "doctor":
        prerequisites()
        for path in HASHES:
            checked(path)
            print(f"SHA256 OK: {path}")
        submodule()
        tool("tlc", ["-help"], timeout=30)
        tool("apalache", ["version"], timeout=30)
    elif command in ("tlc", "sany", "apalache"):
        if not arguments:
            raise RuntimeError(f"Arguments required; use task {command} -- <arguments>")
        tool(command, arguments)
    elif command == "smoke":
        smoke()
    elif command in ("verify", "test"):
        submodule()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        if command == "verify":
            checked(JAR)
            run([sys.executable, str(RUNNER), "--jar", str(JAR), *arguments], cwd=ROOT, env=env)
        else:
            run([sys.executable, "-m", "unittest", "discover", "-s", str(RUNNER.parent),
                 "-p", "test_*.py", "-v"], cwd=ROOT, env=env)
            run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tools"),
                 "-p", "test_*.py", "-v"], cwd=ROOT, env=env)
    else:
        raise RuntimeError(f"Unknown command: {command}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
