import unittest

import gtk
from nose import SkipTest
from sqlalchemy import *
from sqlalchemy.exc import *
from sqlalchemy.orm import *

from bauble.error import CheckConditionError, check
from bauble.test import BaubleTestCase, update_gui
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.plugins.garden.accession import Accession, AccessionEditor, \
    dms_to_decimal, decimal_to_dms, longitude_to_dms, latitude_to_dms, \
    Verification, Voucher
from bauble.plugins.garden.donor import Donor, DonorEditor
from bauble.plugins.garden.source import Donation, Collection
from bauble.plugins.garden.plant import Plant, PlantEditor, AddPlantEditor
from bauble.plugins.garden.location import Location, LocationEditor
from bauble.plugins.garden.propagation import Propagation, PropagationEditor, \
    PropCutting, PropRooted, PropSeed
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species
import bauble.plugins.plants.test as plants_test
from bauble.plugins.garden.institution import Institution, InstitutionEditor
import bauble.prefs as prefs


from datetime import datetime
accession_test_data = ({'id':1 , 'code': u'1.1', 'species_id': 1,
                        'date': datetime.today(),
                        'source_type': u'Donation'},
                       {'id':2 , 'code': u'2.2', 'species_id': 2,
                        'source_type': u'Collection'},
                       )

plant_test_data = ({'id':1 , 'code': u'1', 'accession_id': 1,
                    'location_id': 1},
                   )

location_test_data = ({'id': 1, 'name': u'Somewhere Over The Rainbow',
                       'code': u'RBW'},
                      )

donor_test_data = ({'id': 1, 'name': u'SomeDonor'},
                   )

donation_test_data = ({'id': 1, 'accession_id': 1, 'donor_id': 1},
                      )

collection_test_data = ({'id': 1, 'accession_id': 2, 'locale': u'Somewhere'},
                        )

test_data_table_control = ((Accession, accession_test_data),
                           (Location, location_test_data),
                           (Plant, plant_test_data),
                           (Donor, donor_test_data),
                           (Donation, donation_test_data),
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



class DonorTests(GardenTestCase):

    def __init__(self, *args):
        super(DonorTests, self).__init__(*args)


    def test_delete(self):
        acc = self.create(Accession, species=self.species, code=u'1')
        donor = Donor(name=u'name')
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        self.session.commit()
        self.session.close()

        # test that we can't delete a donor if it has corresponding donations
        import bauble
        session = bauble.Session()
        donor = session.query(Donor).filter_by(name=u'name').one()
        # shouldn't be allowed to delete donor if it has donations,
        # what is happening here is that when deleting the donor the
        # corresponding donations.donor_id's are being be set to null which
        # isn't allowed by the scheme....is this the best we can do? or can we
        # get some sort of error when creating a dangling reference
        session.delete(donor)
        self.assertRaises(SQLError, session.commit)


    def itest_donor_editor(self):
        """
        Interactively test the PlantEditor
        """
        loc = self.create(Donor, name=u'some donor')
        editor = DonorEditor(model=loc)
        editor.start()
        del editor
        assert utils.gc_objects_by_type('DonorEditor') == [], \
            'DonorEditor not deleted'
        assert utils.gc_objects_by_type('DonorEditorPresenter') == [], \
            'DonorEditorPresenter not deleted'
        assert utils.gc_objects_by_type('DonorEditorView') == [], \
            'DonorEditorView not deleted'



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
        editor = PlantEditor(model=[p1, p2])
        update_gui()

        widgets = editor.presenter.view.widgets
        utils.set_widget_value(widgets.plant_action_combo, u'Transfer')
        widgets.trans_to_comboentry.child.props.text = self.location.name
        update_gui()

        editor.handle_response(gtk.RESPONSE_OK)
        for p in editor.plants:
            # TODO: need to assert that the values of
            # editor.presenter._transfer are equal to the transfer in
            # the plant
            self.assert_(len(p.transfers) > 0)



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
        editor = PlantEditor(model=[p1, p2])
        update_gui()

        widgets = editor.presenter.view.widgets
        utils.set_widget_value(widgets.plant_action_combo, u'Removal')
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
            self.assert_(len(p.removal) > 0)


    def test_editor_addnote(self):
        return
        raise NoteImplementedError


    def itest_editor(self):
        p1 = Plant(accession=self.accession, location=self.location,
                   code=u'52')
        p2 = Plant(accession=self.accession, location=self.location,
                   code=u'53')
        self.accession.plants.append(p1)
        self.accession.plants.append(p2)
        plants = [p1, p2]
        self.session.add_all(plants)
        e = PlantEditor(plants)
        e.start()


    def test_bulk_plant_editor(self):
        """
        Test creating multiple plants with the plant editor.
        """
        try:
            import gtk
        except ImportError:
            raise SkipTest('could not import gtk')
        editor = AddPlantEditor(model=self.plant)
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
        assert utils.gc_objects_by_type('AddPlantEditor') == [], \
            'AddPlantEditor not deleted'
        assert utils.gc_objects_by_type('AddPlantEditorPresenter') == [], \
            'AddPlantEditorPresenter not deleted'
        assert utils.gc_objects_by_type('AddPlantEditorView') == [], \
            'AddPlantEditorView not deleted'


    def itest_add_plant_editor(self):
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
        self.session.add_all([loc, loc2])
        self.session.commit()
        p = Plant(accession=self.accession, location=loc)
        editor = AddPlantEditor(model=p)
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
        # these default values have to be initialize in setUp() so
        # that utils.today_str() will work
        self.default_cutting_values = \
            {'cutting_type': u'Nodal',
             'length': 2,
             'tip': u'Intact',
             'leaves': u'Intact',
             'leaves_reduced_pct': 25,
             'flower_buds': u'None',
             'wound': u'Single',
             'fungal_soak': u'Physan',
             'hormone': u'Auxin powder',
             'cover': u'Poly cover',
             'location': u'Mist frame',
             'bottom_heat_temp': 65,
             'bottom_heat_unit': u'F',
             'rooted_pct': 90}
        self.default_seed_values = \
            {'pretreatment': u'Soaked in peroxide solution',
             'nseeds': 24,
             'date_sown': utils.today_str(),
             'container': u"tray",
             'compost': u'standard seed compost',
             'location': u'mist tent',
             'moved_from': u'mist tent',
             'moved_to': u'hardening table',
             'germ_date': utils.today_str(),
             'germ_pct': 99,
             'nseedling': 23,
             'date_planted': utils.today_str()}
        self.accession = self.create(Accession, species=self.species,code=u'1')
        self.session.commit()


    def tearDown(self):
        super(PropagationTests, self).tearDown()

    def get_default_cutting(self):
        cutting = PropCutting()
        for attr, value in self.default_cutting_values.iteritems():
            setattr(cutting, attr, value)
        return cutting

    def get_default_seed(self):
        seed = PropSeed()
        for attr, value in self.default_seed_values.iteritems():
            setattr(seed, attr, value)
        return seed


    def test_cutting_property(self):
        prop = Propagation()
        prop.prop_type = u'UnrootedCutting'
        prop.accession = self.accession
        cutting = self.get_default_cutting()
        cutting.propagation = prop
        rooted = PropRooted()
        rooted.cutting = cutting
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
        prop = Propagation()
        prop.prop_type = u'Seed'
        prop.accession = self.accession
        seed = self.get_default_seed()
        seed.propagation = prop
        self.session.commit()

        self.assert_(seed == prop._seed)
        seed_id = seed.id

        # this should cause the cutting and its rooted children to be deleted
        prop._seed = None
        self.session.commit()
        self.assert_(not self.session.query(PropSeed).get(seed_id))


    def test_cutting_editor(self):
        propagation = Propagation()
        propagation.accession = self.accession
        editor = PropagationEditor(model=propagation)
        widgets = editor.presenter.view.widgets
        view = editor.presenter.view
        view.set_widget_value('prop_type_combo', u'UnrootedCutting')
        view.set_widget_value('prop_date_entry', utils.today_str())
        cutting_presenter = editor.presenter._cutting_presenter
        for widget, attr in cutting_presenter.widget_to_field_map.iteritems():
            view.set_widget_value(widget, self.default_cutting_values[attr])
        update_gui()
        editor.handle_response(gtk.RESPONSE_OK)
        editor.presenter.cleanup()
        editor.commit_changes()
        model = editor.model
        s = object_session(model)
        s.expire(model)
        self.assert_(model.prop_type == u'UnrootedCutting')
        for attr, value in self.default_cutting_values.iteritems():
            v = getattr(model._cutting, attr)
            self.assert_(v==value, '%s = %s(%s)' % (attr, value, v))
        editor.session.close()


    def test_seed_editor(self):
        propagation = Propagation()
        propagation.accession = self.accession
        editor = PropagationEditor(model=propagation)
        widgets = editor.presenter.view.widgets
        view = editor.presenter.view
        view.set_widget_value('prop_type_combo', u'Seed')
        view.set_widget_value('prop_date_entry', utils.today_str())
        cutting_presenter = editor.presenter._seed_presenter
        for widget, attr in cutting_presenter.widget_to_field_map.iteritems():
            w = widgets[widget]
            if isinstance(w, gtk.ComboBoxEntry) and not w.get_model():
                widgets[widget].child.props.text = \
                    self.default_seed_values[attr]
            view.set_widget_value(widget, self.default_seed_values[attr])
        update_gui()
        editor.handle_response(gtk.RESPONSE_OK)
        editor.presenter.cleanup()
        model = editor.model
        s = object_session(model)
        editor.commit_changes()
        s.expire(model)
        self.assert_(model.prop_type == u'Seed')
        from datetime import date
        for attr, value in self.default_seed_values.iteritems():
            v = getattr(model._seed, attr)
            if isinstance(v, date):
                format = prefs.prefs[prefs.date_format_pref]
                v = v.strftime(format)
            self.assert_(v==value, '%s = %s(%s)' % (attr, value, v))
        editor.session.close()



    def itest_editor(self):
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
        s = 'gen sp cf. None'
        sp_str = acc.species_str()
        self.assert_(s == sp_str, '%s == %s' %(s, sp_str))

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

        acc.species.infrasp_rank = u'cv.'
        acc.species.infrasp = u'Cultivar'
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


    def test_source(self):
        #acc = self.session.query(Accession).get(1)
        #donor = self.session.query(Donor).get(1)
        acc = Accession(code=u'1', species=self.species)
        donor = Donor(name=u'me')
        self.session.add_all([acc, donor])
        self.session.commit()

        # set source on accession as a Donation
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        self.session.commit()
        #self.session.expire(acc)
        self.session.refresh(acc)
        self.assertEquals(acc.source.id, donation.id)
        self.assertEquals(acc.source_type, u'Donation')

        # create a new Donation and set that as the source, this should
        # delete the old donation object since it's an orphan,
        old_donation_id = donation.id
        donation2 = Donation()
        donation2.donor = donor
        acc.source = donation2
        self.session.commit()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, donation2.id)
        self.assertEquals(acc.source_type, u'Donation')

        # set the same source twice to make sure the source isn't
        # deleted before setting it again
        acc.source = donation2
        self.session.commit()
        self.assert_(acc.source)

        # delete all the donations
        # TODO: ** important ** the donor
        # should never be deleted if a donation is deleted and a
        # donation should never get deleted if a donor is deleted, an
        # error should be reaised if you attempt to delete a donor
        # that has donations but should an error be raised if you
        # attempt to delete a donation that has a donor, i don't think
        # so

        # make sure the old donation gets deleted since it's an orphan
        print self.session.query(Donation).get(old_donation_id)
        self.assert_(self.session.query(Donation).get(old_donation_id) == None)

        # delete the source by setting acc.source=None
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        acc.source = None
        self.session.commit()
        self.session.expire(acc)
        old_donation_id = donation2.id
        self.assertEquals(acc.source, None)
        self.assertEquals(acc.source_type, None)

        # delete the source 2
        donation = Donation()
        donation.donor = donor
        acc.source = donation
        del acc.source
        self.session.commit()
        self.session.expire(acc)
        old_donation_id = donation2.id
        self.assertEquals(acc.source, None)
        self.assertEquals(acc.source_type, None)

        # make sure the orphaned donation get's deleted
        self.assert_(not self.session.query(Donation).get(old_donation_id))

        # set accession.source to a Collection
        collection = Collection(locale=u'TestAccLocale')
        acc.source = collection
        self.session.commit()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, collection.id)
        self.assertEquals(acc.source_type, u'Collection')

        # changed source from collection to donation
        old_collection_id = collection.id
        donation3 = Donation()
        donation3.donor = donor
        acc.source = donation3
        self.session.commit()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, donation3.id)
        self.assertEquals(acc.source_type, u'Donation')

        # make sure the orphaned collection get's deleted
        self.assert_(not self.session.query(Collection).get(old_collection_id))

        # change source from donation to collection
        old_donation_id = donation3.id
        collection2 = Collection(locale=u'TestAccLocale2')
        acc.source = collection2
        self.session.commit()
        self.session.expire(acc)
        self.assertEquals(acc.source.id, collection2.id)
        self.assertEquals(acc.source_type, u'Collection')

        # change source without flushing
        donation4 = Donation()
        acc.source = donation4
        collection3 = Collection(locale=u'TestAccLocale3')
        acc.source = collection3
        self.session.commit()
#        utils.log.echo(False)

        # make sure the orphaned donation get's deleted
        self.assert_(not self.session.query(Donation).get(old_donation_id))

        # make sure the collection gets deleted when accession does
        collection4 = Collection(locale=u'TestAccLocale4')
        acc.source = collection4
        self.session.commit()
        cid = collection4.id
        self.session.delete(acc)
        self.session.commit()
        self.assert_(not self.session.query(Collection).get(cid))

        # make sure the collection gets deleted when accession does
        acc = Accession(code=u'1', species=self.species)
        donor = Donor(name=u'donor5')
        self.session.add_all([acc, donor])
        self.session.commit()
        donation5 = Donation(donor=donor)
        acc.source = donation5
        self.session.commit()
        did = donation5.id
        self.session.delete(acc)
        self.session.commit()
        self.assert_(not self.session.query(Donation).get(did))


    def test_double_commit(self):
        """
        This tests a bug with SQLAlchemy that was tentatively fixed
        after SQ 0.4.4 was released in r4264.  There is a reference to
        this in the SA mailing list.

        The bug is here just to check if this ever gets fixed.
        """
        import bauble.utils.log as log
        sp = self.session.query(Species).get(1)
        acc = Accession()
        self.session.add(acc)
        acc.species = sp
        acc.code = u"3"
        # not donor_id, should raise an IntegrityError
        donation = Donation()
        acc.source = donation
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            # before SA 0.4.5 this would give and InvalidRequestError
            # about not being able to refresh Accession after a rollback
            try:
                self.session.commit()
            except InvalidRequestError, e:
                # we get here in SA pre-0.4.5, we can't use those
                # versions for bauble
                raise
            except IntegrityError:
                # it should raise an integrity error because there is
                # still no donor_id on donation
                pass


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
        Interactively test the PlantEditor
        """
        donor = self.create(Donor, name=u'test')
        sp2 = Species(genus=self.genus, sp=u'species')
        sp2.synonyms.append(self.species)
        self.session.add(sp2)
        self.session.commit()
        acc = self.create(Accession, species=self.species, code=u'1')
        voucher = Voucher(herbarium=u'abcd', code=u'123')
        acc.vouchers.append(voucher)
        prev = 0
        def mem(size="rss"):
            """Generalization; memory sizes: rss, rsz, vsz."""
            import os
            return int(os.popen('ps -p %d -o %s | tail -1' % \
                                    (os.getpid(), size)).read())

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
            editor = AccessionEditor(model=acc)
            editor.start()
            del editor
            leak = mem()
            debug('%s: %s' % (leak, leak-prev))
            prev = leak
            #debug(mem())

        debug(utils.gc_objects_by_type('XML'))

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
        verification =  Verification()


class LocationTests(GardenTestCase):

    def __init__(self, *args):
        super(LocationTests, self).__init__(*args)

    def setUp(self):
        super(LocationTests, self).setUp()


    def tearDown(self):
        super(LocationTests, self).tearDown()


    def test_location_editor(self):
        #loc = self.create(Location, name=u'some site')
        loc = Location(name=u'some site', code=u'STE')
        editor = LocationEditor(model=loc)
        #editor.presenter.view.dialog.hide_all()
        update_gui()
        widgets = editor.presenter.view.widgets

        # test that the accept buttons are sensitive the text in the
        # entry and the model.site are the same...and that the accept
        # buttons are sensitive
        assert widgets.loc_name_entry.get_text() == loc.name
        assert widgets.loc_ok_button.props.sensitive
        assert widgets.loc_ok_and_add_button.props.sensitive
        assert widgets.loc_next_button.props.sensitive

        # test the accept buttons aren't sensitive when the location
        # entry is empty
        widgets.loc_name_entry.set_text('')
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
        editor.model.name = u'asda'
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


    def itest_location_editor(self):
        """
        Interactively test the PlantEditor
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



class DonationTests(GardenTestCase):

    def __init__(self, *args):
        super(DonationTests, self).__init__(*args)

    def setUp(self):
        super(DonationTests, self).setUp()

    def tearDown(self):
        super(DonationTests, self).tearDown()

    def test_accession_prop(self):
        """
        Test Donation.accession property
        """
        acc = Accession(code=u'1', species=self.species)
        donor = Donor(name=u'donor name')
        donation = Donation(donor=donor)
        self.session.add_all((acc, donation, donor))

        self.assert_(acc.source is None)
        donation.accession = acc
        self.assert_(acc._donation == donation, acc._donation)
        self.assert_(acc.source_type == 'Donation')
        self.assert_(acc.source == donation)
        self.session.commit()


class CollectionTests(GardenTestCase):

    def __init__(self, *args):
        super(CollectionTests, self).__init__(*args)

    def setUp(self):
        super(CollectionTests, self).setUp()

    def tearDown(self):
        super(CollectionTests, self).tearDown()

    def test_accession_prop(self):
        """
        Test Collection.accession property
        """
        acc = Accession(code=u'1', species=self.species)
        collection = Collection(locale=u'some locale')
        self.session.add_all((acc, collection))

        self.assert_(acc.source is None)
        collection.accession = acc
        self.assert_(acc._collection == collection, acc._collection)
        self.assert_(acc.source_type == 'Collection')
        self.assert_(acc.source == collection)
        self.session.commit()


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



