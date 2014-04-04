# -*- coding: utf-8 -*-
"""
Created on Thu Apr  3 21:24:06 2014

@author: Radim Spigel
"""
from __future__ import division
#import pandas
import os
import pprint
import logging
import re
from pandas import DataFrame, read_html
from gittle import Gittle, InvalidRemoteUrl
import datetime
from sets import Set
from argparse import ArgumentParser

class QMetric(object):
    """This class take like argumet path to the project and data
       from subversion system. This data evaulation and walk truth
       and return data for vizualization.
    """

    def __init__(self, path):
        """Inicialization variables for path and subversion data and rc file
            for pylint.
        """
        self.vesion_system = self.GitData(path)

        self._path = self.vesion_system.return_repository_path()
        print self._path
        self.subver_data, self.files = self.vesion_system.get_git_data()
        #logging.info(self.subver_data, self.files)
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
        """Count final rating. First i get difference between positive and
        negative rating. Next i get average how many does contributor
        change file/ count all commits to file.
        Another variable is average ratings for commits what this author did
        to file. After that i get average value for every pylint rating for
        all files. Last is total rating which is mean value from this
        variables. For each variables is set weight"""
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
        """
        This method rate all authors. Main function in this method is iterate
        for every lines which every contributor committed to current file. Has
        some statistic variables. One is counter for counting how many commits
        did to file each contributor. Next variable is sum of average how many
        does contributor change file/ count all commits to file. Next variable
        is most modified file and how many commits did contributor done to this
        file. Another variable is mean value of ratings for every commit getting
        in GitData.modificate_rating. Last variable is pylint negative or
        positive result if author decreases pylint rating gets negative evaluate
        if  author increase pylint rating gets positive else gets nothing.
        """
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
                    author = self.vesion_system.find_author_by_sha(fil["sha"])
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
        for dirpath, dirname, filee in os.walk(self._path):
            if filee != []:
                for fil in filee:
                    if re.search(r".*\.py", fil) is not None:
                        self.quality["files"].append(filee)
                        self.quality["paths"].append(dirpath)
                        self.eval_file_in_history(dirpath + "/" + fil)
            dirpaths.append(dirpath)
            dirnames.append(dirname)
            files.append(filee)

    def find_rating(self, file_html, sha):
        """This method walk through file and find rating which is genereted
        from pylint.
        """
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
                    tmp_rating["time"] = self.vesion_system.find_time_by_sha(sha)
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
        """This method take file and eval this file by history of commits
        thanks to method evaluate.
        """
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
            tmp_df = read_html("/tmp/tmp_pylint_%s.html" % (fname))
            self.pylint_eval.append(tmp_df)
            self.find_rating(fil[1], sha)
        except ImportError:
            logging.warning("No html file")

    def evaluate(self, filee, sha):
        """This method call rollback from GitData. This method returns data
        to previous state. Direction is from recent to first commit.
        """
        #print filee, sha
        if sha == []:
            self.eval_pylint(filee, '')
        else:
            for item in sha:
                #print item
                self.vesion_system.rollback(item)
                self.eval_pylint(filee, item)

    class GitData(object):
        """ This class is for getting contribution, users and other data from Git
        repository.
        """

        def __init__(self, git_path):
            self.__tmp_repository = "/tmp/tmp_repository_"
            self.__tmp_repository += (datetime.datetime.now().isoformat())
            self._data_frame = None
            self._commits_dict = {}
            self.files = {}
            self.line_counter = {}
            self.git_repository = git_path
            str_url = r'(git://github.com/|https://github.com/|git@github.com:)(.*)'
            #r"(.+:)(.*)(\.git)"
            git_url = re.compile(str_url)
            is_url = git_url.search(git_path)
            self.commits = {}
            if is_url is None:
                self.__repository = Gittle(self.git_repository)
                self.__tmp_repository = self.git_repository
            else:
                if self.git_repository.find(".git") < 0:
                    logging.info("Must end .git i will add manualy")
                    self.git_repository += ".git"
                try:
                    Gittle.clone(self.git_repository, self.__tmp_repository)
                except InvalidRemoteUrl:
                    logging.error("Could not clone repository!")
                    #return None
                except ValueError:
                    logging.error("Is not url.")
                self.__repository = Gittle(self.__tmp_repository)
            self.__fill_data()
           # print self.files
            self.eval_commits()
            #print self.files["setup.py"]["modification"]

        def eval_commits(self):
            """This method walk through saved items and evaluate rating commits."""
            for inx in self.files.keys():
                group = self.files[inx].groupby(["author", "line"])
                #print group.groups
                for value in group.groups.itervalues():
                    if len(value) > 1:
                        self.modificate_rating(inx, value)
                       # print inx, value
                        #print #group.groups[key]
          #  print self.files["setup.py"]["rating"]

        def modificate_rating(self, fname, index, procent=0.35):
            """In this method i will walk through every saved commited lines.
            This data structure is
            sha1: line1, range, removed, num_lines, modification, rating
            sha1->line2, range, ...
            sha2->line1, range, ...
            etc.
            Direction is from recent commit to first. If is modification one same
            line in other commis i will evaluate how many commits was between them.
            When ihad range between commits and file doesnt change more then
            argument percent then i chose rating. After that, i change rating of
            commit in DataFrame for file in dictionary of files.
            """
            logging.info("Start of evaulation of ratings for each commit.")
            if fname.find(".py") < 0:
                return
            df_file = self.files[fname]
            length = len(index)
            for idx in range(length-1):
                ackt_range = df_file.ix[index[idx]]["range"]
                next_range = df_file.ix[index[idx + 1]]["range"]
                rang =  next_range - ackt_range
                try:
                    fmod = float(df_file.ix[index[idx]]["removed"]) \
                    / float(df_file.ix[index[idx]]["num_lines"])
                    smod = float(df_file.ix[index[idx + 1]]["removed"]) \
                    / float(df_file.ix[index[idx + 1]]["num_lines"])
                except ZeroDivisionError:
                    smod, fmod = 0, 0
                smod += fmod
                #print fname, smod
                if rang <= 20 and rang > 1 and smod < procent:
                    rating = -3
                elif rang > 20 and rang <= 30 and smod < procent:
                    rating = -2
                elif rang > 30 and rang <= 40 and smod < procent:
                    rating = -1
                elif rang > 40 and rang <= 50 and smod < procent:
                    rating = 0
                else:
                    rating = 1
                    if smod >= procent:
                        smod = 0.0
                self.files[fname].ix[index[idx + 1], "modification"] = smod
                self.files[fname].ix[index[idx + 1], "rating"] = rating
            #print self.files[fname]["rating"]
            logging.info("End of evaluation of ratings for every commit.")

        def return_repository_path(self):
            """ This method returns path to tmp repository"""
            return self.__tmp_repository

        def __get_data_from_df(self, what, data_frame, index="name"):
            """ This method just walk trought nested data frame and fill
            new data frame.
            """
            tmp_val = [idx[index] for idx in data_frame[what]]
            self._data_frame[what] = tmp_val

        def __fill_data(self):
            """ This method fill and parsing data to DataFrame."""
            logging.info("Filling data to _data_frame")
            tmp_df = DataFrame(self.__repository.commit_info())
            self._data_frame = DataFrame(tmp_df.sha, columns=["sha"])
            self._data_frame["description"] = tmp_df.description
            self._data_frame["message"] = tmp_df.message
            self._data_frame["summary"] = tmp_df.summary
            self._data_frame["time"] = tmp_df.time
            #print tmp_df
            #self._data_frame["timezone"] = tmp_df.timezone
            self.__get_data_from_df("author", tmp_df)
            self.__get_data_from_df("committer", tmp_df)
            index = 0
            try:
                array = self.__repository.branch_walker("master")
                master_branch = [sha.id for sha in array]
            except ValueError:
                logging.warning("This repository dont have master branch")
                master_branch = tmp_df.sha
            list_params = []
            app = list_params.append
           # num_proces = 0
            logging.info("Go through master branch and using gittle.diff for \
            getting diff output")
            for idx in master_branch:
                #self._commits_dict[idx] = {}
                diff = self.__repository.diff(idx)
                rang = len(diff)
                app(dict(
                        {"idx": idx,
                         "diff": diff,
                         "range": rang,
                         "index": index}
                    ))
                index += 1
            self._trought_diff(list_params)

        def _trought_diff(self, list_params):
            """
            This method for walk through diff from gittle. Found removed lines,
            added lines to file and make difference betwen. Thanks difference
            betwen added and removed we get changed lines. In this method we call
            method for counting lines in file that will be saved to DataFrame with
            changed lines removed lines and sha thanks to method set_lines_df. I
            want only removed lines for my algorithm because in method
            modificate_rating i go through from recent  to first commit.
            """
            str_pattern = r'@@ ([-\+\d]+),([-\+\d]+) ([-\+\d]+),([-\+\d]+) @@'
            line_pattern = re.compile(str_pattern)
            counter_lines = re.compile(r'\n(\-)(.*)')
            add_lines = re.compile(r'\n(\+)(.*)')
            #blank_lines = re.compile(r'\n( )(.*)')
            for params in list_params:
                for indx in range(params["range"]):
                    #params["index"] += 1
                    tmp_commit = params["diff"][indx]["diff"]
                    line = line_pattern.findall(tmp_commit)
                    removed_line = counter_lines.findall(tmp_commit)
                    add_line = add_lines.findall(tmp_commit)
                    removed = len(removed_line) - 1
                    added = len(add_line)  - 1
                    change = (removed - added)
                    fname = params["diff"][indx]["new"]["path"]
                    if fname == '' or fname == None:
                        fname = params["diff"][indx]["old"]["path"]

                    if re.search(r".*\.py", fname) is None:
                        continue
                    lcount = self.count_lines(fname)
                   # lines_count -= removed
                    for group in line:
                         #       print group[1]
                        start_line = abs(int(group[1]))
                        list_lines = [num + start_line for num in range(removed)]
                        if len(list_lines) > 0:
                            df_lines = self.set_lines_df(list_lines, params["idx"], \
                                                params["index"], change, lcount)
                            if fname in self.files:
                                self.files[fname] = self.files[fname]\
                                            .append(df_lines, ignore_index=True)
                            else:
                                self.files[fname] = df_lines
            logging.info("END of walking through the all diffs for this repo.")

        def count_lines(self, fname):
            """This method count lines in file"""
            if not os.path.exists(self.__tmp_repository + "/" + fname):
                return 0
            if fname not in self.line_counter:
                count = 0
                with open(self.__tmp_repository + "/" + fname) as filer:
                    for ix in filer: count += 1
                self.line_counter[fname] = count
            else:
                return self.line_counter[fname]
            return count

        def set_lines_df(self, list_lines, sha, index, removed, line_count):
            """Method return dataframe lines"""
            tmp_list = []
            append = tmp_list.append
            for line in list_lines:
                append(dict(
                            {"line": line,
                            "author": self.find_author_by_sha(sha),
                            "sha": sha,
                            "range": index,
                            "rating": 1,
                            "num_lines": line_count,
                            "removed": abs(removed),
                            "modification": 0.0,
                            "time": self.find_time_by_sha(sha)
                            }
                         ))
           # print tmp_list
            data_frame = DataFrame(tmp_list)
            return data_frame

        def find_author_by_sha(self, sha):
            """This method finds the author by sha in dataFrame. If not found
               return None.
            """
            index = self._data_frame[self._data_frame.sha == sha].index
            try:
                #print self._data_frame.author[index].values[0]
                return self._data_frame.author[index].values[0]
            except IndexError:
                logging.warning("Sha is not in data frame.")
            return None

        def find_time_by_sha(self, sha):
            """This method finds timestamp by sha in dataFrame. If not found
               return None.
            """
            index = self._data_frame[self._data_frame.sha == sha].index
            try:
                #print self._data_frame.author[index].values[0]
                return self._data_frame.time[index].values[0]
            except IndexError:
                logging.warning("Sha is not in data frame.")
            return None

        def rollback(self, sha):
            """This method will make rollback to version which is set by sha."""
            #print "rollback sha %s" % sha
            self.__repository.checkout_all(sha)

        def rollback_to_first_commit(self, files):
            """This method will make rollback to first commit."""
            sha = None
            for idx in self._commits_dict:
                if self._commits_dict[idx]['files'] == files:
                    sha = idx
                    break
            if sha is None:
                return None
            self.rollback(sha)

        def rollback_to_last_commit(self, files):
            """This method will make rollback to first commit."""
            sha = None
            for idx in self._commits_dict:
                if self._commits_dict[idx]['files'] == files:
                    sha = idx
            if sha is None:
                return None
            self.rollback(sha)

        def find_list_files(self, sha):
            """This method returns list of files for current sha hash."""
            try:
                return self._commits_dict[sha]["files"]
            except BaseException:
                logging.warning("Wrong sha hash or there is no file.")
                return None

        def get_git_data(self):
            """ This method returns data frame for project or None. """
            return (self._data_frame, self.files)


if __name__ == "__main__":
    parser = ArgumentParser(description="This program is for\
        evaluation of quality of project based on hypothetical patterns of\
        quality. Like a first argument insert the Git repository which you\
        want to evaluate.")
    parser.add_argument("path", type=str, help="www or path to git\
        repository this choice evaluate project with default settings. \
        This means that in browser will be started webpage with\
        vizualization of quality.")
    QMETRIC = QMetric(parser.parse_args().path)