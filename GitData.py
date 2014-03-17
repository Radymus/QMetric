# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""
from pandas import DataFrame
from gittle import Gittle, InvalidRemoteUrl
import re
import os
import logging
#import pprint
#import multiprocessing as multiproc
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
                print "Must end .git i will add manualy"
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
        """This method walk trought saved items and evaluate rating commits."""
        for inx in self.files.keys():
            group = self.files[inx].groupby(["author", "line"])
            #print group.groups
            for value in group.groups.itervalues():
                if len(value) > 1:
                    self.modificate_rating(inx, value)
                   # print inx, value
                    #print #group.groups[key]
      #  print self.files["setup.py"]["rating"]
    def modificate_rating(self, fname, index):
        """Modificate rating of commmit."""
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
            if rang <= 20 and rang > 1 and smod < 0.35:
                rating = -3
            elif rang > 20 and rang <= 30 and smod < 0.35:
                rating = -2
            elif rang > 30 and rang <= 40 and smod < 0.35:
                rating = -1
            elif rang > 40 and rang <= 50 and smod < 0.35:
                rating = 0
            else:
                rating = 1
                if smod >= 0.35:
                    smod = 0.0
            self.files[fname].ix[index[idx + 1], "modification"] = smod
            self.files[fname].ix[index[idx + 1], "rating"] = rating
        #print self.files[fname]["rating"]
    def return_repository_path(self):
        """ This method returns path to tmp repository"""
        return self.__tmp_repository

    def __get_data_from_df(self, what, data_frame, index="name"):
        """ This method just walk trought nested data frame and fill
        new data frame.
        """
        tmp_val = [idx[index] for idx in data_frame[what]]
        self._data_frame[what] = tmp_val

    def __del__(self):
        print "///// Destructor /////"

    def __fill_data(self):
        """ This method fill and parsing data to DataFrame."""
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
        for idx in master_branch:
            #self._commits_dict[idx] = {}
            diff = self.__repository.diff(idx)
            rang = len(diff)
            dict_params = {"idx": idx,
                           "diff": diff,
                           "range": rang,
                           "index": index}
            app(dict_params)
            index += 1
        self.walk_diff(list_params)


    def walk_diff(self, list_params):
        """Method for walk trought diff."""
        str_pattern = r'@@ ([-\+\d]+),([-\+\d]+) ([-\+\d]+),([-\+\d]+) @@'
        line_pattern = re.compile(str_pattern)
        counter_lines = re.compile(r'\n(\-)(.*)')
        add_lines = re.compile(r'\n(\+)(.*)')
        #blank_lines = re.compile(r'\n( )(.*)')

        #l_params = []
        #append = l_params.append
        for params in list_params:
            for indx in range(params["range"]):
                #params["index"] += 1
                tmp_commit = params["diff"][indx]["diff"]
                line = line_pattern.findall(tmp_commit)
                found_line = counter_lines.findall(tmp_commit)
                add_line = add_lines.findall(tmp_commit)
                counter = len(found_line) - 1
                added = len(add_line)  - 1 
                removed = (counter - added)
                fname = params["diff"][indx]["new"]["path"]
                if fname == '' or fname == None:
                    fname = params["diff"][indx]["old"]["path"]
                lcount = self.count_lines(fname)
               # lines_count -= removed
                for group in line:
                     #       print group[1]
                    start_line = abs(int(group[1]))
                    list_lines = [num + start_line for num in range(counter)]
                    if len(list_lines) > 0:
                        df_lines = self.get_lines(list_lines, params["idx"], \
                                            params["index"], removed, lcount)
                        if fname in self.files:
                            self.files[fname] = self.files[fname]\
                                        .append(df_lines, ignore_index=True)
                        else:
                            self.files[fname] = df_lines
       # print self.files
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
        
    def get_lines(self, list_lines, sha, index, removed, line_count):
        """Method return dataframe lines"""
        tmp_list = []
        append = tmp_list.append
        for line in list_lines:
            tmp_dict = {"line": line,
                        "author": self.find_author_by_sha(sha),
                        "sha": sha,
                        "range": index,
                        "rating": 1,
                        "num_lines": line_count,
                        "removed": abs(removed),
                        "modification": 0.0,
                        "time": self.find_time_by_sha(sha)}
            append(tmp_dict)
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
#if __name__ == "__main__":
    #git_data = GitData("/tmp/temporary_git_repository")
    #df = git_data.data_frame_project()
