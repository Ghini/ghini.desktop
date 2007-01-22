#
# task.py
#
# Description: manage long running tasks
#
import bauble
import bauble.utils.gtasklet as gtasklet
from bauble.utils.log import debug
import Queue

# TODO: after some specified time the status bar should be cleared but not
# too soon, maybe 30 seconds or so but only once the queue is empty, anytime
# something is added to the queue we should set a 30 second timeout to
# check again if the queue is empty and set the status bar message if it's
# empty

# TODO: how do we pass arguments to the callbac

# TODO: every task should have a way to change the status bar message, i don't
# know if this means passing a sub task to the main task to send messages too
# or if we can just call some function that sets the message on the queue
# task sig:
# task(status

# IDEAS/PLANNING
# - after each task finishes it must yeild the quit message, possibly with a 
# return value or error code or exception or something
# when the quit message is recieved we should check the queue and start the next
# task, this would be a good time to add the timer to clear the statusbar, 
# anytime a new task is added we should clear the timer
# - if there is an error or exception raised in the middle of execution then
# how should we handle it
# - eask task should be independent of the others
# - ability to pass custom message names and callback that should be called 
# when those message are sent
# should we have a global function that manages the progress bar and state or
# should the progress updater just  be a tasklet itself that starts
# another tasklet and waits for it to give up control to update the progress and
# then we know exactly when it finishes execution


def _update_progress(percent=None):
    if not hasattr(bauble, 'gui') or (bauble.gui is None or bauble.gui.progressbar):
        return
    if percent is None:
        bauble.gui.widgets.progressbar.pulse()
    else:
        bauble.gui.widgets.progressbar.set_fraction(percent)
        
            

def _task_monitor(nsteps=None, callback=None):
    '''        
    @param nsteps: total number of steps to complete task
    '''
#    self.__progress_dialog = ProgressDialog(title='Importing...')
#    self.__progress_dialog.show_all()
#    self.__progress_dialog.connect_cancel(self._cancel_import)
    msgwait = gtasklet.WaitForMessages(accept=("quit", "update_progress", 
                                               'update_filename'))
    #if nsteps is None:
    #    bauble.gui.widgets.progressbar.pulse()
    _update_progress(nsteps)
    steps_so_far = 0
    while True:
      yield msgwait
      msg = gtasklet.get_event()      
      if msg.name == 'update_progress':
          steps_so_far += msg.value
          if nsteps is not None:
              percent = float(steps_so_far)/floar(nsteps)
              if 0 < percent < 1.0: # avoid warning
                  _update_progress(percent)
                  #bauble.gui.widgets.progressbar.set_fraction(percent)
              self.__progress_dialog.pb.set_text('%s / %s' % (steps_so_far, nsteps))
          else:
              _update_progress()
              #bauble.gui.widgets.progressbar.pulse()
      if msg.name == "quit":
          debug('_task_progress.quit')
          if callback is not None:
              callback(msg.value)
          #bauble.set_busy(False) 
          #self.__progress_dialog.destroy()
#      elif msg.name == 'update_progress':
#          nsteps += msg.value
#          percent = float(nsteps)/float(total_lines)
#          if 0 < percent < 1.0: # avoid warning
#              self.__progress_dialog.pb.set_fraction(percent)
#          self.__progress_dialog.pb.set_text('%s of %s records' % (nsteps, total_lines))
#      elif msg.name == 'update_filename':
#          filename, table_name = msg.value  
#          msg = 'Importing data into %s table from\n%s' % (table_name, filename)
#          self.__progress_dialog.set_message(msg)
#      elif msg.name == 'insert_error':
#          CSVImporter.__cancel = True
#          utils.message_dialog('insert error')



#def queue_task(task, nsteps, increments, callback, *args):
def queue(task, callback, nsteps, *args):
    '''
    @param task: the task to queue
    @param nsteps: the number of steps to complete the task
    @param increments: number of increments to do nsteps in
    @param callback: the function to call when the task is finished
    @param args: the arguments to pass to the task
    '''
    monitor = gtasklet.run(_task_monitor(nsteps, callback=callback))
    gtasklet.run(task(monitor, *args))



def push_message(context_id, msg):
    return bauble.gui.widgets.statusbar.push(context_id, msg)
