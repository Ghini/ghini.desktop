#
# picasa plugin
#

# 1. should be able to upload photos, have to use picasa to delete and
# do other photo manipulation
#
# 2. show thumbnails in the infobox
#
# 3. on import should autotag with the plant name
#
# 4. create a tool for changing the username and album
#
# 5. store the auth token in bauble meta
#
# 6. What about accessing google through a proxy
#
# 7. Need to create an image cache that stores image in
# ~/.bauble/picasa so that if a file hasn't changed since we last
# downloaded it we don't have to download it again...should also be
# able to set a max cache size so that we delete the oldest files if
# we go over the cache size
#
# 8. By default we should only get the files of a certain size that can be viewed in Bauble but should allow the option to download the original file
#
# 9. Should provide a Save As button so the user can save a copy of
# the file for later use

import os
import urllib2
import urllib

import gdata.photos.service
import gdata.media
import gdata.geo
import gtk

import bauble
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
import bauble.view as view
from bauble.i18n import _
from bauble.utils.log import debug
import bauble.meta as meta
from bauble.plugins.plants import Species


PICASA_TOKEN_KEY = u'picasa_token'

# TODO: should we store the email and album in the BaubleMeta...these
# should only be changeable by an administrator...should probably only
# allow an administrator to even access the PicasaTool
PICASA_EMAIL_KEY = u'picasa_email'
PICASA_ALBUM_KEY = u'picasa_album'

# see http://code.google.com/apis/picasaweb/reference.html#Parameters
#picasa_imgmax = '1600'#d'
picasa_imgmax = 'd'
picasa_thumbsize = '144u'

def update_meta(email=None, album=None, token=None):
    """
    Update the email, album and authorization token in the bauble meta table.
    """
    session = bauble.Session()
    email_meta = meta.get_default(PICASA_EMAIL_KEY, email, session)
    album_meta = meta.get_default(PICASA_ALBUM_KEY, album, session)
    token_meta = meta.get_default(PICASA_TOKEN_KEY, token, session)
    session.add_all([email_meta, album_meta, token_meta])
    session.commit()
    session.close()



def get_auth_token(email, password):
    """
    Update the Picasa Auth Token using the Google Data ClientClient uri
    """
    gd_client = gdata.photos.service.PhotosService()
    gd_client.ClientLogin(username=email, password=password)
    token = gd_client.GetClientLoginToken()
    #debug(token)
    return token



def get_photo_feed(gd_client, tag):
    """
    Get a photo feed with the username and album stored in bauble meta
    table and with has tag.
    """
    email = meta.get_default(PICASA_EMAIL_KEY).value
    user, domain = email.split('@', 1)
    album = meta.get_default(PICASA_ALBUM_KEY).value
    feed = '/data/feed/api/user/%s' % user
    if album:
        feed += '/album/%s' % urllib.quote(album)
    if tag:
        feed += '?kind=photo&tag=%s' % urllib.quote(tag)
    else:
        feed += '?kind=photo'
    feed += '&thumbsize=%s&imgmax=%s' % (picasa_thumbsize, picasa_imgmax)
    #feed += '&thumbsize=%s' % picasa_thumbsize
    debug(feed)
    return gd_client.GetFeed(str(feed))



def get_photos(gd_client, tag):
    """
    Return a list of filenames for the saved photos
    """
    # TODO: should probably break this method up so that we can get
    # the photos one at a time instead of blocking to wait for all the
    # photos to load
    feed = get_photo_feed(gd_client, tag)
    names = []
    for entry in feed.entry:
	filename, headers = urllib.urlretrieve(entry.content.src)
	names.append(filename)
    return names



def upload(image, species):
    """
    Upload an image to the Picasa Web Album

    :param image: the image data
    :param species: the species name
    """
    tag = Species.str(species, markup=False, authors=False)
    session = bauble.Session()
    #token = self.session.query(meta.BaubleMeta.value).\
    #    filter_by(name=picasa.PICASA_TOKEN_KEY).one()[0]
    token = meta.get_default(PICASA_TOKEN_KEY)
    gd_client = gdata.photos.service.PhotosService()
    #gd_client.service = 'lh2'
    gd_client.SetClientLoginToken(token)
    #gd_client.auth_token = token
    album_url = '/data/feed/api/user/%s/album/%s' % (username,
                                                     album.gphoto_id.text)
    photo = gd_client.InsertPhoto(album_url, new_entry, filename,
				  content_type='image/jpeg')


class PicasaSettingsDialog(object):
    """
    A dialog to handle the Picasa settings
    """

    def __init__(self):
        widget_path = os.path.join(paths.lib_dir(), 'plugins', 'picasa',
                                   'gui.glade')
        self.widgets = utils.GladeWidgets(widget_path)
        self.window = self.widgets.settings_dialog
        if bauble.gui:
            self.window.set_transient_for(bauble.gui.window)

        self.widgets.password_entry.connect('changed', self.on_changed)

        email = meta.get_default(PICASA_EMAIL_KEY).value
        self.widgets.email_entry.set_text(email or '')

        album = meta.get_default(PICASA_ALBUM_KEY).value
        self.widgets.album_entry.set_text(album or '')

        auth = meta.get_default(PICASA_TOKEN_KEY).value
        if auth:
            self.widgets.password_entry.set_text('blahblah')

        self._changed = False


    def on_changed(self, *args):
        self._changed = True


    def run(self):
        """
        """
        response = self.window.run()
        self.window.hide()
        if response != gtk.RESPONSE_OK:
            return
        stored_email = meta.get_default(PICASA_EMAIL_KEY).value
        email = self.widgets.email_entry.get_text()
        album = self.widgets.album_entry.get_text()
        passwd = self.widgets.password_entry.get_text()

        if stored_email != email or self._changed:
            token = get_auth_token(email, passwd)
            if not token:
                utils.message_dialog(_('Could not authorize Google '\
                                       'account: %s' % email),
                                     gtk.MESSAGE_ERROR)
                return
            update_meta(utils.utf8(email), utils.utf8(album),
                        utils.utf8(token))
        else:
            update_meta(album=album)



class PicasaSettingsTool(pluginmgr.Tool):
    """
    Tool for changing the Picasa settings and updated the auth token
    """
    category = 'Picasa'
    label = 'Settings'

    @classmethod
    def start(cls):
        d = PicasaSettingsDialog()
        d.run()



class PicasaUploader(object):

    def __init__(self):
        pass

    def build_gui():
        self.assistant = gtk.Assistant()

        # page 1 - information
        label = gtk.Label('This tool will help you upload photos to your '\
                          'Picasa Web Albums')
        self.assistant.append_page()

        # page 2 - select the files
        vbox = gtk.VBox()
        label = gtk.Label('Please select the the images to upload.')

        # page 3 - tag the files and upload
        vbox = gtk.VBox()


    def start(self):
        build_gui()
        pass



class PicasaUploadTool(pluginmgr.Tool):
    """
    Tool for uploading images to the Picasa Web Albums
    """
    category = 'Picasa'
    label = 'Upload'

    @classmethod
    def start(cls):
        d = PicasaUploader()
        d.start()



class PicasaView(pluginmgr.View):

    def __init__(self):
        super(PicasaView, self).__init__()

    def do_something(self, arg):
        pass


# class PicasaCommandHandler(pluginmgr.CommandHandler):

#     command = ''

#     def get_view(self):
#         self.view = None
#         return self.view


#     def __call__(self, arg):
#         self.view.do_something(arg)



class PicasaInfoPage(view.InfoBoxPage):

    def __init__(self):
        super(PicasaInfoPage, self).__init__()
        self.label = _('Images')
        self._disabled = False
        self.gd_client = gdata.photos.service.PhotosService()
        self.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)
        self.icon_view = gtk.IconView()

        # TODO: we set the columns here because for some reason the
        # combination of paned windows, notebooks and scrollbars seems
        # to screw up the icon view automatic row/column handling so
        # that if you make the infobox larger then the images seem to
        # move between rows ok but if you make it smaller it doesn't
        self.icon_view.set_columns(1)
        self.icon_view.set_pixbuf_column(0)
        self.vbox.pack_start(self.icon_view)


    def update(self, row):
        """
        :param: a Species instance
        """
        # TODO: change the interface so the authentication data can be updated
        # if we can't connection
        token = meta.get_default(PICASA_TOKEN_KEY).value
        if not token:
            email = meta.get_default(PICASA_EMAIL_KEY).value
            utils.message_dialog(_('Could not login to Google account as '\
                                   'user %s' % email), gtk.MESSAGE_ERROR)
            return
	self.gd_client.SetClientLoginToken(token)
	tag = Species.str(row, markup=False, authors=False)
        import bauble.task as task
        task.queue(self._populate_iconview, None, None, tag)


    def _populate_iconview(self, tag):
        yield
        try:
            feed = get_photo_feed(self.gd_client, tag)
        except Exception, e:
            debug(e)
        yield
        model = gtk.ListStore(gtk.gdk.Pixbuf)
	for entry in feed.entry:
	    thumb_url = entry.media.thumbnail[0].url
	    thumbnail, headers = urllib.urlretrieve(thumb_url)
            image = gtk.gdk.pixbuf_new_from_file(thumbnail)
            model.append([image])
            yield
        self.icon_view.set_model(model)



class PicasaInfoExpander(view.InfoExpander):
    pass

class PicasaPlugin(pluginmgr.Plugin):
    tools = [PicasaUploadTool, PicasaSettingsTool]
    view = PicasaView
    #commands = [PicasaCommandHandler]

# uncomment the following line to enable this plugin
plugin = PicasaPlugin
