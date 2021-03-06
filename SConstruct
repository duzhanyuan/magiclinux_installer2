### -*- python -*-
# Copyright (C) 2010, zy_sunshine.
# Author:   zy_sunshine <zy.netsec@gmail.com>
# All rights reserved.

import sys
import os
import types

### Command line and Config
#get specdir
specdir = ARGUMENTS.get('specdir', 'spec')
if specdir != '':
    sys.path.insert(0, specdir)
sys.path.insert(0, 'scripts')

import mi_config
mi_config.specdir = specdir
mi_config.sifile = os.path.join(specdir, 'specinfo.py')

#check rpmtype
if mi_config.pkgtype not in ['rpm', 'tar']:
    print "Only rpm and tar are supported in pkgtype."
    sys.exit(1)

#get pkgdirs
for pd in mi_config.pkgdirs.split(':'):
    if not os.path.isdir(pd):
        print "%s is not a directory" % pd
        sys.exit(1)

#get debug option
debugopts = ARGUMENTS.get('debug', None)
if debugopts:
    debugopts = string.split(debugopts, ':')
else:
    debugopts = []
mi_config.debugopts = debugopts

### Base Environment
env = Environment()
for k in mi_config.__dict__:
    if k[:2] != '__' and type(mi_config.__dict__[k]) \
        in (types.BooleanType, types.IntType, types.StringType):
        env[k] = mi_config.__dict__[k]

### Scon Utils
def depInstallExcludeSvn(env, alias, destdir, srcdirs):
    def getAllExcludeSvnFile(dir):
        svndirs = []
        allfiles = []
        excludesvnfiles = []
        topdown = True
        for root, dirs, files in os.walk(dir, topdown):
            for d in dirs:
                if d == '.svn':
                    svndirs.append(os.path.join(root, d))
            for f in files:
                allfiles.append(os.path.join(root, f))
        for f in allfiles:
            issvn = False
            for svndir in svndirs:
                if f.startswith(svndir):
                    issvn = True
                    break
            if not issvn:
                excludesvnfiles.append(f)
        return excludesvnfiles

    for srcd in srcdirs:
        files = []
        if not os.path.isdir(srcd):
            # Omit the file, Only deal with directory.
            continue
        else:
            files = getAllExcludeSvnFile(srcd)
        for f in files:
            related_dir = os.path.dirname(f)
            env.Alias(target=alias, 
                    source=env.Install(os.path.join(destdir,related_dir), f))

def depInstall(env, alias, destdir, files):
    env.Alias(target=alias, source=env.Install(destdir, files))

def depInstallAs(env, alias, destfile, file):
    env.Alias(target=alias, source=env.InstallAs(destfile, file))

def depPyModule(env, alias, dir, sofile, cfiles):
    sopath = os.path.join(mi_config.destdir, mi_config.pythondir, 'site-packages', sofile)
    env.Command(sopath, ['setup.py'] + cfiles,
                ['cd %s; %s setup.py install --prefix=%s/usr' % \
                 (dir, mi_config.pythonbin, mi_config.pyextdir)])
    env.Alias(alias, sopath)
    #env.Depends(alias, sopath)

# python compiler
def pycompiler(source, target, env):
    import py_compile
    for src in source:
        py_compile.compile(str(src))
pycbuilder = Builder(action=pycompiler)
env['BUILDERS']['PYCBuilder'] = pycbuilder

##### Common Function and Class.
def DirValue(dir_or_list, env=env):
    def file_stat(arg, dirname, namelist):
        namelist.sort()
        for name in namelist:
            fullname = os.path.join(dirname, name)
            lst = os.lstat(fullname)
            arg.append((fullname, lst.st_size, lst.st_mtime))
            #arg.append((fullname, lst.st_mode, lst.st_dev,
            #            lst.st_uid, lst.st_gid, lst.st_size, lst.st_mtime))
    if type(dir_or_list) is types.ListType:
        dir_list = dir_or_list
    else:
        dir_list = [dir_or_list]
    dir_value = []
    for dir in dir_list:
        os.path.walk(dir, file_stat, dir_value)
    return env.Value(dir_value)

### Scon Maker
import PkgMaker

class MiPkgMaker(PkgMaker.BinPkgMaker):
    source_prefix = '#bindir/src'
    build_root = mi_config.devrootdir
    pack_prefix = '#bindir'

def getSudoSh(cmd):
    if os.getuid() != 0:
        return 'sudo sh -c "%s" $sudoprom' % cmd
    else:
        return cmd

Export('env')
Export('mi_config')
Export('depInstall', 'depInstallAs', 'depPyModule', 'depInstallExcludeSvn')
Export('DirValue')
Export('PkgMaker', 'MiPkgMaker')
Export('getSudoSh')

##### Construct the magicinstaller main application, tar into :
#       #bindir/root.src.tar.gz         (source file)
#       #bindir/root.src.etc.tar.gz     (config file)
#       needed by rootfs .
SConscript('SConstruct-mi')

##### Construct the mirootfs, tar into :
#       #bindir/mirootfs.gz
#       #bindir/mi-vmlinuz-x.xx.xx
SConscript('SConstruct-rootfs')

##### Construct the target iso file, need :
#       #bindir/mi-vmlinuz-x.xx.xx      (kernel file)
#       #bindir/mirootfs.gz             (initrd file)
SConscript('SConstruct-iso')

