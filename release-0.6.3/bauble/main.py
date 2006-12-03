
import os, sys
import bauble
import gtk # this has to be after import bauble

def bauble_main():
    gtk.gdk.threads_init() # initialize threading
    gtk.gdk.threads_enter()
    bauble.app.main()
    gtk.gdk.threads_leave()

if __name__ == "__main__":    
    bauble_main()

