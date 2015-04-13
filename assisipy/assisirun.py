#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tool for remotely running CASU controllers.
"""

from fabric.api import settings, cd, run, env

import yaml

import os.path
import argparse
import subprocess

class AssisiRun:
    """
    Remote execution tool.
    """
    def __init__(self, project_name):
        """
        Constructor.
        """
        
        self.fabfile_name = project_name[:-6] + 'py'
        self.depspec = {}
        with open(project_name) as project:
            project_spec = yaml.safe_load(project)
            with open(project_spec['dep']) as depfile:
                self.depspec = yaml.safe_load(depfile)

        # Running controllers
        self.running = {}

    def run(self):
        """
        Execute the controllers.
        """
        #env.parallel = True
        counter = 0
        for layer in self.depspec:
            for casu in self.depspec[layer]:
                taskname = layer.replace('-','_') + '_' + casu.replace('-','_')
                cmd = 'fab -f {0} {1}'.format(self.fabfile_name, taskname)
                print(cmd)
                self.running[taskname] = subprocess.Popen(cmd,shell='True')

        for taskname in self.running:
            self.running[taskname].wait()

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Run a set of CASU controllers.')
    parser.add_argument('project', help='name of .assisi file specifying the project details.')
    args = parser.parse_args()

    project = AssisiRun(args.project)
    project.run()
