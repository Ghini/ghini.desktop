#
# view.py
#
# Description: the default view
#

from bauble.utils.log import debug
import bauble.pluginmgr as pluginmgr

# TODO: this should act like the search view and called when no other
# commands are matched from the command entry
class DefaultView(pluginmgr.View):
    
    def search(self, arg):
        debug('DefaultView.search(%s)' % arg)
    
    
class DefaultCommandHandler(pluginmgr.CommandHandler):
    
    command = None
 
    def get_view(self):
        self.view = DefaultView()
        return self.view
    
    def __call__(self, arg):
        debug('DefaultCommandHandler.__call__(%s)' % arg)
        self.view.search(arg)
