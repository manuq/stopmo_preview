from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Peas
from gi.repository import PeasGtk
from gi.repository import Entangle


class AnimArea(Gtk.DrawingArea):
    def __init__(self, pixbuf):
        self.pixbuf = pixbuf
        Gtk.DrawingArea.__init__(self)
        self.connect('draw', self.on_draw)

    def set_pixbuf(self, pixbuf):
        if pixbuf is not None:
            self.pixbuf = pixbuf
            self.queue_draw()

    def on_draw(self, widget, context):
        if self.pixbuf is not None:
            alloc = self.get_allocation()
            pixbuf_width = self.pixbuf.get_width()
            pixbuf_height = self.pixbuf.get_height()
            scale_x = alloc.width / pixbuf_width
            scale_y = alloc.height / pixbuf_height
            scale = min(scale_x, scale_y)
            dx = (alloc.width - pixbuf_width * scale) / 2
            dy = (alloc.height - pixbuf_height * scale) / 2
            context.translate(dx, dy)
            context.scale(scale, scale)
            Gdk.cairo_set_source_pixbuf(context, self.pixbuf, 0, 0)
            context.paint()

class StopmoPreviewWindow(Gtk.Window):
    def __init__(self, plugin_win, session_browser):
        Gtk.Window.__init__(self)
        self.plugin_win = plugin_win
        self.session_browser = session_browser
        self.play_hid = None
        self.idx = 0

        box = Gtk.Box()
        self.add(box)
        box.show()

        pixbuf = self.next_pixbuf()
        self.drawing_area = AnimArea(pixbuf)
        box.pack_start(self.drawing_area, True, True, 0)
        self.drawing_area.show()

        if pixbuf is not None:
            self.set_default_size(pixbuf.get_width() * 2, pixbuf.get_height() * 2)
        self.play()

        self.connect("delete-event", self.on_delete)

    def next_pixbuf(self):
        thumb_loader = self.session_browser.get_thumbnail_loader()
        session = self.session_browser.get_session()

        if session.image_count() == 0:
            return None

        image = session.image_get(self.idx)
        pixbuf = thumb_loader.get_pixbuf(image)

        if self.idx > 0:
            self.idx -= 1
        else:
            self.idx = session.image_count() - 1
        return pixbuf

    def next_frame(self):
        self.drawing_area.set_pixbuf(self.next_pixbuf())
        return True

    def play(self):
        if self.play_hid is None:
            fps = self.plugin_win.config.get_fps()
            milliseconds = 1.0 / fps * 1000
            self.play_hid = GObject.timeout_add(milliseconds,
                                                self.next_frame)

    def stop(self):
        if self.play_hid is not None:
            GObject.source_remove(self.play_hid)
            self.play_hid = None

    def on_delete(self, widget, event):
        self.set_visible(False)
        self.plugin_win.menu.set_active(False)
        return True


class StopmoPreviewPluginWindow(object):
    '''Handles interaction with a single instance of
    the EntangleCameraManager window. We add a menu
    option to the 'Windows' menu which allows the
    photobox mode to be started. It can be stopped
    by pressing escape. In photobox mode the menubar,
    toolbar and controls are all hidden. A single
    shoot button is added at the bottom of the screen'''

    def __init__(self, win, config):
        '''@win: an instance of EntangleCameraManager'''

        self.config = config
        self.win = win
        self.menu = Gtk.CheckMenuItem(label="StopMotion Preview")
        self.menusig = None
        self.ani_win = None

    def do_start_preview(self):
        if self.ani_win is not None:
            self.ani_win.set_visible(True)
            self.ani_win.play()
            return

        builder = self.win.get_builder()

        session_browser = builder.get_object("display-panel").get_child2().get_children()[0]
        self.ani_win = StopmoPreviewWindow(self, session_browser)
        self.ani_win.set_title("StopMotion Preview")
        self.ani_win.show()

    def do_stop_preview(self):
        self.ani_win.set_visible(False)
        self.ani_win.stop()

    def on_toggle_preview(self, src):
        if src.get_active():
            self.do_start_preview()
        else:
            self.do_stop_preview()

    def activate(self):
        '''Activate the plugin on the window'''
        builder = self.win.get_builder()
        wins = builder.get_object("menu-windows")
        items = wins.get_submenu()
        items.append(self.menu)
        self.menu.show()
        self.menusig = self.menu.connect("toggled", self.on_toggle_preview)

    def deactivate(self):
        '''Deactivate the plugin on the window, undoing
        all changes made since the 'activate' call'''

        if self.menu.get_active():
            self.do_stop_preview()
        builder = self.win.get_builder()
        wins = builder.get_object("menu-windows")
        items = wins.get_submenu()
        items.remove(self.menu)
        self.menu.disconnect(self.menusig)


class StopmoPreviewPluginConfig(Gtk.Grid):
    '''Provides integration with GSettings to read/write
    configuration parameters'''

    def __init__(self, plugin_info):
        Gtk.Grid.__init__(self)
        settingsdir = plugin_info.get_data_dir() + "/schemas"
        sssdef = Gio.SettingsSchemaSource.get_default()
        sss = Gio.SettingsSchemaSource.new_from_directory(settingsdir, sssdef, False)
        schema = sss.lookup("org.entangle-photo.plugins.stopmo_preview", False)
        self.settings = Gio.Settings.new_full(schema, None, None)

    def get_fps(self):
        return self.settings.get_int("fps")

    def set_fps(self, fps):
        self.settings.set_int("fps", fps)


class StopmoPreviewPluginConfigure(Gtk.Grid):
    ''''Provides the configuration widget for the plugin'''

    def __init__(self, config):
        Gtk.Grid.__init__(self)
        self.config = config
        adjustment = Gtk.Adjustment(50.0, 1.0, 50.0, 1.0, 5.0, 0.0)
        self.fpstxt = Gtk.SpinButton()
        self.fpstxt.configure(adjustment, 1.0, 0)
        self.attach(Gtk.Label("Frames per second:"),
                    0, 0, 1, 1)
        self.attach(self.fpstxt,
                    1, 0, 2, 1)
        self.set_border_width(6)
        self.set_row_spacing(6)
        self.set_column_spacing(6)

        self.fpstxt.connect("value-changed", self.do_set_fps)

        self.fpstxt.set_value(self.config.get_fps())

    def do_set_fps(self, src):
        self.config.set_fps(src.get_value_as_int())


class StopmoPreviewPlugin(GObject.Object, Peas.Activatable, PeasGtk.Configurable):
    '''Handles the plugin activate/deactivation and
    tracking of camera manager windows. When a window
    appears, it enables the photobox functionality on
    that window'''
    __gtype_name__ = "StopmoPreviewPlugin"

    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)
        self.winsig = None
        self.wins = []
        self.config = None

    def do_activate_window(self, win):
        if not isinstance(win, Entangle.CameraManager):
            return
        pb = StopmoPreviewPluginWindow(win, self.config)
        self.wins.append(pb)
        pb.activate()

    def do_deactivate_window(self, win):
        if not isinstance(win, Entangle.CameraManager):
            return
        oldwins = self.wins
        self.wins = []
        for w in oldwins:
            if w.win == win:
                w.deactivate()
            else:
                self.wins.append(w)

    def do_activate(self):
        if self.config is None:
            self.config = StopmoPreviewPluginConfig(self.plugin_info)

        # Windows can be dynamically added/removed so we
        # must track this
        self.winsig = self.object.connect(
            "window-added",
            lambda app, win: self.do_activate_window(win))
        self.winsig = self.object.connect(
            "window-removed",
            lambda app, win: self.do_deactivate_window(win))

        for win in self.object.get_windows():
            self.do_activate_window(win)

    def do_deactivate(self):
        self.object.disconnect(self.winsig)
        for win in self.object.get_windows():
            self.do_deactivate_window(win)
        self.config = None

    def do_create_configure_widget(self):
        if self.config is None:
            self.config = StopmoPreviewPluginConfig(self.plugin_info)

        return StopmoPreviewPluginConfigure(self.config)
