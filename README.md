# Repository-local TLA tooling

## Quick start

Prerequisites (install separately): Git, Git LFS 3+, [Task](https://taskfile.dev/)
3.x, Python 3.12+, and Java on PATH. Validated on Linux x86-64 with Git LFS
3.7.1, Task 3.52.0, Python 3.14 and OpenJDK 25. Other JVM/platform combinations
are not validated; Apalache bundles native solver libraries. No system installs,
`/usr/local` JAR, Go build, or mutable/latest tool downloads are used here.

```sh
git clone https://github.com/fanyang89/zookeeper-tla.git
cd zookeeper-tla
task setup
task verify
```

**Publication caveat:** this change was committed and tested only locally. The
remote quick start will work with these pins only after a maintainer separately
publishes the spec submodule commit, parent commit, and both Git LFS objects.
No push, PR, or LFS upload was performed as part of this work. An ordinary Git
push without the LFS objects is insufficient. Setup configures local LFS filters
with `git lfs install --local --skip-repo`; it deliberately does not install or
replace hooks. A future publisher must arrange their LFS pre-push integration or
explicit upload themselves.

## Tasks

| Task | Purpose / network |
| --- | --- |
| `task` | List commands only; no model run |
| `task setup` | May fetch **only pinned** missing/pointer LFS payloads and initialize the missing `zookeeper-tla-spec` submodule; unpacks Apalache under ignored `.tools/` |
| `task doctor` | Offline prerequisite versions, SHA-256 checks, spec state, TLC help/version and Apalache version; no model run |
| `task test` | Offline runner acceptance/portability and tooling regression tests |
| `task smoke` | Offline SANY plus tiny self-contained TLC and Apalache checks, not Zab |
| `task verify` | Offline existing 13 connecting-quorum TLC cases, including expected negative controls |
| `task tlc/sany/apalache -- ...` | Direct pinned tool invocation with explicit arguments; no setup/download implicitly |

Setup is repeatable: it does not re-extract a valid cache, overwrite a modified
payload, or update/reset an initialized submodule. Existing submodule edits or
commit drift are reported and preserved; verification uses that working tree,
not a silently forced clean revision. Missing prerequisites, missing submodule,
unhydrated LFS pointers and checksum mismatches fail with actionable errors.
Inspect and preserve modifications before manually restoring corrupt files or
removing/rebuilding `.tools/apalache`. Setup does not initialize Remix, which is
not required for these tasks. `.gitmodules` keeps portable HTTPS URLs.

```sh
task doctor
task test
task smoke
task tlc -- -help
task sany -- tools/ToolSmoke.tla
task apalache -- version
task apalache -- check --length=3 --timeout-smt=10 --inv=TypeOK tools/ToolSmoke.tla
task verify -- --case candidate-safety --seconds 60
```

Task runs commands from the checkout root. Quote paths with spaces normally
(e.g. `task sany -- 'path with spaces/Model.tla'`). Direct commands require
arguments and can run arbitrary user-requested models; they do **not** impose
a wall-clock bound. All launchers default to a 512 MiB Java heap. Smoke uses one
TLC worker, 3 reachable states, an Apalache length bound of 3 and SMT query limit
of 10 seconds, with SANY/TLC/Apalache wall-clock limits of 30/60/120 seconds.

Verification preserves the existing runner's depth 8 and 60-second **per case**
defaults (13 cases), one worker, 512 MiB heap, accepted TLC exit codes and named
counterexample checks. Override only within its documented bounds with arguments
after `--`. The root always supplies `--jar <checkout>/tla-bin/tla2tools.jar`;
standalone runner users may set `--jar` or `TLA2TOOLS_JAR` (CLI takes precedence;
the old `/usr/local/lib/tla2tools.jar` default remains for compatibility).

See the spec's
[connecting-quorum-timeout.md](zookeeper-tla-spec/low-level-spec/zk-3.7/connecting-quorum-timeout.md)
and [verification-statistics.md](zookeeper-tla-spec/low-level-spec/zk-3.7/verification-statistics.md)
for the existing safety/liveness caveats. Bounded evidence is not an unbounded
proof, fair-schedule resolution depends on fairness, and expected counterexamples
are successful negative controls, not infrastructure failures. Apalache smoke
validates only the tiny tooling fixture: **Apalache has not verified the existing
Zab spec or any proposed production Java path A**. No protocol or production Java
sources were changed for tool setup.

## Files, caches and provenance

Only `/apalache.tgz` and `/tla-bin/tla2tools.jar` are Git LFS-managed. `tla-bin/`
is a normal vendored directory, not a gitlink. Text, licenses and notices remain
normal Git; the extracted ~197 MB Apalache JAR is not tracked a second time.
See [tools/PROVENANCE.md](tools/PROVENANCE.md) for exact supplied checksums,
observed versions, source pin, licensing and unresolved binary provenance.
Do not use the retained upstream tla-bin install/download templates in this workflow.

Local extraction is in `.tools/`; smoke and default Apalache results are in
`.tool-results/` (ignored). Direct TLC uses the caller's model/output options;
root `states/` is ignored. Verification writes replayable sources, configs,
commands, logs and `summary.json` outside the spec repository, printing its path.
Scratch uses **the existing `TMPDIR`**, else `~/tmp/pi`; JVM scratch is temporary
and cleaned by the root helper. Runner evidence is retained. Use `--output` for a
new external result directory, e.g. `task verify -- --output "$HOME/tmp/pi/run-1"`.
No global Git settings or system configuration are changed.

## Reproduce the local-clone test before publication

Use a new directory, not the working tree being developed. Local file transport
is permitted **per command only** for the test. Do not commit machine-specific
submodule URLs or set global `protocol.file.allow`.

```sh
source_repo=/absolute/path/to/this/checkout
clone_dir="$HOME/tmp/pi/tla fresh clone"
GIT_LFS_SKIP_SMUDGE=1 git clone --no-hardlinks "$source_repo" "$clone_dir"
cd "$clone_dir"
# Temporary URL override lets setup find the unpublished spec commit locally.
# LFS pull reads payloads from this clone's local origin (not a hosted LFS server).
GIT_CONFIG_COUNT=2 \
GIT_CONFIG_KEY_0=submodule.zookeeper-tla-spec.url \
GIT_CONFIG_VALUE_0="$source_repo/zookeeper-tla-spec" \
GIT_CONFIG_KEY_1=protocol.file.allow GIT_CONFIG_VALUE_1=always task setup
task setup  # already hydrated/initialized: no fetch, no checkout/reset
task doctor
task test
task smoke
task verify
git lfs fsck
git show HEAD:apalache.tgz
git show HEAD:tla-bin/tla2tools.jar
```

The last two commands must show small Git LFS pointer text (SHA-256 oid and size),
not binary data. LFS checkout files and extracted tools in the new clone must be
real independent files, not symlinks back to the source checkout. This validates
local clone readiness, not hosted availability or an upstream binary signature.
