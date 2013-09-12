#!/usr/bin/python
from mi.client.utils import _
from mi.client.utils.magicstep import magicstep
from mi.client.utils import logger, magicpopup, xmlgtk
from mi.utils.miconfig import MiConfig
from xml.dom.minidom import parseString
import os
import gtk
CF = MiConfig.get_instance()

class DoPartition(magicstep):
    '''
    commit the partiton info to change partiton on disk really
    '''
    NAME = 'dopartition'
    LABEL = _('Do Partition')
    def __init__(self, sself):
        magicstep.__init__(self, sself, 'dopartition.xml', 'dopartition')
        if sself is None:
            return
        self.sself = sself
        self.doparted = False
        self.add_action = self.rootobj.tm.add_action
        
    def get_label(self):
        return self.LABEL
    
    def enter(self):
        self.sself.btnback_sensitive(False)
        self.sself.btnnext_sensitive(False)
        self.name_map['pfprog'].set_fraction(0)

        self.name_map['frame_parted'].set_sensitive(True)
        self.rootobj.tm.push_progress(self.name_map['pfprog'],
                                      self.name_map['pfname'])
        
        CF.G.mount_all_list = []
        for devpath in CF.G.all_part_infor.keys():
            for part_tuple in CF.G.all_part_infor[devpath]:
                if part_tuple[7] == '':
                    # :) This mountpoint is not the obsolete "mountpoint", 
                    # which was used by mount every device, removed already, please view the source in magicinstaller1
                    # Note: this mountpoint is point by user at create partition step, / /usr /home and so on.
                    continue
                mntpoint = part_tuple[7]
                devfn = '%s%d' % (devpath, part_tuple[0])
                fstype = part_tuple[6]
                CF.G.mount_all_list.append((mntpoint, devfn, fstype))
        CF.G.mount_all_list.sort(self.malcmp)
        logger.info('CONF.RUN.g_mount_all_list: %s\n' % str(CF.G.mount_all_list))
            
        self.add_action(_('Get all dirty disk'),
                        self.act_parted_get_dirty_result, None,
                        'get_all_dirty_disk', 0)
        return 1
    
    def leave(self):
        if not self.doparted:
            self.doparted = True
            self.sself.btnnext_sensitive(False)
            self.act_start_parted()
            return 0
        else:
            self.sself.btnnext_sensitive(True)
            self.sself.start_install()
            return 1

    def act_parted_get_dirty_result(self, tdata, data):
        self.dirty_disks = tdata
        self.format_list = []
        for devpath in CF.G.all_part_infor.keys():
            for part_tuple in CF.G.all_part_infor[devpath]:
                if part_tuple[5] == 'true': # format_or_not
                    self.format_list.append((devpath,
                                             part_tuple[3], # start
                                             part_tuple[6], # ftype
                                             part_tuple[0])) # partnum
        self.fill_all_info()
        self.name_map['pfprog'].set_fraction(1)
        # We get all information, and commit dirty partition and format can be do.
        self.sself.btnnext_sensitive(True)
        logger.info('self.dirty_disks: %s\n' % str(self.dirty_disks))
        logger.info('self.format_list: %s\n' % str(self.format_list))
        
    def fill_all_info(self):
        pkg_frame = self.id_map['pkg_frame']
        dirty_frame = self.id_map['dirty_frame']
        format_frame = self.id_map['format_frame']
        tgtsys_frame = self.id_map['tgtsys_frame']

        def gen_table(info_list):
            docstr = '''
            <hbox expand="true" fill="true" margin="4">
            <vbox expand="true" fill="true" margin="4">
            <tableV2  margin="5">
            '''
            for k, v in info_list:
                docstr += '''
                <tr>
                    <td><hbox fill="true"><label text="%-40s" /></hbox></td>
                    <td><hbox><label text="%s" /></hbox></td>
                </tr>
                ''' % (k, v)
            docstr += '''
            </tableV2>
            </vbox>

            </hbox>
            '''
            return parseString(docstr)
        
        # Package Information
        info_list = []
        for (pafile, dev, fstype, reldir, isofn) in [CF.G.choosed_patuple, ]:
            if isofn != '':
                info_list.append((isofn, os.path.join(dev, isofn)))
            else:
                info_list.append((isofn, os.path.join(dev, reldir)))
        pkg_table = gen_table(info_list)
        
        # Dirty Disk
        info_list = []
        for disk in self.dirty_disks: # ['/dev/sda']
            info_list.append((disk, ""))
        dirty_table = gen_table(info_list)
        
        # Format Partition
        info_list = []
        for (devpath, start, ftype, partnum) in self.format_list: # [('/dev/sda', 935649280, 'ext3', 3)]
            info_list.append(('%s%s' % (devpath, partnum), _('Filesystem type: %s') % ftype))
        format_table = gen_table(info_list)
        
        # target system partition
        info_list = []
        for mntpoint, devfn, fstype in CF.G.mount_all_list:
            info_list.append( (_('Mount point: %s') % mntpoint, _('Device info: %s %s') %(devfn, fstype)) )
        tgtsys_table = gen_table(info_list)
        
        for table, frame in ((pkg_table, pkg_frame), (dirty_table, dirty_frame), 
                             (format_table, format_frame), (tgtsys_table, tgtsys_frame)):
            xmlwidget = xmlgtk.xmlgtk(table)
            frame.add(xmlwidget.widget)
        
    def act_start_parted(self):
        self.act_parted_commit_start(0)

    def act_parted_commit_start(self, pos):
        if pos < len(self.dirty_disks):
            actinfor = _('Write the partition table of %s.')
            actinfor = actinfor % self.dirty_disks[pos]
            self.add_action(actinfor, self.act_parted_commit_result, pos,
                            'commit_devpath', self.dirty_disks[pos])
        else:
            self.act_parted_format_start(0)

    def act_parted_commit_result(self, tdata, data):
        result = tdata
        if result:
            # Error occurred. Stop it?
            logger.error('commit_result ERROR: %s\n' % str(result))
        self.act_parted_commit_start(data + 1)

    def malcmp(self, c0, c1):
        if c0[0] < c1[0]:    return -1
        elif c0[0] > c1[0]:  return 1
        return 0

    def act_parted_format_start(self, pos):
        if pos < len(self.format_list):
            actinfor = 'Formating %s on %s%d.'
            actinfor = actinfor % (self.format_list[pos][2],
                                   self.format_list[pos][0],
                                   self.format_list[pos][3])
            logger.info('format_start: %s\n' % str(actinfor))
            self.add_action(actinfor, self.act_parted_format_result, pos,
                            'format_partition',
                            self.format_list[pos][0], # devpath.
                            self.format_list[pos][1], # part_start.
                            self.format_list[pos][2]) # fstype
        else:
            self.act_end_parted()

    def act_parted_format_result(self, tdata, data):
        result = tdata
        class CallBack():
            def __init__(self, cb):
                self.cb = cb
            def ok_clicked(self, widget, data):
                self.cb()
                
        if result:
            # Error occurred. Stop it?
            # Yes, we should stop it, and we should stop at mount failed place too.
            # TOOD: we should give a stop option too.
            logger.info('format_result ERROR: %s\n' % str(result))
            call_back = CallBack(lambda : self.act_parted_format_start(data + 1))
            magicpopup.magicmsgbox(call_back, _('Format Partition Error: %s' % result),
                       magicpopup.magicmsgbox.MB_ERROR,
                       magicpopup.magicpopup.MB_OK)
            #self.rootobj.btnback_do()
        else:
            self.act_parted_format_start(data + 1)

    def act_end_parted(self):
        self.rootobj.tm.pop_progress()
        self.name_map['pfname'].set_text('')
        self.name_map['pfprog'].set_fraction(1)
        self.name_map['frame_parted'].set_sensitive(False)
        
        self.sself.btnnext_clicked(None, None)
        
def TestMIStep_dopartition():
    from mi.client.tests import TestRootObject
    obj = TestRootObject(DoPartition)
    obj.init()
    
    CF.G.choosed_patuple = ('pafile', 'dev', 'fstype', 'reldir', 'isofn')
    obj.xmlgtk_obj.dirty_disks = ['dirty_disk01', 'dirty_disk02']
    obj.xmlgtk_obj.format_list = [('/dev/sda', 935649280, 'ext3', 3), ('/dev/sdb', 935649280, 'ext4', 4)]
    CF.G.mount_all_list = [('/', 'devfn', 'fstype'), ('/', 'devfn1', 'fstype1')]
    
    obj.xmlgtk_obj.fill_all_info()
    
    obj.main()
    
if __name__ == '__main__':
    TestMIStep_dopartition()
    
