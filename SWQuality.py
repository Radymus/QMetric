# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""

import pandas
import os
import pprint
#import logging
import re



class ProjectQuality(object):
    """This class take like argumet path to the project and data
       from subversion system. This data evaulation and walk truth
       and return data for vizualization.
    """


    def __init__(self, path, subversion_data):
        """Inicialization variables for path and subversion data and rc file
            for pylint.
        """
        self._path = path
        self.subver_data, self.commits = subversion_data
        pprint.pprint(self.commits)
        self.return_data = None
        #test for existion rcfile for pylint
        if not os.path.exists("/tmp/rc"):
            os.system("pylint --generate-rcfile > /tmp/rc")
        self.__rc_file = os.getcwd()+"/rc"
        self.quality = {}
        self.quality["files"] = []
        self.quality["paths"] = []
        self.pylint_eval = []
        self.rating = []
        self.get_structure()


    def get_structure(self):
        """This method create dictionary of files in the project."""
        dirpaths, dirnames, files = [], [], []
        for dirpath, dirname, filee in os.walk(self._path):
            if filee != []:
                for fil in filee:
                    if re.search(r".*\.py", fil) is not None:
                        self.quality["files"].append(filee)
                        self.quality["paths"].append(dirpath)
                        self.evaluate(dirpath+"/"+fil)
            dirpaths.append(dirpath)
            dirnames.append(dirname)
            files.append(filee)


    def find_rating(self, file_html):
        """This method walk truth file and find rating."""
        str_rating = r"Your code has been rated at ([-\d\.]+)\/10 "
        str_rating += r"\(previous run: ([\d\.]+)\/10.*"
        re_rating = re.compile(str_rating)
        tmp_rating = {}
        with open("/tmp/tmp_pylint.html") as fname:
            for line in fname:
                frating = re_rating.search(line)
                if frating is not None:
                    tmp_rating[file_html] = {}
                    tmp_rating[file_html]["actual_rated"] = frating.group(1)
                    tmp_rating[file_html]["previous_rated"] = frating.group(2)
                   # tmp_rating[file_html]["change"] = found_rating.group(3)
        self.rating.append(tmp_rating)


    def evaluate(self, filee):
        """This method evaulation data"""
        print filee
        if type(filee) == []:
            for item in filee:
                os.system("pylint --output=html "+item+" > \
             /tmp/tmp.html")
                tmp_df = pandas.read_html("/tmp/tmp_pylint.html")
                self.pylint_eval.append(tmp_df)
                self.find_rating(item)
        else:
            os.system("pylint --rcfile=/tmp/rc --output=html "+filee+" > \
             /tmp/tmp_pylint.html")
            tmp_df = pandas.read_html("/tmp/tmp_pylint.html")
            self.pylint_eval.append(tmp_df)
            self.find_rating(filee)
        #pprint.pprint(tmp_df[0])
        #pprint.ppirnt(self.rating)
