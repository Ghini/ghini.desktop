class StoredQueries(object):
    def __init__(self):
        self.page = 0
        self.__label = [''] * 10
        self.__tooltip = [''] * 10
        self.__query = [''] * 10

    def __getitem__(self, index):
        return {'index': index,
                'label': self.__label[index - 1],
                'tooltip': self.__tooltip[index - 1],
                'query': self.__query[index - 1]}

    def __iter__(self):
        self.__index = 1
        return self

    def next(self):
        if self.__index > len(self.__label):
            raise StopIteration
        else:
            self.__index += 1
            return self[self.__index - 1]

    @property
    def label(self):
        return self.__label[self.page - 1]

    @label.setter
    def label(self, value):
        self.__label[self.page - 1] = value

    @property
    def tooltip(self):
        return self.__tooltip[self.page - 1]

    @tooltip.setter
    def tooltip(self, value):
        self.__tooltip[self.page - 1] = value

    @property
    def query(self):
        return self.__query[self.page - 1]

    @query.setter
    def query(self, value):
        self.__query[self.page - 1] = value

    def __repr__(self):
        return '[p:%d; l:%s; t:%s; q:%s' % (self.page, self.__label, self.__tooltip, self.__query)
