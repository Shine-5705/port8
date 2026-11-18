/* Hand-written sample in the style of a QNX SDP 7.1 resource manager + driver.
 * It exists only to exercise port8's rules; it is not taken from any QNX BSP. */
#include <stdio.h>
#include <sys/neutrino.h>
#include <sys/procmgr.h>
#include <sys/mman.h>
#include <pthread.h>

#define UART_IRQ 76

static struct sigevent uart_event;
static pthread_mutex_t *shared_lock;

const struct sigevent *uart_isr(void *area, int id) {
    /* InterruptAttach() is fine in a comment and must not be flagged */
    return &uart_event;
}

int main(void) {
    int chid, rcvid, irq_id;
    struct _clockperiod period = { 10000, 0 };
    char msg[64];

    procmgr_ability(0, PROCMGR_ADN_ROOT | PROCMGR_AOP_ALLOW | PROCMGR_AID_INTERRUPTEVENT, PROCMGR_AID_EOL);
    ClockPeriod(CLOCK_REALTIME, &period, NULL, 0);

    int fd = shm_open("/uart-stats", O_RDWR | O_CREAT, 0600);
    shared_lock = mmap(NULL, sizeof *shared_lock, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    pthread_mutex_init(shared_lock, NULL);

    irq_id = InterruptAttach(UART_IRQ, uart_isr, NULL, 0, _NTO_INTR_FLAGS_TRK_MSK);
    printf("InterruptAttach(UART_IRQ) ok\n");

    struct sched_param sp; sp.sched_priority = 255;
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);

    chid = ChannelCreate(0);
    for (;;) {
        rcvid = MsgReceive(chid, msg, sizeof msg, NULL);
        MsgReply(rcvid, 0, NULL, 0);
    }
    return 0;
}
