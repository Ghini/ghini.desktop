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
# ~/.bauble/images so that if a file hasn't changed since we last
# downloaded it we don't have to download it again...should also be
# able to set a max cache size so that we delete the oldest files if
# we go over the cache size
#
# 8. By default we should only get the files of a certain size that
# can be viewed in Bauble but should allow the option to download the
# original file
#
# 9. Should provide a Save As button so the user can save a copy of
# the file for later use

# IDEA: we could probably make this module more generic and based on
# mixins where we add the functionality for getting the photos by
# mixing in different implentations for different services


import os
import urllib2
import urllib
import tempfile

import gdata.photos.service
import gdata.media
import gdata.geo
import gtk
import sqlalchemy as sa
import sqlalchemy.orm as orm

import bauble
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
import bauble.view as view
from bauble.i18n import _
import bauble.meta as meta
from bauble.plugins.plants import Species
from bauble.utils.log import debug
import bauble.utils.thread as thread

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

default_path = os.path.join(paths.user_dir(), 'photos')

# keep a copy of the feeds that we retrieve by tag
__feed_cache = {}

def update_meta(email=None, album=None, token=None):
    """
    Update the email, album and authorization token in the bauble meta table.
    """
    session = bauble.Session()
    email_meta = meta.get_default(PICASA_EMAIL_KEY, email, session)
    album_meta = meta.get_default(PICASA_ALBUM_KEY, album, session)
    token_meta = meta.get_default(PICASA_TOKEN_KEY, token, session)
    __feed_cache.clear()
    session.add_all([email_meta, album_meta, token_meta])
    session.commit()
    session.close()



def get_auth_token(email, password):
    """
    Update the Picasa Auth Token using the Google Data ClientClient uri
    """
    gd_client = gdata.photos.service.PhotosService()
    gd_client.ClientLogin(username=email, password=password)
    __feed_cache.clear()
    return gd_client.GetClientLoginToken()



def get_photo_feed(gd_client, user=None, album=None, tag=None):
    """
    Get a photo feed with the username and album stored in bauble meta
    table and with has tag.
    """
    feed = '/data/feed/api/user/%s' % user
    if album:
        feed += '/album/%s' % urllib.quote(album)
    if tag:
        feed += '?kind=photo&tag=%s' % urllib.quote(tag)
    else:
        feed += '?kind=photo'
    feed += '&thumbsize=%s&imgmax=%s' % (picasa_thumbsize, picasa_imgmax)
    return gd_client.GetFeed(str(feed))



class PhotoCache(object):
    """
    The PhotoCache allows photos stored on the filesystem to be looked
    up by an id that is unique to the service the file was downloaded
    from.
    """
    def __init__(self, path=None, create=False):
        """
        :param path: the path to the sqlite database
        :param create: create the database if it doesn't exists
        """
        if not path:
            path = os.path.join(default_path, 'photos.db')
        uri = 'sqlite:///%s' % path
        self.engine = sa.create_engine(uri)
        self.engine.contextual_connect()
        self.metadata = Base.metadata
        self.metadata.bind = self.engine
        self.Session = orm.sessionmaker(bind=self.engine, autoflush=False)
        if create:
            self.metadata.drop_all(checkfirst=True)
            self.metadata.create_all()


    def exists(self, path=None):
        """
        Check if a PhotoCache database exists at path.  If path is
        None then the path defaults to $HOME/photos/photos.db
        """
        if not path:
            path = os.path.join(default_path, 'photos.db')
        return self.engine.has_table(Photo.__tablename__)


    def __getitem__(self, id):
        """
        Get photos from the database by tag
        """
        # select item from database and return a list of matching filenames
        session = self.Session()
        photo = session.query(Photo).filter_by(id=utils.utf8(id)).first()
        session.close()
        return photo


    def get(self, id):
        return self[id]


    def add(self, id, path):
        """
        Add photos to the cache
        """
        session = self.Session()
        photo = Photo(id=utils.utf8(id), path=utils.utf8(path))
        session.add(photo)
        session.commit()
        session.close()


    def remove(self, id):
        """
        Remove a photo entry from the cache.
        """
        session = self.Session()
        photo = self[utils.utf8(id)]
        session.delete(photo)
        session.commit()
        session.close()



from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class Photo(Base):
    """
    id: a unique id for the photos, created by using the name of the
    service and the unique photo id for the service,
    e.g. picasa:26734123

    path: the path of the photo on the filesystem
    """
    __tablename__ = 'photo'
    id = sa.Column(sa.Unicode(64), primary_key=True, nullable=False)
    path = sa.Column(sa.UnicodeText, nullable=False)



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
        return response



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


# def upload(image, species):
#     """
#     Upload an image to the Picasa Web Album

#     :param image: the image data
#     :param species: the species name
#     """
#     tag = Species.str(species, markup=False, authors=False)
#     session = bauble.Session()
#     #token = self.session.query(meta.BaubleMeta.value).\
#     #    filter_by(name=picasa.PICASA_TOKEN_KEY).one()[0]
#     token = meta.get_default(PICASA_TOKEN_KEY)
#     gd_client = gdata.photos.service.PhotosService()
#     #gd_client.service = 'lh2'
#     gd_client.SetClientLoginToken(token)
#     #gd_client.auth_token = token
#     album_url = '/data/feed/api/user/%s/album/%s' % (username,
#                                                      album.gphoto_id.text)
#     photo = gd_client.InsertPhoto(album_url, new_entry, filename,
# 				  content_type='image/jpeg')

# class PicasaUploader(object):

#     def __init__(self):
#         pass

#     def build_gui():
#         self.assistant = gtk.Assistant()

#         # page 1 - information
#         label = gtk.Label('This tool will help you upload photos to your '\
#                           'Picasa Web Albums')
#         self.assistant.append_page()

#         # page 2 - select the files
#         vbox = gtk.VBox()
#         label = gtk.Label('Please select the the images to upload.')

#         # page 3 - tag the files and upload
#         vbox = gtk.VBox()


#     def start(self):
#         build_gui()
#         pass



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



def _get_feed_worker(worker, gd_client, tag):
    """
    Get the feed and then start new threads to get each one of the
    images.
    """
    # TODO: we should have to get the feed if its already been fetched
    # this session, maybe we need some sort of in memory database of
    # feeds that have been fetched
    email = meta.get_default(PICASA_EMAIL_KEY).value
    try:
        user, domain = email.split('@', 1)
    except:
        user = email
    album = meta.get_default(PICASA_ALBUM_KEY).value

    if tag in __feed_cache:
        feed = __feed_cache[tag]
    else:
        feed = get_photo_feed(gd_client, user, album, tag)
        __feed_cache[tag] = feed

    path = os.path.join(default_path)
    if not os.path.exists(path):
        os.makedirs(path)

    cache = PhotoCache()
    for entry in feed.entry:
        url = entry.media.thumbnail[0].url
        photo_id = 'picasa:%s' % entry.gphoto_id.text
        photo = cache[photo_id]
        def _get():
            extension = url[-4:]
            fd, filename = tempfile.mkstemp(suffix=extension, dir=path)
            urllib.urlretrieve(url, filename)
            cache.add(photo_id, filename)
        if not photo:
            _get()
        if not os.path.exists(photo.path):
            cache.remove(photo_id)
            _get()
        # publish the id of the image in the image cache
        worker.publish(photo_id)



# The iconview_worker represents the thread and is global so that we
# can check if it is running and cancel it if necessary.
iconview_worker = None

def _on_get_feed_publish(worker, data, iconview):
    model = iconview.get_model()
    cache = PhotoCache()
    for photo_id in data:
        filename = cache[photo_id].path
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        model.append([pixbuf])


def populate_iconview(gd_client, iconview, tag):
    """
    Get the photos with tag from the PicasaWeb or from the photo cache
    and populate the iconview.

    :param gd_client:
    :param iconview:
    :param tag:
    """
    global iconview_worker
    if iconview_worker:
        iconview_worker.cancel()

    utils.clear_model(iconview)
    model = gtk.ListStore(gtk.gdk.Pixbuf)
    iconview.set_model(model)

    cache = PhotoCache()
    if not cache.exists():
        PhotoCache(create=True)

    iconview_worker = thread.GtkWorker(_get_feed_worker, gd_client, tag)
    iconview_worker.connect('published', _on_get_feed_publish, iconview)
    iconview_worker.execute()
    return iconview_worker



class PicasaInfoPage(view.InfoBoxPage):

    def __init__(self):
        super(PicasaInfoPage, self).__init__()
        self.label = _('Images')
        self._disabled = False
        self.gd_client = gdata.photos.service.PhotosService()
        self.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)
        self.iconview = gtk.IconView()

        # TODO: we set the columns here because for some reason the
        # combination of paned windows, notebooks and scrollbars seems
        # to screw up the icon view automatic row/column handling so
        # that if you make the infobox larger then the images seem to
        # move between rows ok but if you make it smaller it doesn't
        self.iconview.set_columns(1)
        self.iconview.set_pixbuf_column(0)
        self.vbox.pack_start(self.iconview)

        loading_image = os.path.join(paths.lib_dir(), 'images', 'loading.gif')
        animation = gtk.gdk.PixbufAnimation(loading_image)
        self._progress_image = gtk.Image()
        self._progress_image.set_from_animation(animation)


    def set_busy(self, busy=True):
        if not busy:
            self.vbox.remove(self._progress_image)
        else:
            self.vbox.pack_start(self._progress_image, expand=False,fill=False)
            self.vbox.reorder_child(self._progress_image, 0)


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
        self.set_busy()
        worker = populate_iconview(self.gd_client, self.iconview, tag)
        def on_done(*args):
            self.set_busy(False)
        worker.connect('done', on_done, False)



class PicasaPlugin(pluginmgr.Plugin):
    tools = [PicasaUploadTool, PicasaSettingsTool]
    view = PicasaView
    #commands = [PicasaCommandHandler]

    @classmethod
    def install(cls, import_defaults):
        # TODO: create cache database
        #ImageCache.create()
        pass


# uncomment the following line to enable this plugin
plugin = PicasaPlugin
