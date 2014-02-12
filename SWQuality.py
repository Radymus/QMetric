# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""
from pylint.lint import Run
from pylint.reporters.text import TextReporter
import pandas
import os
import logging
import re
class WritebleObject(object):
    "Dummy outpu stream for pylint"
    def __init__(self):
	self.content = []
    def write(self, st):
	"dummy write"
	self.content.append(st)

    def read(self):
	"dummy read"
	return self.content

class ProjectQuality(object):
    """This class take like argumet path to the project and data from subversion
        system. This data evaulation and walk truth and return data for
        vizualization.
    """
    def __init__(self, path, subversion_data):
        """Inicialization variables for path and subversion data and rc file
            for pylint.
        """
        self._path = path
        self.subver_data = subversion_data
        self.return_data = None
        #test for existion rcfile for pylint
        if not os.path.exists(os.getcwd()+"/rc"):
            os.system("pylint generate-rcfile > rc")
        self.__rc_file = os.getcwd()+"/rc"
        self.pylint_output = WritebleObject()
        self.quality = {}
        self.quality["files"] = []
        self.quality["paths"] = []
        self.get_structure()
    def check_type(self,name,path):
        """This method is for check if is type ok."""
        for t in self.__types:
            if re.match(".*\."+t,name):
                self.quality[name] = {}
                self.quality[name]["path"] = path
                self.evaluate(name)

    def get_structure(self):
        """This method create dictionary of files in the project."""
        dirpaths,dirnames,files = [],[],[]
        for dirpath, dirname, filee in os.walk(self._path):
            if filee != []:
                for fil in filee:
                    if re.search(".*\.py",fil) is not None:
                        self.quality["files"].append(filee)
                        self.quality["paths"].append(dirpath)
                        self.evaluate(dirpath+fil)
            #dirpaths.append(dirpath);dirnames.append(dirname)
            #files.append(filee)
        #return (dirpaths,dirnames,files)


    def evaluate(self, files):
        """This method evaulation data"""
        if type(files) == []:
            result = Run(files, reporter=TextReporter(self.pylint_output), exit=False)
        else:
            result = Run([files], reporter=TextReporter(self.pylint_output), exit=False)
        print result



