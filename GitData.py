# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""
import pandas
from gittle import Gittle, InvalidRemoteUrl
import re
import logging
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

    def __fill_data(self):
        """ This method fill and parsing data to DataFrame."""
        tmp_df = pandas.DataFrame(self.__repository.commit_info())
        file_pattern = re.compile(r'diff --git [a/]?(\S+) [b/]?(\S+)')
        line_pattern = re.compile(r'@@ ([-\+\.,\d]+) ([-\.\+\,\d]+) @@')
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
        #try:
        if 1:
            array = self.__repository.branch_walker("master")
            master_branch = [sha.id for sha in array]
        #except:
         #   logging.warning("This repository dont have master branch")
          #  master_branch = tmp_df.sha
        for idx in master_branch:
            self._commits_dict[idx] = {}
            rang = len(self.__repository.diff(idx))
            if rang <= 0:
                commit.append("")
                lines.append("")
                files.append("")
                continue
            for indx in range(rang):
                tmp_commit = self.__repository.diff(idx)[indx]["diff"]
                commit.append(tmp_commit)
                #line = line_pattern.search(tmp_commit)
                #fil_e = file_pattern.search(tmp_commit)
                line = line_pattern.findall(tmp_commit)
                fil_e = file_pattern.findall(tmp_commit)
                if line is not None:
                    lines.append(line)
                else:
                    lines.append("")
                if fil_e is not None:
                    files.append(fil_e)
                else:
                    files.append("")

            self._commits_dict[idx]["commit"] = {}
            self._commits_dict[idx]["commit"] = commit
            self._commits_dict[idx]["files"] = {}
            self._commits_dict[idx]["files"] = files
            self._commits_dict[idx]["lines"] = {}
            self._commits_dict[idx]["lines"] = lines
            self._commits_dict[idx]["author"] = tmp_df["author"][index]["name"]
            commit = []
            files = []
            lines = []
            index += 1
        #print json.dumps(self._commits_dict)
        print self._commits_dict["070b1f59ea1db25fc10de927793194076c9a277a"]
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

    def rollbakc_to_last_commit(self, files):
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
        return (self._data_frame, self._commits_dict)
#if __name__ == "__main__":
    #git_data = GitData("/tmp/temporary_git_repository")
    #df = git_data.data_frame_project()
