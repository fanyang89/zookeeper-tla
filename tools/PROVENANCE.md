# Pinned, supplied tool inputs

These are byte-for-byte local inputs, not downloads performed by setup. SHA-256
values record the supplied bytes; they are **not upstream checksum/signature
verification**. No upstream release source has been established for either binary.

| File | Observed version | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `tla-bin/tla2tools.jar` | TLC 2.19, 08 August 2024 (`tlc2.TLC -help`) | 2274532 | `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88` |
| `apalache.tgz` | bundled JAR reports 0.62.2 | 192004307 | `95746f11062b2dea716052c8f03258496a194afc4e9dd29e985f488ea3e90b76` |
| extracted `apalache/lib/apalache.jar` (ignored, never committed separately) | manifest Implementation-Version/Specification-Version 0.62.2; CLI `version` 0.62.2 | 196982672 | `079b6c2320252469dcf79afec6886b8255d3dd1b34a9484433c88986752efaa8` |

The Apalache manifest identifies the Apalache Development Team and
`https://github.com/apalache-mc/apalache`. This identifies the software, **not**
the source commit or origin of this particular supplied build. Its archive
contains only directories, two launchers, LICENSE and the JAR. All are retained
unaltered in the LFS archive. `APALACHE-LICENSE` is an exact normal-Git copy of
that LICENSE. Embedded dependency notices remain in the original JARs.

`tla-bin/` is an ordinary vendored directory, based on
`https://github.com/pmer/tla-bin.git` at
`91d5e51a4f29426b5273704628f755f8ee325900`. The MIT LICENSE, README and upstream
install/download templates are retained. Only `.gitignore` was changed to permit
tracking the supplied JAR. The JAR was ignored/untracked upstream, so that source
commit does not establish its binary provenance. The former nested `.git` was
moved intact to a durable external backup during import (path in implementation
report); it is not part of this repository or another submodule.

Do **not** run the upstream `install.sh` or `download_or_update_tla.sh` for this
workflow: those use an installation PREFIX and/or mutable remote releases. Root
Task commands use absolute checkout-local JAR paths. Apalache is invoked with a
space-safe Java argv instead of the supplied bash launcher (whose temporary-path
argument is unquoted), retaining its Java compatibility probe but limiting heap
to 512 MiB instead of the launcher's 4 GiB default. The archive itself is unchanged.
