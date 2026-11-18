/* QNX SDP 8.0 style interrupt service thread (pattern from the QNX 8.0 Programmer's Guide). */
#include <sys/neutrino.h>
#include <pthread.h>
#define IRQ_NUM 76
static volatile int done;
void *hardware_ist(void *unused) {
    int const id = InterruptAttachThread(IRQ_NUM, _NTO_INTR_FLAGS_NO_UNMASK);
    while (!done) {
        InterruptWait(_NTO_INTR_WAIT_FLAGS_UNMASK | _NTO_INTR_WAIT_FLAGS_FAST, NULL);
    }
    InterruptDetach(id);
    return NULL;
}
int serve(int chid) { char m[8]; rcvid_t rcvid = MsgReceive(chid, m, sizeof m, NULL); return MsgReply(rcvid, 0, NULL, 0); }
