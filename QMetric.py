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
from subprocess import Popen, PIPE
import pylab
from collections import deque
import pickle
from dulwich.errors import RefFormatError 

TMP_DIR = tempfile.gettempdir()

LOG_FORMAT = "%(name)s:%(asctime)s:%(message)s"
logging.basicConfig(format=LOG_FORMAT, filename="logfile.log")
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
GIT_URL = r'(git://github.com/|https://github.com/|git@github.com:)(.*)'

def pylab_graph(ratings):
    """
    This function prints graphs with library pylab.
    """
    for author in ratings:
        l_comm = [item["rating"] for item in ratings[author]["time"]]          
        if (len(ratings[author]["pylint"]) !=
            len(l_comm)):
            LOGGER.info("{0}: Rating for pylint and for commit is "
                    "not match! pylint: {1} != commits {2}"
                    .format(author, len(ratings[author]["pylint"]),
                            len(l_comm)))
                          
        if(len(l_comm) < 2):
            LOGGER.info("{0}: Rating for commit"
                    " is lesser then 2.".format(author))
            continue
        pylab.title("Author: {0}".format(author))
        #pylab.ylim([0, 11])
        pylab.subplot(311)
        pylab.plot(l_comm, color="red")
        pylab.subplot(312)
        pylab.plot(ratings[author]["pylint"], color="blue")
        #pylab.ylim([50, 100])
        pylab.subplot(313)
        pylab.plot(ratings[author]["metrics"], color="green")
        author = author.replace(" ", "_")
        author = author.replace(".", "")
        pylab.savefig(r"graph_rep_{0}".format(author))
        pylab.clf()

def eval_static_metrics(filee):
    """
    This function calls radon which evaluate static metric for file.
    """
    s_metric = Popen(("radon mi {0}".format(filee)).split(),
                       stdout=PIPE) 
                    
    mindex = s_metric.stdout.read()
    mi__ = 0
    if re.search(r"- ([^ /])", mindex) is not None:
        mi__ = ord(re.search(r"- ([^ /])", mindex).group(1))
        mi__ -= 70
        mi__ = abs(mi__)
        mi__ /= 5
        mi__ *= 100
    s_metric = Popen(("radon raw {0}".format(filee)).split(),
                       stdout=PIPE) 
    raw = s_metric.stdout.read()
    raws = {}
    r_patt = re.compile(r"LOC  ([\d]+)[\s]*LLOC: ([\d]+)[\s]*SLOC: ([\d]+).*")
    if r_patt.search(raw) is not None:
        found_raw = r_patt.search(raw)
        print found_raw.group(1), found_raw.group(2), found_raw.group(3)
    if re.search(r"^LOC: ([\d]+)", raw) is not None:
        raws["LOC"] = re.search(r"^LOC: ([\d]+)", raw).group(1)
    if re.search(r"^LLOC: ([\d]+)", raw) is not None:
        raws["LLOC"] = re.search(r"^LOC: ([\d]+)", raw).group(1)
    if re.search(r"^SLOC: ([\d]+)", raw) is not None:
        raws["SLOC"] = re.search(r"^LOC: ([\d]+)", raw).group(1)
    if re.search(r"^LOC: ([\d]+)", raw) is not None:
        raws["LOC"] = re.search(r"^LOC: ([\d]+)", raw).group(1)
    #print raw
    s_metric = Popen(("radon cc -a {0}".format(filee)).split(),
                       stdout=PIPE) 
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
    pylint = Popen(("pylint --rcfile=/tmp/rc -f text %s" % filee).split(),
                       stdout=PIPE)
    output = pylint.stdout.read()
    str_rating = r"Your code has been rated at ([-\d\.]+)\/10 "
    str_rating += r"(\(previous run: ([\d\.]+)\/10.*)?"
    results_re = re.compile(str_rating)
    frating = results_re.search(output)
    metric = eval_static_metrics(filee)
    if frating is None:
        LOGGER.warning("No pylint rating for {0} with shas {1}".format
                (filee, sha))
        return {}
    return dict(
            actual_rated=frating.group(1),
            previous_rated=frating.group(3),
            pylint_file=filee,
            metrics=metric,
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

def avg(list_el):
    """This method returns average value for list"""
    if len(list_el) > 0:
        return sum(list_el) / len(list_el)
    else:
        return 0.0

def generate_report(project_name, ratings):
    """ Function for generating report """
    report = "Project: %s\n" % (project_name,)
    for author in ratings:
        report += "#########################################################\n"
        report += "======================================================\n"
        report += "Authors: {0}\n".format(author)
        report += "Current average (hyphotetical + pylint) quality of project"
        report += (" is : {0} \n".format(ratings[author]["final_rating"]))
        report += "Current average hyphotetical quality of project"
        report += (" is : {0} \n"
                            .format(ratings[author]["hyphotetical_rating"]))
        report += "Current average pylint quality of project"
        report += (" is : {0} \n".format(ratings[author]["pylint_rating"]))
        report += "======================================================\n"
        #_sorted = sorted(ratings[author]["time"], key=itemgetter("time"))        
        for idx, rtime in enumerate(ratings[author]["time"]):
            report += "**************************************************\n"
            report += "Quality of contributor/s:\n"
            report += "File: {0}\n".format(rtime["file"])
            report += "Date: {0}\n".format(time.ctime(rtime["time"]))
            report += "Rating: {0}\n".format(rtime["rating"])
                                    #ratings[author]["avg_comm_rating"][idx])
        report += "**************************************************\n"
        #_sorted = sorted(ratings[author]["pylint_time"], key=itemgetter("time"))
        for ptime in ratings[author]["pylint_time"]:
            report += "---------------------------------------------------\n"
            report += "Pylint rating and static software metric:\n"
            report += "File: {0}\n".format(ptime["files"])
            report += "Date: {0}\n".format(time.ctime(ptime["time"]))
            report += "Rating pylint {0}\n".format(ptime["pylint"])
            report += "Rating pylint {0}\n".format(ptime["metrics"])
        report += "---------------------------------------------------\n"
    report += "#########################################################\n"
    return report

class QMetric(object):
    """This class take like argumet path to the project and data
       from subversion system. This data evaulation and walk truth
       and return data for vizualization.
    """

    def __init__(self, path, branch, specific_sha=None):
        """Inicialization variables for path and subversion data and rc file
            for pylint.
        """
        self.vesion_system = self.GitData(path, branch, specific_sha)
        self._path = self.vesion_system.return_repository_path()
        LOGGER.debug('Repo Path: {0}'.format(self._path))
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
        self.rating = {}
        if self.project_name == "":
            self.project_name = self._path.replace("/", "")
        if os.path.exists("/tmp/{0}_pylint.p".format(self.project_name)):
            LOGGER.info("File with pylint rating exists loading data.")
            self.rate()            
            get_data = pickle.load(open("/tmp/%s_pylint.p" % self.project_name, "rb"))
            for author in self.rating:
                if author not in get_data:
                    LOGGER.warning("For this {0} user is not pylint rating "
                    "in file.".format(author))
                    continue
                self.rating[author]["pylint"] = get_data[author]["pylint"]
                self.rating[author]["pylint_time"] = get_data[author]["pylint_time"]
                self.rating[author]["metrics"] = get_data[author]["metrics"]
        else:
            LOGGER.info("First evaluation could take lot of time must first "
                "time evaluate with pylint.")
            self.__get_pylint()
            pickle.dump(self.rating, 
			open("/tmp/%s_pylint.p" % self.project_name, "wb"))      
            self.rate()
        weights = dict(count_w=0.1, comm_w=0.1, avg_pylint_w=0.1, pylint_w=0.1)
        self.count_final_rating(weights)
        with open("result.txt", "w") as result_file:
            result_file.write(generate_report(self.project_name, self.rating))
        pylab_graph(self.rating)
        #LOGGER.info(generate_report(self.project_name, self.rating))
        #LOGGER.info("Pylint evaluation was %s" % self.count_pylint_eval)

    def __get_pylint(self):
        """This method create dictionary of files in the project."""
        for _file in self.files.keys():
            self.eval_file_in_history(_file)

    def eval_file_in_history(self, filee):
        """This method take file and eval this file by history of commits
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
        """This method call rollback from GitData. This method returns data
        to previous state. Direction is from recent to first commit.
        """
        if file_name not in self.pylint_rating:
            self.pylint_rating[file_name] = []
        for idx, item in enumerate(sha):
            self.vesion_system.rollback(item)
            fname = self._path + "/" + file_name
            self.count_pylint_eval += 1
            LOGGER.info("Start pylint for file: {0}".format(fname))
            self.pylint_rating[file_name].append(eval_pylints(fname, item))
            file_d = self.pylint_rating[file_name][idx]
            try:
                author = self.vesion_system.find_author_by_sha(file_d["sha"])
                if author not in self.rating:
                    self.__init_structure(author)
                if any(file_d):
                    rtime = self.vesion_system.find_time_by_sha(file_d["sha"])
                    actual_rated = float(file_d["actual_rated"])
                    metric = float(file_d["metrics"])
                    self.rating[author]["metrics"].append(metric)
                    self.rating[author]["pylint"].append(actual_rated)
                    self.rating[author]["pylint_time"].append(dict(time=rtime,
                                                     pylint=actual_rated,
                                                     files=file_name,
                                                     metrics=metric
                                                     ))
                    self.rating[author]["files"].append(file_name)
                    # because we direction is from last to first must take prev
                    # with actual
                    if file_d["actual_rated"] < file_d["previous_rated"]:
                        self.rating[author]["pylint-"] += 1
                    elif file_d["actual_rated"] > file_d["previous_rated"]:
                        self.rating[author]["pylint+"] += 1
            except KeyError:
                LOGGER.warning("No sha {0}".format(item))

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
           # count_line = self.files[fname].groupby(["author", "line"])
           # self.__add_average_commit_counts(count_line, count)
            self.__add_another_commit_ratings(count, fname)
            
    def __init_structure(self, author):
        """
        Method for creating structure for authors.
        """
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
        self.rating[author]["avg_count"] = deque()
        #mean of all rating of commits
        self.rating[author]["avg_comm_rating"] = deque()
        self.rating[author]["pylint_time"] = list()
        self.rating[author]["time"] = deque()
        self.rating[author]["files"] = deque()
        self.rating[author]["metrics"] = list()
        self.rating[author]["hyphotetical_rating"] = 0.0
        self.rating[author]["pylint_rating"] = 0.0
        #self.rating[author]["list_comm_ratings"] = []
        #final rating
        self.rating[author]["final_rating"] = 0.0
        #list of ratings
        self.rating[author]["pylint"] = list()

    def __add_another_commit_ratings(self, count, file_name):
        """
        This method count mean value of ratings for every commit getting
        in GitData.modificate_rating. Also search most modified file.
        """
        for author in count.groups.iterkeys():
            if author not in self.rating:
                self.__init_structure(author)            
            if self.rating[author]["CCMMFile"] < len(count.groups[author]):
                self.rating[author]["CCMMFile"] = len(count.groups[author])
                self.rating[author]["MMFile"] = file_name
            rat = self.files[file_name]
            shas = rat[rat.author == author]["sha"].unique()
            self.rating[author]["time"] += [
                dict(time=rat[rat.sha == sha]["time"].unique(),
                 rating=rat[rat.sha == sha]["rating"].mean(),
                 file=file_name) for sha in shas]

    def count_final_rating(self, weight):
        """Count final rating. First i get difference between positive and
        negative rating. Next i get average how many does contributor
        change file/ count all commits to file.
        Another variable is average ratings for commits what this author did
        to file. After that i get average value for every pylint rating for
        all files. Last is total rating which is mean value from this
        variables. For each variables is set weight"""
        for author in self.rating.keys():
            avg_pylint = self.rating[author]["pylint+"]
            avg_pylint -= self.rating[author]["pylint-"]
            avg_pylint *= weight["pylint_w"]
            LOGGER.info("pylint+ {0} pylint- {1} diff {2}".format
                (self.rating[author]["pylint+"], self.rating[author]["pylint-"],
                 avg_pylint))
            avg_count = avg(self.rating[author]["avg_count"]) * 100
            avg_count *= weight["count_w"]
            l_comm = [item["rating"] for item in self.rating[author]["time"]]
            avg_comm = avg(l_comm) * 100
            avg_comm *= weight["comm_w"]
            avg_comm /= 4
            self.rating[author]["hyphotetical_rating"] = avg_comm * 10
            avg_pylint = avg_pylint * weight["avg_pylint_w"]
            avg_list_pylint = avg(self.rating[author]["pylint"])
            self.rating[author]["pylint_rating"] = avg_list_pylint * 10
            final = (avg_count + avg_comm)
            LOGGER.info("Author: {0} \nAvg lines: {1}\nAvg commits:"
            "{2}\nFinal: {3}".format(author, avg_count, avg_comm, final))
            self.rating[author]["avg_pylint"] = avg_list_pylint * 10
            final = (final * 10 + avg_list_pylint * 10) / 2
            if final < 100.0:
                self.rating[author]["final_rating"] = final
            else:
                self.rating[author]["final_rating"] = 100.0
            LOGGER.info(r"Final after eval {0} \nFinal oylint {1}".format
                (self.rating[author]["final_rating"],
                 self.rating[author]["avg_pylint"]))

    class GitData(object):
        """ This class is for getting contribution, users and other data from
        Git repository.
        """
        def __init__(self, uri, branch="master", specific_sha=None, cached=False):
            self._data_frame = None
            self.files = {}
            self.git_repository = uri
            git_url = re.compile(GIT_URL)
            _uri_safe = ''.join([c for c in uri if c.isalnum()])
            self.repo_path = os.path.join(TMP_DIR, _uri_safe)
            self.__tmp_repository = self.repo_path
            self.index_sha = 0
            self.size = 0
            self.__spec_file = None
            self.specific_sha = specific_sha
            if not cached and os.path.exists(self.repo_path):
                #dont use cached repo
                shutil.rmtree(self.repo_path)
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
                    if not cached and os.path.exists(n_path):
                        #dont use cached repo
                        shutil.rmtree(n_path)                    
                    if branch is None:
                        os.system("git clone {0} {1}".format(uri, n_path))
                    else:
                        os.system("git clone -b {0} {1} {2}"
                                        .format(branch, uri, n_path))                        
                    self.__tmp_repository = n_path 
                self.__repository = Gittle(self.__tmp_repository, origin_uri=uri)
                self.__repository.DEFAULT_BRANCH = branch
            if branch not in self.__repository.branches:
                LOGGER.error("Branch {0} is no in {1}".format(branch, uri))
                raise Exception("Branch {0} is no in {1}".format(branch, uri))
            self.__fill_data(branch, specific_sha)
            #self.modificate_rating()
            self.eval_commit_to_future()
            
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
                after_comm = [idx for idx, found in enumerate(__branch) 
                                        if found.find(specific_sha) >= 0]
                after_sha = __branch[after_comm[0]:] 
                after_sha = after_sha[::-1]
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
                        
        def _diff(self, params, print_diff_=False):
            author = self.find_author_by_sha(params["sha"])
            rtime = self.find_time_by_sha(params["sha"])    
            diff = params["diff"]
            for dict_diff in diff:
                fname = dict_diff["new"]["path"]
                if fname == '' or fname == None:
                    fname = dict_diff["old"]["path"]
                if re.search(r".*\.py", fname) is None:
                    continue
                if self.specific_sha is not None:
                    if self.__spec_file is None:
                        self.__spec_file = fname
                    elif fname != self.__spec_file:
                        continue
                if print_diff_:
                    self.print_diff(diff)
                lines = dict_diff["diff"].split("\n")
                list_lines = []
                list_added = []
                list_removed = []
                line_num, rem_line = 0, 0
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
                        line_num = abs(int(new_nr.split(',')[0]))
                        continue
                    if line[0] == ' ':
                        line_num += 1
                        rem_line = line_num
                        continue
                    if line[0] == '-':
                        removed += 1
                        list_removed.append(rem_line)
                        rem_line += 1
                        
                        continue
                    if line[0] == '+':
                        added += 1
                        list_added.append(line_num)  
                        line_num += 1 
                        list_lines.append(line_num)
                        continue
                changed = added - abs(removed)
                dict_df = [{
                            "added_lines": list_added,
                            "removed_lines": list_removed,
                            "author": author,
                            "sha": params["sha"],
                            "range": params["index"],
                            "rating": 4,
                           # "num_lines": 0,
                            "removed_counter": removed,
                            "added_counter" : added,
                            "changed_lines": changed,
                            "modification": 0.0,
                            "time": rtime,
                            "file": fname
                         }]
                if fname in self.files:
                    __tmp = DataFrame(dict_df)
                    self.files[fname] = self.files[fname]\
                                          .append(__tmp, ignore_index=True)
                else:
                    self.files[fname] = DataFrame(dict_df)
                    
        def print_diff(self, diff):
            """
            Method for save fixes in string format with number of lines.
            """
            for dict_diff in diff:
                fname = dict_diff["new"]["path"]
                if fname == '' or fname == None:
                    fname = dict_diff["old"]["path"]
                if re.search(r".*\.py", fname) is None:
                    continue
                if self.specific_sha is not None:
                    if self.__spec_file is None:
                        self.__spec_file = fname
                    elif fname != self.__spec_file:
                        continue
                lcount = 0
                if fname not in self.files:
                    lcount = self.count_lines(fname)                                  
                lines = dict_diff["diff"].split("\n")
                list_lines = []
                line_num, rm = 0, 0
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
                        line_num = abs(int(new_nr.split(',')[0]))
                        continue
                    if line[0] == ' ':
                        list_lines.append(line_num)   
                        line_num += 1
                        rm = line_num
                    if line[0] == '-':
                        rm += 1
                        removed += 1
                    if line[0] == '+':
                        added += 1
                        list_lines.append(line_num)
                        line_num += 1
                    LOGGER.info((line_num-1, rm-1, line))
                changed = added - abs(removed)
                if lcount <= 0:
                    lcount = abs(changed)  
                    
        def eval_commit_to_future(self):
            for file_name in self.files.keys(): 
                file_ = self.files[file_name]
                size = file_.count().values[0]#get size of df
                for row in xrange(size):
                    #start index                
                    start_index = row + 1
                    # how many commits we must iterate
                    max_size = size - start_index
                    added_lines = file_.at[row, "added_lines"]
                    threshold = max_size * 0.1 
                    rating = 4
                    if not any(added_lines):
                        continue #special case when was only removing
                    for idx in xrange(start_index ,size):
                        LOGGER.info("IDX > {0}".format(idx))
                        LOGGER.info("ADDED {0}".format(added_lines))
                        LOGGER.info("REMOVED {0}"
                             .format(file_.at[idx, "removed_lines"]))
                        for line in (file_.at[idx, "removed_lines"]):
                            if line in added_lines:
                                added_lines.remove(line)
                        if len(added_lines) <= 0:
                            range_ = idx - start_index
                            rating = calculate_rating(range_, threshold)
                            break
                        if idx >= (threshold * 5):
                            rating = 4
                            break
                        LOGGER.info("IDX > {0} RATING {1}".format(idx, rating))
                    self.files[file_name].at[row, "rating"] = rating
                    lines = file_.at[row, "added_counter"]
                    lines -= file_.at[row, "removed_counter"]
                        
        def count_lines(self, fname):
            """This method count lines in file"""
            if not os.path.exists(self.__tmp_repository + "/" + fname):
                return 0
            count = 0
            with open(self.__tmp_repository + "/" + fname) as filer:
                for line in filer:
                    count += 1
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
                LOGGER.warning(r"Sha {0}, {1} is not in data frame.".format
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
                LOGGER.warning("Sha {0}, {1} is not in data frame.".format
                            (sha, index))
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
    PARSER.add_argument("debug", action='store_true',
                        help="enable debugging output")
    ARGS = PARSER.parse_args()
    PATH = ARGS.path
    BRANCH = ARGS.branch
    DEBUG = ARGS.debug
    if DEBUG:
        LOGGER.setLevel(logging.DEBUG)
    QMETRIC = QMetric(PATH, BRANCH) #, specific_sha="571388539b6579d7225aca"
