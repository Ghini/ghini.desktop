#
# a test plugin
#
import gtk
import bauble
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
import bauble.task
from bauble.utils.log import debug

class TestTask:

    def __init__(self):
        pass

    def task(self):
        bauble.gui.progressbar.set_pulse_step(.1)
        msg = ''
        for i in range(1, 10):
            msg = '%s...%s' % (msg, i)
            bauble.task.set_message(msg)
            bauble.gui.progressbar.pulse()
            yield
            try:
                if i == 2:
                    #raise Exception
                    pass
            except Exception, e:
                debug(e)
                break

    def start(self):
        def callback(*args):
            #debug('entered callback')
            for i in xrange(0, 100):
                pass
            msg = 'task finished'
            #utils.message_dialog(msg)
#            d = utils.create_message_dialog(msg)
#            yield (gtasklet.WaitForSignal(d, "response"),
#                   gtasklet.WaitForSignal(d, "close"))
#            gtasklet.get_event()
#            d.destroy()
            debug('leaving callback')
        bauble.task.queue(self.task, callback, None)


class TestTool(pluginmgr.Tool):
    category = "Test"
    label = "Task"

    @classmethod
    def start(cls):
        t = TestTask()
        t.start()
        t.start()
        t.start()
        t.start()

class TestView(pluginmgr.View):

    def __init__(self):
        super(TestView, self).__init__()
        self.label = gtk.Label('a load of crap')
        self.pack_start(self.label)


    def do_something(self, arg):
        self.label.set_text('arg: %s' % arg)


class TestCommandHandler(pluginmgr.CommandHandler):

    command = 'test'

    def get_view(self):
        self.view = TestView()
        return self.view

    def __call__(self, arg):
        self.view.do_something(arg)


class TestPlugin(pluginmgr.Plugin):
    tools = [TestTool]
    views = TestView
    commands = [TestCommandHandler]


# TODO: how do we include the test plugin in a src dist but not in a
# binary or py2exe dist
##plugin = TestPlugin
