DEFAULT_CONFIG = "~/.config/pianobar/config"

import atexit # for process clean-up
import multiprocessing # for ...multiprocessing
import os # for debugging and other utilities
import socket # for udp
import subprocess # for managing pianobar instance

# PRLRuntime provides an overarching class that encapsulates the
# environment for all PianobarRemoteListeners. PRLRuntime takes
# ownership of the pianobar process.
class PRLRuntime():
    def __init__(self, config=None):
        # convenience method to read pianobar's config file
        def parse_config(config_file):
            import ConfigParser
            parser = ConfigParser.SafeConfigParser()
            parser.read([config_file])
            return parser
        
        if config:
            self.config = parse_config(config)
        else:
            self.config = parse_config(os.path.expanduser(DEFAULT_CONFIG))
            
        self.inactive_listeners = []
        self.pool = []
        
        self.__initialize_commands()

        atexit.register(self.terminate)

    # TODO: add support for complicated commands like act_stationcreate
    def __initialize_commands(self):
        # small hack that allows assignment in anonymous functions
        def set(dct, k, v):
            dct[k] = v

        self.commands = {}
        map(lambda kv: set(self.commands, kv[0], kv[1]),
            self.config.items("Keybindings"))
        
    def start_pianobar(self):
        # convenience method to parse config file for fifo if one is
        # specified. otherwise, the default file is used.
        def fifo_path():
            if self.config.has_option("Misc", "fifo"):
                return self.config.get("Misc", "fifo")
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
    # TODO: what happens when pianobar dies?
    def handle(self, data):
        self.fifo.write(self.commands[data])

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
        try:
            self.sock.bind((self.udp_ip, self.udp_port))
        except socket.error, msg:
            print "Failed to bind: " + msg

        while True:
            data, addr = self.sock.recvfrom(1024) # buffer size of 1024 bytes
            self.runtime.handle(data)
