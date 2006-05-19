
import os, sys
import bauble
import gtk # this has to be after import bauble

import bauble.paths as paths
sys.path.insert(0, 'c:\\gtk\\bin')
os.environ['GTK_BASEPATH'] = 'c:\\gtk'
print sys.path

if __name__ == "__main__":    
    gtk.threads_init() # initialize threading
    gtk.threads_enter()
    bauble.app.main()
    gtk.threads_leave()