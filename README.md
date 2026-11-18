# port8

**Find what breaks when you move QNX SDP 7.1 code to QNX SDP 8.0, before you run the compiler.**

QNX OS 8.0 drops Interrupt Service Routines, makes receive IDs 64-bit, moves message queues into the kernel, reserves priorities 254 and 255 and changes a dozen other things. They are all in the [Migrating to QNX OS 8.0](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxsdp.migration/topic/kernel.html) guide, spread across pages. port8 turns that guide into a host-side checker: point it at a driver, a resource manager or a BSP buildfile and it lists each breakage with the line, the fix and the documentation page it comes from.

Built for the **QNX Global Hackathon 2026**, category **Developer Tooling & Host Tools**.

```
$ port8 tests/fixtures/legacy-driver
uart_intr.c:31:14  error  Q8001  InterruptAttach() family removed (ISRs are not supported)
    irq_id = InterruptAttach(UART_IRQ, uart_isr, NULL, 0, _NTO_INTR_FLAGS_TRK_MSK);
    fix: Use InterruptAttachThread() and InterruptWait(), or InterruptAttachEvent() and call InterruptUnmask() after each event.
...
port8: scanned 3 files: 6 errors, 4 warnings, 1 notes
```

## What it checks

Each rule is taken from the QNX SDP 8.0 documentation. If the docs do not say it, port8 does not flag it. `port8 --rules` prints every rule with its source.

| Rule | Severity | What changed in 8.0 |
| --- | --- | --- |
| Q8001 | error | `InterruptAttach()`, `InterruptAttachArray()`, `InterruptHookIdle2()`, `InterruptHookTrace()` removed; ISRs unsupported |
| Q8002 | error | `PROCMGR_AID_INTERRUPTEVENT` discontinued (auto-fix to `PROCMGR_AID_INTERRUPT`) |
| Q8003 | warning | `PROCMGR_AID_XTHREAD_THREADCTL` discontinued |
| Q8004 | error | Runtime `ClockPeriod()` changes unsupported; use procnto `-C` |
| Q8005 | error | `MsgKeyData()` unsupported |
| Q8006 | error | `libmq` unsupported; message queues are in the kernel (Makefiles, buildfiles) |
| Q8007 | warning | Receive IDs are 64-bit `rcvid_t`, not `int` (auto-fix for single declarations, adds the 7.1 compatibility typedef) |
| Q8008 | warning | `pthread_rwlockattr_{get,set}clock()` replaced by `pthread_rwlock_clock{rd,wr}lock()` |
| Q8009 | error | `_NTO_COF_UNREGEVENTS` unsupported; register events |
| Q8010 | warning | `ThreadCreate()` needs a pre-allocated stack |
| Q8011 | warning | Priorities 255 (IPIs) and 254 (clock IST) are reserved |
| Q8012 | info | `qtime->nsec` obsolete; use `clock_gettime_ns()` and friends |
| Q8013 | info | Runmasks need a matching cluster defined at boot (`startup -c`) |
| Q8014 | info | `InterruptAttachEvent()` with a non-interrupt event adds latency; prefer `InterruptAttachThread()` |
| Q8015 | warning | Sync primitives in shared memory need `PTHREAD_PROCESS_SHARED` |
| Q8101 | warning | buildfile: procnto `-n` is ignored |
| Q8102 | info | buildfile: review procnto `-m` options; superlocking ones must go |
| Q8103 | error | buildfile: procnto `-U` unsupported |

Comments and string literals are stripped before matching, with line and column positions kept, so `/* InterruptAttach() */` or a log message is never flagged.

## Use

```bash
pip install git+https://github.com/Shine-5705/port8
port8 path/to/driver                 # human report, exit 1 on errors
port8 . --format sarif > port8.sarif # GitHub code scanning
port8 . --format md                  # paste into a PR or wiki
port8 . --fix                        # safe rewrites only: Q8002, Q8007
port8 --rules                        # every rule and its QNX 8.0 doc page
```

In GitHub Actions:

```yaml
- uses: Shine-5705/port8@main
  with: { path: src, fail-on: error }
```

## How this targets QNX 8.0

- The rules encode the QNX SDP 8.0 migration guide and Programmer's Guide; every finding links its page.
- `examples/qnx8-ist/` is the QNX 8.0 interrupt-service-thread pattern from the Programmer's Guide with a `qcc` Makefile, and port8 reports it clean.
- Build and run instructions for the target side: QNX SDP 8.0, `qcc -Vgcc_ntox86_64`, target x86_64 QEMU image from `mkqnximage`. The qcc build of the example has not been run yet, because the SDK needs a myQNX licence (see Honest status).

## Develop

```bash
python3 -m unittest discover -s tests -v   # 6 tests, standard library only
```

## Honest status

- port8 runs on Linux, macOS and Windows with Python 3.9+ and no dependencies. Tests pass.
- The fixtures in `tests/fixtures` are hand-written samples, not code from any QNX BSP.
- Matching is pattern-based, not a full C parser. It is tuned to have no false positives on the samples and the QNX 8.0 example. Expect some on unusual macro-heavy code; please open an issue.
- Not yet done: building `examples/qnx8-ist` with qcc and running a ported driver on a QNX 8.0 QEMU target. Both need the QNX SDP 8.0 SDK from a myQNX account.

## License

Apache-2.0.
