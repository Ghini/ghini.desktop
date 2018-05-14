"""This is a package for fibra handlers.

A fibra handler can be registered to handle values which are yielded from 
running tasklets.

Eg:
>>> import fibra
>>> import fibra.handlers.sleep
>>> s = fibra.Schedule()
>>> sleep_handler = fibra.handlers.sleep.SleepHandler()
>>> s.register_handler(sleep_handler)

sets up a scheduler with the SleepHandler installed. To see what types a
SleepHandler will handle:

>>> print sleep_handler.handled_types
[<class 'fibra.handlers.sleep.Sleep'>, <type 'int'>, <type 'float'>, <type 'long'>]

To see what extra functions a handler will add to the scheduler:

>>> print sleep_handler.exported_functions
[<bound method SleepHandler.defer of <fibra.handlers.sleep.SleepHandler object at 0xa13fd0>>]


To create a custom handler, use the following protocol.

class Handler(object):
    handled_types = [list_of_handled_types]
    def handle(self, yielded_value, task):
        #do something with the task 
        #but DONT add it back to the scheduler here!
        pass

    def pre_schedule(self):
        #add tasks back into the schedule in this function.
        self.schedule.install(task)

"""
