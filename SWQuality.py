# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""
from __future__ import division
import pandas
import os
import pprint
import logging
import re

#import multiprocessing as multiproc
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
        print self.git_data
        self.subver_data, self.files = subversion_data.get_git_data()
        #pprint.pprint(self.files)
        #print self.files.keys()
        #print self.files["gittle/utils/urls.py"]
        self.return_data = None
        #test for existion rcfile for pylint
        if not os.path.exists("/tmp/rc"):
            os.system("pylint --generate-rcfile > /tmp/rc")
        self.__rc_file = os.getcwd() + "/rc"
        self.quality = {}
        self.quality["files"] = []
        self.quality["paths"] = []
        self.pylint_rating = {}
        self.pylint_eval = []
        self.rating = {}
        self.get_structure()
        #pprint.pprint(self.pylint_rating)
        self.create_final_structure()
        self.rate()
        self.count_final_rating(dict(count_w=0.1, comm_w=0.1, avg_pylint_w=0.1, pylint_w=0.1))
        pprint.pprint(self.rating)
       # self.rate()
    def create_final_structure(self):
        """Creating of structure for authors."""
        authors = self.subver_data.groupby(["author"])
        for author in authors.groups.keys():
            self.rating[author] = {}
            #if pylint rating was > then prev
            self.rating[author]["pylint+"] = 0
            #if pylint rating was < then prev
            self.rating[author]["pylint-"] = 0
            #most modified file
            self.rating[author]["MMFile"] = ""
            #count commits in MMFile
            self.rating[author]["CCMMFile"] = 0
            #avg of all average of commits
            self.rating[author]["avg_count"] = 0.0
            #count of all average of commits for prev avg_count
            self.rating[author]["count_all_comm"] = 0
            #mean of all rating of commits
            self.rating[author]["avg_comm_rating"] = 0.0
            #final rating
            self.rating[author]["final_rating"] = 0.0
            #list of ratings
            self.rating[author]["pylint"] = []

    def count_final_rating(self, weight):
        """Count final rating"""
        for author in self.rating.keys():
            avg_pylint = (self.rating[author]["pylint+"]-self.rating[author]["pylint-"])
            avg_pylint *= weight["pylint_w"]
            avg_count = self.rating[author]["avg_count"] * weight["count_w"]
            avg_comm = self.rating[author]["avg_comm_rating"] * weight["comm_w"]
            avg_pylint = avg_pylint * weight["avg_pylint_w"]
            avg_list_pylint = sum(self.rating[author]["pylint"])
            if len(self.rating[author]["pylint"]) > 0:
                avg_list_pylint /= len(self.rating[author]["pylint"])
            final = (avg_pylint + avg_count + avg_comm + avg_list_pylint) / 4
            if (final*100) < 100.0:
                self.rating[author]["final_rating"] = final*100
            else:
                self.rating[author]["final_rating"] = 100.0

    def rate(self):
        """This method rate all authors."""
        for fname in self.files.keys():
            count = self.files[fname].groupby("author")
            count_line = self.files[fname].groupby(["author", "line"])
            for author in count_line.groups.keys():
                #if len(count_line.groups[author]) > 0:
                self.rating[author[0]]["count_all_comm"] += 1
                c_line = len(count_line.groups[author])
                count_ = len(count.groups[author[0]])
               # print author[0], c_line, count_,float(c_line/count_)
                self.rating[author[0]]["avg_count"] += float(c_line/count_)
                #print self.rating[author[0]]["avg_count"]
            for author in count.groups.keys():
                self.rating[author]["avg_count"] /= self.rating[author]["count_all_comm"]
                if self.rating[author]["CCMMFile"] < len(count.groups[author]):
                    self.rating[author]["CCMMFile"] = len(count.groups[author])
                    self.rating[author]["MMFile"] = fname
                rat = self.files[fname]
                rat["avg_comm_rating"] = rat[rat.author == author]["rating"].mean()

            #shas = self.files[fname].groupby("sha")
            try:
                #for fil in self.pylint_rating[fname]:
                    #print fil
                for fil in self.pylint_rating[fname]:
                    author = self.git_data.find_author_by_sha(fil["sha"])
                    self.rating[author]["pylint"].append(float(fil["actual_rated"]))
                    if fil["actual_rated"] < fil["previous_rated"]:
                        self.rating[author]["pylint-"] += 1
                    elif fil["actual_rated"] > fil["previous_rated"]:
                        self.rating[author]["pylint+"] += 1
            except KeyError:
                logging.warning("not in pylint_rating")
        #print self.rating

    def get_structure(self):
        """This method create dictionary of files in the project."""
        dirpaths, dirnames, files = [], [], []
        #out = multiproc.Queue()
        #chunksize = multiproc.cpu_count()
        #procs = []
       # lock = multiproc.Lock()
        for dirpath, dirname, filee in os.walk(self._path):
            if filee != []:
                for fil in filee:
                    if re.search(r".*\.py", fil) is not None:
                        #print fil
                        self.quality["files"].append(filee)
                        self.quality["paths"].append(dirpath)
                      #  pool = multiproc.Process(
                      #  target=self.eval_file_in_history,
                       # args=(dirpath + "/" + fil, lock)).start()
                        #procs.append(pool)
                        #pool.start()
                        #pool.start()
                       # pool.close()
                        #pool.join()
                        #self.evaluate(dirpath+"/"+fil)
                        self.eval_file_in_history(dirpath + "/" + fil)
            dirpaths.append(dirpath)
            dirnames.append(dirname)
            files.append(filee)
        #resultdic = {}
        #for i in range(chunksize):
        #    resultdic.update(out.get())
        #for p in procs:
        #    p.join()
        #return resultdic
    def find_rating(self, file_html, sha):
        """This method walk truth file and find rating."""
        str_rating = r"Your code has been rated at ([-\d\.]+)\/10 "
        str_rating += r"\(previous run: ([\d\.]+)\/10.*"
        re_rating = re.compile(str_rating)
        tmp_rating = {}
        #print self.git_data.find_time_by_sha(sha)
        fnm = file_html.replace("/", "_")
        with open("/tmp/tmp_pylint_%s.html" %(fnm)) as fname:
            for line in fname:
                frating = re_rating.search(line)
                if frating is not None:
                    tmp_rating["actual_rated"] = frating.group(1)
                    tmp_rating["previous_rated"] = frating.group(2)
                    tmp_rating["time"] = self.git_data.find_time_by_sha(sha)
                    tmp_rating["sha"] = sha
                    #tmp_rating[file_html]["change"] = found_rating.group(3)
        #self.rating.append(tmp_rating)
                    if file_html in self.pylint_rating:
                        self.pylint_rating[file_html].append(tmp_rating)
                    else:
                        self.pylint_rating[file_html] = []
                        self.pylint_rating[file_html].append(tmp_rating)

    def get_file(self, filee):
        """This method returns list of sha for file from df."""
        #print filee

        fil = filee.split(self._path + "/")
        #print fil, fil[1]
        try:
            files = self.files[fil[1]]["sha"].values
            return files
        except KeyError:
            #logging.warning("This file %s is not in dataframe." % (fil[1]))
            return []

    def eval_file_in_history(self, filee):
        """This method take file and eval this file by history of commits."""
      #  lock.acquire()
        files = self.get_file(filee)
        #print files
        if files != []:
            sets = Set(files)
            list_sha = list(sets)
            #print list_sha
            self.evaluate(filee, list_sha)
        else:
            self.evaluate(filee, [])
       # lock.release()
        #out.put(self.pylint_rating)

    def eval_pylint(self, filee, sha):
        """Call pylint for file"""
        fil = filee.split(self._path + "/")
        fname = fil[1].replace("/", "_")
        os.system("pylint --rcfile=/tmp/rc --output=html " + filee + " > \
             /tmp/tmp_pylint_%s.html" % (fname))
        try:
            tmp_df = pandas.read_html("/tmp/tmp_pylint_%s.html" % (fname))
            self.pylint_eval.append(tmp_df)
            self.find_rating(fil[1], sha)
        except ImportError:
            logging.warning("No html file")

    def evaluate(self, filee, sha):
        """This method evaulation data"""
        #print filee, sha
        if sha == []:
            self.eval_pylint(filee, '')
        else:
            for item in sha:
                #print item
                self.git_data.rollback(item)
                self.eval_pylint(filee, item)
        #if type(filee) == []:
         #   for item in filee:
          #      self.eval_pylint(item, sha)
           # else:
            #    self.eval_pylint(filee, sha)

        #pprint.pprint(tmp_df[0])
        #pprint.ppirnt(self.rating)
