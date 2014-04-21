# -*- coding: utf-8 -*-
"""
Created on Thu Apr  3 21:24:06 2014

@author: Radim Spigel
"""
from __future__ import division
import shutil
import os
import logging
import re
from pandas import DataFrame
from gittle import Gittle, InvalidRemoteUrl
from argparse import ArgumentParser
import pprint
import tempfile
import time
from subprocess import Popen, PIPE

TMP_DIR = tempfile.gettempdir()

LOG_FORMAT = "%(name)s:%(asctime)s:%(message)s"
logging.basicConfig(format=LOG_FORMAT, filename="log.log")
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

def eval_pylint((filee, sha)):
    """Call pylint for file"""
    pylint = Popen(("pylint --rcfile=/tmp/rc -f text %s" % filee).split(), stdout=PIPE)
    pylint.wait()
    output = pylint.stdout.read()
    str_rating = r"Your code has been rated at ([-\d\.]+)\/10 "
    str_rating += r"(\(previous run: ([\d\.]+)\/10.*\))?"
    results_re = re.compile(str_rating)
    frating = results_re.search(output)
    if frating is None:
        LOGGER.warning("No pylint rating for %s with shas %s"
            % (filee, sha))
        return
    return dict(
                    actual_rated=frating.group(1),
                    previous_rated=frating.group(3),
                    pylint_file=filee,
                    sha=sha
            )
def generate_report(project_name, ratings):
    """ Function for generating report """
    report = "Project: %s\n" % (project_name,)
    for author in ratings.keys():
          report += "======================================================\n"
          report += "Authors: %s\n" % (author, )
          report += ("Current average (hyphotetical + pylint) quality of project"
                      "is : %s \n" % (ratings[author]["final_rating"],))
          report += ("Current average hyphotetical quality of project"
                      "is : %s \n" % (ratings[author]["hyphotetical_rating"],))
          report += ("Current average pylint quality of project"
                      "is : %s \n" % (ratings[author]["pylint_rating"],))
          report += "======================================================\n"
          for ix, rtime in enumerate(ratings[author]["time"]):
              report += "======================================================\n"
              report += "Quality of contributor/s:\n"
              report += "Date: %s\n" % time.ctime(rtime)
              report += "Rating: %s\n" % ratings[author]["avg_comm_rating"][ix]
          for ix, ptime in enumerate(ratings[author]["pylint_time"]):
              report += "======================================================\n"
              report += "Pylint rating:\n"
              report += "File: %s\n" % ratings[author]["files"][ix]
              report += "Date: %s\n" % time.ctime(ptime)
              report += "Rating %s\n" % ratings[author]["pylint"][ix]
          report += "======================================================\n"
    return report

class QMetric(object):
    """This class take like argumet path to the project and data
       from subversion system. This data evaulation and walk truth
       and return data for vizualization.
    """

    def __init__(self, path, branch, allow_pylint=False):
        """Inicialization variables for path and subversion data and rc file
            for pylint.
        """
        self.vesion_system = self.GitData(path, branch)

        self._path = self.vesion_system.return_repository_path()
        LOGGER.debug('Repo Path: %s' % (self._path, ))
        self.subver_data, self.files = self.vesion_system.get_git_data()
        self.return_data = None
        #test for existion rcfile for pylint
        spath = path.split('/')
        self.project_name = spath[len(spath)-1].split('.')[0]
        if not os.path.exists("/tmp/rc"):
            os.system("pylint --generate-rcfile > /tmp/rc")
        self.__rc_file = os.getcwd() + "/rc"
        self.pylint_rating = {}
        self.count_pylint_eval = 0
        self.pylint_eval = []
        if allow_pylint:
            self.__get_pylint()
        self.rating = {}
        self.rate()
        weights = dict(count_w=0.1, comm_w=0.1, avg_pylint_w=0.1, pylint_w=0.1)
        self.count_final_rating(weights)
        LOGGER.info(generate_report(self.project_name, self.rating))
        #LOGGER.info("Pylint evaluation was %s" % self.count_pylint_eval)

    def get_pylint(self):
        """This method create dictionary of files in the project."""
        dirpaths, dirnames, files = [], [], []
        for dirpath, dirname, filee in os.walk(self._path):
            if filee != []:
                for fil in filee:
                    if re.search(r".*\.py", fil) is not None:
                        self.eval_file_in_history(dirpath + "/" + fil)

    def __get_pylint(self):
        """This method create dictionary of files in the project."""
        for _file in self.files.keys():
            self.eval_file_in_history(_file)

    def eval_file_in_history(self, filee):
        """This method take file and eval this file by history of commits
        thanks to method evaluate.
        """
       # shas = self.get_shas(filee)
        try:
            shas = self.files[filee]["sha"].unique()
        except KeyError:
            LOGGER.error(r"No sha for this file %s " % (filee,))
            return
        if shas != []:
            #sets = set(shas)
            #list_sha = list(sets)
            self.evaluate(filee, shas)
        else:
            LOGGER.error(r"No sha for this file %s " % (filee,))
            return

    def get_shas(self, filee):
        """This method returns list of sha for file from df."""
        fil = filee.split(self._path + "/")
        try:
            files = self.files[fil[1]]["sha"].values
            return files
        except KeyError:
            return []

    def evaluate(self, file_name, sha):
        """This method call rollback from GitData. This method returns data
        to previous state. Direction is from recent to first commit.
        """
        #params = []
        if file_name not in self.pylint_rating:
            self.pylint_rating[file_name] = []
        for item in sha:
            self.vesion_system.rollback(item)
            fname = self._path + "/" + file_name
            self.count_pylint_eval += 1
            LOGGER.info("Start pylint for file: %s" % (fname,))
            self.pylint_rating[file_name].append(self.eval_pylints(fname, item))

    def eval_pylints(self, filee, sha):
        """Call pylint for file"""
        pylint = Popen(("pylint --rcfile=/tmp/rc -f text %s" % filee).split(),
                       stdout=PIPE)
        pylint.wait()

        output = pylint.stdout.read()
        str_rating = r"Your code has been rated at ([-\d\.]+)\/10 "
        str_rating += r"(\(previous run: ([\d\.]+)\/10.*)?"
        results_re = re.compile(str_rating)
        frating = results_re.search(output)
        if frating is None:
            LOGGER.warning("No pylint rating for %s with shas %s"
            % (filee, sha))
            return
        return dict(
                    actual_rated=frating.group(1),
                    previous_rated=frating.group(3),
                    pylint_file=filee,
                    sha=sha
            )

    def rate(self):
        """
        This method rates authors. Main function in this method is iterate
        for every lines which every contributor committed to current file.
        Has some statistic variables. One is counter for counting how many
        commits did to file each contributor.

        Next variable is sum of average how many does contributor change
        file/ count all commits to file. Next variable is most modified
        file and how many commits did contributor done to this file.

        Another variable is mean value of ratings for every commit getting
        in GitData.modificate_rating.

        Last variable is pylint negative or positive result if author
        decreases pylint rating gets negative evaluate
        if author increase pylint rating gets positive else gets nothing.
        """
        for fname in self.files.keys():
            if len(self.files[fname]) <= 0:
                continue
            count = self.files[fname].groupby("author")
            count_line = self.files[fname].groupby(["author", "line"])
            self.__add_average_commit_counts(count_line, count, fname)
            self.__add_another_commit_ratings(count, fname)
            self.__add_pylint_avgs(fname)

    def __add_average_commit_counts(self, count_line, count, fname):
        """
        This method counts all commits(for getting range between commits
        which modified same line). Also count sum of averages how many does
        contributor change file/ count all commits to file.
        """
        for author in count_line.groups.iterkeys():
            if author not in self.rating:
                self.rating[author[0]] = {}
                #if pylint rating was > then prev
                self.rating[author[0]]["pylint+"] = 0
                #if pylint rating was < then prev
                self.rating[author[0]]["pylint-"] = 0
                #most modified file
                self.rating[author[0]]["MMFile"] = ""
                #count commits in MMFile
                self.rating[author[0]]["CCMMFile"] = 0
                #avg of all average of commits
                self.rating[author[0]]["avg_count"] = []
                #count of all average of commits for prev avg_count
                self.rating[author[0]]["count_all_comm"] = 0
                #mean of all rating of commits
                self.rating[author[0]]["avg_comm_rating"] = []
                self.rating[author[0]]["pylint_time"] = []
                self.rating[author[0]]["time"] = []
                self.rating[author[0]]["files"] = []
                self.rating[author[0]]["hyphotetical_rating"] = 0.0
                self.rating[author[0]]["pylint_rating"] = 0.0
               #self.rating[author]["list_comm_ratings"] = []
                #final rating
                self.rating[author[0]]["final_rating"] = 0.0
                #list of ratings
                self.rating[author[0]]["pylint"] = []
            self.rating[author[0]]["count_all_comm"] += 1
            c_line = len(count_line.groups[author])
            count_ = len(count.groups[author[0]])
            self.rating[author[0]]["avg_count"].append(float(c_line / count_))

    def __add_another_commit_ratings(self, count, file_name):
        """
        This method count mean value of ratings for every commit getting
        in GitData.modificate_rating. Also search most modified file.
        """
        for author in count.groups.iterkeys():
            if self.rating[author]["CCMMFile"] < len(count.groups[author]):
                self.rating[author]["CCMMFile"] = len(count.groups[author])
                self.rating[author]["MMFile"] = file_name
            rat = self.files[file_name]
            #self.rating[author]["commits_rating"].append()
            shas = rat[rat.author == author]["sha"].unique()
            self.rating[author]["avg_comm_rating"] = [
                rat[rat.sha == sha]["rating"].mean() for sha in shas]
            self.rating[author]["time"] = [
                rat[rat.sha == sha]["time"].unique() for sha in shas]

    def __add_pylint_avgs(self, file_name):
        """
        This method counts positive and negative pylint ratings, take all
        ratings to list for averaging.
        """
        try:
            for fil in self.pylint_rating[file_name]:
                if fil is None:
                    continue
                author = self.vesion_system.find_author_by_sha(fil["sha"])
                time = self.vesion_system.find_time_by_sha(fil["sha"])
                actual_rated = float(fil["actual_rated"])
                self.rating[author]["pylint"].append(actual_rated)
                self.rating[author]["pylint_time"].append(time)
                self.rating[author]["files"].append(file_name)
                # because we direction is from last to first must take prev
                # with actual
                if fil["actual_rated"] < fil["previous_rated"]:
                    self.rating[author]["pylint-"] += 1
                elif fil["actual_rated"] > fil["previous_rated"]:
                    self.rating[author]["pylint+"] += 1
        except KeyError:
            LOGGER.warning(r"not in pylint_rating for %s" % (file_name,))

    def count_final_rating(self, weight):
        """Count final rating. First i get difference between positive and
        negative rating. Next i get average how many does contributor
        change file/ count all commits to file.
        Another variable is average ratings for commits what this author did
        to file. After that i get average value for every pylint rating for
        all files. Last is total rating which is mean value from this
        variables. For each variables is set weight"""
        for author in self.rating.keys():
            avg_pylint = (self.rating[author]["pylint+"] -\
            self.rating[author]["pylint-"])
            avg_pylint *= weight["pylint_w"]
            LOGGER.info("pylint+ %s pylint- %s diff %s" %
                (self.rating[author]["pylint+"], self.rating[author]["pylint-"],
                 avg_pylint))
            avg_count = self.avg(self.rating[author]["avg_count"]) * 100
            avg_count *= weight["count_w"]
            avg_comm = self.avg(self.rating[author]["avg_comm_rating"]) * 100
            avg_comm *= weight["comm_w"]
            avg_comm /= 4
            self.rating[author]["hyphotetical_rating"] = avg_comm * 10
            avg_pylint = avg_pylint * weight["avg_pylint_w"]
            avg_list_pylint = self.avg(self.rating[author]["pylint"])
            self.rating[author]["pylint_rating"] = avg_list_pylint * 10
            final = (avg_count + avg_comm)
            LOGGER.info("Author: %s \nAvg lines: %s\nAvg commits: %s\nFinal: %s"
                % (author, avg_count, avg_comm, final))
            self.rating[author]["avg_pylint"] = avg_list_pylint * 10
            if (final*10) < 100.0:
                self.rating[author]["final_rating"] = final*10
            else:
                self.rating[author]["final_rating"] = 100.0
            LOGGER.info(r"Final after eval %s \nFinal oylint %s"
            % (self.rating[author]["final_rating"],
               self.rating[author]["avg_pylint"]))

    def avgs(self, list_el):
        """This method returns average value for list"""
        pprint.pprint(list_el)
        ret_val = 0.0
        for sublist in list_el:
            if len(sublist) > 0:
                ret_val += sum(sublist) / len(sublist)
            else:
                ret_val += 0.0
        return ret_val

    def avg(self, list_el):
        """This method returns average value for list"""
        if len(list_el) > 0:
            return sum(list_el) / len(list_el)
        else:
            return 0.0

    class GitData(object):
        """ This class is for getting contribution, users and other data from Git
        repository.
        """

        def __init__(self, uri, branch="master", cached=False):
            self._data_frame = None
            self._commits_dict = {}
            self.files = {}
            self.line_counter = {}
            self.git_repository = uri
            str_url = r'(git://github.com/|https://github.com/|git@github.com:)(.*)'
            git_url = re.compile(str_url)
            _uri_safe = ''.join([c for c in uri if c.isalnum()])
            self.repo_path = os.path.join(TMP_DIR, _uri_safe)
            self.__tmp_repository = self.repo_path
            if not cached and os.path.exists(self.repo_path):
                #dont use cached repo
                shutil.rmtree(self.repo_path)
            is_url = git_url.search(uri)
            self.commits = {}
            if is_url is None:
                self.__repository = Gittle(self.git_repository)
                self.__tmp_repository = self.git_repository
            else:
                if self.git_repository.find(".git") < 0:
                    LOGGER.info(r"Must end .git i will add manualy")
                    self.git_repository += ".git"
                try:
                    LOGGER.info(r'Cloning git repo: %s' % self.repo_path)
                    Gittle.clone(self.git_repository, self.__tmp_repository)
                except InvalidRemoteUrl:
                    LOGGER.error(r"Could not clone repository!")
                except ValueError:
                    LOGGER.error(r"Is not url.")
                except KeyError as err:
                    raise Exception(r"Could not clone repository. Error: %s" %
                                    (err,))
                self.__repository = Gittle(self.__tmp_repository)
            self.__fill_data(branch)
            self.eval_commits()

        def eval_commits(self):
            """
            This method walk through saved items and evaluate
            rating commits.
            """
            for inx in self.files.keys():
                if len(self.files[inx]) <= 0:
                    continue
                group = self.files[inx].groupby(["author", "line"])
                for value in group.groups.itervalues():
                    if len(value) > 1:
                        self.modificate_rating(inx, value)

        def modificate_rating(self, fname, index, percent=0.35):
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
            if fname.find(".py") < 0:
                return
            LOGGER.info("Start of evaulation line in %s file %s" %
                        (self.files[fname].ix[index[0]]["line"], fname))
            df_file = self.files[fname]
            length = len(index)
            for idx in range(length-1):
                ackt_range = df_file.ix[index[idx]]["range"]
                next_range = df_file.ix[index[idx + 1]]["range"]
                rang = next_range - ackt_range
                try:
                    fmod = float(df_file.ix[index[idx]]["changed_lines"]) \
                    / float(df_file.ix[index[idx]]["num_lines"])
                    smod = float(df_file.ix[index[idx + 1]]["changed_lines"]) \
                    / float(df_file.ix[index[idx + 1]]["num_lines"])
                except ZeroDivisionError:
                    smod, fmod = 0, 0
                smod += fmod
                ratings, smod = self.__calc_rating(rang, smod, percent)
                self.files[fname].ix[index[idx + 1], "modification"] = smod
                self.files[fname].ix[index[idx + 1], "rating"] = ratings
            LOGGER.debug(r"End of evaluation of ratings for every commit.")

        def __calc_rating(self, rang_btwn, modif_lines, percent):
            """
            This method rate the commit on based set arguments.
            Return calculated rating and inicator of modification in file.
            """
            if rang_btwn <= 25 and rang_btwn > 1 and modif_lines < percent:
                rating = 0
            elif rang_btwn > 25 and rang_btwn <= 35 and modif_lines < percent:
                rating = 1
            elif rang_btwn > 35 and rang_btwn <= 45 and modif_lines < percent:
                rating = 2
            elif rang_btwn > 45 and rang_btwn <= 55 and modif_lines < percent:
                rating = 3
            else:
                rating = 4
            if modif_lines >= percent:
                modif_lines = 0.0
                #rating = 4
            return (rating, modif_lines)

        def return_repository_path(self):
            """ This method returns path to tmp repository"""
            return self.__tmp_repository

        def __get_data_from_df(self, what, data_frame, index="name"):
            """ This method just walk trought nested data frame and fill
            new data frame.
            """
            self._data_frame[what] = [idx[index] for idx in data_frame[what]]

        def __fill_data(self, branch):
            """ This method fill and parsing data to DataFrame."""
            LOGGER.info("Filling data to _data_frame")
            self._data_frame = DataFrame(self.__repository.commit_info())
            try:
                __branch = [sha.id for sha in
                    self.__repository.branch_walker(branch)]
            except ValueError:
                raise Exception(r"This repository dont have %s branch" %
                                (branch,))
            LOGGER.info(r"Go through master branch and using gittle.diff for"
            "getting diff output")
            for idx, sha in enumerate(__branch):
                self._diff({"sha": sha,
                         "diff": self.__repository.diff(sha),
                        "index": idx
                    })

        def _diff(self, params):
            """
            This method for walk through diff from gittle. Found removed lines,
            added lines to file and make difference betwen. Thanks difference
            betwen added and removed we get changed lines. In this method we call
            method for counting lines in file that will be saved to DataFrame with
            changed lines removed lines and sha thanks to method set_lines_df. I
            want only removed lines for my algorithm because in method
            modificate_rating i go through from recent  to first commit.
            """
            if len(params) <= 0:
                return
            author = self.find_author_by_sha(params["sha"])
            time = self.find_time_by_sha(params["sha"])
            for indx, dict_diff in enumerate(params["diff"]):
                fname = dict_diff["new"]["path"]
                if fname == '' or fname == None:
                    fname = dict_diff["old"]["path"]
                if re.search(r".*\.py", fname) is None:
                    continue
                lcount = self.count_lines(fname)
                params["index"] += 1
                lines = dict_diff["diff"].split("\n")
                list_lines = []
                line_num = 0
                removed, added, changed = 0, 0, 0
                for line in lines:
                    if len(line) <= 0 or line is None:
                        continue
                    if (line.startswith('diff ') or
                        line.startswith('index ') or
                        line.startswith('--- ') or
                        line.startswith('+++ ')):
                        continue
                    if line.startswith('@@ '):
                        _, old_nr, new_nr, _ = line.split(' ', 3)
                        line_num = int(new_nr.split(',')[0])
                        continue
                    if line[0] == ' ':
                        line_num += 1
                        continue
                    if line[0] == '-':
                        removed += 1
                        list_lines.append(line_num)
                        line_num += 1
                        list_lines.append(line_num)
                        continue
                    if line[0] == '+':
                        added += 1
                        continue
                changed = added - removed
                list_to_df = [{"line": rem_line,
                            "author": author,
                            "sha": params["sha"],
                            "range": params["index"],
                            "rating": 4,
                            "num_lines": lcount,
                            "removed_lines": removed,
                            "add_lines" : added,
                            "changed_lines": abs(changed),
                            "modification": 0.0,
                            "time": time
                         }for rem_line in list_lines]
                if fname in self.files:
                    __tmp = DataFrame(list_to_df)
                    self.files[fname] = self.files[fname]\
                                          .append(__tmp, ignore_index=True)
                else:
                    self.files[fname] = DataFrame(list_to_df)

        def count_lines(self, fname):
            """This method count lines in file"""
            if not os.path.exists(self.__tmp_repository + "/" + fname):
                return 0
            if fname not in self.line_counter:
                count = 0
                with open(self.__tmp_repository + "/" + fname) as filer:
                    for line in filer:
                        count += 1
                self.line_counter[fname] = count
            else:
                return self.line_counter[fname]
            return count

        def find_author_by_sha(self, sha):
            """This method finds the author by sha in dataFrame. If not found
               return None.
            """
            index = self._data_frame[self._data_frame.sha == sha]["author"]
            if sha == '' or sha == []:
                return None
            try:
                return index.values[0]["name"]
            except IndexError:
                LOGGER.warning(r"Sha %s, %s is not in data frame." %
                        (sha, index))
            return None

        def find_time_by_sha(self, sha):
            """This method finds timestamp by sha in dataFrame. If not found
               return None.
            """
            index = self._data_frame[self._data_frame.sha == sha].index
            if sha == '' or sha == []:
                return None
            try:
                return self._data_frame.time[index].values[0]
            except IndexError:
                LOGGER.warning("Sha %s, %s is not in data frame." %
                            (sha, index))
            return None

        def rollback(self, sha):
            """
            This method will make rollback to version which is set by sha.
            """
            try:
                self.__repository.checkout_all(sha)
            except IOError:
                LOGGER.warning("Couldn't rollback on sha %s." % (sha,))
            except KeyError:
                LOGGER.warning("Couldn't rollback on sha %s." % (sha,))

        def get_git_data(self):
            """ This method returns data frame for project or None. """
            return (self._data_frame, self.files)


if __name__ == "__main__":
    PARSER = ArgumentParser(
        description=("This program is for evaluation of quality of "
                     "project based on hypothetical patterns of quality."))

    PARSER.add_argument("path", help="www or path to git repo to evaluate")
    PARSER.add_argument("--branch", default="master",
                        help="set branch what we wanna evaluate,"
                        "default is master branch")
    PARSER.add_argument("debug", action='store_true',
                        help="enable debugging output")
    PARSER.add_argument("debug", action='store_true',
                        help="enable debugging output")
    ARGS = PARSER.parse_args()
    PATH = ARGS.path
    BRANCH = ARGS.branch
    DEBUG = ARGS.debug
    if DEBUG:
        LOGGER.setLevel(logging.DEBUG)
    QMETRIC = QMetric(PATH, BRANCH)
