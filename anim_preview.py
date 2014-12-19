#
# Entangle: Tethered Camera Control & Capture
#
# Copyright (C) 2014 Daniel P. Berrange
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Peas
from gi.repository import PeasGtk
from gi.repository import Entangle


class AnimPreviewWindow(Gtk.Window):
    def __init__(self, menu):
        Gtk.Window.__init__(self)
        self.menu = menu
        self.connect("destroy", self.close)
        self.connect("key-release-event", self.do_key_release)

    def close(self, widget):
        self.menu.set_active(False)


    def do_key_release(self, src, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.menu.set_active(False)

class AnimPreviewPluginWindow(object):
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
        self.menu = Gtk.CheckMenuItem(label="Preview Animation")
        self.button = Gtk.Button("Play")
        self.menusig = None
        self.buttonsig = None
        self.ani_win = None

    def do_start_preview(self):
        self.ani_win = AnimPreviewWindow(self.menu)
        self.ani_win.set_title("Animation Preview")
        self.ani_win.show()

        builder = self.win.get_builder()
        pane = builder.get_object("win-box")
        pane.pack_start(self.button, False, True, 0)
        self.button.show()
        self.button.grab_focus()
        self.buttonsig = self.button.connect("clicked", self.do_play)

    def do_stop_preview(self):
        self.ani_win.destroy()

        builder = self.win.get_builder()
        pane = builder.get_object("win-box")
        pane.remove(self.button)
        self.button.disconnect(self.buttonsig)

    def do_toggle_preview(self, src):
        if src.get_active():
            self.do_start_preview()
        else:
            self.do_stop_preview()

    def do_play(self, src):
        # self.win.capture()
        print("playing at {0} fps".format(self.config.get_fps()))

    def activate(self):
        '''Activate the plugin on the window'''
        builder = self.win.get_builder()
        wins = builder.get_object("menu-windows")
        items = wins.get_submenu()
        items.append(self.menu)
        self.menu.show()
        self.menusig = self.menu.connect("toggled", self.do_toggle_preview)

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


class AnimPreviewPluginConfig(Gtk.Grid):
    '''Provides integration with GSettings to read/write
    configuration parameters'''

    def __init__(self, plugin_info):
        Gtk.Grid.__init__(self)
        settingsdir = plugin_info.get_data_dir() + "/schemas"
        sssdef = Gio.SettingsSchemaSource.get_default()
        sss = Gio.SettingsSchemaSource.new_from_directory(settingsdir, sssdef, False)
        schema = sss.lookup("org.entangle-photo.plugins.anim_preview", False)
        self.settings = Gio.Settings.new_full(schema, None, None)

    def get_fps(self):
        return self.settings.get_int("fps")

    def set_fps(self, fps):
        self.settings.set_int("fps", fps)


class AnimPreviewPluginConfigure(Gtk.Grid):
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

        self.fpstxt.connect("changed", self.do_set_fps)

        self.fpstxt.set_value(self.config.get_fps())

    def do_set_fps(self, src):
        self.config.set_fps(src.get_value_as_int())


class AnimPreviewPlugin(GObject.Object, Peas.Activatable, PeasGtk.Configurable):
    '''Handles the plugin activate/deactivation and
    tracking of camera manager windows. When a window
    appears, it enables the photobox functionality on
    that window'''
    __gtype_name__ = "AnimPreviewPlugin"

    object = GObject.property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)
        self.winsig = None
        self.wins = []
        self.config = None

    def do_activate_window(self, win):
        if not isinstance(win, Entangle.CameraManager):
            return
        pb = AnimPreviewPluginWindow(win, self.config)
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
            self.config = AnimPreviewPluginConfig(self.plugin_info)

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
            self.config = AnimPreviewPluginConfig(self.plugin_info)

        return AnimPreviewPluginConfigure(self.config)
