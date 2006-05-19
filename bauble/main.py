
import os, sys
import bauble
import gtk # this has to be after import bauble

def bauble_main():
    gtk.threads_init() # initialize threading
    gtk.threads_enter()
    bauble.app.main()
    gtk.threads_leave()

if __name__ == "__main__":    
    bauble_main()

