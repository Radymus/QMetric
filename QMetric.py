# -*- coding: utf-8 -*-
"""
Created on Thu Apr  3 21:24:06 2014

@author: Radim Spigel
"""

from __future__ import division
from argparse import ArgumentParser
from gittle import Gittle
import os
from pandas import DataFrame, read_html
import pprint
import re
import shutil
# set is available as a built-in since 2.6
import tempfile

# setup default logger
import logging
log_format = "%(name)s:%(asctime)s:%(message)s"
logging.basicConfig(format=log_format)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_ = r'(git://github.com/|https://github.com/|git@github.com:)(.*)'
GIT_URL_RE = re.compile(_)
TMP_DIR = tempfile.gettempdir()


class QMetric(object):
    """This class takes a git repo path, evaluates theoretical
       commit quality and returns resulting data ready for
       further processing.
    """

    def __init__(self, path):
        """Clone and initialize Git Repo, collect a bunch of
           metrics stats, generate pylint rc file.
        """
        self.vesion_system = GitData(path)

        self._path = self.vesion_system.repo_path
        logger.debug('Repo Path: %s' % self._path)
        self.subver_data, self.files = self.vesion_system.get_git_data()
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
        self.create_final_structure()
        self.rate()
        weights = dict(count_w=0.1, comm_w=0.1, avg_pylint_w=0.1, pylint_w=0.1)
        self.count_final_rating(weights)
        logger.info('Rating: %s' % pprint.pformat(self.rating))

    def create_final_structure(self):
        """Creating of structure for authors."""
        authors = self.subver_data.groupby(["author"])
        for author in authors.groups.iterkeys():
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
        for rating in self.rating.itervalues():
            avg_pylint = (rating["pylint+"] - rating["pylint-"])
            avg_pylint *= weight["pylint_w"]
            avg_count = rating["avg_count"] * weight["count_w"]
            avg_comm = rating["avg_comm_rating"] * weight["comm_w"]
            avg_pylint = avg_pylint * weight["avg_pylint_w"]
            avg_list_pylint = sum(rating["pylint"])
            if len(rating["pylint"]) > 0:
                avg_list_pylint /= len(rating["pylint"])
            final = (avg_pylint + avg_count + avg_comm + avg_list_pylint) / 4
            if (final * 100) < 100.0:
                rating["final_rating"] = final * 100
            else:
                rating["final_rating"] = 100.0

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
        if  author increase pylint rating gets positive else gets nothing.
        """
        # FIXME: too deeply nested?
        # break this up into more manageable, readable functions?
        for fname in self.files.iterkeys():
            count = self.files[fname].groupby("author")
            count_line = self.files[fname].groupby(["author", "line"])
            for author in count_line.groups.iterkeys():
                self.rating[author[0]]["count_all_comm"] += 1
                c_line = len(count_line.groups[author])
                count_ = len(count.groups[author[0]])
                self.rating[author[0]]["avg_count"] += float(c_line / count_)
            for author in count.groups.iterkeys():
                a_rating = self.rating[author]
                self.rating[author]["avg_count"] /= a_rating["count_all_comm"]
                if self.rating[author]["CCMMFile"] < len(count.groups[author]):
                    self.rating[author]["CCMMFile"] = len(count.groups[author])
                    self.rating[author]["MMFile"] = fname
                rat = self.files[fname]
                a_rating_mean = rat[rat.author == author]["rating"].mean()
                rat["avg_comm_rating"] = a_rating_mean

            try:
                for fil in self.pylint_rating[fname]:
                    author = self.vesion_system.find_author_by_sha(fil["sha"])
                    actual_rated = float(fil["actual_rated"])
                    self.rating[author]["pylint"].append(actual_rated)
                    if fil["actual_rated"] < fil["previous_rated"]:
                        self.rating[author]["pylint-"] += 1
                    elif fil["actual_rated"] > fil["previous_rated"]:
                        self.rating[author]["pylint+"] += 1
            except KeyError:
                logger.warning("not in pylint_rating")

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
        _rating = {}
        fnm = file_html.replace("/", "_")
        with open("/tmp/tmp_pylint_%s.html" % fnm) as fname:
            for line in fname:
                frating = re_rating.search(line)
                if frating is not None:
                    _rating["actual_rated"] = frating.group(1)
                    _rating["previous_rated"] = frating.group(2)
                    _rating["time"] = self.vesion_system.find_time_by_sha(sha)
                    _rating["sha"] = sha
                    if file_html in self.pylint_rating:
                        self.pylint_rating[file_html].append(_rating)
                    else:
                        self.pylint_rating[file_html] = []
                        self.pylint_rating[file_html].append(_rating)

    def get_file(self, filee):
        """This method returns list of sha for file from df."""

        fil = filee.split(self._path + "/")
        try:
            files = self.files[fil[1]]["sha"].values
            return files
        except KeyError:
            return []

    def eval_file_in_history(self, filee):
        """This method take file and eval this file by history of commits
        thanks to method evaluate.
        """
        files = self.get_file(filee)
        if files != []:
            sets = set(files)
            list_sha = list(sets)
            self.evaluate(filee, list_sha)
        else:
            self.evaluate(filee, [])

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
        except ImportError as e:
            logger.warning("No html file: %s" % e)

    def evaluate(self, filee, sha):
        """This method call rollback from GitData. This method returns data
        to previous state. Direction is from recent to first commit.
        """
        if sha == []:
            self.eval_pylint(filee, '')
        else:
            for item in sha:
                self.vesion_system.rollback(item)
                self.eval_pylint(filee, item)


class GitData(object):
    """ This class is for getting contribution, users and other data from Git
    repository.
    """

    def __init__(self, uri, cached=False):
        self._data_frame = None
        self._commits_dict = {}
        self.files = {}
        self.line_counter = {}
        self.commits = {}

        # strip out everything but alpha/numerical characters
        # to make a path that is fs safe
        # this way we always clone repo to same place
        # and can avoid clone multiple times if already cached
        _uri_safe = ''.join([c for c in uri if c.isalnum()])
        self.repo_path = os.path.join(TMP_DIR, _uri_safe)
        if not cached and os.path.exists(self.repo_path):
            # dont use cached repo...
            shutil.rmtree(self.repo_path)
        else:
            # FIXME: add function to 'fetch' and 'pull' branch
            # if working with previously cloned/cached repo
            pass

        # if we have a url, clone (cache) the repo to disk
        if GIT_URL_RE.search(uri):
            logger.info('Cloning git repo: %s' % self.repo_path)
            Gittle.clone(uri, self.repo_path)

        # load the repo with Gittle
        self.__repository = Gittle(self.repo_path)

        self.__fill_data()
        self.eval_commits()

    def eval_commits(self):
        """This method walk through saved items and evaluate rating commits."""
        for inx in self.files.iterkeys():
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
        logger.info("Start of evaulation of ratings for each commit.")
        if fname.find(".py") < 0:
            return
        df_file = self.files[fname]
        length = len(index)
        for idx in range(length - 1):
            ackt_range = df_file.ix[index[idx]]["range"]
            next_range = df_file.ix[index[idx + 1]]["range"]
            rang = next_range - ackt_range
            try:
                removed = float(df_file.ix[index[idx]]["removed"])
                num_lines = float(df_file.ix[index[idx]]["num_lines"])
                fmod = removed / num_lines
                # index + 1
                removed = float(df_file.ix[index[idx + 1]]["removed"])
                num_lines = float(df_file.ix[index[idx + 1]]["num_lines"])
                smod = removed / num_lines
            except ZeroDivisionError:
                smod, fmod = 0, 0
            smod += fmod
            # FIXME: again, to complex (mccabe complexity)
            # http://en.wikipedia.org/wiki/Cyclomatic_complexity
            # maybe move these into a method that accepts rang, smod, percent
            # and return back rating
            # eg...
            # rating = self._calc_rating(rang, smod, percent)
            if rang <= 20 and rang > 1 and smod < percent:
                rating = -3
            elif rang > 20 and rang <= 30 and smod < percent:
                rating = -2
            elif rang > 30 and rang <= 40 and smod < percent:
                rating = -1
            elif rang > 40 and rang <= 50 and smod < percent:
                rating = 0
            else:
                rating = 1
                # FIXME: why reset smod here?
                # could be done outside of this if/else clause?
                if smod >= percent:
                    smod = 0.0
            self.files[fname].ix[index[idx + 1], "modification"] = smod
            self.files[fname].ix[index[idx + 1], "rating"] = rating
        logger.debug("End of evaluation of ratings for every commit.")

    def __get_data_from_df(self, what, data_frame, index="name"):
        """ This method just walk trought nested data frame and fill
        new data frame.
        """
        tmp_val = [idx[index] for idx in data_frame[what]]
        self._data_frame[what] = tmp_val

    def __fill_data(self):
        """ This method fill and parsing data to DataFrame."""
        logger.info("Filling data to _data_frame")
        tmp_df = DataFrame(self.__repository.commit_info())
        self._data_frame = DataFrame(tmp_df.sha, columns=["sha"])
        self._data_frame["description"] = tmp_df.description
        self._data_frame["message"] = tmp_df.message
        self._data_frame["summary"] = tmp_df.summary
        self._data_frame["time"] = tmp_df.time
        self.__get_data_from_df("author", tmp_df)
        self.__get_data_from_df("committer", tmp_df)
        index = 0
        try:
            array = self.__repository.branch_walker("master")
            master_branch = [sha.id for sha in array]
        except ValueError:
            logger.warning("This repository has no master branch")
            # FIXME: what is this doing? if no master (or whatever
            # branch we're trying to evaluate) shouldn't we raise
            # exception?
            master_branch = tmp_df.sha
        list_params = []
        logger.info(
            "Get diff output of master branch using gittle.diff")
        for idx in master_branch:
            diff = self.__repository.diff(idx)
            rang = len(diff)
            list_params.append(
                (dict(idx=idx, diff=diff, range=rang, index=index)))
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
        for params in list_params:
            for indx in range(params["range"]):
                tmp_commit = params["diff"][indx]["diff"]
                line = line_pattern.findall(tmp_commit)
                removed_line = counter_lines.findall(tmp_commit)
                add_line = add_lines.findall(tmp_commit)
                removed = len(removed_line) - 1
                added = len(add_line) - 1
                change = (removed - added)
                fname = params["diff"][indx]["new"]["path"]
                if fname == '' or fname is None:
                    fname = params["diff"][indx]["old"]["path"]

                if re.search(r".*\.py", fname) is None:
                    continue
                lcount = self.count_lines(fname)
                for group in line:
                    start_line = abs(int(group[1]))
                    list_lines = [num + start_line for num in range(removed)]
                    if len(list_lines) > 0:
                        df_lines = self.set_lines_df(
                            list_lines, params["idx"], params["index"],
                            change, lcount)
                        if fname in self.files:
                            self.files[fname].append(df_lines,
                                                     ignore_index=True)
                        else:
                            self.files[fname] = df_lines
        logger.debug("END of walking through the all diffs for this repo.")

    def count_lines(self, fname):
        """This method count lines in file"""
        path = os.path.join(self.repo_path, fname)
        if not os.path.exists(path):
            return 0
        if fname not in self.line_counter:
            count = 0
            with open(path) as filer:
                for ix in filer:
                    count += 1
            self.line_counter[fname] = count
        else:
            return self.line_counter[fname]
        return count

    def set_lines_df(self, list_lines, sha, index, removed, line_count):
        """Method return dataframe lines"""
        tmp_list = []
        for line in list_lines:
            tmp_list.append(
                {"line": line,
                 "author": self.find_author_by_sha(sha),
                 "sha": sha,
                 "range": index,
                 "rating": 1,
                 "num_lines": line_count,
                 "removed": abs(removed),
                 "modification": 0.0,
                 "time": self.find_time_by_sha(sha)})
        data_frame = DataFrame(tmp_list)
        return data_frame

    def find_author_by_sha(self, sha):
        """This method finds the author by sha in dataFrame. If not found
            return None.
        """
        index = self._data_frame[self._data_frame.sha == sha].index
        try:
            return self._data_frame.author[index].values[0]
        except IndexError:
            logger.warning("Sha is not in data frame.")
        return None

    def find_time_by_sha(self, sha):
        """This method finds timestamp by sha in dataFrame. If not found
            return None.
        """
        index = self._data_frame[self._data_frame.sha == sha].index
        try:
            return self._data_frame.time[index].values[0]
        except IndexError:
            logger.warning("Sha is not in data frame.")
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
            logger.warning("Wrong sha hash or there is no file.")
            return None

    def get_git_data(self):
        """ This method returns data frame for project or None. """
        return (self._data_frame, self.files)


if __name__ == "__main__":
    parser = ArgumentParser(
        description=("This program is for evaluation of quality of "
                     "project based on hypothetical patterns of quality."))

    parser.add_argument("path", help="www or path to git repo to evaluate")

    parser.add_argument("debug", action='store_true',
                        help="enable debugging output")

    # FIXME: add ability to specify which branch to evaluate
    args = parser.parse_args()

    path = args.path
    debug = args.debug

    if debug:
        logger.setLevel(logging.DEBUG)

    QMetric(path)
