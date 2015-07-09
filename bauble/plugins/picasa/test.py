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
from nose import SkipTest

import gtk

import bauble.meta as meta
import bauble.plugins.picasa as picasa
from bauble.test import BaubleTestCase, check_dupids
import bauble.utils as utils


def test_duplicate_ids():
    """
    Test for duplicate ids for all .glade files in the picasa plugin.
    """
    import bauble.plugins.picasa as mod
    import glob
    head, tail = os.path.split(mod.__file__)
    files = glob.glob(os.path.join(head, '*.glade'))
    for f in files:
        assert(not check_dupids(f))


class PicasaTests(BaubleTestCase):

    def __init__(self, *args):
        super(PicasaTests, self).__init__(*args)

    def test_photo_cache(self):
        """
        Test bauble.plugins.picasa.PhotoCache
        """
        import tempfile
        fd, filename = tempfile.mkstemp()
        cache = picasa.PhotoCache(path=filename, create=True)
        photoid = u'testid'
        cache.add(photoid, u'testpath')
        self.assert_(cache[photoid].id == photoid)

        cache.remove(photoid)
        self.assert_(not cache[photoid])

#     def test_populate_iconview(self):
#         import gdata.photos.service
#         user = u''
#         passwd = u''
#         token = picasa.get_auth_token(user, passwd)
#         picasa.update_meta(user, u'Plants', token)
#         gd_client = gdata.photos.service.PhotosService()
#         gd_client.SetClientLoginToken(token)
#         picasa.populate_iconview(gd_client, iconview=None,
#                                  tag='Maxillaria elatior')

    def test_get_auth_token(self):
        """
        Test retrieving auth token from Google
        """

        raise SkipTest("test requires a valid authentication on picasa")
        user = ''
        passwd = ''
        token = picasa.get_auth_token(user, passwd)
        self.assert_(token)

    def test_update_meta(self):
        """
        Test bauble.plugins.picasa.update_meta() function.
        """

        email = u'email'
        album = u'album'
        token = u'token'
        picasa.update_meta(email=u'email', album=u'album', token=u'token')
        self.assert_(email == meta.get_default(picasa.PICASA_EMAIL_KEY).value)
        self.assert_(album == meta.get_default(picasa.PICASA_ALBUM_KEY).value)
        self.assert_(token == meta.get_default(picasa.PICASA_TOKEN_KEY).value)

        album2 = u'album2'
        picasa.update_meta(album=album2)
        self.assert_(album2 == meta.get_default(picasa.PICASA_ALBUM_KEY).value)

    def _get_settings(self):
        """
        Get the Picasa connection settings
        """
        d = picasa.PicasaSettingsDialog()
        return d.run()

    def test_infopage(self):
        raise SkipTest('Not Implemented')
        from bauble.plugins.plants import Family, Genus, Species
        email = ''
        passwd = ''
        album = 'Plants'
        if email:
            token = picasa.get_auth_token(email, passwd)
            picasa.update_meta(email=email, album=album, token=token)
        f = Family(family=u'Orchidaceae')
        g = Genus(family=f, genus=u'Maxillaria')
        sp = Species(genus=g, sp=u'elatior')
        self.session.add_all([f, g, sp])
        self.session.commit()
        self.dialog = gtk.Dialog()
        self.dialog.set_size_request(250, 700)
        page = picasa.PicasaInfoPage()
        page.update(sp)
        self.dialog.vbox.pack_start(page)
        self.dialog.show_all()
        self.dialog.run()

    def test_get_photo_feed(self):
        """
        Interactively test picasa.get_photo_feed()
        """
        raise SkipTest('Not Implemented')
        if self._get_settings() != gtk.RESPONSE_OK:
            return

        email = meta.get_default(picasa.PICASA_EMAIL_KEY).value
        album = meta.get_default(picasa.PICASA_ALBUM_KEY).value
        token = meta.get_default(picasa.PICASA_TOKEN_KEY).value
        picasa.update_meta(email, album, utils.utf8(token))
        import gdata.photos.service
        gd_client = gdata.photos.service.PhotosService()
        gd_client.SetClientLoginToken(token)

        # this tag is specific to the Plant album on brettatoms account
        tag = 'Maxillaria variabilis'
        feed = picasa.get_photo_feed(gd_client, email, album, tag)
        self.assert_(len(feed.entry) > 0)
