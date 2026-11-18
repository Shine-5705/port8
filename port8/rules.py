"""Migration rules from QNX SDP 7.1 to QNX SDP 8.0.

Every rule cites the QNX SDP 8.0 documentation page it is derived from. Nothing here is guessed:
if the docs do not say it, port8 does not flag it.
"""
import re

DOC_KERNEL = "https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxsdp.migration/topic/kernel.html"
DOC_BSP = "https://www.qnx.com/developers/docs/8.0/com.qnx.doc.qnxsdp.migration/topic/bsps.html"
DOC_IST = "https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.prog/topic/inthandler_Thread_or_Event.html"

C_EXT = (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh")
BUILD_EXT = (".build",)
MAKE_NAMES = ("Makefile", "common.mk", "CMakeLists.txt")


class Rule:
    def __init__(self, id, severity, title, pattern, advice, doc, applies="c", fix=None):
        self.id, self.severity, self.title = id, severity, title
        self.pattern = re.compile(pattern)
        self.advice, self.doc, self.applies, self.fix = advice, doc, applies, fix


RULES = [
    Rule("Q8001", "error", "InterruptAttach() family removed (ISRs are not supported)",
         r"\bInterruptAttach(Array)?\s*\(|\bInterruptHook(Idle2|Trace)\s*\(",
         "Use InterruptAttachThread() and InterruptWait(), or InterruptAttachEvent() and call InterruptUnmask() after each event.",
         DOC_KERNEL),
    Rule("Q8002", "error", "PROCMGR_AID_INTERRUPTEVENT is discontinued",
         r"\bPROCMGR_AID_INTERRUPTEVENT\b",
         "Processes only need PROCMGR_AID_INTERRUPT to attach to interrupts.", DOC_KERNEL,
         fix=(r"\bPROCMGR_AID_INTERRUPTEVENT\b", "PROCMGR_AID_INTERRUPT")),
    Rule("Q8003", "warning", "PROCMGR_AID_XTHREAD_THREADCTL is discontinued",
         r"\bPROCMGR_AID_XTHREAD_THREADCTL\b",
         "ThreadCtlExt() no longer needs this ability; remove it from ability lists and security policies.", DOC_KERNEL),
    Rule("Q8004", "error", "Changing the clock period at runtime is not supported",
         r"\bClockPeriod(_r)?\s*\(",
         "Remove runtime ClockPeriod() changes; configure with the procnto-smp-instr -C option instead. Reading the period is fine, but procnto is now tickless.",
         DOC_KERNEL),
    Rule("Q8005", "error", "MsgKeyData() is no longer supported",
         r"\bMsgKeyData\s*\(", "Remove MsgKeyData() and use a different integrity check for message payloads.", DOC_KERNEL),
    Rule("Q8006", "error", "libmq is no longer supported (message queues are in the kernel)",
         r"(-lmq\b|\blibmq\b|LIBS\s*\+?=.*\bmq\b)",
         "Drop libmq from link lines and buildfiles; the POSIX mq_* API is served by the kernel.", DOC_KERNEL, applies="build"),
    Rule("Q8007", "warning", "Receive ID stored as int; QNX 8.0 uses 64-bit rcvid_t",
         r"(?<!typedef )\b(?:unsigned\s+)?int\s+(?:\**\s*\w+\s*(?:=[^,;]*)?,\s*)*\**\s*\w*rcvid(?!_t\b)\w*\b",
         "Declare receive IDs as rcvid_t. For dual 7.1/8.0 builds add: #ifndef __RCVID_T_SIZE / typedef int rcvid_t; / #endif.",
         DOC_KERNEL, fix=(r"(?<!typedef )\b(?:unsigned\s+)?int(\s+\w*rcvid(?!_t\b)\w*\s*[;=])", r"rcvid_t\1")),
    Rule("Q8008", "warning", "pthread_rwlockattr_{get,set}clock() replaced",
         r"\bpthread_rwlockattr_(get|set)clock\s*\(",
         "Use pthread_rwlock_clockrdlock() / pthread_rwlock_clockwrlock().", DOC_KERNEL),
    Rule("Q8009", "error", "Unregistered events from other processes are not supported",
         r"\b_NTO_COF_UNREGEVENTS\b",
         "Register events with MsgRegisterEvent() and drop _NTO_COF_UNREGEVENTS.", DOC_KERNEL),
    Rule("Q8010", "warning", "ThreadCreate() must be passed a pre-allocated stack",
         r"\bThreadCreate(_r)?\s*\(",
         "Pass a pre-allocated stack in the thread attributes, or use pthread_create(), which allocates one for you.", DOC_KERNEL),
    Rule("Q8011", "warning", "Priority 254/255 is reserved",
         r"(sched_priority\s*=\s*25[45]\b|pthread_setschedprio\s*\([^,]+,\s*25[45]\s*\)|SchedSet\s*\([^;]*\b25[45]\b)",
         "255 is reserved for IPIs and 254 by default for the clock IST. Use 253 or lower.", DOC_KERNEL),
    Rule("Q8012", "info", "qtime->nsec is obsolete",
         r"\bqtime\s*->\s*nsec\b",
         "Use clock_gettime_ns(), clock_gettime_mon_ns() or clock_gettime_rt_ns() for hardware-granularity time.", DOC_KERNEL),
    Rule("Q8013", "info", "Runmask needs a matching cluster in QNX 8.0",
         r"\b_NTO_TCTL_RUNMASK(_GET_AND_SET(_INHERIT)?)?\b",
         "Define a cluster for this runmask at boot with the startup -c option; runmasks can only be set on the active thread.", DOC_KERNEL),
    Rule("Q8014", "info", "InterruptAttachEvent() with a non-interrupt event adds latency",
         r"\bInterruptAttachEvent\s*\(",
         "Prefer InterruptAttachThread() (lowest overhead), or pass a SIGEV_INTR_INIT() event. Other event types create a kernel-persona thread.", DOC_IST),
    # buildfile rules
    Rule("Q8101", "warning", "procnto -n is ignored (lazy stack allocation disabled)",
         r"\bprocnto[\w-]*\b[^\n]*\s-n\b", "Remove -n from the procnto line.", DOC_KERNEL, applies="buildfile"),
    Rule("Q8102", "info", "Review procnto -m options: superlocking ones must go (kernel is superlocked by default)",
         r"\bprocnto[\w-]*\b[^\n]*\s-m\w*", "Check each -m option against the QNX 8.0 procnto reference and remove the ones that relate to superlocking.", DOC_KERNEL, applies="buildfile"),
    Rule("Q8103", "error", "procnto -U (unregistered events) is not supported",
         r"\bprocnto[\w-]*\b[^\n]*\s-U\b", "Remove -U and register events with MsgRegisterEvent().", DOC_KERNEL, applies="buildfile"),
]

# File-level rule: process-shared sync primitives must be initialised with PTHREAD_PROCESS_SHARED.
SHM_RE = re.compile(r"\b(shm_open|mmap)\s*\(")
DEFAULT_SYNC_RE = re.compile(r"\b(pthread_mutex_init|pthread_cond_init|sem_init|pthread_rwlock_init|pthread_barrier_init)\s*\([^,]+,\s*(NULL|0)\b")
SHARED_RE = re.compile(r"PTHREAD_PROCESS_SHARED")
SHARED_RULE = Rule("Q8015", "warning", "Sync primitive in shared memory without PTHREAD_PROCESS_SHARED",
                   r"$^", "Sync primitives are no longer shareable between processes by default; initialise them with an attribute set to PTHREAD_PROCESS_SHARED.",
                   DOC_KERNEL)
