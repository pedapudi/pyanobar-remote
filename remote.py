# This simple script acts as a remote for pianobar[1]. Its primary
# purpose is to provide a simple way for multiple remotes to
# interact with a single instance of pianobar
#
# This is currently just being tested and by no means in deployable
# condition.
# Sunil Pedapudi (skpedapudi@gmail.com)
# Nov. 6, 2011
#
# [1] https://github.com/PromyLOPh/pianobar
# TODO: add better default behavior so this doesn't break on machines
# other than my own.
# (1) parameterize 
#   DONE (a) udp port
#   DONE (b) fifo
#   DONE (c) config file
# (2) figure out default behavior for lack of config
#   (a) prompt user?
# (3) figure out default behavior if ctl is missing
#   DONE (a) mkfifo? (resolved: yes, mkfifo)
# (4) what are failsafe defaults for keybindings?
#   (a) make a config file?
# (5) create an install.sh that makes fifo and config?
# (6) embed event_cmd behavior into this script (somehow)
# (7) handle concurrency to fifo by acquiring lock? may be unnecessary
#     since fifo buffers anyway. could explore listener-side buffering
#     with locks

from pianobarremote import PRLRuntime, PianobarRemoteListener

from sys import argv # for handling cli arguments

# set to public ip if provided; else, use localhost
UDP_IP = argv[1] if len(argv) > 1 else "127.0.0.1"

# use specified port unless missing; then, use arbitrary default
UDP_PORT = int(argv[2]) if len(argv) > 2 else 64266 # PIANO on T9 - 10000

if __name__ == "__main__":    
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
    
