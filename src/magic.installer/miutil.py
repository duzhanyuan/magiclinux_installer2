#!/usr/bin/python
from mipublic import *
import os
import sys
import isys

USE_ISYS = False

class AttrDict(dict):
    """A dict class, holding the dict. Two extra method to get dict
    value, e.g.:
    attrs = attrs_dict(cat)
    attrs.tips
    attrs('tips')"""
    def __init__(self, d={}):
        self.d = d
    def __call__(self, arg):
        return self.get(arg, None)
    def __getattr__(self, attr):
        return self.get(attr, None)

class NamedTuple(tuple):
    """Access a tuple by attribute name. e.g.:
    class AutoPartTuple(NamedTuple):
        attr_oder = ['mountpoint', 'size', 'filesystem']

    part = ('/', '32G', 'ext2')
    part = AutoPartTuple(part)
    print part.mountpoint,  part.size, part.filesystem
    """
    attr_order = []
    def __init__(self, seq):
        tuple.__init__(self, seq)

    def __getattr__(self, attr):
        idx = self.attr_order.index(attr)
        return self[idx]

def run_bash(cmd, argv=[], root='/'):
    import subprocess
    def chroot():
        os.chroot(root)
    cmd_res = {}
    res = subprocess.Popen([cmd] + argv, 
                            stdout = subprocess.PIPE, 
                            stderr = subprocess.PIPE, 
                            preexec_fn = chroot, cwd = root,
                            close_fds = True)
    res.wait()
    cmd_res['out']=res.stdout.readlines()
    cmd_res['err']=res.stderr.readlines()
    cmd_res['ret']=res.returncode
    return cmd_res

def treedir(dir, complete_path=True):
    all_dirs = []
    all_files = []
    topdown = True
    for root, dirs, files in os.walk(dir, topdown):
        for d in dirs:
            if complete_path:
                all_dirs.append(os.path.join(root, d))
            else:
                all_dirs.append(d)
        for f in files:
            if complete_path:
                all_files.append(os.path.join(root, f))
            else:
                all_files.append(f)
    return all_dirs, all_files

logf = None

def openlog(filename):
    global logf, dolog
    if dolog:
    	try:
            logf = file(filename, 'w')
    	except:
            print 'Open log file %s failed.\n' % filename
            logf = None

def dolog(str, *args, **argw):
    global logf, dolog

    if dolog:
        if logf:
            logf.write('%s' % str)
            logf.flush()
    	print str,

def closelog():
    global logf, dolog
    if dolog:
    	if logf:
            logf.close()

# mntdir --> [loop_dev, isopath]
LOOP_DEVICES = {}
FREE_LOOP = ['/dev/loop0', '/dev/loop1', '/dev/loop2', '/dev/loop3',
            '/dev/loop4', '/dev/loop5', '/dev/loop6', '/dev/loop7']
USED_LOOP = []
def _init_free_loop():
    global FREE_LOOP
    new_free_loop = []
    for lo in FREE_LOOP:
        ret, msg = isys.loopstatus(lo)
        if not ret:
            new_free_loop.append(lo)
        else:
            #print msg
            pass
    FREE_LOOP = new_free_loop
_init_free_loop()

def remove_empty_dir(dir):
    if not os.path.exists(dir):
        return True, ''
    if os.path.ismount(dir):
        return False, 'Remove dir failed %s is a mount point' % dir
    else:
        if not os.listdir(dir):
            try:
                os.rmdir(dir)
            except OSError, e:
                return False, str(e)
        else:
            return False, 'Remove dir failed: %s is not a empty dir' % dir
    return True, ''

def get_new_loop():
    try:
        new_loop = FREE_LOOP.pop(0)
    except IndexError,e:
        return False, 'Have No loop devices: %s' % str(e)
    USED_LOOP.append(new_loop)
    return True, new_loop

def free_loop(loop_dev):
    f_flag = False
    f_dev_s = None
    for s in range(len(USED_LOOP)):
        if USED_LOOP[s] == loop_dev:
            f_flag = True
            f_dev_s = s
    if f_flag:
        f_dev = USED_LOOP.pop(f_dev_s)
        FREE_LOOP.append(f_dev)

def mount_dev(fstype, devfn, mntdir=None,flags=None):
    def mount_loop_dev(isopath, mntdir):
        ret, msg = get_new_loop()
        if ret:
            new_loop = msg
            loop_iso = [new_loop, isopath]
            LOOP_DEVICES[mntdir] = loop_iso
            cmd = '/sbin/losetup'
            argv = [new_loop, isopath]
            cmdres = run_bash(cmd, argv)
            if cmdres['ret']:
                errmsg = str(cmdres['err'])
                free_loop(new_loop)
                return False, errmsg
            else:
                cmd = '/bin/mount'
                argv = [new_loop, mntdir]
                cmdres = run_bash(cmd, argv)
                if cmdres['ret']:
                    errmsg = str(cmdres['err'])
                    return False, errmsg
                else:
                    return True, mntdir
        else:
            return False, msg

    def get_mnt_dir(devfn):
        mntdir = '/tmpfs/mnt/%s' % os.path.basename(devfn)
        ret, msg = remove_empty_dir(mntdir)
        if not ret:
            for sub in range(30):
                mntdir = '/tmpfs/mnt/%s_%s' % (os.path.basename(devfn), sub)
                ret, msg = remove_empty_dir(mntdir)
                if not ret:
                    continue
                else:
                    return True, mntdir
            return False, 'Can not get mntdir automatically.'
        else:
            return True, mntdir

    if not mntdir:
        # Not special point the mnt dir, we should get it automatically.
        ret, msg = get_mnt_dir(devfn)
        if ret:
            mntdir = msg
        else:
            return False, msg
    else:
        ret, msg = remove_empty_dir(mntdir)
        if not ret:
            return False, msg
        try:
            os.makedirs(mntdir)
        except OSError, e:
            return False, str(e)

    dolog("mount_dev: Device = %s Mount = %s Fstype = %s\n" % \
        (devfn, mntdir, fstype))
    if not os.path.exists(mntdir):
        os.makedirs(mntdir)
    if USE_ISYS:
        try:
            isys.mount(fstype, devfn, mntdir, flags)
        except SystemError, e:
            errmsg = "mount_dev: mount failed: %s\n" % str(e)
            dolog(errmsg)
            return False, errmsg
        else:
            return True, mntdir
    else:
        f_loop = False
        if flags:
            flag_list = flags.split(',')
        else:
            flag_list = []
        new_flag_list = []
        for f in flag_list:
            if f.strip().startswith('loop'):
                f_loop = True
            else:
                new_flag_list.append(f.strip())
        flags = ','.join(new_flag_list)
        if f_loop:
            isopath = devfn
            ret, msg = mount_loop_dev(isopath, mntdir)
            if not ret:
                return False, msg
            else:
                return True, mntdir
        cmd = ''
        argv = []
        if fstype in ['ntfs', 'ntfs-3g']:
            cmd = '/bin/ntfs-3g'
            argv = [devfn, mntdir]
        else:
            cmd = '/bin/mount'
            if flags:
                argv = ['-t', fstype, '-o', flags, devfn, mntdir]
            else:
                argv = ['-t', fstype, devfn, mntdir]
        dolog("Run mount command: %s %s\n" % (cmd, ' '.join(argv)))
        cmdres = run_bash(cmd, argv)
        if cmdres['ret']:
            errmsg = "mount_dev: mount failed: %s\n" % str([cmdres['out'], cmdres['err']])
            return False, errmsg
        else:
            return True, mntdir

def umount_dev(mntdir, rmdir=True):
    def umount_loop_dev(mntdir):
        cmd = '/bin/umount'
        argv = [mntdir]
        cmdres = run_bash(cmd, argv)
        if cmdres['ret']:
            return False, str(cmdres['err'])
        else:
            loop_dev, isopath = LOOP_DEVICES[mntdir]
            cmd = '/sbin/losetup'
            argv = ['-d', loop_dev]
            cmdres = run_bash(cmd, argv)
            if cmdres['ret']:
                return False, str(cmdres['err'])
            else:
                free_loop(loop_dev)
                LOOP_DEVICES.pop(mntdir, '')
                return True, ''

    isys.sync()
    if USE_ISYS:
        try:
            isys.umount(mntdir)
        except SystemError, e:
            errmsg = "umount_dev: umount failed: %s\n" % str(e)
            dolog(errmsg)
            return False, errmsg
    else:
        f_loop = False
        for mntp in LOOP_DEVICES.keys():
            if mntp == mntdir:
                f_loop = True
        if f_loop:
            ret, msg = umount_loop_dev(mntdir)
            if not ret:
                return False, msg
            else:
                return True, ''

        cmd = '/bin/umount'
        argv = [mntdir]
        dolog("Run umount command: %s %s\n" % (cmd, ' '.join(argv)))
        cmdres = run_bash(cmd, argv)
        if cmdres['ret']:
            errmsg = "umount_dev: umount failed: %s\n" % str([cmdres['out'], cmdres['err']])
            return False, errmsg
    if 0:
        # attempt to remove the mnt dir. For next mount.
        ret, msg = remove_empty_dir(mntdir)
        if not ret:
            return False, msg
    # If there have nothing error happend, return true.
    return True, ''


def search_file(filename, pathes,
                prefix = '', postfix = '',
                exit_if_not_found = True):
    for p in pathes:
        f = os.path.join(prefix, p, postfix, filename)
        if os.access(f, os.R_OK):
            return f
    if exit_if_not_found:
        os.write(sys.stderr.fileno(), "Can't find %s in %s\n" % (filename, str(pathes)))
        sys.exit(1)
    return None

def convert_str_size(size):
    "Convert SIZE of 1K, 2M, 3G to bytes"
    if not size:
        return 0
    k = 1
    try:
        size = int(float(size))
    except ValueError:
        if size[-1] in ('k', 'K'):
            k = 1024
        elif size[-1] in ('m', 'M'):
            k = 1024 * 1024
        elif size[-1] in ('g', 'G'):
            k = 1024 * 1024 * 1024
        try:
            size = int(float(size[:-1]))
        except ValueError:
            return None
    return size * k


#
# colors, for nice output
#

class color_default:
    def __init__(self):
        self.name = 'default'
        self.black =    '\x1b[0;30m'
        self.red =  '\x1b[0;31m'
        self.green =    '\x1b[0;32m'
        self.yellow =   '\x1b[0;33m'
        self.blue = '\x1b[0;34m'
        self.magenta =  '\x1b[0;35m'
        self.cyan = '\x1b[0;36m'
        self.white =    '\x1b[0;37m'
        self.normal =   '\x1b[0m'
        self.bold = '\x1b[1m'
        self.clear =    '\x1b[J'

class color_bw:
    def __init__(self):
        self.name = 'bw'
        self.black =    '\x1b[0;30m'
        self.red =  '\x1b[0m'
        self.green =    '\x1b[0m'
        self.yellow =   '\x1b[0m'
        self.blue = '\x1b[0m'
        self.magenta =  '\x1b[0m'
        self.cyan = '\x1b[0m'
        self.white =    '\x1b[0m'
        self.normal =   '\x1b[0m'
        self.bold = '\x1b[0m'
        self.clear =    '\x1b[J'

color_classes = {
    'default':  color_default,
    'bw':       color_bw
}
color_c = color_classes['default']()

#
# different useful prints
#

def printl(line, color = color_c.normal, bold = 0):
    "Prints a line with a color"
    out = ''
    if line and line[0] == '\r':
        clear_line()
    if bold:
        out = color_c.bold
    out = color + out + line + color_c.normal
    safe_write(out)
    safe_flush()

def perror(line):
    "Prints an error"
    out = ''
    out += color_c.yellow + color_c.bold + '!' + color_c.normal
    out += color_c.red + color_c.bold + '!' + color_c.normal
    out += color_c.blue + color_c.bold + '!' + color_c.normal
    out += ' ' + color_c.green + color_c.bold + line + color_c.normal + '\a'
    safe_write(out)
    safe_flush()

def pexc(line):
    "Prints an exception"
    out = '\n'
    out += ( color_c.cyan + color_c.bold + '!' + color_c.normal ) * 3
    safe_write(out)
    safe_write(color_c.bold + line)
    safe_flush()
    traceback.print_exc()
    safe_write(color_c.normal)
    safe_write('\n')
    safe_flush()

def beep(q = 0):
    "Beeps unless it's told to be quiet"
    if not q:
        printl('\a')


def safe_flush():
    """Safely flushes stdout. It fixes a strange issue with flush and
    nonblocking io, when flushing too fast."""
    c = 0
    while c < 100:
        try:
            sys.stdout.flush()
            return
        except IOError:
            c +=1
            time.sleep(0.01 * c)
    raise Exception, 'flushed too many times, giving up. Please report!'

def safe_write(text):
    """Safely writes to stdout. It fixes the same issue that safe_flush,
    that is, writing too fast raises errors due to nonblocking fd."""
    c = 1
    while c:
        try:
            sys.stdout.write(text)
            return
        except IOError:
            c += 1
            time.sleep(0.01 * c)
    raise Exception, 'wrote too many times, giving up. Please report!'
