import time
import definitions

def current_time_ms():
    return int(round(time.time() * 1000))


def vprint(string):
    if definitions.VERBOSE:
        print(string)

def vvprint(string):
    if definitions.EXTRAVERBOSE:
        print(string)

def upload():
    pass


defs = definitions
