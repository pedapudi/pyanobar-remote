# This simple script acts as a remote for pianobar[1]. Its primary
# purpose is to provide a simple way for multiple remotes to
# interact with a single instance of pianobar
#
# This is currently just being tested and by no means in deployable
# condition.
# Sunil Pedapudi (skpedapudi@gmail.com)
# Nov. 5, 2011
#
# [1] https://github.com/PromyLOPh/pianobar

import atexit, multiprocessing, os, socket, subprocess, sys
UDP_IP="127.0.0.1" # run on localhost
UDP_PORT=64266 # PIANO on T9 - 10000

# TODO: fix this massive hack by introducing a schema and packets
# that understand pianobar's commands. try reading the config
# file.
COMMANDS={
    "next": ["echo", "-ne", "n"],
    "playpause":["echo", "-ne", "p"],
    }

# PRLRuntime provides an overarching class that encapsulates the
# environment for all PianobarRemoteListeners. PRLRuntime takes
# ownership of the pianobar process. 
class PRLRuntime():
    def __init__(self):
        self.listeners = []
        atexit.register(self.terminate)

    def start_pianobar(self):
        # note: always initialize pianobar before fifo
        self.pianobar = subprocess.Popen("pianobar", stdout = subprocess.PIPE)
        self.fifo = open("/home/sunil/.config/pianobar/ctl", "w")
        #TODO: figure out how to use default station on pianobar
        subprocess.call(["echo", "-e", "20\n"], stdout=self.fifo)

    # add listeners that can control current pianobar instance
    # TODO: change this to dynamically add listeners
    def register_listener(self, listener):
        self.listeners.append(listener)

    # start a separate process per listener
    def start_listeners(self):
        #TODO: name the processes
        self.pool = [multiprocessing.Process(target=l.listen)
                     for l in self.listeners]
        for p in self.pool:
            p.daemon = True
            p.start()

    # clean up all running processes and open files as well as kill pianobar
    def terminate(self):
        for p in self.pool:
            p.terminate()
        self.fifo.close()
        self.pianobar.kill()

# PianobarRemoteListener is intended to run in its own thread. It accepts UDP
# packets describing which action to take on pianobar in a blocking fashion.
class PianobarRemoteListener():
    def __init__(self, fifo, udp_ip, udp_port):
        self.fifo = fifo
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        
    def listen(self):
        self.sock = socket.socket(socket.AF_INET, # IPv4
                                  socket.SOCK_DGRAM) # UDP
        self.sock.bind((self.udp_ip, self.udp_port))
        while True:
            data, addr = self.sock.recvfrom(1024) # buffer size of 1024 bytes
            # TODO: explore architecture: pass command up to runtime instead of
            # interacting directly with fifo?
            subprocess.call(COMMANDS[data], stdout=self.fifo) # giant hack

runtime = PRLRuntime()
runtime.start_pianobar()

listener = PianobarRemoteListener(runtime.fifo, UDP_IP, UDP_PORT)

runtime.register_listener(listener)
runtime.start_listeners()

from time import sleep
while(True):
    # TODO: figure out how to parse pianobar event_cmd. 
    # and display that as output
    # (line 393 of pianobar/ui.h)
    sleep(60)
    
