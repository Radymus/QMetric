# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""
import pandas
from gittle import Gittle, InvalidRemoteUrl
import re
import logging
import pprint
import multiprocessing as multiproc
import datetime
#import json

class GitData(object):
    """ This class is for getting contribution, users and other data from Git
    repository.
    """
    def __init__(self, git_path):
        self.__tmp_repository = "/tmp/tmp_repository_"
        self.__tmp_repository += (datetime.datetime.now().isoformat())
        self._data_frame = None
        self._commits_dict = {}
        tmp_dict = [{
              "file":"__init",
              "line":-1,
              "author":"__init",
              "sha":"__init",
              "count": -1,
              "range": -1,
              "rating": -4,
              #"final_num_lines": final,
             # "prev_num_lines": prev,
              "flag":False,
              }]
        self.commit_rating = pandas.DataFrame(tmp_dict)
        self.comm_list = []
        #self.commit_rating = pandas.DataFrame()
        self.git_repository = git_path
        str_url = r"(.+:)(.*)(\.git)"
        git_url = re.compile(str_url)
        is_url = git_url.search(git_path)
        self.commits = {}
        if is_url is None:
            print "Must end .git i will add manualy"
            self.git_repository += ".git"
        try:
            Gittle.clone(self.git_repository, self.__tmp_repository)
        except InvalidRemoteUrl:
            logging.error("Could not clone repository!")
            return None
        self.__repository = Gittle(self.__tmp_repository)
        self.__fill_data()

    def return_repository_path(self):
        """ This method returns path to tmo repository"""
        return self.__tmp_repository

    def __get_data_from_df(self, what, data_frame, index="name"):
        """ This method just walk trought nested data frame and fill
	    new data frame.
	  """
        tmp_val = [idx[index] for idx in data_frame[what]]
        self._data_frame[what] = tmp_val
    def __call__(self, dict_params):
        """Call method."""
        self.walk_diff(dict_params)
    def __del__(self):
        print "///// Destructor /////"
    def __fill_data(self):
        """ This method fill and parsing data to DataFrame."""
        tmp_df = pandas.DataFrame(self.__repository.commit_info())
        self._data_frame = pandas.DataFrame(tmp_df.sha, columns=["sha"])
        self._data_frame["description"] = tmp_df.description
        self._data_frame["message"] = tmp_df.message
        self._data_frame["summary"] = tmp_df.summary
        self._data_frame["time"] = tmp_df.time
	#print tmp_df
	#self._data_frame["timezone"] = tmp_df.timezone
        self.__get_data_from_df("author", tmp_df)
        self.__get_data_from_df("committer", tmp_df)
        commit, files, lines = [], [], []
        index = 0
        try:
            array = self.__repository.branch_walker("master")
            master_branch = [sha.id for sha in array]
        except:
            logging.warning("This repository dont have master branch")
            master_branch = tmp_df.sha
        list_params = []
        app = list_params.append
       # num_proces = 0
        for idx in master_branch:
            #self._commits_dict[idx] = {}
            diff = self.__repository.diff(idx)
            rang = len(diff)
            dict_params = {"idx":idx, "diff":diff, "range":rang, "index":index}
            app(dict_params)
        self.walk_diff(list_params)
            #self.walk_diff(dict_params)
            #pool = multiproc.Process(target=self.walk_diff, args=[dict_params])
            #pool.start()
            #pool.join()
           # list_params.append(dict_params)
            #num_proces += 1
            #self.walk_diff(dict_params)
            #thread = threading.Thread(target=self.walk_diff, args=[dict_params])
            #thread.start()


    def walk_diff(self, list_params):
        str_pattern = r'@@ ([-\+\d]+),([-\+\d]+) ([-\+\d]+),([-\+\d]+) @@'
        line_pattern = re.compile(str_pattern)
        counter_lines = re.compile('\n(\-| )(.*)')
        #l_params = []
        #append = l_params.append
        for params in list_params:
            for indx in range(params["range"]):
                params["index"] += 1
                tmp_commit = params["diff"][indx]["diff"]
                line = line_pattern.findall(tmp_commit)
                found_line = counter_lines.findall(tmp_commit)
                counter = len(found_line)-1
                fname = params["diff"][indx]["new"]["path"]
                if fname == '':
                    fname = params["diff"][indx]["old"]["path"]
                for group in line:
                     #       print group[1]
                    start_line = abs(int(group[1]))
                    list_lines = [num+start_line for num in range(counter)]
                    dict_params = {"idx":params["idx"],
                                   "index":params["index"],
                                    "fname":fname,
                                    "lines":list_lines
                                }
                   # append(dict_params)
                    self.add_commits(dict_params)
                #self.add_commits(dict_params)

    def get_lines(self, list_params):
        """Try optimalized searchnig..."""
        rating = 1
        flag = False
        count = 1
        list_df = []
        append = list_df.append
        for params in list_params:
            for line in params["lines"]:
                rang = params["index"]
                tmp_dict = {
                  "file":params["fname"],
                  "line":line,
                  "author":self.find_author_by_sha(params["idx"]),
                  "sha":params["idx"],
                  "count": count,
                  "range": rang,
                  "rating": rating,
                  "flag":flag,
                  }
                append(tmp_dict)
        self.commit_rating = pandas.DataFrame(list_df)
        length = len(self.commit_rating)
        for index in range(length):
            try:
                count = self.commit_rating[(self.commit_rating.file == params["fname"])
                        & (self.commit_rating.line == line)
                        & (self.commit_rating.count > 1)
                        & (self.commit_rating.index > index)].values[0][1]
                _rang = self.commit_rating[(self.commit_rating.file == params["fname"])
                        & (self.commit_rating.line == line)
                        & (self.commit_rating.count > 1)
                        & (self.commit_rating.index > index)].values[0][5]
                #print count, _rang
                count = int(count)+1
            except IndexError:
                count = 1
                _rang = 0
            try:
                flag = self.commit_rating[(self.commit_rating.file == params["fname"])
                       & (self.commit_rating.line == line)
                       & (self.commit_rating.sha == params["idx"])
                       & (self.commit_rating.index > index)].values[0][3]#.values flag
            except IndexError:
                flag = False
            rang = params["index"] - _rang
            if rang <= 20 and rang > 1 and flag:
                rating = -3
                flag = True
            elif rang > 20 and rang <= 30 and flag:
                rating = -2
                flag = True
            elif rang > 30 and rang <= 40 and flag:
                rating = -1
                flag = True
            elif rang > 40 and rang <= 50 and flag:
                rating = 0
                flag = False
            else:
                rating = 1
                flag = False

            tmp_dict = {
              "file":params["fname"],
              "line":line,
              "author":self.find_author_by_sha(params["idx"]),
              "sha":params["idx"],
              "count": count,
              "range": rang,
              "rating": rating,
              "flag":flag,
              }
            self.comm_list.append(tmp_dict)

    def add_commits(self, params):
        """Method for evaluation the commits. Add one line to dataFrame.
        """
        #for params in list_params:
        for line in params["lines"]:
            try:
                count = self.commit_rating[(self.commit_rating.file == params["fname"])
                        & (self.commit_rating.line == line)
                        & (self.commit_rating.count > 1)].values[0][1]
                _rang = self.commit_rating[(self.commit_rating.file == params["fname"])
                        & (self.commit_rating.line == line)
                        & (self.commit_rating.count > 1)].values[0][5]
                #print count, _rang
                count = int(count)+1
            except IndexError:
                count = 1
                _rang = 0
            try:
                flag = self.commit_rating[(self.commit_rating.file == params["fname"])
                       & (self.commit_rating.line == line)
                       & (self.commit_rating.sha == params["idx"])].values[0][3]#.values flag
            except IndexError:
                flag = False
            rang = params["index"] - _rang
            if rang <= 20 and rang > 1 and flag:
                rating = -3
                flag = True
            elif rang > 20 and rang <= 30 and flag:
                rating = -2
                flag = True
            elif rang > 30 and rang <= 40 and flag:
                rating = -1
                flag = True
            elif rang > 40 and rang <= 50 and flag:
                rating = 0
                flag = False
            else:
                rating = 1
                flag = False

            tmp_dict = {
              "file":params["fname"],
              "line":line,
              "author":self.find_author_by_sha(params["idx"]),
              "sha":params["idx"],
              "count": count,
              "range": rang,
              "rating": rating,
              "flag":flag,
              "timestamp":self.find_time_by_sha(params["idx"]),
              }
            #self.comm_list.append(tmp_dict)
            self.commit_rating = self.commit_rating.append(tmp_dict, ignore_index=True)

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
        return (self._data_frame, self.commit_rating)
#if __name__ == "__main__":
    #git_data = GitData("/tmp/temporary_git_repository")
    #df = git_data.data_frame_project()
