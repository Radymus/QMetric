# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""

import pandas
import os
import pprint
import logging
import re
import multiprocessing as multiproc
from sets import Set

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
        self.git_data = subversion_data
        self.subver_data, self.files = subversion_data.get_git_data()
        #pprint.pprint(self.files)
        print self.files.keys()
        #print self.files["gittle/utils/urls.py"]
        self.return_data = None
        #test for existion rcfile for pylint
        if not os.path.exists("/tmp/rc"):
            os.system("pylint --generate-rcfile > /tmp/rc")
        self.__rc_file = os.getcwd()+"/rc"
        self.quality = {}
        self.quality["files"] = []
        self.quality["paths"] = []
        self.pylint_rating = {}
        self.pylint_eval = []
        self.rating = []
        self.get_structure()
        print self.pylint_rating

    def get_structure(self):
        """This method create dictionary of files in the project."""
        dirpaths, dirnames, files = [], [], []
        for dirpath, dirname, filee in os.walk(self._path):
            if filee != []:
                for fil in filee:
                    if re.search(r".*\.py", fil) is not None:
                        self.quality["files"].append(filee)
                        self.quality["paths"].append(dirpath)
                        #pool = multiproc.Process(target=self.eval_file_in_history, \
                        #args=[fil])
                        #pool.start()
                        #pool.join()
                        #self.evaluate(dirpath+"/"+fil)
                        self.eval_file_in_history(dirpath+"/"+fil)
            dirpaths.append(dirpath)
            dirnames.append(dirname)
            files.append(filee)


    def find_rating(self, file_html, sha):
        """This method walk truth file and find rating."""
        str_rating = r"Your code has been rated at ([-\d\.]+)\/10 "
        str_rating += r"\(previous run: ([\d\.]+)\/10.*"
        re_rating = re.compile(str_rating)
        tmp_rating = {}
        print self.git_data.find_time_by_sha(sha)
        with open("/tmp/tmp_pylint.html") as fname:
            for line in fname:
                frating = re_rating.search(line)
                if frating is not None:
                    tmp_rating["actual_rated"] = frating.group(1)
                    tmp_rating["previous_rated"] = frating.group(2)
                    tmp_rating["time"] =self.git_data.find_time_by_sha(sha)
                    tmp_rating["sha"] = sha
                    #tmp_rating[file_html]["change"] = found_rating.group(3)
        #self.rating.append(tmp_rating)
                    if self.pylint_rating.has_key(file_html):
                        self.pylint_rating[file_html].append(tmp_rating)
                    else:
                        self.pylint_rating[file_html] = []
                        self.pylint_rating[file_html].append(tmp_rating)

    def get_file(self, filee):
        """This method returns list of sha for file from df."""
        #print filee

        fil = filee.split(self._path+"/")
        #print fil, fil[1]
        try:
            files = self.files[fil[1]]["sha"].values
            return files
        except KeyError:
            logging.warning("This file %s is not in dataframe."%(fil[1]))
            return []

    def eval_file_in_history(self, filee):
        """This method take file and eval this file by history of commits."""
        files = self.get_file(filee)
        #print files
        if files != []:
            sets = Set(files)
            list_sha = list(sets)
            #print list_sha
            self.evaluate(filee, list_sha)
    def eval_pylint(self, filee, sha):
        """Call pylint for file"""
        os.system("pylint --rcfile=/tmp/rc --output=html "+filee+" > \
             /tmp/tmp_pylint.html")
        tmp_df = pandas.read_html("/tmp/tmp_pylint.html")
        self.pylint_eval.append(tmp_df)
        self.find_rating(filee, sha)

    def evaluate(self, filee, sha):
        """This method evaulation data"""
        #print filee, sha
        for item in sha:
            print item
                #self.git_data.rollback(item)
            self.eval_pylint(filee, item)
        #if type(filee) == []:
         #   for item in filee:
          #      self.eval_pylint(item, sha)
           # else:
            #    self.eval_pylint(filee, sha)

        #pprint.pprint(tmp_df[0])
        #pprint.ppirnt(self.rating)
