# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.

import os

from sqlalchemy import or_
#from sqlalchemy.exc import *

from nose import SkipTest

import bauble.plugins.tag as tag_plugin
from bauble.plugins.plants import Family
from bauble.plugins.tag import Tag, TagEditorPresenter, TagInfoBox
from bauble.test import BaubleTestCase, check_dupids, mockfunc
from bauble.editor import GenericEditorView, MockView
import bauble.utils as utils
from functools import partial
import gtk


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the tag plugin.
    """
    import bauble.plugins.tag as mod
    import glob
    head, tail = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, '*.glade'))
    for f in files:
        assert(not check_dupids(f))


class TagMenuTests(BaubleTestCase):
    def test_no_tags(self):
        m = tag_plugin.tags_menu_manager.build_menu()
        self.assertTrue(isinstance(m, gtk.Menu))
        self.assertEquals(len(m.get_children()), 1)
        self.assertEquals(m.get_children()[0].get_label(), _('Tag Selection'))

    def test_one_tag(self):
        tagname = u'some_tag'
        t = Tag(tag=tagname, description=u'description')
        self.session.add(t)
        self.session.flush()
        m = tag_plugin.tags_menu_manager.build_menu()
        self.assertTrue(isinstance(m, gtk.Menu))
        self.assertEquals(len(m.get_children()), 6)
        self.assertTrue(m.get_children()[1], gtk.SeparatorMenuItem)
        self.assertEquals(m.get_children()[2].get_label(), tagname)
        self.assertTrue(m.get_children()[3], gtk.SeparatorMenuItem)

    def test_more_tags(self):
        tagname = u'%s-some_tag'
        t1 = Tag(tag=tagname % 1, description=u'description')
        t2 = Tag(tag=tagname % 3, description=u'description')
        t3 = Tag(tag=tagname % 2, description=u'description')
        t4 = Tag(tag=tagname % 0, description=u'description')
        t5 = Tag(tag=tagname % 4, description=u'description')
        self.session.add_all([t1, t2, t3, t4, t5])
        self.session.flush()
        m = tag_plugin.tags_menu_manager.build_menu()
        self.assertTrue(isinstance(m, gtk.Menu))
        self.assertEquals(len(m.get_children()), 10)
        for i in range(5):
            self.assertEquals(m.get_children()[i + 2].get_label(), tagname % i)


class TagTests(BaubleTestCase):

    def __init__(self, *args, **kwargs):
        super(TagTests, self).__init__(*args, **kwargs)
        import bauble.prefs
        bauble.prefs.testing = True

    def setUp(self):
        super(TagTests, self).setUp()
        self.family = Family(family=u'family')
        self.session.add(self.family)
        self.session.commit()

    def tearDown(self):
        super(TagTests, self).tearDown()

    def test_str(self):
        """
        Test Tag.__str__ method
        """
        name = u'test'
        tag = Tag(tag=name)
        self.assertEquals(str(tag), name)

    def test_create_named_empty_tag(self):
        name = u'name123'
        r = self.session.query(Tag).filter_by(tag=name).all()
        self.assertEquals(len(r), 0)
        tag_plugin.create_named_empty_tag(name)
        r = self.session.query(Tag).filter_by(tag=name).all()
        self.assertEquals(len(r), 1)
        t0 = r[0]
        self.assertEquals(t0.tag, name)
        tag_plugin.create_named_empty_tag(name)
        t1 = self.session.query(Tag).filter_by(tag=name).one()
        self.assertEquals(t0, t1)

    def test_tag_nothing(self):
        t = Tag(tag=u'some_tag', description=u'description')
        self.session.add(t)
        self.session.flush()
        t.tag_objects([])
        self.assertEquals(t.objects, [])
        self.assertEquals(t.search_view_markup_pair(),
                          (u'some_tag - <span weight="light">tagging nothing</span>',
                           '(Tag) - <span weight="light">description</span>'))

    def test_tag_objects(self):
        family2 = Family(family=u'family2')
        self.session.add(family2)
        self.session.commit()
        family1_id = self.family.id
        family2_id = family2.id
        tag_plugin.tag_objects('test', [self.family, family2])

        # we do not offer gettin object by string
        # get object by tag
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        tagged_objs = tag.objects
        sorted_pairs = sorted([(type(o), o.id) for o in tagged_objs])
        self.assertEquals(sorted([(Family, family1_id),
                                  (Family, family2_id)]),
                          sorted_pairs)

        tag_plugin.tag_objects('test', [self.family, family2])
        self.assertEquals(tag.objects, [self.family, family2])

        #
        # first untag one, then both
        #
        tag_plugin.untag_objects('test', [self.family])

        # get object by tag
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        tagged_objs = tag.objects
        self.assertEquals(tagged_objs, [family2])

        #
        # first untag one, then both
        #
        tag_plugin.untag_objects('test', [self.family, family2])

        # get object by tag
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        tagged_objs = tag.objects
        self.assertEquals(tagged_objs, [])

    def test_is_tagging(self):
        family2 = Family(family=u'family2')
        t1 = Tag(tag=u'test1')
        self.session.add_all([family2, t1])
        self.session.flush()
        self.assertFalse(t1.is_tagging(family2))
        self.assertFalse(t1.is_tagging(self.family))
        t1.tag_objects([self.family])
        self.session.flush()
        self.assertFalse(t1.is_tagging(family2))
        self.assertTrue(t1.is_tagging(self.family))

    def test_search_view_markup_pair(self):
        family2 = Family(family=u'family2')
        t1 = Tag(tag=u'test1')
        t2 = Tag(tag=u'test2')
        self.session.add_all([family2, t1, t2])
        self.session.flush()
        t1.tag_objects([self.family, family2])
        t2.tag_objects([self.family])
        self.assertEquals(t1.search_view_markup_pair(),
                          ('test1 - <span weight="light">tagging 2 objects of type Family</span>',
                           '(Tag) - <span weight="light"></span>'))
        self.assertEquals(t2.search_view_markup_pair(),
                          ('test2 - <span weight="light">tagging 1 objects of type Family</span>',
                           '(Tag) - <span weight="light"></span>'))
        t2.tag_objects([t1])
        self.session.flush()
        self.assertEquals(t2.search_view_markup_pair(),
                          ('test2 - <span weight="light">tagging 2 objects of 2 different types: Family, Tag</span>',
                           '(Tag) - <span weight="light"></span>'))

    def test_remove_callback_no_confirm(self):
        # T_0
        f5 = Tag(tag=u'Arecaceae')
        self.session.add(f5)
        self.session.flush()
        self.invoked = []

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=False)
        utils.message_details_dialog = partial(
            mockfunc, name='message_details_dialog', caller=self)
        from bauble.plugins.tag import remove_callback
        result = remove_callback([f5])
        self.session.flush()

        # effect
        print self.invoked
        self.assertFalse('message_details_dialog' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove Tag: Arecaceae?')
                        in self.invoked)
        self.assertEquals(result, None)
        q = self.session.query(Tag).filter_by(tag=u"Arecaceae")
        matching = q.all()
        self.assertEquals(matching, [f5])

    def test_remove_callback_confirm(self):
        # T_0
        f5 = Tag(tag=u'Arecaceae')
        self.session.add(f5)
        self.session.flush()
        self.invoked = []
        save_status = tag_plugin.tags_menu_manager.reset

        # action
        utils.yes_no_dialog = partial(
            mockfunc, name='yes_no_dialog', caller=self, result=True)
        tag_plugin.tags_menu_manager.reset = partial(
            mockfunc, name='_reset_tags_menu', caller=self)
        from bauble.plugins.tag import remove_callback
        result = remove_callback([f5])
        tag_plugin.tags_menu_manager.reset = save_status
        self.session.flush()

        # effect
        print self.invoked
        self.assertTrue('_reset_tags_menu' in
                         [f for (f, m) in self.invoked])
        self.assertTrue(('yes_no_dialog', u'Are you sure you want to '
                         'remove Tag: Arecaceae?')
                        in self.invoked)
        self.assertEquals(result, True)
        q = self.session.query(Tag).filter_by(tag=u"Arecaceae")
        matching = q.all()
        self.assertEquals(matching, [])


class GetTagIdsTests(BaubleTestCase):

    def setUp(self):
        super(GetTagIdsTests, self).setUp()
        self.fam1 = Family(family=u'Fabaceae')
        self.fam2 = Family(family=u'Poaceae')
        self.fam3 = Family(family=u'Solanaceae')
        self.fam4 = Family(family=u'Caricaceae')
        self.session.add_all([self.fam1, self.fam2, self.fam3, self.fam4])
        self.session.commit()
        tag_plugin.tag_objects('test1', [self.fam1, self.fam2])
        tag_plugin.tag_objects('test2', [self.fam1])
        tag_plugin.tag_objects('test3', [self.fam2, self.fam3])
        self.session.commit()

    def tearDown(self):
        self.session.query(Family).delete()
        self.session.query(Tag).delete()
        self.session.commit()
        super(GetTagIdsTests, self).tearDown()

    def test_get_tag_ids1(self):
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1, self.fam2])
        self.assertEquals(s_all, set([1]))
        self.assertEquals(s_some, set([2, 3]))

    def test_get_tag_ids2(self):
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1])
        self.assertEquals(s_all, set([1, 2]))
        self.assertEquals(s_some, set([]))

    def test_get_tag_ids3(self):
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam2])
        test_id = set([1, 3])
        self.assertEquals(s_all, test_id)
        self.assertEquals(s_some, set([]))

    def test_get_tag_ids4(self):
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam3])
        test_id = set([3])
        self.assertEquals(s_all, test_id)
        self.assertEquals(s_some, set([]))

    def test_get_tag_ids5(self):
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1, self.fam3])
        test_id = set([])
        self.assertEquals(s_all, test_id)
        self.assertEquals(s_some, set([1, 2, 3]))

    def test_get_tag_ids6(self):
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1, self.fam4])
        self.assertEquals(s_all, set([]))
        self.assertEquals(s_some, set([1, 2]))

    def test_get_tag_ids7(self):
        self.session.query(Tag).delete()
        self.session.commit()
        tag_plugin.tag_objects('test1', [self.fam1, self.fam4])
        tag_plugin.tag_objects('test2', [self.fam1])
        tag_plugin.tag_objects('test3', [self.fam2, self.fam4])
        self.session.commit()
        s_all, s_some, s_none = tag_plugin.get_tag_ids([self.fam1, self.fam2, self.fam3, self.fam4])
        self.assertEquals(s_all, set([]))
        self.assertEquals(s_some, set([1, 2, 3]))


import bauble.db as db


class MockTagView(GenericEditorView):
    def __init__(self):
        self._dirty = False
        self.sensitive = False
        self.dict = {}
        self.widgets = None
        self.window = gtk.Dialog()

    def get_window(self):
        return self.window
        
    def is_dirty(self):
        return self._dirty

    def connect_signals(self, *args):
        pass

    def set_accept_buttons_sensitive(self, value):
        self.sensitive = value

    def mark_problem(self, widget_name):
        pass

    def widget_set_value(self, widget, value, markup=False, default=None,
                         index=0):
        self.dict[widget] = value

    def widget_get_value(self, widget, index=0):
        return self.dict.get(widget)


class TagPresenterTests(BaubleTestCase):
    'Presenter manages view and model, implements view callbacks.'

    def __init__(self, *args, **kwargs):
        super(TagPresenterTests, self).__init__(*args, **kwargs)
        import bauble.prefs
        bauble.prefs.testing = True

    def test_when_user_edits_name_name_is_memorized(self):
        model = Tag()
        view = MockTagView()
        presenter = TagEditorPresenter(model, view)
        view.widget_set_value('tag_name_entry', u'1234')
        presenter.on_text_entry_changed('tag_name_entry')
        self.assertEquals(presenter.model.tag, u'1234')

    def test_when_user_inserts_existing_name_warning_ok_deactivated(self):
        session = db.Session()

        # prepare data in database
        obj = Tag(tag=u'1234')
        session.add(obj)
        session.commit()
        session.close()
        ## ok. thing is already there now.

        session = db.Session()
        view = MockTagView()
        obj = Tag()  # new scratch object
        session.add(obj)  # is in session
        presenter = TagEditorPresenter(obj, view)
        self.assertTrue(not view.sensitive)  # not changed
        presenter.on_unique_text_entry_changed('tag_name_entry', u'1234')
        self.assertEquals(obj.tag, u'1234')
        self.assertTrue(view.is_dirty())
        self.assertTrue(not view.sensitive)  # unacceptable change
        self.assertTrue(presenter.has_problems())

    def test_widget_names_and_field_names(self):
        model = Tag()
        view = MockTagView()
        presenter = TagEditorPresenter(model, view)
        for widget, field in presenter.widget_to_field_map.items():
            self.assertTrue(hasattr(model, field), field)
            presenter.view.widget_get_value(widget)

    def test_when_user_edits_fields_ok_active(self):
        model = Tag()
        view = MockTagView()
        presenter = TagEditorPresenter(model, view)
        self.assertTrue(not view.sensitive)  # not changed
        view.widget_set_value('tag_name_entry', u'1234')
        presenter.on_text_entry_changed('tag_name_entry')
        self.assertEquals(presenter.model.tag, u'1234')
        self.assertTrue(view.sensitive)  # changed

    def test_when_user_edits_description_description_is_memorized(self):
        pass

    def test_presenter_does_not_initialize_view(self):
        session = db.Session()

        # prepare data in database
        obj = Tag(tag=u'1234')
        session.add(obj)
        view = MockTagView()
        presenter = TagEditorPresenter(obj, view)
        self.assertFalse(view.widget_get_value("tag_name_entry"))
        presenter.refresh_view()
        self.assertEquals(view.widget_get_value("tag_name_entry"), u'1234')

    def test_if_asked_presenter_initializes_view(self):
        session = db.Session()

        # prepare data in database
        obj = Tag(tag=u'1234')
        session.add(obj)
        view = MockTagView()
        TagEditorPresenter(obj, view, refresh_view=True)
        self.assertEquals(view.widget_get_value("tag_name_entry"), u'1234')


class AttachedToTests(BaubleTestCase):

    def __init__(self, *args, **kwargs):
        super(AttachedToTests, self).__init__(*args, **kwargs)
        import bauble.prefs
        bauble.prefs.testing = True

    def setUp(self):
        super(AttachedToTests, self).setUp()
        obj1 = Tag(tag=u'medicinal')
        obj2 = Tag(tag=u'maderable')
        obj3 = Tag(tag=u'frutal')
        fam = Family(family=u'Solanaceae')
        self.session.add_all([obj1, obj2, obj3, fam])
        self.session.commit()

    def test_attached_tags_empty(self):
        fam = self.session.query(Family).one()
        self.assertEquals(Tag.attached_to(fam), [])

    def test_attached_tags_singleton(self):
        fam = self.session.query(Family).one()
        obj2 = self.session.query(Tag).filter(Tag.tag == u'maderable').one()
        tag_plugin.tag_objects(obj2, [fam])
        self.assertEquals(Tag.attached_to(fam), [obj2])

    def test_attached_tags_many(self):
        fam = self.session.query(Family).one()
        tags = self.session.query(Tag).all()
        for t in tags:
            tag_plugin.tag_objects(t, [fam])
        self.assertEquals(Tag.attached_to(fam), tags)


class TagInfoBoxTest(BaubleTestCase):
    def test_can_create_infobox(self):
        ib = TagInfoBox()

    def test_update_infobox_from_empty_tag(self):
        t = Tag(tag=u'name', description=u'description')
        ib = TagInfoBox()
        ib.update(t)
        self.assertEquals(ib.widgets.ib_description_label.get_text(), t.description)
        self.assertEquals(ib.widgets.ib_name_label.get_text(), t.tag)
        self.assertEquals(ib.general.table_cells, [])

    def test_update_infobox_from_tagging_tag(self):
        t = Tag(tag=u'name', description=u'description')
        x = Tag(tag=u'objectx', description=u'none')
        y = Tag(tag=u'objecty', description=u'none')
        z = Tag(tag=u'objectz', description=u'none')
        self.session.add_all([t, x, y, z])
        self.session.commit()
        t.tag_objects([x, y, z])
        ib = TagInfoBox()
        self.assertEquals(ib.general.table_cells, [])
        ib.update(t)
        self.assertEquals(ib.widgets.ib_description_label.get_text(), t.description)
        self.assertEquals(ib.widgets.ib_name_label.get_text(), t.tag)
        self.assertEquals(len(ib.general.table_cells), 2)
        self.assertEquals(ib.general.table_cells[0].get_text(), u'Tag')
        self.assertEquals(type(ib.general.table_cells[1]), gtk.EventBox)
        label = ib.general.table_cells[1].get_children()[0]
        self.assertEquals(label.get_text(), ' 3 ')


class TagCallbackTest(BaubleTestCase):
    def test_on_add_tag_activated_wrong_view(self):
        class FakeGui:
            def __init__(self):
                self.invoked = []
            def get_view(self):
                return MockView(selection=[])
            def show_message_box(self, *args, **kwargs):
                self.invoked.append((args, kwargs))
                pass
        import bauble
        bauble.gui = localgui = FakeGui()
        tag_plugin._on_add_tag_activated()
        reload(bauble)
        self.assertEquals(localgui.invoked[0],
                          (('In order to tag an item you must first search for something and select one of the results.', ), {}))

    def test_on_add_tag_activated_search_view_empty_selection(self):
        class FakeGui:
            def __init__(self):
                self.invoked = []
            def get_view(self):
                view = MockView()
                view.get_selected_values = lambda: []
                return view
            def show_message_box(self, *args, **kwargs):
                self.invoked.append((args, kwargs))
                pass
        import bauble
        bauble.gui = localgui = FakeGui()
        utils.message_dialog = bauble.gui.show_message_box
        tag_plugin._on_add_tag_activated()
        reload(bauble)
        reload(utils)
        self.assertEquals(localgui.invoked[0],
                          (('Nothing selected', ), {}))

