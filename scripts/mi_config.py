### -*- python -*-
# Copyright (C) 2010, zy_sunshine.
# Author:   zy_sunshine <zy.netsec@gmail.com>
# All rights reserved

import os
import sys

TOPDIR = os.environ.get('MI_BUILD_TOP')
if not TOPDIR:
    TOPDIR = os.path.dirname(os.path.dirname(__file__))

def _p(*args):
    return os.path.join(*args)

# Specify the kernel version which used by MI environment.
#mikernelver = '2.6.35.4'
mikernelver = '3.4.51-1mgc30.x86_64'

# If .distmode exists, enable Distributor Mode
develmode = not os.path.exists('.distmode')

#{{ User custom default value
langset = 'en:zh_CN'
#}}

#{{{ User custom default value
welcome = 'Welcome to the Auto Distribution provided by MagicInstaller.'
distname = 'AutoDistribution'
distver = '0.0'
distkernelver = '2.6.9'
pkgtype = 'rpm'
langset = 'en:zh_CN'

if mikernelver[:3]=='2.4':
    kmods_arrange = {
        "boot" : [ '@ext3.o', '@jfs.o', '@ntfs.o', '@reiserfs.o', '@vfat.o' ],
        "scsi" : [ '@xfs.o', '@sd_mod.o', '@kernel/drivers/md', '@kernel/drivers/scsi' ],
        "net" : ['@xfs.o', '@kernel/drivers/md', '@kernel/drivers/net' ]
        }
else:
    kmods_arrange = {
        "boot" : [ '@jfs.ko', '@ntfs.ko', '@vfat.ko' ],
        "scsi" : [ '@xfs.ko', '@sd_mod.ko', '@kernel/drivers/scsi' ],
        "net" : ['@xfs.ko', '@kernel/drivers/net' ]
        }

autopart_profile = {}

specdir = _p(TOPDIR, 'spec')
specfn  = _p(TOPDIR, 'spec/specinfo.py')
pkgarr = _p(TOPDIR, 'result/pkgarr.py')
pkgdirs = specdir + '/packages'
hotfixfiles_dir = specdir + '/hotfix'
addfiles_dir = specdir + '/addfiles'

dolog = True                           # Log message or not
nonewt = False                          # Without newt or not
useudev = True                         # Use udev or not
bootload = 'grub'

# For scripts/PkgArrang.py
volume_limit_list = [620 * 1024 * 1024, 640 * 1024 * 1024, 640 * 1024 * 1024]
placement_list = [[]]
toplevel_groups = {}
add_deps = {}
remove_deps = {}
basepkg_list = []
abs_pos = []
noscripts_list = []

# merge specinfo
import specinfo
for key in dir(specinfo):
    if (key[:2] != '__'):
        vars()[key] = specinfo.__dict__[key]
del specinfo

# iso name
max_cd_no = 9
isofn_fmt = '%s-%s-%d.iso'
def mkisofn(iso_no):
    global distname, distver
    return _p(TOPDIR, 'result/' + isofn_fmt % (distname, distver, iso_no))
bootiso_fn = os.path.basename(mkisofn(1))

if useudev:
    udev_arg = '--use-udev'
else:
    udev_arg = ''
# }}}

# {{{ Run setting
# boot screen mode
gui_mode = 788 #785

if gui_mode == 785:
    full_width  = 640
    full_height = 480
elif gui_mode == 788:
    full_width  = 800
    full_height = 600
gui_resolution = '%dx%d' % (full_width, full_height)

hotfixdir = '/tmp/update'
# }}}

# {{{ Build environment
tmpdir = _p(TOPDIR, 'tmp')
bindir = _p(TOPDIR, 'bindir')

# Some dirs and files in tmpdir.
devrootdir = os.path.join(tmpdir, 'devroot')   # building sources dir

# For iso.
bootcd_dir = os.path.join(tmpdir, 'bootcd')
miimages_cddir = 'boot'
miimages_dir = os.path.join(bootcd_dir, miimages_cddir)
mlbase_dir = os.path.join(bootcd_dir, distname, 'base')     # Linux dist base dir in bootcd

# Python
pythonbin = '/usr/bin/python'
pythondir = 'usr/lib/python2.7'
#}}}

#{{ build rootfs environment
busybox_version = '1.17.2'                       # busybox in rootfs

root_bindir = '/usr/bin'
root_libdir = '/$pythondir/site-packages'
root_datadir = '/usr/share/MagicInstaller'
#root_moduledir = '/usr/share/MagicInstaller/modules'
#root_operationdir = '/usr/share/MagicInstaller/operations'

# whether use sudo promopt in sudo commands, every time.
use_sudo_prom = False
sudoprom = ''
if use_sudo_prom:
    sudoprom = ' && sudo -k'
    # If use sudo promopt, clean sudo timpstamp first.
    os.system('echo "clean sudo timestamp..." %s' % sudoprom)

#}}

#{{ build magicinstaller src environment (src/*)
destdir = os.path.join(tmpdir, 'root.src.step1')      # with magicinstaller root src files
pyextdir = os.path.join(tmpdir, 'root.src.pyext')   # python module for MI.

# i18n translation
textdomain = 'magic.installer'
translators = ''
copyright_holder = 'Charles Wang, Zhang Yang'
all_linguas = ['zh_CN']

lang_map = {'ja_JP': ('eucJP', 'eucJP'),
             'ko_KR' : ('eucKR', 'eucKR'),
             'zh_CN': ('gb2312', 'GB2312'), # GB2312 is used by iconv in po file charset translate
             'zh_TW': ('big5', 'BIG5') }
# For magicinstaller debug
ip_mihost = '192.168.56.111'
ip_devhost = '192.168.56.1'
#}}

pkgarr_ser_hdpath = [
    "boot",
    "MagicLinux",
    "usr/share/MagicInstaller",
    "",
    "tmp",
]

