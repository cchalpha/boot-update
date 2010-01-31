#!/usr/bin/python2

import os, sys, commands

from ..extension import Extension
from ..resolver import Resolver
from ..helper import *

r=None

def getExtension(config):
	global r
	r=Resolver(config)
	return GRUBLegacyExtension(config)

class GRUBLegacyExtension(Extension):

	def __init__(self,config):
		self.fn = "/boot/grub/grub.conf"
		self.config = config
		self.bootitems = []

	def isAvailable(self):
		msgs=[]
		ok=True
		return [ok, msgs]

	def generateBootEntry(self,l,sect,kname,kext):
		global r

		ok=True
		allmsgs=[]

		l.append("")
		self.bootitems.append("%s - %s" % ( sect, kname))
		l.append("title %s - %s" % ( sect, kname ))
		
		kpath=r.RelativePathTo(kname,"/boot")
		params=self.config.item(sect,"params")
		if "root=auto" in params:
			params.remove("root=auto")
			rootdev = fstabGetRootDevice()
			if rootdev[0:5] != "/dev/":
				ok = False
				allmsgs.append(["fatal","(root=auto) grub-legacy - cannot find a valid / entry in /etc/fstab."])
				return [ ok, allmsgs ]

			params.append("root=%s" % rootdev )
		
		if "rootfstype=auto" in params:
			params.remove("rootfstype=auto")
			fstype = fstabGetFilesystemOfDevice(myroot)
			if fstype == "":
				ok = False
				allmsgs.append(["fatal","(rootfstype=auto) grub-legacy - cannot find a valid / entry in /etc/fstab."])
				return [ ok, allmsgs ]
			for item in params:
				if item[0:5] == "root=":
					params.append("rootfstype=%s" % fstype)
					break

		if fstabHasEntry("/boot"):
			# If /boot exists, then this is our grub "root" (where we look for boot loader stages and kernels)
			rootfs="/boot"
			rootdev=fstabGetDeviceOfFilesystem(rootfs)
		else:
			# If /boot doesn't exist, the root filesystem is treated as grub's "root"
			rootfs = "/"
			rootdev = None
			for item in params:
				if item[0:5] == "root=":
					rootdev = item[5:]
					break
		if rootdev == None:
			rootdev=fstabGetDeviceOfFilesystem(rootfs)
		if rootdev == "":
			ok = False
			allmsgs.append(["fatal","grub-legacy - root filesystem undefined - update /etc/fstab or pass non-auto root= parameter."])
			return [ ok, allmsgs ]

		# Now that we have the grub root in /dev/sd?? format, attempt to convert it to (hd?,?) format
		if rootdev[0:5] != "/dev/":
			ok = False
			allmsgs.append(["fatal","grub-legacy - %s is not a valid GRUB root - ensure /etc/fstab is correct or specify a root= parameter." % rootdev ] )
			return [ ok, allmsgs ]
		if rootdev[5:7] != "sd":
			allmsgs.append(["warn","grub-legacy - encountered \"%s\", a non-\"sd\" device. Root setting may not be accurate." % rootdev])
		rootmaj = ord(rootdev[7]) - ord('a')
		try:
			rootmin = int(rootdev[8:]) - 1
		except TypeError:
			ok = False
			allmsgs.append(["fatal","grub-legacy - couldn't calculate the root minor for \"%s\"." % rootdev])
			return [ ok, allmsgs ]
		# print out our grub-ified root setting
		l.append("root (hd%s,%s)" % (rootmaj, rootmin ))
		l.append("kernel %s %s" % ( kpath," ".join(params) ))
		initrds=r.FindInitrds(sect, kname, kext)
		for initrd in initrds:
			l.append("initrd %s" % self.command.RelativePathTo(initrd,"/boot"))
		l.append("")

		return [ ok, allmsgs ]

	def generateConfigFile(self):
		l=[]
		c=self.config
		ok=True
		allmsgs=[]
		global r
		l.append(c.condSubItem("boot/timeout", "timeout %s"))
		# pass our boot entry generator function to GenerateSections, and everything is taken care of for our boot entries

		ok, msgs, defpos, defname = r.GenerateSections(l,self.generateBootEntry)
		allmsgs += msgs
		if not ok:
			return [ ok, allmsgs, l ]
		
		if defpos != None:
			l += [ 
				""
				"default %s" % defpos
			]
	
		allmsgs.append(["info","Configuration file %s generated - %s lines." % ( self.fn, len(l))])
		allmsgs.append(["info","Kernel \"%s\" will be booted by default." % defname])

		return [ok, allmsgs, l]
			