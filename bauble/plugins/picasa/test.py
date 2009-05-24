from nose import *

import gtk

import bauble.meta as meta
import bauble.plugins.picasa as picasa
from bauble.test import BaubleTestCase
import bauble.utils as utils
from bauble.utils.log import debug


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
        # TODO: will probably have to skip this test since requires a
        # password
        raise SkipTest
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
        self.assert_(email==meta.get_default(picasa.PICASA_EMAIL_KEY).value)
        self.assert_(album==meta.get_default(picasa.PICASA_ALBUM_KEY).value)
        self.assert_(token==meta.get_default(picasa.PICASA_TOKEN_KEY).value)

        album2 = u'album2'
        picasa.update_meta(album=album2)
        self.assert_(album2==meta.get_default(picasa.PICASA_ALBUM_KEY).value)


    def _get_settings(self):
        """
        Get the Picasa connection settings
        """
        d = picasa.PicasaSettingsDialog()
        return d.run()


    def itest_infopage(self):
        from bauble.plugins.plants import Family, Genus, Species
        email = ''
        passwd = ''
        album='Plants'
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



    def itest_get_photo_feed(self):
	"""
        Interactively test picasa.get_photo_feed()
        """
        if self._get_settings() != gtk.RESPONSE_OK:
            return

        email = meta.get_default(picasa.PICASA_EMAIL_KEY).value
        try:
            user, domain = email.split('@', 1)
        except Exception:
            user = email
        album = meta.get_default(picasa.PICASA_ALBUM_KEY).value
        token = meta.get_default(picasa.PICASA_TOKEN_KEY).value
	picasa.update_meta(email, album, utils.utf8(token))
	import gdata.photos.service
	gd_client = gdata.photos.service.PhotosService()
	gd_client.SetClientLoginToken(token)

        # this tag is specific to the Plant album on brettatoms account
        tag = 'Maxillaria elatior'
	feed = picasa.get_photo_feed(gd_client, user, album, tag)
        self.assert_(len(feed.entry) > 0)
