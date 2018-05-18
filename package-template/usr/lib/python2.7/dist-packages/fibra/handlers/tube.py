"""
Implements 'pipe' like functionality.
"""

import weakref


class EmptyTube(Exception): pass
class ClosedTube(Exception): pass


class TubePush(object):
    __slots__ = ['tube', 'arg', 'wait']
    def __init__(self, tube, arg, wait):
        self.tube = tube
        self.arg = arg
        self.wait = wait


class TubePop(object):
    __slots__ = ['tube', 'wait']
    def __init__(self, tube, wait):
        self.tube = tube
        self.wait = wait

class TubeClose(object):
    __slots__ = ['tube']
    def __init__(self, tube):
        self.tube = tube
    


class Tube(object):
    instances = {}
    _instances = weakref.WeakValueDictionary()

    def __new__(class_, name=None):
        if name is not None and name in class_.instances:
            return class_.instances[name]
        self = object.__new__(class_)
        self.pushing = []
        self.popping = []
        if name is not None:
            class_.instances[name] = self
        class_._instances[id(self)] = self
        self.closed = False
        return self
 
    def push(self, arg, wait=False):
        if self.closed: raise ClosedTube()
        return TubePush(self, arg, wait)

    def pop(self, wait=True):
        if self.closed: raise ClosedTube()
        return TubePop(self, wait)

    def close(self):
        self.closed = True
        return TubeClose(self)


class TubeHandler(object):
    handled_types = TubePush, TubePop, TubeClose
    wait = False
    active = False

    def status(self):
        return len(Tube._instances)

    def handle(self, v, task):
        tube = v.tube
        if v.__class__ is TubePush:
            if tube.popping:
                self.schedule.install(tube.popping.pop(0), v.arg)
                self.schedule.install(task)
                self.wait = True
            else:
                if v.wait:
                    tube.pushing.append((task, v.arg))
                else:
                    tube.pushing.append((None, v.arg))
                    self.schedule.install(task)
                    self.wait = True
                    
        elif v.__class__ is TubePop:
            if tube.pushing:
                t,v = tube.pushing.pop(0)
                if t: self.schedule.install(t)
                self.schedule.install(task, v)
                self.wait = True
            else:
                if v.wait:
                    tube.popping.append(task)
                else:
                    self.schedule.install(task, EmptyTube())

        elif v.__class__ is TubeClose:
            for t,v in tube.pushing:
                self.schedule.install(t, ClosedTube())
            for t in tube.popping:
                self.schedule.install(t, ClosedTube())
            self.schedule.install(task)
            
    def pre_schedule(self):
        wait = self.wait
        self.wait = False
        self.active = wait

