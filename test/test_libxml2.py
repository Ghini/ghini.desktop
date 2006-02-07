# test that libxml2 is properly importing so that we know the formatter
# plugin is working, especially on windows where we have to do some path
# trickery

try:
    import libxml2
except:
    print "what now???"
else:
    print "todo bien"