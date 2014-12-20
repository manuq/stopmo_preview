#!/usr/bin/env python

import os
import subprocess
import shutil
from gi.repository import GLib

config_dir = GLib.get_user_config_dir()
plugins_dir = os.path.join(config_dir, 'entangle', 'plugins', 'anim_preview')

if os.path.exists(plugins_dir):
    shutil.rmtree(plugins_dir)
shutil.copytree('src', plugins_dir)

schemas_dir = os.path.join(plugins_dir, 'schemas')
subprocess.call(['glib-compile-schemas', schemas_dir])
