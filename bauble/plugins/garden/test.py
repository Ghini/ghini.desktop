import os
import datetime
import unittest

import gtk
from nose import SkipTest
from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm import *

import bauble
import bauble.db as db
from bauble.error import CheckConditionError, check
from bauble.test import BaubleTestCase, update_gui, check_dupids
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.plugins.garden.accession import *
from bauble.plugins.garden.source import *
from bauble.plugins.garden.plant import *
from bauble.plugins.garden.location import *
from bauble.plugins.garden.propagation import *
from bauble.plugins.plants.family import *
from bauble.plugins.plants.genus import *
from bauble.plugins.plants.species_model import *
import bauble.plugins.plants.test as plants_test
from bauble.plugins.garden.institution import *
import bauble.prefs as prefs


accession_test_data = ({'id':1 , 'code': u'1.1', 'species_id': 1},
                       {'id':2 , 'code': u'2.2', 'species_id': 2,
                        'source_type': u'Collection'},
                       )

plant_test_data = ({'id':1 , 'code': u'1', 'accession_id': 1,
                    'location_id': 1},
                   )

location_test_data = ({'id': 1, 'name': u'Somewhere Over The Rainbow',
                       'code': u'RBW'},
                      )

contact_test_data = ({'id': 1, 'name': u'SomeContact'},
                   )

# donation_test_data = ({'id': 1, 'accession_id': 1, 'donor_id': 1},
#                       )

collection_test_data = ({'id': 1, 'accession_id': 2, 'locale': u'Somewhere'},
                        )

default_cutting_values = \
            {'cutting_type': u'Nodal',
             'length': 2,
             'tip': u'Intact',
             'leaves': u'Intact',
             'leaves_reduced_pct': 25,
             'flower_buds': u'None',
             'wound': u'Single',
             'fungicide': u'Physan',
             'media': u'standard mix',
             'container': u'4" pot',
             'hormone': u'Auxin powder',
             'cover': u'Poly cover',
             'location': u'Mist frame',
             'bottom_heat_temp': 65,
             'bottom_heat_unit': u'F',
             'rooted_pct': 90}

default_seed_values = \
            {'pretreatment': u'Soaked in peroxide solution',
             'nseeds': 24,
             'date_sown': datetime.date.today(),#utils.today_str(),
             'container': u"tray",
             'media': u'standard seed compost',
             'location': u'mist tent',
             'moved_from': u'mist tent',
             'moved_to': u'hardening table',
             'media': u'standard mix',
             'germ_date': datetime.date.today(),#utils.today_str(),
             'germ_pct': 99,
             'nseedlings': 23,
             'date_planted': datetime.date.today()} #utils.today_str()}

test_data_table_control = ((Accession, accession_test_data),
                           (Location, location_test_data),
                           (Plant, plant_test_data),
                           (Contact, contact_test_data),
                           (Collection, collection_test_data))

def setUp_data():
    """
    create_test_data()
    #if this method is called again before tearDown_test_data is called you
    #will get an error about the test data rows already existing in the database
    """
    for cls, data in test_data_table_control:
        table = cls.__table__
        for row in data:
            table.insert().execute(row).close()
        for col in table.c:
            utils.reset_sequence(col)
    i = Institution()
    i.name = u'TestInstitution'
    i.technical_contact = u'TestTechnicalContact Name'
    i.email = u'contact@test.com'
    i.contact = u'TestContact Name'
    i.code = u'TestCode'



# TODO: if we ever get a GUI tester then do the following
# test all possible combinations of entering data into the accession editor
# 1. new accession without source
# 2. new accession with source
# 3. existing accession without source
# 4. existing accession with new source
# 5. existing accession with existing source
# - create test for parsing latitude/longitude entered into the lat/lon entries


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the gardens plugin.
    """
    import bauble.plugins.garden as mod
    import glob
    head, tail = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, '*.glade'))
    for f in files:
        assert(not check_dupids(f))



class GardenTestCase(BaubleTestCase):

    def __init__(self, *args):
        super(GardenTestCase, self).__init__(*args)

    def setUp(self):
        super(GardenTestCase, self).setUp()
        plants_test.setUp_data()
        #setUp_test_data()
        self.family = Family(family=u'fam')
        self.genus = Genus(family=self.family, genus=u'gen')
        self.species = Species(genus=self.genus, sp=u'sp')
        self.session.add_all([self.family, self.genus, self.species])
        self.session.commit()

    # def tearDown(self):
    #     print >>sys.stderr, 'GardenTestCase.tearDown()'
    #     super(GardenTestCase, self).tearDown()

    def create(self, class_, **kwargs):
        obj = class_(**kwargs)
        self.session.add(obj)
        return obj


class ContactTests(GardenTestCase):

    def __init__(self, *args):
        super(ContactTests, self).__init__(*args)


    # def test_delete(self):
    #     acc = self.create(Accession, species=self.species, code=u'1')
    #     contact = Contact(name=u'name')
    #     donation = Donation()
    #     donation.contact = contact
    #     acc.source = donation
    #     self.session.commit()
    #     self.session.close()

    #     # test that we can't delete a contact if it has corresponding donations
    #     import bauble
    #     session = db.Session()
    #     contact = session.query(Contact).filter_by(name=u'name').one()
    #     # shouldn't be allowed to delete contact if it has donations,
    #     # what is happening here is that when deleting the contact the
    #     # corresponding donations.contact_id's are being be set to null which
    #     # isn't allowed by the scheme....is this the best we can do? or can we
    #     # get some sort of error when creating a dangling reference
    #     session.delete(contact)
    #     self.assertRaises(SQLError, session.commit)


    def itest_contact_editor(self):
        """
        Interactively test the PlantEditor
        """
        loc = self.create(Contact, name=u'some contact')
        editor = ContactEditor(model=loc)
        editor.start()
        del editor
        assert utils.gc_objects_by_type('ContactEditor') == [], \
            'ContactEditor not deleted'
        assert utils.gc_objects_by_type('ContactEditorPresenter') == [], \
            'ContactEditorPresenter not deleted'
        assert utils.gc_objects_by_type('ContactEditorView') == [], \
            'ContactEditorView not deleted'



class PlantTests(GardenTestCase):

    def __init__(self, *args):
        super(PlantTests, self).__init__(*args)

    def setUp(self):
        super(PlantTests, self).setUp()
        self.accession = self.create(Accession, species=self.species,code=u'1')
        self.location = self.create(Location, name=u'site', code=u'STE')
        self.plant = self.create(Plant, accession=self.accession,
                                 location=self.location, code=u'1')
        self.session.commit()

    def tearDown(self):
        super(PlantTests, self).tearDown()


    def test_constraints(self):
        """
        Test the contraints on the plant table.
        """
        # test that we can't have duplicate codes with the same accession
        plant2 = Plant(accession=self.accession, location=self.location,
                       code=self.plant.code)
        self.session.add(plant2)
        self.assertRaises(IntegrityError, self.session.commit)
        # rollback the IntegrityError so tearDown() can do its job
        self.session.rollback()


    def test_delete(self):
        """
        Test that when a plant is deleted...
        """
        pass


    def test_editor_transfer(self):
        """
        """
        # TODO: right now the test only shows adding a transfer to a
        # plant but we need to be sure that transfers are appended if
        # transfers already exist on the plant
        try:
            import gtk
        except ImportError:
            raise SkipTest('could not import gtk')

        # delete any plants in the database
        for plant in self.session.query(Plant):
            self.session.delete(plant)
        self.session.commit()

        p1 = Plant(accession=self.accession, location=self.location, code=u'1')
        p2 = Plant(accession=self.accession, location=self.location, code=u'2')
        self.accession.plants.append(p1)
        self.accession.plants.append(p2)
        editor = PlantStatusEditor(model=[p1, p2])
        update_gui()

        widgets = editor.presenter.view.widgets
        widgets.plant_transfer_radio.set_active(True)
        widgets.trans_to_comboentry.child.props.text = self.location.name
        update_gui()

        editor.handle_response(gtk.RESPONSE_OK)
        for p in editor.plants:
            # TODO: need to assert that the values of
            # editor.presenter._transfer are equal to the transfer in
            # the plant
            self.assert_(len(p.transfers) > 0)
        editor.presenter.cleanup()


    def test_editor_removal(self):
        """
        """
        # TODO: right now the test only shows adding a transfer to a
        # plant but we need to be sure that transfers are appended if
        # transfers already exist on the plant
        # TODO: need to also test the the plants.removal was not set
        try:
            import gtk
        except ImportError:
            raise SkipTest('could not import gtk')

        # delete any plants in the database
        for plant in self.session.query(Plant):
            self.session.delete(plant)
        self.session.commit()

        p1 = Plant(accession=self.accession, location=self.location, code=u'1')
        p2 = Plant(accession=self.accession, location=self.location, code=u'2')
        self.accession.plants.append(p1)
        self.accession.plants.append(p2)
        editor = PlantStatusEditor(model=[p1, p2])
        update_gui()

        widgets = editor.presenter.view.widgets
        widgets.plant_remove_radio.set_active(True)
        utils.set_widget_value(widgets.rem_reason_combo, u'DEAD')
        update_gui()


        self.assert_(len(editor.presenter.problems)<1,
                     'widgets have problems')

        editor.handle_response(gtk.RESPONSE_OK)
        for p in editor.plants:
            # TODO: need to assert that the values of
            # editor.presenter._transfer are equal to the transfer in
            # the plant
            #debug(p.removal)
            self.assert_(p.removal)
        editor.presenter.cleanup()


    def test_editor_addnote(self):
        raise SkipTest('Not Implemented')


    def itest_status_editor(self):
        p1 = Plant(accession=self.accession, location=self.location,
                   code=u'52')
        p2 = Plant(accession=self.accession, location=self.location,
                   code=u'53')
        self.accession.plants.append(p1)
        self.accession.plants.append(p2)
        plants = [p1, p2]
        self.session.add_all(plants)
        e = PlantStatusEditor(plants)
        e.start()


    def test_bulk_plant_editor(self):
        """
        Test creating multiple plants with the plant editor.
        """
        try:
            import gtk
        except ImportError:
            raise SkipTest('could not import gtk')
        editor = PlantEditor(model=self.plant)
        #editor.start()
        update_gui()
        rng = '2,3,4-6'

        for code in utils.range_builder(rng):
            q = self.session.query(Plant).join('accession').\
                filter(and_(Accession.id==self.plant.accession.id,
                            Plant.code==utils.utf8(code)))
            self.assert_(not q.first(), 'code already exists')

        widgets = editor.presenter.view.widgets
        # make sure the entry gets a Problem added to it if an
        # existing plant code is used in bulk mode
        widgets.plant_code_entry.set_text('1,' + rng)
        update_gui()
        problem = (editor.presenter.PROBLEM_DUPLICATE_PLANT_CODE,
                   editor.presenter.view.widgets.plant_code_entry)
        self.assert_(problem in editor.presenter.problems,
                     'no problem added for duplicate plant code')

        # create multiple plant codes
        widgets.plant_code_entry.set_text(rng)
        update_gui()
        editor.handle_response(gtk.RESPONSE_OK)

        for code in utils.range_builder(rng):
            q = self.session.query(Plant).join('accession').\
                filter(and_(Accession.id==self.plant.accession.id,
                            Plant.code==utils.utf8(code)))
            self.assert_(q.first(), 'plant %s.%s not created' % \
                            (self.accession, code))

        editor.presenter.cleanup()
        del editor
        assert utils.gc_objects_by_type('PlantEditor') == [], \
            'PlantEditor not deleted'
        assert utils.gc_objects_by_type('PlantEditorPresenter') == [], \
            'PlantEditorPresenter not deleted'
        assert utils.gc_objects_by_type('PlantEditorView') == [], \
            'PlantEditorView not deleted'


    def itest_editor(self):
        """
        Interactively test the PlantEditor
        """
        for plant in self.session.query(Plant):
            self.session.delete(plant)
        for location in self.session.query(Location):
            self.session.delete(location)
        self.session.commit()

        #editor = PlantEditor(model=self.plant)
        loc = Location(name=u'site1', code=u'1')
        loc2 = Location(name=u'site2', code=u'2')
        loc2a = Location(name=u'site2a', code=u'2a')
        self.session.add_all([loc, loc2, loc2a])
        self.session.commit()
        p = Plant(accession=self.accession, location=loc)
        editor = PlantEditor(model=p)
        editor.start()
        del editor

        assert utils.gc_objects_by_type('PlantEditor') == [], \
            'PlantEditor not deleted'
        assert utils.gc_objects_by_type('PlantEditorPresenter') == [], \
            'PlantEditorPresenter not deleted'
        assert utils.gc_objects_by_type('PlantEditorView') == [], \
            'PlantEditorView not deleted'


class PropagationTests(GardenTestCase):


    def __init__(self, *args):
        super(PropagationTests, self).__init__(*args)


    def setUp(self):
        super(PropagationTests, self).setUp()
        self.accession = self.create(Accession, species=self.species,code=u'1')
        # self.location = self.create(Location, name=u'name', code=u'code')
        # self.plant = self.create(Plant, accession=self.accession,
        #                          location=self.location, code=u'2')
        self.session.commit()


    def tearDown(self):
        #self.session.delete(self.location)
        #self.session.delete(self.plant)
        #self.session.commit()
        #self.session.begin()
        super(PropagationTests, self).tearDown()


    def test_plant_prop(self):
        """
        Test the Accession->AccessionPropagation->Propagation relation
        """
        loc = Location(name=u'name', code=u'code')
        plant = Plant(accession=self.accession, location=loc, code=u'1')
        prop = Propagation()
        prop.plant = plant
        prop.prop_type = u'UnrootedCutting'
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = prop
        self.session.commit()
        self.assert_(prop in self.accession.propagations)
        self.assert_(prop.accession == self.accession)


    def test_plant_prop(self):
        """
        Test the Plant->PlantPropagation->Propagation relation
        """
        prop = Propagation()
        loc = self.create(Location, name=u'site1', code=u'1')
        plant = self.create(Plant, accession=self.accession, location=loc,
                            code=u'1')
        prop.prop_type = u'UnrootedCutting'
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = prop
        plant.propagations.append(prop)
        self.session.commit()
        self.assert_(prop in plant.propagations)
        self.assert_(prop.plant == plant)


    def test_get_summary(self):
        loc = Location(name=u'name', code=u'code')
        plant = Plant(accession=self.accession, location=loc, code=u'1')
        prop = Propagation()
        prop.plant = plant
        prop.prop_type = u'UnrootedCutting'
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = prop
        rooted = PropRooted()
        rooted.cutting = cutting
        self.session.commit()
        summary = prop.get_summary()
        #debug(summary)
        self.assert_(summary)

        prop = Propagation()
        prop.prop_type = u'Seed'
        prop.plant = plant
        seed = PropSeed(**default_seed_values)
        seed.propagation = prop
        self.session.commit()
        summary = prop.get_summary()
        #debug(summary)
        self.assert_(summary)


    def test_cutting_property(self):
        loc = Location(name=u'name', code=u'code')
        plant = Plant(accession=self.accession, location=loc, code=u'1')
        prop = Propagation()
        prop.plant = plant
        prop.prop_type = u'UnrootedCutting'
        prop.accession = self.accession
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = prop
        rooted = PropRooted()
        rooted.cutting = cutting
        self.session.add(rooted)
        self.session.commit()

        self.assert_(rooted in prop._cutting.rooted)

        rooted_id = rooted.id
        cutting_id = cutting.id
        self.assert_(rooted_id, 'no prop_rooted.id')

        # setting the _cutting property on Propagation should cause
        # the cutting and its rooted children to be deleted
        prop._cutting = None
        self.session.commit()
        self.assert_(not self.session.query(PropCutting).get(cutting_id))
        self.assert_(not self.session.query(PropRooted).get(rooted_id))


    def test_seed_property(self):
        loc = Location(name=u'name', code=u'code')
        plant = Plant(accession=self.accession, location=loc, code=u'1')
        prop = Propagation()
        plant.propagations.append(prop)
        prop.prop_type = u'Seed'
        prop.accession = self.accession
        seed = PropSeed(**default_seed_values)
        self.session.add(seed)
        seed.propagation = prop
        self.session.commit()

        self.assert_(seed == prop._seed)
        seed_id = seed.id

        # this should cause the cutting and its rooted children to be deleted
        prop._seed = None
        self.session.commit()
        self.assert_(not self.session.query(PropSeed).get(seed_id))


    def test_cutting_editor(self):
        loc = Location(name=u'name', code=u'code')
        plant = Plant(accession=self.accession, location=loc, code=u'1')
        propagation = Propagation()
        plant.propagations.append(propagation)
        editor = PropagationEditor(model=propagation)
        widgets = editor.presenter.view.widgets
        view = editor.presenter.view
        view.set_widget_value('prop_type_combo', u'UnrootedCutting')
        view.set_widget_value('prop_date_entry', utils.today_str())
        cutting_presenter = editor.presenter._cutting_presenter
        for widget, attr in cutting_presenter.widget_to_field_map.iteritems():
            #debug('%s=%s' % (widget, self.default_cutting_values[attr]))
            view.set_widget_value(widget, default_cutting_values[attr])
        update_gui()
        editor.handle_response(gtk.RESPONSE_OK)
        editor.presenter.cleanup()
        editor.commit_changes()
        model = editor.model
        s = object_session(model)
        s.expire(model)
        self.assert_(model.prop_type == u'UnrootedCutting')
        for attr, value in default_cutting_values.iteritems():
            v = getattr(model._cutting, attr)
            self.assert_(v==value, '%s = %s(%s)' % (attr, value, v))
        editor.session.close()


    def test_seed_editor(self):
        loc = Location(name=u'name', code=u'code')
        plant = Plant(accession=self.accession, location=loc, code=u'1')
        propagation = Propagation()
        plant.propagations.append(propagation)
        editor = PropagationEditor(model=propagation)
        widgets = editor.presenter.view.widgets
        view = editor.presenter.view
        view.set_widget_value('prop_type_combo', u'Seed')
        view.set_widget_value('prop_date_entry', utils.today_str())
        cutting_presenter = editor.presenter._seed_presenter
        for widget, attr in cutting_presenter.widget_to_field_map.iteritems():
            w = widgets[widget]
            if isinstance(w, gtk.ComboBoxEntry) and not w.get_model():
                widgets[widget].child.props.text = default_seed_values[attr]
            view.set_widget_value(widget, default_seed_values[attr])
        update_gui()
        editor.handle_response(gtk.RESPONSE_OK)
        editor.presenter.cleanup()
        model = editor.model
        s = object_session(model)
        editor.commit_changes()
        s.expire(model)
        self.assert_(model.prop_type == u'Seed')
        for attr, expected in default_seed_values.iteritems():
            v = getattr(model._seed, attr)
            if isinstance(v, datetime.date):
                format = prefs.prefs[prefs.date_format_pref]
                v = v.strftime(format)
                if isinstance(expected, datetime.date):
                    expected = expected.strftime(format)
            self.assert_(v==expected, '%s = %s(%s)' % (attr, expected, v))
        editor.session.close()



    def itest_editor(self):
        """
        Interactively test the PropagationEditor
        """
        from bauble.plugins.garden.propagation import PropagationEditor
        propagation = Propagation()
        #propagation.prop_type = u'UnrootedCutting'
        propagation.accession = self.accession
        editor = PropagationEditor(model=propagation)
        propagation = editor.start()
        debug(propagation)
        self.assert_(propagation.accession)



class VoucherTests(GardenTestCase):

    def __init__(self, *args):
        super(VoucherTests, self).__init__(*args)

    def setUp(self):
        super(VoucherTests, self).setUp()
        self.accession = self.create(Accession, species=self.species,code=u'1')
        self.session.commit()

    def tearDown(self):
        super(VoucherTests, self).tearDown()

    def test_voucher(self):
        """
        Test the Accession.voucher property
        """
        voucher = Voucher(herbarium=u'ABC', code=u'1234567')
        voucher.accession = self.accession
        self.session.commit()
        voucher_id = voucher.id
        self.accession.vouchers.remove(voucher)
        self.session.commit()
        self.assert_(not self.session.query(Voucher).get(voucher_id))

        # test that if we set voucher.accession to None then the
        # voucher is deleted but not the accession
        voucher = Voucher(herbarium=u'ABC', code=u'1234567')
        voucher.accession = self.accession
        self.session.commit()
        voucher_id = voucher.id
        acc_id = voucher.accession.id
        voucher.accession = None
        self.session.commit()
        self.assert_(not self.session.query(Voucher).get(voucher_id))
        self.assert_(self.session.query(Accession).get(acc_id))


class SourceTests(GardenTestCase):

    def __init__(self, *args):
        super(SourceTests, self).__init__(*args)

    def setUp(self):
        super(SourceTests, self).setUp()
        self.accession = self.create(Accession, species=self.species, code=u'1')

    def tearDown(self):
        super(SourceTests, self).tearDown()


    def _make_prop(self, source):
        source.propagation = Propagation(prop_type=u'Seed')

        # a propagation doesn't normally have _seed and _cutting but
        # its ok here for the test
        seed = PropSeed(**default_seed_values)
        seed.propagation = source.propagation
        cutting = PropCutting(**default_cutting_values)
        cutting.propagation = source.propagation
        self.session.commit()
        prop_id = source.propagation.id
        seed_id = source.propagation._seed.id
        cutting_id = source.propagation._cutting.id
        return prop_id, seed_id, cutting_id


    def test_propagation(self):
        """
        Test the Source.propagation relation
        """
        # test setting and then removing the propagation on the source
        source = Source()
        self.accession.source = source
        prop_id, seed_id, cutting_id = self._make_prop(source)
        self.session.commit()
        source.propagation = None
        self.session.commit()
        self.assert_(seed_id)
        self.assert_(cutting_id)
        self.assert_(prop_id)
        self.assert_(not self.session.query(PropSeed).get(seed_id))
        self.assert_(not self.session.query(PropCutting).get(cutting_id))
        self.assert_(not self.session.query(Propagation).get(prop_id))


        source = Source()
        self.accession.source = source
        prop_id, seed_id, cutting_id = self._make_prop(source)
        tmp_session = db.Session()
        prop2 = source.propagation
        #self.session.expunge(prop2)
        source.propagation = None
        #tmp_session.add(prop2)
        #tmp_session.close()
        self.session.commit()
        #tmp_session.close()
        self.assert_(not self.session.query(PropSeed).get(seed_id))
        self.assert_(not self.session.query(PropCutting).get(cutting_id))
        self.assert_(not self.session.query(Propagation).get(prop_id))
        self.session.commit()


    def test(self):
        """
        Test bauble.plugins.garden.Source and related properties
        """
        source = Source()
        debug(source.plant_propagation)
        #self.assert_(hasattr(source, 'plant_propagation'))

        location = Location(code=u'1')
        plant = Plant(accession=self.accession, location=location, code=u'1')
        plant.propagations.append(Propagation(prop_type=u'Seed'))
        self.session.commit()

        source.source_contact = SourceContact()
        source.source_contact.contact = Contact(name=u'name')
        source.source_contact.contact_code = u'1'
        source.collection = Collection(locale=u'locale')
        source.propagation = Propagation(prop_type=u'Seed')
        source.plant_propagation = plant.propagations[0]
        source.accession = self.accession # test the source's accession property
        self.session.commit()

        # test that cascading works properly
        src_contact_id = source.source_contact.id
        contact_id = source.source_contact.contact.id
        coll_id = source.collection.id
        prop_id = source.propagation.id
        plant_prop_id = source.plant_propagation.id
        self.accession.source = None # tests the accessions source
        self.session.commit()

        # the SourceContact, Colection and Propagation should be
        # deleted since they are specific to the source
        self.assert_(not self.session.query(SourceContact).get(src_contact_id))
        self.assert_(not self.session.query(Collection).get(coll_id))
        self.assert_(not self.session.query(Propagation).get(prop_id))

        # the contact and plant propagation shouldn't be deleted since
        # they are independent of the source
        self.assert_(self.session.query(Contact).get(contact_id))
        self.assert_(self.session.query(Propagation).get(plant_prop_id))





class AccessionTests(GardenTestCase):

    def __init__(self, *args):
        super(AccessionTests, self).__init__(*args)

    def setUp(self):
        super(AccessionTests, self).setUp()

    def tearDown(self):
        super(AccessionTests, self).tearDown()


    def test_species_str(self):
        """
        Test Accesion.species_str()
        """
        acc = self.create(Accession, species=self.species, code=u'1')
        s = 'gen sp'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' % (s, sp_str))
        acc.id_qual = '?'
        s = 'gen sp(?)'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' % (s, sp_str))

        acc.id_qual = 'aff.'
        acc.id_qual_rank = 'sp'
        s = 'gen aff. sp'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        # here species.infrasp is None but we still allow the string
        acc.id_qual = 'cf.'
        acc.id_qual_rank = 'infrasp'
        s = 'gen sp cf.'#' None'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' % (s, sp_str))

        # species.infrasp is still none but these just get pasted on
        # the end so it doesn't matter
        acc.id_qual = 'incorrect'
        acc.id_qual_rank = 'infrasp'
        s = 'gen sp(incorrect)'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        acc.id_qual = 'forsan'
        acc.id_qual_rank = 'sp'
        s = 'gen sp(forsan)'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

        acc.species.set_infrasp(1, u'cv.', u'Cultivar')
        acc.id_qual = u'cf.'
        acc.id_qual_rank = u'infrasp'
        s = "gen sp cf. 'Cultivar'"
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))


        # test that the cached string is returned

        # have to commit because the cached string won't be returned
        # on dirty species
        self.session.commit()
        s2 = acc.species_str()
        assert id(sp_str) == id(s2), '%s(%s) == %s(%s)' % (sp_str, id(sp_str),
                                                           s2, id(s2))

        # this used to test that if the id_qual was set but the
        # id_qual_rank wasn't then we would get an error. now we just
        # show an warning and put the id_qual on the end of the string
#         acc.id_qual = 'aff.'
#         acc.id_qual_rank = None
#         self.assertRaises(CheckConditionError, acc.species_str)


    def test_delete(self):
        """
        Test that when an accession is deleted any orphaned rows are
        cleaned up.
        """
        acc = self.create(Accession, species=self.species, code=u'1')
        plant = self.create(Plant, accession=acc,
                            location=Location(name=u'site', code=u'STE'),
                            code=u'1')
        self.session.commit()

        # test that the plant is deleted after being orphaned
        plant_id = plant.id
        self.session.delete(acc)
        self.session.commit()
        self.assert_(not self.session.query(Plant).get(plant_id))


    def test_constraints(self):
        """
        Test the constraints on the accession table.
        """
        acc = Accession(species=self.species, code=u'1')
        self.session.add(acc)
        self.session.commit()

        # test that accession.code is unique
        acc = Accession(species=self.species, code=u'1')
        self.session.add(acc)
        self.assertRaises(IntegrityError, self.session.commit)


    def test_accession_editor(self):
        acc = Accession(code=u'code', species=self.species)
        editor = AccessionEditor(acc)
        update_gui()

        widgets = editor.presenter.view.widgets
        # make sure there is a problem if the species entry text isn't
        # a species string
        widgets.acc_species_entry.set_text('asdasd')
        assert editor.presenter.problems

        # make sure the problem is removed if the species entry text
        # is set to a species string

        # fill in the completions
        widgets.acc_species_entry.set_text(str(self.species)[0:3])
        update_gui() # ensures idle callback is called to add completions
        # set the fill string which should match from completions
        widgets.acc_species_entry.set_text(str(self.species))
        assert not editor.presenter.problems, editor.presenter.problems

        # commit the changes and cleanup
        editor.model.name = u'asda'
        import gtk
        editor.handle_response(gtk.RESPONSE_OK)
        editor.session.close()
        editor.presenter.cleanup()
        del editor

        assert utils.gc_objects_by_type('AccessionEditor') == [], \
            'AccessionEditor not deleted'
        assert utils.gc_objects_by_type('AccessionEditorPresenter') == [], \
            'AccessionEditorPresenter not deleted'
        assert utils.gc_objects_by_type('AccessionEditorView') == [], \
            'AccessionEditorView not deleted'


    def itest_editor(self):
        """
        Interactively test the AccessionEditor
        """
        #donor = self.create(Donor, name=u'test')
        sp2 = Species(genus=self.genus, sp=u'species')
        sp2.synonyms.append(self.species)
        self.session.add(sp2)
        self.session.commit()
        # import datetime again since sometimes i get an weird error
        import datetime
        acc_code = '%s%s1' % (datetime.date.today().year, Plant.get_delimiter())
        acc = self.create(Accession, species=self.species, code=acc_code)
        voucher = Voucher(herbarium=u'abcd', code=u'123')
        acc.vouchers.append(voucher)
        prev = 0
        def mem(size="rss"):
            """Generalization; memory sizes: rss, rsz, vsz."""
            import os
            return int(os.popen('ps -p %d -o %s | tail -1' % \
                                    (os.getpid(), size)).read())

        # add verificaiton
        ver = Verification()
        ver.verifier = u'me'
        ver.date = datetime.date.today()
        ver.prev_species = self.species
        ver.species = self.species
        ver.level = 1
        acc.verifications.append(ver)

        location = Location(name=u'loc1', code=u'loc1')
        plant = Plant(accession=acc, location=location, code=u'1')
        prop = Propagation(prop_type=u'Seed')
        seed = PropSeed(**default_seed_values)
        seed.propagation = prop
        plant.propagations.append(prop)
        self.session.commit()


        #editor = AccessionEditor(model=acc)
        # try:
        #     editor.start()
        # except Exception, e:
        #     import traceback
        #     debug(traceback.format_exc(0))
        #     debug(e)
        # return
        editor = None
        for x in range(0, 1):
            #editor = AccessionEditor(model=acc)
            editor = AccessionEditor()
            editor.start()
            del editor
            leak = mem()
            debug('%s: %s' % (leak, leak-prev))
            prev = leak
            #debug(mem())

        assert utils.gc_objects_by_type('AccessionEditor') == [], \
            'AccessionEditor not deleted'
        assert utils.gc_objects_by_type('AccessionEditorPresenter') == [], \
            'AccessionEditorPresenter not deleted'
        assert utils.gc_objects_by_type('AccessionEditorView') == [], \
            'AccessionEditorView not deleted'


class VerificationTests(GardenTestCase):

    def __init__(self, *args):
        super(VerificationTests, self).__init__(*args)

    def setUp(self):
        super(VerificationTests, self).setUp()

    def tearDown(self):
        super(VerificationTests, self).tearDown()


    def test_verifications(self):
        acc = self.create(Accession, species=self.species, code=u'1')
        self.session.add(acc)
        self.session.commit()

        ver =  Verification()
        ver.verifier = u'me'
        ver.date = datetime.date.today()
        ver.level = 1
        ver.species = acc.species
        ver.prev_species = acc.species
        acc.verifications.append(ver)
        try:
            self.session.commit()
        except Exception, e:
            debug(e)
            self.session.rollback()
        self.assert_(ver in acc.verifications)
        self.assert_(ver in self.session)



class LocationTests(GardenTestCase):

    def __init__(self, *args):
        super(LocationTests, self).__init__(*args)

    def setUp(self):
        super(LocationTests, self).setUp()


    def tearDown(self):
        super(LocationTests, self).tearDown()


    def test_location_editor(self):
        loc = self.create(Location, name=u'some site', code=u'STE')
        self.session.commit()
        editor = LocationEditor(model=loc)
        update_gui()
        widgets = editor.presenter.view.widgets

        # test that the accept buttons are NOT sensitive since nothing
        # has changed and that the and the text entries and model are
        # the same
        assert widgets.loc_name_entry.get_text() == loc.name
        assert widgets.loc_code_entry.get_text() == loc.code
        assert not widgets.loc_ok_button.props.sensitive
        assert not widgets.loc_ok_and_add_button.props.sensitive
        assert not widgets.loc_next_button.props.sensitive

        # test the accept buttons become sensitive when the name entry
        # is changed
        widgets.loc_name_entry.set_text('')
        update_gui()
        assert widgets.loc_ok_button.props.sensitive
        assert widgets.loc_ok_and_add_button.props.sensitive
        assert widgets.loc_next_button.props.sensitive

        # test the accept buttons become NOT sensitive when the code
        # entry is empty since this is a required field
        widgets.loc_code_entry.set_text('')
        update_gui()
        assert not widgets.loc_ok_button.props.sensitive
        assert not widgets.loc_ok_and_add_button.props.sensitive
        assert not widgets.loc_next_button.props.sensitive

        # test the accept buttons aren't sensitive from setting the textview
        import gtk
        buff = gtk.TextBuffer()
        buff.set_text('saasodmadomad')
        widgets.loc_desc_textview.set_buffer(buff)
        assert not widgets.loc_ok_button.props.sensitive
        assert not widgets.loc_ok_and_add_button.props.sensitive
        assert not widgets.loc_next_button.props.sensitive

        # commit the changes and cleanup
        editor.model.name = editor.model.code = u'asda'
        editor.handle_response(gtk.RESPONSE_OK)
        editor.session.close()
        editor.presenter.cleanup()
        del editor

        assert utils.gc_objects_by_type('LocationEditor') == [], \
            'LocationEditor not deleted'
        assert utils.gc_objects_by_type('LocationEditorPresenter') == [], \
            'LocationEditorPresenter not deleted'
        assert utils.gc_objects_by_type('LocationEditorView') == [], \
            'LocationEditorView not deleted'


    def itest_editor(self):
        """
        Interactively test the PlantStatusEditor
        """
        loc = self.create(Location, name=u'some site', code=u'STE')
        editor = LocationEditor(model=loc)
        editor.start()
        del editor
        assert utils.gc_objects_by_type('LocationEditor') == [], \
            'LocationEditor not deleted'
        assert utils.gc_objects_by_type('LocationEditorPresenter') == [], \
            'LocationEditorPresenter not deleted'
        assert utils.gc_objects_by_type('LocationEditorView') == [], \
            'LocationEditorView not deleted'



# class CollectionTests(GardenTestCase):

#     def __init__(self, *args):
#         super(CollectionTests, self).__init__(*args)

#     def setUp(self):
#         super(CollectionTests, self).setUp()

#     def tearDown(self):
#         super(CollectionTests, self).tearDown()

#     def test_accession_prop(self):
#         """
#         Test Collection.accession property
#         """
#         acc = Accession(code=u'1', species=self.species)
#         collection = Collection(locale=u'some locale')
#         self.session.add_all((acc, collection))

#         self.assert_(acc.source is None)
#         collection.accession = acc
#         self.assert_(acc._collection == collection, acc._collection)
#         self.assert_(acc.source_type == 'Collection')
#         self.assert_(acc.source == collection)
#         self.session.commit()


class InstitutionTests(GardenTestCase):

    # TODO: create a non interactive tests that starts the
    # InstututionEditor and checks that it doesn't leak memory

    def itest_editor(self):
        e = InstitutionEditor()
        e.start()


# latitude: deg[0-90], min[0-59], sec[0-59]
# longitude: deg[0-180], min[0-59], sec[0-59]

ALLOWED_DECIMAL_ERROR = 5
THRESHOLD = .01
DMS = 0 # DMS
DEG_MIN_DEC = 1 # Deg with minutes decimal
DEG_DEC = 2 # Degrees decimal
UTM = 3 # Datum(wgs84/nad83 or nad27), UTM Zone, Easting, Northing

# decimal points to accuracy in decimal degrees
# 1 +/- 8000m
# 2 +/- 800m
# 3 +/- 80m
# 4 +/- 8m
# 5 +/- 0.8m
# 6 +/- 0.08m

from decimal import Decimal
dec = Decimal
conversion_test_data = (
                        ((('N', 17, 21, dec(59)), # dms
                          ('W', 89, 1, 41)),
                         ((dec(17), dec('21.98333333')), # deg min_dec
                          (dec(-89), dec('1.68333333'))),
                         (dec('17.366389'), dec('-89.028056')), # dec deg
                         (('wgs84', 16, 284513, 1921226))), # utm
                        ((('S', 50, 19, dec('32.59')), # dms
                          ('W', 74, 2, dec('11.6'))),
                         ((dec(-50), dec('19.543166')), # deg min_dec
                          (dec(-74), dec('2.193333'))),
                         (dec('-50.325719'), dec('-74.036556')), # dec deg
                          (('wgs84', 18, 568579, 568579)),
                          (('nad27', 18, 568581, 4424928))),
                        ((('N', 9, 0, dec('4.593384')),
                          ('W', 78, 3, dec('28.527984'))),
                         ((9, dec('0.0765564')),
                          (-78, dec('3.4754664'))),
                         (dec('9.00127594'), dec('-78.05792444')))
                        )

#parse_lat_lon_data = ('17, 21, 59', '17 21 59', '17:21:59',
#                      '17, 21.98333333', '17 21.98333333',
#                      '17.36638889',
#                      '50, 19, 32.59', '50 19 32.59', '50:19:32.59',
#                      '-50 19.543166', '-50, 19.543166',
#                      '-50.325719')
parse_lat_lon_data = ('17 21 59', '17 21.98333333', '17.03656',
                      '50 19 32.59', '-50 19.543166', '-50.32572')


class DMSConversionTests(unittest.TestCase):

    # test coordinate conversions
    def test_dms_to_decimal(self):
        # test converting DMS to degrees decimal
        ALLOWED_ERROR = 6
        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]
            lat_dec = dms_to_decimal(*dms_data[0])
            lon_dec = dms_to_decimal(*dms_data[1])
            self.assertAlmostEqual(lat_dec, dec_data[0], ALLOWED_ERROR)
            self.assertAlmostEqual(lon_dec, dec_data[1], ALLOWED_ERROR)



    def test_decimal_to_dms(self):
        # test converting degrees decimal to dms, allow a certain
        # amount of error in the seconds
        ALLOWABLE_ERROR = 2
        for data_set in conversion_test_data:
            dms_data = data_set[DMS]
            dec_data = data_set[DEG_DEC]

            # convert to DMS
            lat_dms = latitude_to_dms(dec_data[0])
            self.assertEqual(lat_dms[0:2], dms_data[0][0:2])
            # test seconds with allowable error
            self.assertAlmostEqual(lat_dms[3], dms_data[0][3], ALLOWABLE_ERROR)

            lon_dms = longitude_to_dms(dec_data[1])
            self.assertEqual(lon_dms[0:2], dms_data[1][0:2])
            # test seconds with allowable error
            self.assertAlmostEqual(lon_dms[3], dms_data[1][3], ALLOWABLE_ERROR)


    def test_parse_lat_lon(self):
        for data in parse_lat_lon_data:
            pass



