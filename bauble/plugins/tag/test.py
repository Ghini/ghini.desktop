# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import os

from sqlalchemy import or_
#from sqlalchemy.exc import *

from nose import SkipTest

import bauble.plugins.tag as tag_plugin
from bauble.plugins.plants import Family
from bauble.plugins.tag import Tag, TagEditorPresenter
from bauble.test import BaubleTestCase, check_dupids
from bauble.editor import GenericEditorView


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


class TagTests(BaubleTestCase):

    def __init__(self, *args, **kwargs):
        super(TagTests, self).__init__(*args, **kwargs)
        import bauble.prefs
        bauble.prefs.testing = True

    family_ids = [1, 2]

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
        self.assert_(str(tag) == name)

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
        # now untag everything
        #
        tag_plugin.untag_objects('test', [self.family, family2])

        # get object by tag
        tag = self.session.query(Tag).filter_by(tag=u'test').one()
        tagged_objs = tag.objects
        self.assertEquals(tagged_objs, [])

    def test_get_tag_ids(self):
        family2 = Family(family=u'family2')
        self.session.add(family2)
        self.session.flush()
        tag_plugin.tag_objects('test', [self.family, family2])
        tag_plugin.tag_objects('test2', [self.family])

        # test we only return the ids the objects have in common
        #sel = select([tag_table.c.id], tag_table.c.tag==u'test')
        results = self.session.query(Tag.id).filter_by(tag=u'test')
        test_id = [r[0] for r in results]
        # should only return id for "test"
        ids = tag_plugin.get_tag_ids([self.family, family2])
        self.assert_(ids == test_id, '%s==%s' % (ids, test_id))

        # test that we return multiple tag ids if the objs share tags
        tag_plugin.tag_objects('test2', [family2])
        #sel = select([tag_table.c.id], or_(tag_table.c.tag==u'test',
        #                                   tag_table.c.tag==u'test2'))
        results = self.session.query(Tag.id).filter(or_(Tag.tag == u'test',
                                                        Tag.tag == u'test2'))
        test_id = sorted([r[0] for r in results])
        # should return ids for both test and test2
        ids = sorted(tag_plugin.get_tag_ids([self.family, family2]))
        self.assert_(ids == test_id, '%s == %s' % (ids, test_id))

import bauble.db as db


class MockTagView(GenericEditorView):
    def __init__(self):
        self._dirty = False
        self.sensitive = False
        self.dict = {}
        self.widgets = None

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
        self.assertEquals(model.tag, u'1234')

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
        self.assertEquals(model.tag, u'1234')
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
