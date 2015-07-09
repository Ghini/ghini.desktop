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
#
# picasa plugin
#

# 1. should be able to upload photos, have to use picasa to delete and
# do other photo manipulation
#
# 2. on import should autotag with the plant name
#
# 3. need to be able to set a max cache size to delete the oldest
# files if we go over the cache size
#
# 4. By default we should only get the files of a certain size that
# can be viewed in Bauble but should allow the option to download the
# original file
#
# 5. Should provide a Save As button so the user can save a copy of
# the file for later use
#

#  TODO: create a timeout when fetching the feed so the infopage
#  doesn't just sit there and look busy

# TODO: the infobox can get a little confused if you switch between
# two species too fast and just get hung on with the progress image

# IDEA: we could probably make this module more generic and based on
# mixins where we add the functionality for getting the photos by
# mixing in different implentations for different services
import gtk
import gobject

import os
import sys
import tempfile
import urllib
from Queue import Queue

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import bauble.db as db
from bauble.i18n import _


# this little dummyfile hack fixes an annoying deprecation warning
# when importing gdata 1.2.4
class dummyfile(object):
    def write(*x):
        pass

tmp = sys.stderr
sys.stderr = dummyfile()
import gdata.photos.service
sys.stderr = tmp

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base

import bauble
import bauble.meta as meta
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
import bauble.utils.thread as thread
import bauble.view as view
from bauble.plugins.plants import Species

PICASA_TOKEN_KEY = u'picasa_token'

# TODO: should we store the email and album in the BaubleMeta...these
# should only be changeable by an administrator...should probably only
# allow an administrator to even access the PicasaTool
PICASA_EMAIL_KEY = u'picasa_email'
PICASA_ALBUM_KEY = u'picasa_album'

# see http://code.google.com/apis/picasaweb/reference.html#Parameters
picasa_imgmax = 'd'  # "d" means download the original
picasa_thumbsize = '144u'

default_path = os.path.join(paths.user_dir(), 'photos')

# keep a copy of the feeds that we retrieve by tag
__feed_cache = {}


def update_meta(email=None, album=None, token=None):
    """
    Update the email, album and authorization token in the bauble meta table.
    """
    # TODO: should we allow setting the values to None
    session = db.Session()
    if email:
        email = utils.utf8(email)
        meta.get_default(PICASA_EMAIL_KEY, email, session).value = email
    if album:
        album = utils.utf8(album)
        meta.get_default(PICASA_ALBUM_KEY, album, session).value = album
    if token:
        token = utils.utf8(token)
        meta.get_default(PICASA_TOKEN_KEY, token, session).value = token
    session.commit()
    session.close()
    __feed_cache.clear()


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
    def __init__(self, path=None, create=True):
        """
        :param path: the path to the sqlite database
        :param create: create the database if it doesn't exists
        """
        if not path:
            path = os.path.join(default_path, 'photos.db')
        if create and not os.path.exists(path):
            # create the file
            head, tail = os.path.split(path)
            try:
                os.makedirs(head)
            except:
                pass
            open(path, 'wb+').close()
        uri = 'sqlite:///%s' % path
        self.engine = sa.create_engine(uri)
        self.engine.connect()
        self.metadata = Base.metadata
        self.metadata.bind = self.engine
        self.Session = orm.sessionmaker(bind=self.engine, autoflush=False)
        if create and os.path.exists(path):
            self.metadata.drop_all(checkfirst=True)
            self.metadata.create_all()

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
        self.widgets = utils.load_widgets(widget_path)
        self.window = self.widgets.settings_dialog
        if bauble.gui:
            self.window.set_transient_for(bauble.gui.window)

        self.widgets.password_entry.connect('changed', self.on_changed)

        email = meta.get_default(PICASA_EMAIL_KEY, '').value
        self.widgets.email_entry.set_text(email or '')

        album = meta.get_default(PICASA_ALBUM_KEY, '').value
        self.widgets.album_entry.set_text(album or '')

        auth = meta.get_default(PICASA_TOKEN_KEY, '').value
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
            return response
        stored_email = meta.get_default(PICASA_EMAIL_KEY).value.strip()
        email = self.widgets.email_entry.get_text().strip()
        album = self.widgets.album_entry.get_text().strip()
        passwd = self.widgets.password_entry.get_text().strip()

        if stored_email != email or self._changed:
            try:
                token = get_auth_token(email, passwd)
            except Exception, e:
                logger.debug(e)
                token = None
            if not token:
                utils.message_dialog(_('Could not authorize Google '
                                       'account: %s' % email),
                                     gtk.MESSAGE_ERROR)
                return False
            update_meta(utils.utf8(email), utils.utf8(album),
                        utils.utf8(token))
        else:
            update_meta(album=album)
        return response


# the _exc_queue hold any exceptions that we get in _get_feed_worker
_exc_queue = Queue()


def _get_feed_worker(worker, gd_client, tag):
    """
    Get the feed and then start new threads to get each one of the
    images.
    """
    # TODO: we should have to get the feed if its already been fetched
    # this session, maybe we need some sort of in memory database of
    # feeds that have been fetched
    email = meta.get_default(PICASA_EMAIL_KEY).value
    album = meta.get_default(PICASA_ALBUM_KEY).value

    if tag in __feed_cache:
        feed = __feed_cache[tag]
    else:
        try:
            feed = get_photo_feed(gd_client, email, album, tag)
        except Exception, e:
            worker.canceled = True
            _exc_queue.put(e)
            return
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
            photo = cache[photo_id]
        if not photo:
            _get()
        if not os.path.exists(photo.path):
            cache.remove(photo_id)
            _get()
        # publish the id of the image in the image cache
        worker.publish(photo_id)
        worker.publishQueue.join()  # wait for publish tofinish


# The iconview_worker represents the thread and is global so that we
# can check if it is running and cancel it if necessary.
iconview_worker = None


def _on_get_feed_publish(worker, data, iconview):
    """
    Add the photo the the iconview.

    :param worker: GtkWorker
    :param data: a list of ids of the image in the PhotoCache
    :param iconview: gtk.IconView
    """
    model = iconview.get_model()
    cache = PhotoCache()
    for photo_id in data:
        filename = cache[photo_id].path
        pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        model.append([pixbuf])
    worker.publishQueue.task_done()


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

    cache = PhotoCache(create=True)  # creates the cache if it doesn't exists

    iconview_worker = thread.GtkWorker(_get_feed_worker, gd_client, tag)
    iconview_worker.connect('published', _on_get_feed_publish, iconview)
    iconview_worker.execute()
    return iconview_worker


class StatusBox(gtk.VBox):
    """
    A VBox that makes it easier to control the different states of
    information and errors in the PicasaInfoPage.
    """
    def __init__(self, button_callback):
        super(StatusBox, self).__init__()
        self.label = gtk.Label()
        self.pack_start(self.label, False, False)

        loading_image = os.path.join(paths.lib_dir(), 'images', 'loading.gif')
        animation = gtk.gdk.PixbufAnimation(loading_image)
        self.progress_image = gtk.Image()
        self.progress_image.set_from_animation(animation)
        self.pack_start(self.progress_image, False, False)

        self.button = gtk.Button(_('Settings'))
        self.button.connect('clicked', button_callback)
        self.pack_start(self.button, False, False, padding=10)

    def set_text(self, text):
        """
        Set the label label text and show the label widget.
        """
        self.label.show()
        self.label.set_text(text)

    def set_busy(self, busy=True):
        """
        If False then hide the progress image.  If True then hide the
        button and label widgets and show the progress image.
        """
        if busy:
            self.button.hide()
            self.label.hide()
            self.progress_image.show()
        else:
            self.progress_image.hide()

    def on_error(self, message):
        """
        Hide the progress image and show the label and button.
        """
        self.progress_image.hide_all()
        self.label.set_text(message)
        self.label.show()
        self.button.show_all()


class PicasaInfoPage(view.InfoBoxPage):

    def __init__(self):
        super(PicasaInfoPage, self).__init__()
        self.label = _('Images')
        self._disabled = False
        self.gd_client = gdata.photos.service.PhotosService()
        #self.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_ALWAYS)

        self.iconview = gtk.IconView()
        # TODO: we set the columns here because for some reason the
        # combination of paned windows, notebooks and scrollbars seems
        # to screw up the icon view automatic row/column handling so
        # that if you make the infobox larger then the images seem to
        # move between rows ok but if you make it smaller it doesn't
        self.iconview.set_columns(1)
        self.iconview.set_pixbuf_column(0)
        self.vbox.pack_start(self.iconview)

        self._current_row = None

        def on_clicked(*args):
            d = PicasaSettingsDialog()
            if d.run():
                self.update(self._current_row)

        self.status_box = StatusBox(on_clicked)
        self.vbox.pack_start(self.status_box)
        self.show_status_box()

    def show_status_box(self):
        """
        Show the status box and hide the iconview.
        """
        self.iconview.hide_all()
        if self.iconview.get_parent():
            self.vbox.remove(self.iconview)
        if not self.status_box.get_parent():
            self.vbox.pack_start(self.status_box, True, True)
        self.status_box.show()

    def hide_status_box(self):
        """
        Show the iconview and hide the status box.
        """
        self.status_box.hide_all()
        if self.status_box.get_parent():
            self.vbox.remove(self.status_box)
        if not self.iconview.get_parent():
            self.vbox.pack_start(self.iconview)
        self.iconview.show()

    def set_busy(self, busy=True):
        """
        Toggle the throbber.
        """
        if busy:
            self.show_status_box()
            self.status_box.set_busy()
        else:
            self.status_box.set_busy(False)

    def on_error(self, message, species):
        self.show_status_box()
        self.status_box.on_error(message)

    def update(self, row):
        """
        Update the Picasa info page.

        :param: a Species instance
        """
        self._current_row = row
        token_meta = meta.get_default(utils.utf8(PICASA_TOKEN_KEY))
        if not token_meta:
            msg = _('Could not login to PicasaWeb account.')
            self.on_error(msg, species=row)
            return
        token = token_meta.value
        self.gd_client.SetClientLoginToken(token)
        tag = Species.str(row, markup=False, authors=False)
        self.set_busy()
        worker = populate_iconview(self.gd_client, self.iconview, tag)

        def on_done(*args):
            if not _exc_queue.empty():
                exc = _exc_queue.get()
                msg = 'Could not retrieve the photos.\n\n'
                if isinstance(exc, gdata.photos.service.GooglePhotosException):
                    msg += exc.message
                else:
                    msg += str(exc)
                gobject.idle_add(self.on_error, msg, row)
                return
            self.set_busy(False)
            model = self.iconview.get_model()
            if len(model) == 0:
                gobject.idle_add(self.status_box.set_text, _('No images'))
                gobject.idle_add(self.show_status_box)
            else:
                gobject.idle_add(self.hide_status_box)
        worker.connect('done', on_done, False)


# def upload(image, species):
#     """
#     Upload an image to the Picasa Web Album

#     :param image: the image data
#     :param species: the species name
#     """
#     tag = Species.str(species, markup=False, authors=False)
#     session = db.Session()
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
#                                   content_type='image/jpeg')

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


# class PicasaUploadTool(pluginmgr.Tool):
#     """
#     Tool for uploading images to the Picasa Web Albums
#     """
#     category = 'Picasa'
#     label = 'Upload'

#     @classmethod
#     def start(cls):
#         d = PicasaUploader()
#         d.start()

class PicasaSettingsTool(pluginmgr.Tool):
    """
    Tool for changing the Picasa settings and updated the auth token
    """
    category = _('Picasa')
    label = _('Settings')

    @classmethod
    def start(cls):
        d = PicasaSettingsDialog()
        d.run()


# class PicasaView(pluginmgr.View):

#     def __init__(self):
#         super(PicasaView, self).__init__()

#     def do_something(self, arg):
#         pass

class PicasaPlugin(pluginmgr.Plugin):
    #tools = [PicasaUploadTool, PicasaSettingsTool]
    tools = [PicasaSettingsTool]
    #view = PicasaView
    #commands = [PicasaCommandHandler]


plugin = PicasaPlugin
