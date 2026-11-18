# Build for QNX SDP 8.0 (needs the SDK: source ~/qnx800/qnxsdp-env.sh first)
TARGET ?= gcc_ntox86_64
all: ist.o
ist.o: ist.c
	qcc -V$(TARGET) -Wall -c ist.c -o ist.o
clean:
	rm -f ist.o
