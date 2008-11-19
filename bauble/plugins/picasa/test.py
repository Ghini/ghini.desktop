from nose import *

import bauble.meta as meta
import bauble.plugins.picasa as picasa
from bauble.test import BaubleTestCase
import bauble.utils as utils
from bauble.utils.log import debug


class PicasaTests(BaubleTestCase):

    def __init__(self, *args):
        super(PicasaTests, self).__init__(*args)


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
        Test the picasa.update_meta function
        """
        picasa.update_meta(u'email', u'album', u'token')


    def get_photos(self):
	email = u''
	password = ''
	album = u'Plants'
	token = picasa.get_auth_token(email, password) 
	picasa.update_meta(email, album, utils.utf8(token))
	import gdata.photos.service
	gd_client = gdata.photos.service.PhotosService()
	gd_client.SetClientLoginToken(token)
	feed = picasa.get_photo_feed(gd_client, "Maxillaria elatior")	
	import urllib2, urllib	
	import os
	for entry in feed.entry:
	    src = entry.content.src
	    debug(src)
	    filename, headers = urllib.urlretrieve(src)
	    debug(filename)
	    debug(os.path.exists(filename))	    
	    #debug(headers)


    def itest_get_photo_feed(self):
	"""
        Test the PicasaSettingsDialog
        """
	#raise SkipTest
	email = u''
	password = ''
	album = u''
	token = picasa.get_auth_token(email, password) 
	picasa.update_meta(email, album, utils.utf8(token))
	import gdata.photos.service
	gd_client = gdata.photos.service.PhotosService()
	gd_client.SetClientLoginToken(token)
	feed = picasa.get_photo_feed(gd_client, "Maxillaria elatior")
	for entry in feed.entry:
	    debug(entry.title.text)


    def itest_picasa_settings_dialog(self):
        """
        Test the PicasaSettingsDialog
        """
        email_meta = meta.get_default(picasa.PICASA_EMAIL_KEY, u'email')
        album_meta = meta.get_default(picasa.PICASA_ALBUM_KEY, u'album')
        token_meta = meta.get_default(picasa.PICASA_TOKEN_KEY, u'token')
        self.session.add_all([email_meta, album_meta, token_meta])
        self.session.commit()

        d = picasa.PicasaSettingsDialog()
        d.run()


