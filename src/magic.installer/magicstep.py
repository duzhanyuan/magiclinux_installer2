#!/usr/bin/python
# Copyright (C) 2003, Charles Wang.
# Author:  Charles Wang <charles@linux.net.cn>
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANT; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public LIcense for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, 59 Temple
# Place - Suite 330, Boston, MA 02111-1307, USA.


import gtk
from gettext import gettext as _
from xml.dom.minidom import parse, parseString
import os

import xmlgtk
import magicpopup

from mipublic import hotfixdir, search_file

class magicstep (xmlgtk.xmlgtk):
    def __init__(self, rootobj, uixml_file, uirootname=None):
        self.rootobj = rootobj

        # magic.installer-->btnnext_do() will remove these classname from steps.
        # Added by zy_sunshine
        self.skip_stepnames = []
        
        self.values = rootobj.values.documentElement # Just a short cut.
        self.uixml_path = search_file(uixml_file,
                                 [hotfixdir, '.'],
                                 postfix = 'UIxml')
        uixml = parse(self.uixml_path)
        ### hack to add a debug title
        rootnode = None
        if not uirootname:
            uixml_rootnode = uixml.documentElement
        else:
            uixml_rootnodes = uixml.getElementsByTagName(uirootname)
            if uixml_rootnodes == []:
                uixml_rootnode = uixml.documentElement
            else:
                for uixml_rootnode in uixml_rootnodes[0].childNodes:
                    if uixml_rootnode.nodeType == uixml_rootnode.ELEMENT_NODE:
                        break
        newdom = parseString('<vbox margin="4"><label name="dbgmsg" line_wrap="true" fill="true" text="test label"/></vbox>').documentElement
        uixml_rootnode.appendChild(newdom)
        xmlgtk.xmlgtk.__init__(self, uixml, uirootname)
        self.fill_values(self.values)
        self.stepid = None
        self.confdir = ''
        self.pypath = ''
        
    def init(self):
        print 'init %d' % self.stepid
        if self.stepid > 0 and self.confdir:
            preconf = os.path.join(self.confdir, 'step%s.xml' % (self.stepid - 1))
            if os.path.exists(preconf):
                self.values = parse(preconf).documentElement

        self.name_map['dbgmsg'].set_text('step %d ui: %s py: %s' % (self.stepid,
                self.uixml_path, self.pypath))
        
    def fini(self):
        print 'fini %d' % self.stepid
        curconf = os.path.join(self.confdir, 'step%s.xml' % self.stepid)
        print curconf
        f = open(curconf, 'w')
        self.values.ownerDocument.writexml(f)
        f.close()
        
    
    def get_label(self):
        return _("UNDEFINED")

    def default_btnhelp_clicked(self, widget, data, filename):
        magicpopup.magichelp_popup(filename)

    def default_btncancel_clicked(self, widget, data):
        self.rootobj.tm.add_action('Quit', None, None, 'quit', 0)

    # Define the 'btnback_clicked' will display the 'Back' button.
    #def btnback_clicked(self, widget, data):
    # Return true, it will switch to the previous step, otherwise nothing happend.

    # Define the 'btnnext_clicked' will display the 'Next' button.
    #def btnnext_clicked(self, widget, data):
    # Return true, it will switch to the next step, otherwise nothing happend.

    def default_btnfinish_clicked(self, widget, data):
        self.rootobj.tm.add_action('Quit', None, None, 'quit', 0)

class magicstepgroup (magicstep):
    def __init__(self, rootobj, uixml_file, substep_list, uirootname=None):
        magicstep.__init__(self, rootobj, uixml_file, uirootname)
        self.substep_list = substep_list
        self.substep = substep_list[0]

    def subswitch(self, substep):
        if substep != self.substep:
            self.name_map[self.substep].hide()
            self.name_map[substep].show()
            if hasattr(self, 'switch_%s_%s' % (self.substep, substep)):
                eval('self.switch_%s_%s()' % (self.substep, substep))
            self.substep = substep

    def enter(self):
        if hasattr(self, 'check_enter_%s' % self.substep):
            return eval('self.check_enter_%s()' % self.substep)
        # Always switch to substep_list.
        self.subswitch(self.substep_list[0])
        return 1

    def leave(self):
        if hasattr(self, 'check_leave_%s' % self.substep):
            return eval('self.check_leave_%s()' % self.substep)
        return 1

    def btnback_clicked(self, widget, data):
        if hasattr(self, 'check_leave_%s' % self.substep):
            if not eval('self.check_leave_%s()' % self.substep):
                return 0
        if self.substep == self.substep_list[0]:
            return 1
        prevstep = ''
        for curstep in self.substep_list:
            if curstep == self.substep:
                break
            prevstep = curstep
        if hasattr(self, 'check_enter_%s' % prevstep):
            if not eval('self.check_enter_%s()' % prevstep):
                return 0
        self.subswitch(prevstep)
        return 0

    def btnnext_clicked(self, widget, data):
        nextstep = ''
        if hasattr(self, 'check_leave_%s' % self.substep):
            if not eval('self.check_leave_%s()' % self.substep):
                return 0
        if self.substep == self.substep_list[-1]:
            return 1
        if hasattr(self, 'get_%s_next' % self.substep):
            nextstep = eval('self.get_%s_next()' % self.substep)
            if not nextstep:
                return 1 # Go to next toplevel-step.
        else:
            # Get next step. Notice nextstep variable is not a local var.
            curstep = ''
            for nextstep in self.substep_list:
                if curstep == self.substep:
                    break
                curstep = nextstep
        if hasattr(self, 'check_enter_%s' % nextstep):
            if not eval('self.check_enter_%s()' % nextstep):
                return 0
        self.subswitch(nextstep)
        return 0
