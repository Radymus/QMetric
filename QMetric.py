 #!/usr/bin/env python -W ignore::DeprecationWarning
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
import tempfile
import time
import urllib2
from subprocess import Popen, PIPE
import pprint
import pickle
from numpy import average as avg
import matplotlib.pyplot as plt
import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from mpld3 import show_d3, plugins
from dulwich.errors import RefFormatError
from datetime import datetime

TMP_DIR = tempfile.gettempdir()

LOG_FORMAT = "%(name)s:%(asctime)s:%(message)s"
logging.basicConfig(format=LOG_FORMAT, filename="logfile.log")
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
GIT_URL = r'(git://github.com/|https://github.com/|git@github.com:)(.*)'


class JsonStructure(object):
    """This class is for creating JSON structure."""
    def __init__(self):
        self.structure = {}
        self.structure["Name"] = str()
        self.structure["Averag_Commits_Ratings"] = 0
        self.structure["Average_Pylint"] = 0
        self.structure["Average_Software_Metrics"] = 0
        self.structure["Added_lines"] = 0
        self.structure["Removed_lines"] = 0
        self.structure["All_commits"] = 0
        self.structure["Pylint_positive"] = 0
        self.structure["Pylint_negative"] = 0
        self.structure["Most_modified_file"] = ""
        self.structure["Commits_to_most_modified_file"] = 0
        self.structure["Data"] = []

    def return_structure(self):
        """This return initialized JSON structure."""
        return self.structure


def get_d3():
    """
    This function downloads D3 lib. if doesn't exist.
    """
    d3_filename = 'd3.v3.min.js'
    if not os.path.exists(d3_filename):
        page = urllib2.urlopen('http://d3js.org/d3.v3.min.js')
        with open(d3_filename, 'w') as d3ffile:
            d3ffile.write(page.read())


def get_lists_for_graphs(ratings, author):
    """
    This function returns list of ratings for pylint, radon a two hyphotetical
    algorithms and list of dates.
    """
    list_comm = []
    list_pylint = []
    list_metrics = []
    list_rating_two = []
    list_dates = []
    lsorted = sorted(ratings[author]["time"].keys())
    for rtime in lsorted:
        if "pylint" not in ratings[author]["time"][rtime][0]:
            continue
        for item in ratings[author]["time"][rtime]:
            list_comm.append(item["rating_one"])
            list_pylint.append(item["pylint"])
            list_metrics.append(item["metric"])
            list_rating_two.append(item["rating_two"])
            list_dates.append(datetime.fromtimestamp(float(rtime)))
    return (list_comm, list_pylint, list_metrics, list_rating_two, list_dates)


def graph_authors(ratings, no_subplot, d3_plot, to_file, no_date):
    """
    This function prints graphs with library matplotlib and mpld3.
    Take arguments:
        ratings = nested dictionary which contains like key author, like data
                other metrics like pylint output, radon output, algorithms
                from QMetric and another for graphs
        no_subplot = if enable will be plots every curves in one graph else
                        plots every statistic to diffrent graph
        d3_plot = if enable is used for plotting library matplotlib + mpld3
                    else there will be graphs only in matplotlib
        no_dates = if enable which is in default, the x axis will have only
                    index of commit
    """
    for author in ratings:
        geted = get_lists_for_graphs(ratings, author)
        list_comm = geted[0]
        list_pylint = geted[1]
        list_metrics = geted[2]
        list_rating_two = geted[3]
        list_dates = geted[4]
        if len(list_comm) < 2:
            continue
        fig, ax = plt.subplots()
        authorl = author.replace(" ", "_")
        authorl = authorl.replace(".", "")
        plt.title("Author: {0}".format(authorl))
        ax.bar(range(4), [ratings[author]["hyphotetical_rating_one"],
                ratings[author]["hyphotetical_rating_two"],
                ratings[author]["pylint_rating"],
                ratings[author]["radon_rating"]], align="center")
        plt.xticks(range(4), ["First algorithm", "Second algorithm",
                           "Average pylint", "Average Radon"], size="small")
        plt.savefig(r"final_results_{0}".format(authorl))
        if no_date:
            list_dates = [num for num in xrange(len(list_comm))]
        plt.ylabel("Ratings %")
        plt.xlabel("Number of commits")
        if no_subplot:
            plt.ylim([-1, 101])
            plt.plot(list_dates, list_comm, color="red")
            plt.plot(list_dates, list_rating_two, color="black")
            plt.plot(list_dates, list_pylint, color="blue")
            plt.plot(list_metrics, color="green")
        else:

            plt.ylim([0, 101])
            plt.subplot(411)
            plt.ylabel("Ratings %")
            plt.xlabel("Number of commits")
            plt.plot(list_dates, list_comm, color="red")
            plt.title("Author: {0}".format(authorl))
            plt.subplot(412)
            plt.ylabel("Ratings %")
            plt.xlabel("Number of commits")
            plt.plot(list_dates, list_rating_two, color="black")
            plt.subplot(413)
            plt.ylabel("Ratings %")
            plt.xlabel("Number of commits")
            plt.plot(list_dates, list_pylint, color="blue")
            plt.subplot(414)
            plt.ylabel("Ratings %")
            plt.xlabel("Number of commits")
            plt.plot(list_dates, list_metrics, color="green")
        if to_file:
            plt.savefig(r"graph_rep_{0}".format(authorl))
        else:
            plt.show()
        if d3_plot and to_file:
            get_d3()
            plugins.connect(fig, plugins.Reset(), plugins.Zoom())
            show_d3()
        plt.clf()


def eval_static_metrics(filee):
    """
    This function calls radon which evaluate software metrics for selected
    file.
    """
    s_metric = Popen(("radon mi {0}".format(filee)).split(), stdout=PIPE)
    mindex = s_metric.stdout.read()
    mi__ = 0
    if re.search(r"- ([^ /])", mindex) is not None:
        mi__ = ord(re.search(r"- ([^ /])", mindex).group(1))
        mi__ -= 70
        mi__ = abs(mi__)
        mi__ /= 5
        mi__ *= 100
    s_metric = Popen(("radon cc -a {0}".format(filee)).split(), stdout=PIPE)
    ccomplexity = s_metric.stdout.read()
    cc_patt = re.compile(r"Average complexity: ([A,B,C,D,E,F]).*")
    complexity = None
    if cc_patt.search(ccomplexity) is not None:
        complexity = ord(cc_patt.search(ccomplexity).group(1))
        complexity -= 70
        complexity = abs(complexity)
        complexity /= 5
        complexity *= 100
    if complexity is not None:
        metric = (complexity + mi__) / 2
    else:
        metric = mi__
    LOGGER.info("Metric > {0}".format(metric))
    return metric


def eval_pylints(filee, sha):
    """
    Call pylint for file returns dictionary of actual rating, previous
    rating, file which was evaluate and sha.
    """
    pylint_file = ("pylint --rcfile=/tmp/rc -f text %s" % filee).split()
    pylint = Popen(pylint_file, stdout=PIPE)
    output = pylint.stdout.read()
    str_rating = r"Your code has been rated at ([-\d\.]+)\/10 "
    str_rating += r"(\(previous run: ([\d\.]+)\/10.*)?"
    results_re = re.compile(str_rating)
    frating = results_re.search(output)
    metric = eval_static_metrics(filee)
    if frating is None:
        LOGGER.warning("No pylint rating for {0} with shas {1}".format(filee, sha))
        return {}
    return dict(
            actual_rated=frating.group(1),
            previous_rated=frating.group(3),
            pylint_file=filee,
            metric=metric,
            sha=sha
            )


def calculate_rating(range_, threshold):
    """
    This method rate the commit on based set arguments.
    Return calculated rating and inicator of modification in file.
    """
    if range_ < threshold:
        rating = 0
    elif range_ >= threshold and range_ <= (threshold * 2):
        rating = 1
    elif range_ >= threshold * 2 and range_ <= (threshold * 3):
        rating = 2
    elif range_ >= threshold * 3 and range_ <= (threshold * 4):
        rating = 3
    else:
        rating = 4
    return rating


def generate_report(project_name, ratings):
    """
    Function for generating report like argument takes name of project and
    ratings which is nested dictionary for ratings of every author.
    """
    report = "Project: %s\n" % (project_name,)
    for author in ratings:
        report += "#########################################################\n"
        report += "======================================================\n"
        report += "Authors: {0}\n".format(author)
        report += "Current average hyphotetical quality of project version 1:"
        report += (" {0}\n".format(ratings[author]["hyphotetical_rating_one"]))
        report += "Current average hyphotetical quality of project version 2:"
        report += (" {0}\n".format(ratings[author]["hyphotetical_rating_two"]))
        report += "Current average pylint quality of project"
        report += (" is : {0} \n".format(ratings[author]["pylint_rating"]))
        report += "Current average radon quality of project"
        report += (" is : {0} \n".format(ratings[author]["radon_rating"]))
        report += "======================================================\n"
        lsorted = sorted(ratings[author]["time"].keys())
        idx = 0
        for rtime in lsorted:
            if "pylint" not in ratings[author]["time"][rtime][0]:
                continue
            for item in ratings[author]["time"][rtime]:
                report += "Quality of contributor/s:\n"
                report += "Index in graph: {0}\n".format(idx)
                report += "Index to diff file: {0}\n".format(item["index"])
                report += "File: {0}\n".format(item["files"])
                report += "Date: {0}\n".format(time.ctime(rtime))
                report += "Commit rating version 1.: "
                report += "%.02f\n" % (float(item["rating_one"]))
                report += "Commit rating version 2.: "
                report += "%.02f\n" % (float(item["rating_two"]))
                report += "Rating pylint %.02f\n" % float(item["pylint"])
                report += "Rating radon %.02f\n" % float(item["metric"])
                report += "-------------------------------------------------\n"
                idx += 1
    report += "#########################################################\n"
    return report


class QMetric(object):
    """
    This category will clone repo and get all the commits for selected branch
    and evaluate rating for each commit.
    This category takes over as an argument the project we want to evaluate,
    branch (default branch is master).
    Another optional arguments are:
    specific_sha = specific sha can be bug-fix or some interesting commit
    threshold = this argument allows set threshold for iteration which is half
                of all commits
    correction = this argument allows count correction value for rating of
                first algorithm.
    Example:
        q = QMetric(path, branch)

        or

        q = QMetric(path, branch, threshold=True, correction=True) That will
            allows all correction arguments.

        For plotting graph for authors is need to call functions like
        this.
        graph_authors(q.rating, ...)
    """

    def __init__(self, path, branch, specific_sha=None, threshold=False,
                 correction=False):
        """Inicialization variables for path and subversion data and rc file
            for pylint.
        """
        spath = path.split('/')
        self.project_name = spath[len(spath)-1].split('.')[0]
        self.vesion_system = self.GitData(path, branch,
                    specific_sha=specific_sha, project_name=self.project_name,
                    threshold=threshold, correction=correction)
        self._path = self.vesion_system.return_repository_path()
        LOGGER.debug('Repo Path: {0}'.format(self._path))
        self.subver_data, self.files = self.vesion_system.get_git_data()
        self.return_data = None
        #test for existion rcfile for pylint
        if not os.path.exists("/tmp/rc"):
            os.system("pylint --generate-rcfile > /tmp/rc")
        self.__rc_file = os.getcwd() + "/rc"
        self.count_pylint_eval = 0
        self.authors = {}
        tmp_pylint = "/tmp/{0}_pylint.p".format(self.project_name)
        if (specific_sha is None and
            os.path.exists("/tmp/{0}_pylint.p".format(self.project_name))):
            LOGGER.info("File with pylint rating exists loading data.")
            get_data = pickle.load(open(tmp_pylint, "rb"))
            self.authors = get_data
        else:
            LOGGER.info("First evaluation could take lot of time must first "
                "time evaluate with pylint.")
            self.__get_pylint()
            pickle.dump(self.authors, open(tmp_pylint, "wb"))
        self.rate()
        json_data = self.count_final_rating()
        result_label = "result_{0}".format(self.project_name)
        with open(result_label + ".txt", "w") as result_file:
            result_file.write(generate_report(self.project_name, self.authors))
        with open(result_label + ".json", "w") as jsonf:
            jsonf.write(pprint.pformat(json_data))

    def __get_pylint(self):
        """
        This method create dictionary of files and get pylint and radon
        evaluation.
        """
        for _file in self.files.keys():
            self.eval_file_in_history(_file)

    def eval_file_in_history(self, filee):
        """
        This method take file and eval this file by history of commits
        thanks to method evaluate.
        """
        try:
            shas = self.files[filee]["sha"].unique()
        except KeyError:
            LOGGER.error(r"No sha for this file {0} ".format(filee))
            return
        if shas != []:
            self.evaluate(filee, shas)
        else:
            LOGGER.error(r"No sha for this file {0} ".format(filee))
            return

    def evaluate(self, file_name, sha):
        """
        This method call rollback from GitData for previous state. Direction
        is from first to last commit.
        """
        for idx, item in enumerate(sha):
            self.vesion_system.rollback(item)
            fname = self._path + "/" + file_name
            self.count_pylint_eval += 1
            LOGGER.info("Start pylint for file: {0}".format(fname))
            file_d = eval_pylints(fname, item)
            try:
                author = self.vesion_system.find_author_by_sha(file_d["sha"])
                if author not in self.authors:
                    self.__init_structure(author)
                if any(file_d):
                    rtime = self.vesion_system.find_time_by_sha(file_d["sha"])
                    actual_rated = float(file_d["actual_rated"])
                    metric = float(file_d["metric"])
                    self.authors[author]["metric"].append(metric)
                    self.authors[author]["pylint"].append(actual_rated * 10)
                    if rtime not in self.authors[author]["time"]:
                        self.authors[author]["time"][rtime] = []
                    self.authors[author]["time"][rtime].append(dict(
                                                     pylint=actual_rated * 10,
                                                     files=file_name,
                                                     metric=metric
                                                     ))
                    self.authors[author]["files"].append(file_name)
                    # because we direction is from first to last must take prev
                    # with actual
                    if file_d["actual_rated"] < file_d["previous_rated"]:
                        self.authors[author]["pylint-"] += 1
                    elif file_d["actual_rated"] > file_d["previous_rated"]:
                        self.authors[author]["pylint+"] += 1
            except KeyError:
                LOGGER.warning("No sha {0}".format(item))

    def rate(self):
        """
        This method call for adding another metrics.
        """
        for fname in self.files.keys():
            if len(self.files[fname]) <= 0:
                continue
            count = self.files[fname].groupby("author")
            self.__add_commit_ratings(count, fname)

    def __init_structure(self, author):
        """
        Method for creating structure for authors.
        """
        self.authors[author] = {}
        #if pylint rating was > then prev
        self.authors[author]["pylint+"] = 0
        #if pylint rating was < then prev
        self.authors[author]["pylint-"] = 0
        #most modified file
        self.authors[author]["MMFile"] = ""
        #count commits in MMFile
        self.authors[author]["CCMMFile"] = 0
        #avg of all average of commits
        self.authors[author]["commit_ratings_one"] = list()
        self.authors[author]["commit_ratings_two"] = list()
        #mean of all rating of commits
        self.authors[author]["pylint_time"] = list()
        self.authors[author]["time"] = dict()
        self.authors[author]["files"] = list()
        self.authors[author]["metric"] = list()
        self.authors[author]["hyphotetical_rating_one"] = 0.0
        self.authors[author]["hyphotetical_rating_two"] = 0.0
        self.authors[author]["pylint_rating"] = 0.0
        self.authors[author]["radon_rating"] = 0.0
        self.authors[author]["Commit_count"] = 0
        self.authors[author]["added"] = 0
        self.authors[author]["removed"] = 0
        #list of ratings
        self.authors[author]["pylint"] = list()

    def __add_commit_ratings(self, count, file_name):
        """
        This method adds data to the structure for the authors.
        Add:
        pylin+ is counter of how many current author had positive(better
                rating then in previous run) evaluation get by pylint.
        pylint- this is counter how many current author had negativ evaluations.
        MMFile is variable for most modified file
        CCMMFile is variable for count of commits to most modified file
        commit_ratings_one variable for rating geted from first algorithm
        commit_ratings_two variable for rating geted from second algorithm
        pylint_rating variable for rating geted from tool pylint
        radon_rating variable for rating geted from tool radon
        added variable for count of added lines by current author
        removed variable for count of removed lines by current author
        Commit_counbt variable for count all commits for current author
        """
        for author in count.groups.iterkeys():
            if author not in self.authors:
                self.__init_structure(author)
            self.authors[author]["Commit_count"] += len(count.groups[author])
            add = self.files[file_name].groupby("author")["added_counter"].sum()
            self.authors[author]["added"] += add[author]
            rem = self.files[file_name].groupby(["author"])["removed_counter"].sum()
            self.authors[author]["removed"] += rem[author]
            if self.authors[author]["CCMMFile"] < len(count.groups[author]):
                self.authors[author]["CCMMFile"] = len(count.groups[author])
                self.authors[author]["MMFile"] = file_name
            rat = self.files[file_name]
            shas = rat[rat.author == author]["sha"].unique()
            for sha in shas:
                rtime = rat[rat.sha == sha]["time"].values[0]
                comms = rat[rat.sha == sha]["rating_one"].mean()
                index = rat[rat.sha == sha]["range"].values[0]
                comms_two = rat[rat.sha == sha]["rating_two"].mean()
                self.authors[author]["commit_ratings_one"].append(comms)
                self.authors[author]["commit_ratings_two"].append(comms_two)
                if rtime in self.authors[author]["time"]:
                    for item in self.authors[author]["time"][rtime]:
                        if file_name == item["files"]:
                            item["rating_one"] = comms
                            item["rating_two"] = comms_two
                            item["index"] = index
                else:
                    self.authors[author]["time"][rtime] = []
                    self.authors[author]["time"][rtime].append(dict(
                                                        files=file_name,
                                                        rating_one=comms,
                                                        rating_two=comms_two,
                                                        index=index
                                                            ))

    def count_final_rating(self):
        """
        This method creates output structurein JSON based by JsonStructure.
        """
        json_struct = []
        for author in self.authors.keys():
            avg_comm = avg(self.authors[author]["commit_ratings_one"])
            avg_comm_two = avg(self.authors[author]["commit_ratings_two"])
            metrics = avg(self.authors[author]["metric"])
            self.authors[author]["hyphotetical_rating_one"] = avg_comm
            self.authors[author]["hyphotetical_rating_two"] = avg_comm_two
            avg_list_pylint = avg(self.authors[author]["pylint"])
            self.authors[author]["pylint_rating"] = avg_list_pylint
            self.authors[author]["radon_rating"] = metrics
            json_dict = JsonStructure().return_structure()
            json_dict["Name"] = author
            json_dict["Average_Pylint"] = avg_list_pylint
            json_dict["Average_Pylint"] = metrics
            json_dict["Average_Software_Metrics"] = metrics
            json_dict["Average_Commits_Ratings_one"] = avg_comm
            json_dict["Average_Commits_Ratings_two"] = avg_comm_two
            json_dict["Added_lines"] = self.authors[author]["added"]
            json_dict["Removed_lines"] = self.authors[author]["removed"]
            json_dict["All_commits"] = self.authors[author]["Commit_count"]
            json_dict["Pylint_positive"] = self.authors[author]["pylint+"]
            json_dict["Pylint_negative"] = self.authors[author]["pylint-"]
            json_dict["Most_modified_file"] = self.authors[author]["MMFile"]
            json_dict["Commits_to_most_modified_file"] = self.authors[author]["CCMMFile"]
            json_dict["Data"] = []
            ratings = self.authors[author]["time"]
            for date in ratings:
                for idx in ratings[date]:
                    if "pylint" not in idx:
                        continue
                    json_dict["Data"].append(dict(
                                        Pylint_Rating=idx["pylint"],
                                        Date=str(date),
                                        Commit_Rating_v_1=idx["rating_one"],
                                        Commit_Rating_v_2=idx["rating_two"],
                                        Software_Metrics_Rating=idx["metric"]
                                        ))
            json_struct.append(json_dict)

        return json_struct

    class GitData(object):
        """
        This class is for getting contribution, users and other data from
        Git repository.
        """
        def __init__(self, uri, branch="master", project_name="project",
                         specific_sha=None, threshold=False, correction=False):
            self._data_frame = None
            self.files = {}
            self.project_name = project_name
            self.git_repository = uri
            git_url = re.compile(GIT_URL)
            _uri_safe = ''.join([c for c in uri if c.isalnum()])
            self.repo_path = os.path.join(TMP_DIR, _uri_safe)
            self.__tmp_repository = self.repo_path
            self.index_sha = 0
            self.size = 0
            self.__first = True
            self.__spec_file = []
            self.specific_sha = specific_sha
            if os.path.exists(self.repo_path):
                #dont use cached repo
                shutil.rmtree(self.repo_path)
            if os.path.exists("diff_{0}.txt".format(self.project_name)):
                os.remove("diff_{0}.txt".format(self.project_name))
            is_url = git_url.search(uri)
            if is_url is None:
                self.__repository = Gittle(self.git_repository)
                self.__tmp_repository = self.git_repository
            else:
                if self.git_repository.find(".git") < 0:
                    LOGGER.info(r"Must end .git i will add manualy")
                    self.git_repository += ".git"
                try:
                    LOGGER.info(r'Cloning git repo: {0}'.format(self.repo_path))
                    Gittle.clone(self.git_repository, self.__tmp_repository)
                except InvalidRemoteUrl as err:
                    raise Exception(r"Could not clone repository! Is not url."
                        " Error: {0}".format(err))
                except ValueError as err:
                    raise Exception(r"Is not url."
                        " Error: {0}".format(err))
                except KeyError as err:
                    raise Exception(r"Could not clone repository."
                        " Error: {0}".format(err))
                except RefFormatError:
                    n_path = "/tmp/{0}".format(_uri_safe)
                    if os.path.exists(n_path):
                        #dont use cached repo
                        shutil.rmtree(n_path)
                    if branch is None:
                        os.system("git clone {0} {1} 2>&1".format(uri, n_path))
                    else:
                        os.system("git clone -b {0} {1} {2} 2>&1"
                                        .format(branch, uri, n_path))
                    self.__tmp_repository = n_path
                self.__repository = Gittle(self.__tmp_repository, origin_uri=uri)
                self.__repository.DEFAULT_BRANCH = branch
            if branch not in self.__repository.branches:
                LOGGER.error("Branch {0} is no in {1}".format(branch, uri))
                raise Exception("Branch {0} is no in {1}".format(branch, uri))
            self.__fill_data(branch, specific_sha)
            self.eval_commit_to_future(threshold, correction)

        def return_repository_path(self):
            """ This method returns path to tmp repository"""
            return self.__tmp_repository

        def __fill_data(self, branch, specific_sha):
            """ This method fill and parsing data to DataFrame."""
            LOGGER.info("Filling data to _data_frame")
            self._data_frame = DataFrame(self.__repository.commit_info(branch=branch))
            try:
                __branch = [sha.id for sha in
                    self.__repository.branch_walker(branch)]
            except ValueError:
                raise Exception(r"This repository dont have {0} branch".format
                                (branch))
            LOGGER.info(r"Go through master branch and using gittle.diff for"
            "getting diff output")
            if specific_sha is None:
                __branch = __branch[::-1]
                self.size = len(__branch)
                self.diff_for_shas(__branch)
            else:
                __branch = __branch[::-1]
                after_comm = [idx for idx, found in enumerate(__branch)
                                        if found.find(specific_sha) >= 0]
                if not any(after_comm):
                    raise Exception("This sha {0} is not in this repo.".format(specific_sha))
                after_sha = __branch[after_comm[0]:]
                self.size = len(after_sha)
                self.diff_for_shas(after_sha)

        def diff_for_shas(self, list_shas):
            """
            Method for itereting through list od shas and call _diff
            method.
            """
            for idx, sha in enumerate(list_shas):
                diff = None
                diff = self.__repository.diff(sha)
                if diff is None or not any(diff):
                    continue
                self._diff({"sha": sha,
                             "diff": diff,
                            "index": idx
                            })

        def _diff(self, params):
            """
            This method take diff and returns from this output added and
            removed lines for evaluation. Also creates file with diff output.
            """
            author = self.find_author_by_sha(params["sha"])
            rtime = self.find_time_by_sha(params["sha"])
            diff = params["diff"]
            for dict_diff in diff:
                fname = dict_diff["new"]["path"]
                if fname == '' or fname is None:
                    fname = dict_diff["old"]["path"]
                if re.search(r".*\.py$", fname) is None:
                    continue
                if re.search(r"setup.py", fname) is not None:
                    continue
                if self.specific_sha is not None:
                    if self.__first:
                        self.__spec_file.append(fname)
                    elif fname not in self.__spec_file:
                        continue
                lines = dict_diff["diff"].split("\n")
                list_lines = []
                list_added = []
                list_removed = []
                add_hashed = []
                rem_hashed = []
                line_num, rem_line = 0, 0
                removed, added, changed = 0, 0, 0
                #counting for graphs is from 0 no from 1
                diff = "\nindex: {0}".format(params["index"])
                diff += " sha: {0}".format(params["sha"])
                diff += " date: {0}\n".format(time.ctime(rtime))
                diff += "LN\tRL\tDIFF\n"
                name_diff = "diff_{0}.txt".format(self.project_name)
                with open(name_diff, "a") as diff_file:
                    diff_file.write(diff)
                    for line in lines:
                        if len(line) <= 0 or line is None:
                            continue
                        if (line.startswith('diff ') or
                            line.startswith('index ') or
                            line.startswith('--- ') or
                            line.startswith('+++ ') or
                            line.startswith('new mode')):
                            continue
                        if line.startswith('@@ '):
                            _, old_nr, new_nr, _ = line.split(' ', 3)
                            line_num = abs(int(new_nr.split(',')[0]))
                            rem_line = abs(int(old_nr.split(',')[0]))
                            continue
                        if line.startswith(' '):
                            line_num += 1
                            rem_line += 1
                        if line[0] == '-':
                            removed += 1
                            list_removed.append(rem_line)
                            rem_hashed.append(line[1:].encode('base64', 'strict'))
                            rem_line += 1
                        if line[0] == '+':
                            added += 1
                            list_added.append(line_num)
                            add_hashed.append(line[1:].encode('base64', 'strict'))
                            list_lines.append(line_num)
                            line_num += 1
                        diff_file.write("{0}\t{1}\t{2}\n".format((line_num - 1),
                                        (rem_line - 1), line))
                changed = added - abs(removed)
                dict_df = [{
                            "added_lines": list_added,
                            "removed_lines": list_removed,
                            "hash_added": add_hashed,
                            "hash_removed": rem_hashed,
                            "author": author,
                            "sha": params["sha"],
                            "range": params["index"],
                            "rating_one": 100,
                            "rating_two": 100,
                            "removed_counter": removed,
                            "added_counter" : added,
                            "changed_lines": changed,
                            "modification": 0.0,
                            "time": rtime,
                            "file": fname
                            }]
                if fname in self.files:
                    __tmp = DataFrame(dict_df)
                    self.files[fname] = self.files[fname].append(__tmp, ignore_index=True)
                else:
                    self.files[fname] = DataFrame(dict_df)
                self.__first = False

        def eval_commit_to_future(self, thresh_fl, correction):
            """
            Using this method I will check through all the saved commits and
            evaluate the theoretic quality of these commits. Both algorithms
            used here are based on a simple principle of added and removed
            lines. According to these algorithms, there is a calculation of
            the rating.
            Output data structure is:
            sha1-> range, removed_counter, added_counter, added_lines,
            removed_lines, rating_one, rating_two etc.
            sha2-> range, removed_counter, added_counter, added_lines,
            removed_lines, rating etc.
            etc.
            The direction of rating goes from the first commit to the last one.
            There are two different ways. The first algorithm ends if there are
            no lines left of if it reaches the end of list. After that the rate
            is being calculated.
            The second algorithm is set for default rating value of 100. It
            subtracts value from this default one and is calculated this way:
            value = (100/added_lines) * removed lines
            """
            for file_name in self.files.keys():
                file_ = self.files[file_name]
                #get size of df
                size = file_.count().values[0]
                for row in xrange(size):
                    #start index
                    start_index = row + 1
                    # how many commits we must iterate
                    max_size = size - start_index
                    added_lines = list(file_.at[row, "hash_added"])
                    threshold = max_size * 0.1
                    rating = 4
                    #special case when was only removing
                    if not any(added_lines):
                        continue
                    rating_two = 100
                    minus_val = len(added_lines)
                    for idx in xrange(start_index, size):
                        for line in (file_.at[idx, "hash_removed"]):
                            if line in added_lines:
                                added_lines.remove(line)
                                rating_two -= (100 / minus_val)
                                added_lines = added_lines
                        if len(added_lines) <= 0:
                            range_ = idx - start_index
                            rating = calculate_rating(range_, threshold)
                            break
                        if thresh_fl and idx >= (threshold * 5):
                            rating = 4
                            break
                    first_added = len(file_.at[row, "hash_added"])
                    if correction:
                        if rating > 1 and len(added_lines) < first_added / 4:
                            rating -= 2
                        elif rating > 0 and len(added_lines) < first_added / 2:
                            rating -= 1
                    rating = (rating / 4) * 100
                    self.files[file_name].at[row, "rating_one"] = rating
                    self.files[file_name].at[row, "rating_two"] = rating_two

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
                LOGGER.warning(r"Sha {0}, {1} is not in data frame.".format(sha, index))
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
                LOGGER.warning("Sha {0}, {1} is not in data frame.".format(sha, index))
            return None

        def rollback(self, sha):
            """
            This method will make rollback to version which is set by sha.
            """
            try:
                self.__repository.checkout_all(sha)
            except IOError:
                LOGGER.warning("Couldn't rollback on sha {0}.".format(sha))
            except KeyError:
                LOGGER.warning("Couldn't rollback on sha {0}.".format(sha))

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
    PARSER.add_argument("--specific_sha", default=None,
                        help="set specific sha what we wanna evaluate")
    PARSER.add_argument("--no_to_file", action='store_false',
                        help="enable if we don't wanna save graph to file,"
                        "default is master branch")
    PARSER.add_argument("--no_d3", action='store_false',
                        help="enable if we don't wanna save graph like d3 "
                        "graph,")
    PARSER.add_argument("--corrections", action='store_true',
                        help="set argument corrections for hyphotetical,"
                        "algorithm")
    PARSER.add_argument("--threshold", action='store_true',
                        help="enable argument threshold for hyphotetical "
                        "algorithm,")
    PARSER.add_argument("--allow_subplots", action='store_true',
                        help="enable argument for sublots")
    PARSER.add_argument("--graph_by_dates", action='store_false',
                        help="enable graph where is x axis set by dates.")
    PARSER.add_argument("debug", action='store_true',
                        help="enable debugging output")
    ARGS = PARSER.parse_args()
    PATH = ARGS.path
    SHA = ARGS.specific_sha
    BRANCH = ARGS.branch
    DEBUG = ARGS.debug
    TO_FILE = ARGS.no_to_file
    GRAPH_D3 = ARGS.no_d3
    CORRECTIONS = ARGS.corrections
    THRESHOLD = ARGS.threshold
    SUBPLOT = ARGS.allow_subplots
    DATES = ARGS.graph_by_dates
    if DEBUG:
        LOGGER.setLevel(logging.DEBUG)
    QMETRIC = QMetric(PATH, BRANCH, SHA, THRESHOLD, CORRECTIONS)
    graph_authors(QMETRIC.authors, SUBPLOT, GRAPH_D3, TO_FILE, DATES)
