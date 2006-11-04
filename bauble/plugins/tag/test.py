
#if __name__ == '__main__':
#    # for testing
#    sqlhub.processConnection = connectionForURI("sqlite:///tmp/test.sqlite")
#    sqlhub.processConnection.getConnection()
#
#
#    class Person(SQLObject):
#        name = StringCol()
#        def __str__(self):
#            return self.name                
#
#    class Donkey(SQLObject):
#        name = StringCol()    
#        def __str__(self):
#            return self.name
#        
#    tables = [Person, Donkey, TagCategory, Tag, TagObjId, TagIntermediate]
#    def create_tables():
#        for t in tables:
#            t.dropTable(True)
#            t.createTable()
#    create_tables()
#    
#    p = Person(name='Ted')
#    tag_object('human', p)
#    tag_object('hawaiin', p)
#
#    d = Donkey(name='Crapper')
#    tag_object('hawaiin', d)
#
#    for t in get_tags(p):
#        print str(t)
#        print '----------------'
#        for id in t.ids:
#            print '-- ' + str(id)
#        print '\n'