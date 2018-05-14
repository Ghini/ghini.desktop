"""
Fibra is a sophisticated scheduler for cooperative tasks.

It's a bit lke Stackless Python. It uses Python generator functions
to create tasks which can be iterated.


"""
from schedule import *
from handlers.sleep import Sleep
from handlers.nonblock import Unblock
from handlers.tasks import Async, Return, Finished, Suspend, Self
from handlers.tube import Tube, EmptyTube, ClosedTube
from handlers.io import Read, Write
