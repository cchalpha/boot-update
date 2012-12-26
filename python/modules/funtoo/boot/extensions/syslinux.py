# -*- coding: ascii -*-

import os
import shlex

from subprocess import Popen
from subprocess import PIPE
from subprocess import STDOUT

from funtoo.boot.extension import Extension
from funtoo.boot.extension import ExtensionError

def getExtension(config):
	""" Gets the extension based on the configuration """
	return SYSLINUXExtension(config)

class SYSLINUXExtension(Extension):
	""" Implements an extension for the syslinux bootloader """

	def __init__(self, config, testing = False):
		Extension.__init__(self,config)
		self.grubpath =  "{path}/{dir}".format(path = self.config["boot/path"], dir = self.config["syslinux/dir"])
		self.fn = "{path}/{file}".format(path = self.grubpath, file = self.config["syslinux/file"])
		self.bootitems = []
		self.testing = testing
		self.defpos = 0
		self.defname = "undefined"

	def generateOtherBootEntry(self, l, sect):
		""" Generates the boot entry for other systems """
		ok = True
		msgs = []

		# TODO support in the future

		return [ ok, msgs ]

	def generateBootEntry(self, l, sect, kname, kext):
		""" Generates the boot entry """
		ok = True
		allmsgs = []
		mytype = self.config["{s}/type" .format(s = sect)]

		if mytype == "xen":
			# ATM, xen is not supported #
			ok = False
			allmsgs.append([ "fatal", "Type 'xen' is not supported in syslinux" ])
			return [ ok, allmsg ]
		
		l.append("")
		label = self.generateSysLinuxLabel( kname )
		l.append("LABEL {l}".format(l = label))

		# self.bootitems records all our boot items
		self.bootitems.append(label)

		kpath = self.r.StripMountPoint(kname)
		params = self.config["{s}/params".format(s = sect)].split()

		ok, allmsgs, myroot = self.r.DoRootAuto(params, ok, allmsgs)
		if not ok:
			return [ ok, allmsgs ]
		ok, allmsgs, fstype = self.r.DoRootfstypeAuto(params, ok, allmsgs)
		if not ok:
			return [ ok, allmsgs ]

		initrds = self.config.item(sect, "initrd")
		initrds = self.r.FindInitrds(initrds, kname, kext)
		if myroot and ('root=' + myroot) in params and 0 == len(initrds):
			params.remove('root=' + myroot)
			params.append('root=' + self.r.resolvedev(myroot))

		l.append("  KERNEL {k}".format(k = kpath))
		l.append("  APPEND {par}".format(par = " ".join(params)))
		for initrd in initrds:
			l.append("  INITRD {rd}".format(rd = self.r.StripMountPoint(initrd)))

		return [ ok, allmsgs ]

	def generateConfigFile(self):
		l = []
		c = self.config
		ok = True
		allmsgs = []
		# pass our boot entry generator function to GenerateSections,
		# and everything is taken care of for our boot entries

		ok, msgs, self.defpos, self.defname = self.r.GenerateSections(l, self.generateBootEntry, self.generateOtherBootEntry)
		allmsgs += msgs
		if not ok:
			return [ ok, allmsgs, l]

		l = [
			"PROMPT {prompt}".format(prompt = c["syslinux/prompt"]),
			"TIMEOUT {time}".format(time = int(c["boot/timeout"]) * 10 ),
			"DEFAULT {name}".format(name = self.generateSysLinuxLabel( self.defname )) #.replace(" ", "_"))
		] + l

		allmsgs.append(["warn","Please note that SYSLINUX support is *BETA* quality and is for testing only."])

		return [ok, allmsgs, l]
	
	def generateSysLinuxLabel(self, kname):
		""" Generate syslinux LABEL from the given kernel name """
		return os.path.basename(kname)
