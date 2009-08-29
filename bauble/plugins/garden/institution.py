#
# institution.py
#
# Description: edit and store information about the institution in the bauble
# meta
#

import os
import bauble
import bauble.editor as editor
import bauble.meta as meta
import bauble.utils as utils
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import debug

# TODO: the institution editor is a live editor where the database is
# updated as the user types. This is a bit slow and maybe we could add
# a callback so that the database isn't updated until the user stops
# typing...or just commit on OK

class Singleton(object):
    __instance = None
    def __new__(cls, *args, **kwargs):
        if Singleton.__instance == None:
            obj = object.__new__(cls, *args, **kwargs)
            Singleton.__instance = obj
        return Singleton.__instance


class Institution(Singleton):
    '''
    Institution is a "live" object. When properties are changed the changes
    are immediately reflected in the database.

    Institution values are stored in the Bauble meta database and not in
    its own table
    '''
    __properties = ('name', 'abbreviation', 'code', 'contact',
                    'technical_contact', 'email', 'tel', 'fax', 'address')
    __db_tmpl = 'inst_%s'
    #table = meta.bauble_meta_table
    # TODO: update this to not use this table directly
    table = meta.BaubleMeta.__table__
    prop = lambda s, p: utils.utf8(s.__db_tmpl % p)

    def __getattr__(self, prop):
        if prop not in self.__properties:
            msg = _('Institution.__getattr__: %s not a property on '\
                    'Intitution') % prop
            raise ValueError(msg)
        r = self.table.select(self.table.c.name==self.prop(prop)).execute().fetchone()
        if r is None:
            return None
        return r['value']


    def __setattr__(self, prop, value):
        if prop not in self.__properties:
            msg = _('Institution.__setattr__: %s not a property on '\
                    'Intitution') % prop
            raise ValueError(msg)
        prop = self.prop(prop)
        value = utils.utf8(value)
        s = self.table.select(self.table.c.name == prop).execute()
        # have to check if the property exists first because sqlite doesn't
        # raise an error if you try to update a value that doesn't exist and
        # do an insert and then catching the exception if it exists and then
        # updating the value is too slow
        if s.fetchone() is None:
##            debug('insert: %s = %s' % (prop, value))
            self.table.insert().execute(name=prop, value=value)
        else:
##            debug('update: %s = %s' % (prop, value))
            self.table.update(self.table.c.name==prop).execute(value=value)



class InstitutionEditorView(editor.GenericEditorView):

    # i think the institution editor's field are pretty self explanatory
    _tooltips = {}

    def __init__(self, parent=None):
        filename = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                'institution.glade')
        super(InstitutionEditorView, self).__init__(filename, parent=parent)

    def get_window(self):
        return self.widgets.inst_dialog

    def start(self):
        return self.get_window().run()


class InstitutionEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'inst_name': 'name',
                           'inst_abbr': 'abbreviation',
                           'inst_code': 'code',
                           'inst_contact': 'contact',
                           'inst_tech': 'technical_contact',
                           'inst_email': 'email',
                           'inst_tel': 'tel',
                           'inst_fax': 'fax',
                           'inst_addr': 'address'
                           }

    def __init__(self, model, view):
        super(InstitutionEditorPresenter, self).__init__(model, view)
        self.refresh_view()
        for widget, field in self.widget_to_field_map.iteritems():
            self.assign_simple_handler(widget, field)
        self.__dirty = False



    def set_model_attr(self, attr, value, validator):
        super(InstitutionEditorPresenter, self).set_model_attr(attr, value,
                                                               validator)
        self.__dirty = True


    def dirty(self):
        return self.__dirty


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            self.view.set_widget_value(widget, getattr(self.model, field))


    def start(self, commit_transaction=True):
        return self.view.start()


class InstitutionEditor(object):

    def __init__(self, parent=None):
        self.model = Institution()
        self.view = InstitutionEditorView(parent=parent)
        self.presenter = InstitutionEditorPresenter(self.model, self.view)


    def start(self):
        self.presenter.start()


class InstitutionCommand(pluginmgr.CommandHandler):
    command = ('inst', 'institution')
    view = None

    def __call__(self, cmd, arg):
        InstitutionTool.start()


class InstitutionTool(pluginmgr.Tool):
    label = _('Institution')

    @classmethod
    def start(cls):
        e = InstitutionEditor()
        e.start()
