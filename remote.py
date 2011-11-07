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
# TODO: add better default behavior so this doesn't break on machines
# other than my own.
# (1) parameterize 
#   (a) udp port
#   (b) fifo
#   (c) config file
# (2) figure out default behavior for lack of config
#   (a) prompt user?
# (3) figure out default behavior if ctl is missing
#   (a) mkfifo?
# (4) what are failsafe defaults for keybindings?
#   (a) make a config file?
# (5) create an install.sh that makes fifo and config?
# (6) embed event_cmd behavior into this script (somehow)
# (7) handle concurrency to fifo by acquiring lock? may be unnecessary
#     since fifo buffers anyway. could explore listener-side buffering
#     with locks

import atexit # for process clean-up
import multiprocessing # for ...multiprocessing
import os # for debugging and other utilities
import socket # for udp
import subprocess # for managing pianobar instance

from sys import argv # for handling cli arguments

# set to public ip if provided; else, use localhost
UDP_IP = argv[1] if len(argv) > 1 else "127.0.0.1"

# use specified port unless missing; then, use arbitrary default
UDP_PORT = int(argv[2]) if len(argv) > 2 else 64266 # PIANO on T9 - 10000

# convenience method to read pianobar's config file
def parse_config(config_file=os.path.expanduser("~/.config/pianobar/config")):
    import ConfigParser
    parser = ConfigParser.SafeConfigParser()
    parser.read([config_file])
    return parser

CONFIG = parse_config()

# PRLRuntime provides an overarching class that encapsulates the
# environment for all PianobarRemoteListeners. PRLRuntime takes
# ownership of the pianobar process. 
class PRLRuntime():
    def __init__(self):
        self.inactive_listeners = []
        self.pool = []
        atexit.register(self.terminate)

    def start_pianobar(self):
        # convenience method to parse config file for fifo if one is
        # specified. otherwise, the default file is used.
        def fifo_path():
            if CONFIG.has_option("Misc", "fifo"):
                return CONFIG.get("Misc", "fifo")
            return os.path.expanduser("~/.config/pianobar/ctl")

        def get_named_pipe():
            fp = fifo_path()
            if not os.path.exists(fp):
                os.mkfifo(fp)
            return open(fp , "w", 0) # unbuffered
                    
        # note: always initialize pianobar before fifo
        self.pianobar = subprocess.Popen("pianobar", stdout = subprocess.PIPE)
        self.fifo = get_named_pipe()

    # add listeners that can control current pianobar instance
    def register_listener(self, listener):
        self.inactive_listeners.append(listener)

    # start a separate process per listener
    def start_listeners(self):
        #TODO: name the processes
        new_pool = [multiprocessing.Process(target=l.listen)
                     for l in self.inactive_listeners]
        for p in new_pool:
            p.daemon = True
            p.start()
        self.pool += new_pool

    # clean up all running processes and open files as well as kill pianobar
    def terminate(self):
        for p in self.pool:
            p.terminate()
        self.fifo.close()
        self.pianobar.kill()

    # TODO: return the event that results from executing the command
    def handle(self, command):
        self.fifo.write(command())

# PianobarRemoteListener is intended to run in its own thread. It accepts UDP
# packets describing which action to take on pianobar in a blocking fashion.
class PianobarRemoteListener():
    def __init__(self, rt, udp_ip, udp_port):
        self.runtime = rt
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        
    def listen(self):
        self.sock = socket.socket(socket.AF_INET, # IPv4
                                  socket.SOCK_DGRAM) # UDP
        self.sock.bind((self.udp_ip, self.udp_port))
        while True:
            data, addr = self.sock.recvfrom(1024) # buffer size of 1024 bytes
            self.runtime.handle(lambda: COMMANDS[data])

# TODO: add support for complicated commands like act_stationcreate
# TODO: parameterize config file
def initialize_commands():
    # small hack that allows assignment in anonymous functions
    def set(dct, k, v):
        dct[k] = v

    comm = {}
    map(lambda kv: set(comm, kv[0], kv[1]),
                       CONFIG.items("Keybindings"))
    
    global COMMANDS    
    COMMANDS = comm    
    
if __name__ == "__main__":  
    initialize_commands()
    
    runtime = PRLRuntime()
    runtime.start_pianobar()

    listener = PianobarRemoteListener(runtime, UDP_IP, UDP_PORT)

    runtime.register_listener(listener)
    runtime.start_listeners()

    # don't judge me. this will be fixed -- i promise
    from time import sleep
    while(True): 
        # TODO: figure out how to parse pianobar event_cmd. 
        # and display that as output
        # (line 393 of /path/to/pianobar/ui.h)
        sleep(60)
    
