# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 18:58:08 2014

@author: Radim Spigel
"""
import argparse
from GitData import GitData
from SWQuality import ProjectQuality

class GetParameters(object):
    """
        This class is for getting parameters from command line.
    """


    def __init__(self):
        """Initialization and return arguments to instance."""
        self.args = None
        self.arg_parser()
        #self.return_parameter()

    def arg_parser(self):
        """This method is for inicialization of argparser and add options.

        """
        parser = argparse.ArgumentParser(description="This program is for\
        evaluation of quality of project based on hypothetical patterns of\
        quality. Like a first argument insert the Git repository which you\
        want to evaluate.")
        parser.add_argument("path", type=str, help="www or path to git\
        repository this choice evaluate project with default settings. \
        This means that in browser will be started webpage with\
        vizualization of quality.")
        parser.add_argument("--result_file", type=file,
                            help="this choice evaluate project \
                            with default settings patterns of quality.\
                            In browser will be webpage with vizualization \
                            of quality + will be generated result.txt which\
                            will be contain complete report of computation.\
                            Others arguments are used for setting weight of\
                            individual patterns of quality.")
        parser.add_argument("--sw_metrics", help="will be computed quality of \
        of project and also software metrics.")
        parser.add_argument("--bug_w", type=int, choices=range(1, 11),
                            help="weight of bug evaulation.\
                            Default settings is 3.")
        parser.add_argument("--error_density_w", type=int, choices=range(1, 11),
                            help="weight of\
                            error density. Default settings is 5.")
        parser.add_argument("--fatal_error_density_w", type=int,
                            choices=range(1, 11),
                            help="weight of fatal error density. \
                            Default settings is 5.")
        parser.add_argument("--convention_density_w", type=int,
                            choices=range(1, 11),
                            help="weight of\
                            convention density. Default settings is 5.")
        parser.add_argument("--refactor_density_w", type=int,
                            choices=range(1, 11),
                            help="weight of\
                            error density. Default settings is 5.")
        parser.add_argument("--mod_contrib_w", type=int, choices=range(1, 11),
                            help="weight of modification contribution.\
                            Default settings is 5.")
        parser.add_argument("--setting_file", type=file,
                            help="this choice will load setting file for\
                            setting all wanted parameters. Example of content\
                            the file: bug_w=4,result_file,warning_density=6")
        self.args = parser.parse_args()
        #self.return_parameter()


    def return_parameter(self):
        """ This method returns dictionary of parameters."""
        print self.args
        return self.args.path


if __name__ == "__main__":
    PATH = GetParameters().return_parameter()
    GIT_DATA = GitData(PATH)
    QUALITY = ProjectQuality(GIT_DATA.return_repository_path(),\
    GIT_DATA)
