#!/usr/bin/env python
#############################################################################
##
## Copyright (C) 2013 Digia Plc and/or its subsidiary(-ies).
## Contact: http://www.qt-project.org/legal
##
## This file is part of the release tools of the Qt Toolkit.
##
## $QT_BEGIN_LICENSE:LGPL$
## Commercial License Usage
## Licensees holding valid commercial Qt licenses may use this file in
## accordance with the commercial license agreement provided with the
## Software or, alternatively, in accordance with the terms contained in
## a written agreement between you and Digia.  For licensing terms and
## conditions see http://qt.digia.com/licensing.  For further information
## use the contact form at http://qt.digia.com/contact-us.
##
## GNU Lesser General Public License Usage
## Alternatively, this file may be used under the terms of the GNU Lesser
## General Public License version 2.1 as published by the Free Software
## Foundation and appearing in the file LICENSE.LGPL included in the
## packaging of this file.  Please review the following information to
## ensure the GNU Lesser General Public License version 2.1 requirements
## will be met: http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html.
##
## In addition, as a special exception, Digia gives you certain additional
## rights.  These rights are described in the Digia Qt LGPL Exception
## version 1.1, included in the file LGPL_EXCEPTION.txt in this package.
##
## GNU General Public License Usage
## Alternatively, this file may be used under the terms of the GNU
## General Public License version 3.0 as published by the Free Software
## Foundation and appearing in the file LICENSE.GPL included in the
## packaging of this file.  Please review the following information to
## ensure the GNU General Public License version 3.0 requirements will be
## met: http://www.gnu.org/copyleft/gpl.html.
##
##
## $QT_END_LICENSE$
##
#############################################################################

# import the print function which is used in python 3.x
from __future__ import print_function

# built in imports
import copy
from distutils.spawn import find_executable # runCommand method
import os
import signal
import sys
import time
import urllib
from urlparse import urlparse
import shutil
import subprocess
import traceback

# own imports
import environmentfrombatchfile

# make a timeout for download jobs
import socket
socket.setdefaulttimeout(30)

class DirRenamer(object):
    def __init__(self, path, newName):
        self.oldName = path
        self.newName = os.path.join(os.path.split(path)[0], newName)
        print("self.oldName: " + self.oldName)
        print("self.newName: " + self.newName)
    def __enter__(self):
        if self.oldName != self.newName:
            os.rename(self.oldName, self.newName)
    def __exit__(self, type, value, traceback):
        if self.oldName != self.newName:
            os.rename(self.newName, self.oldName)

def compress(path, directoryName, sevenZipTarget, callerArguments):
    sevenZipExtension = os.extsep + '7z'
    parentDirectoryPath = os.path.abspath(os.path.join(path, '..'))
    if os.path.splitext(sevenZipTarget)[1] != sevenZipExtension:
        sevenZipTarget = sevenZipTarget + sevenZipExtension
    sevenZipFileName = os.path.split(sevenZipTarget)[1]
    with DirRenamer(path, directoryName) as otherThing:
        runCommand(' '.join(('7z a -mx9', sevenZipFileName, directoryName)), parentDirectoryPath, callerArguments)

    currentSevenZipPath = os.path.join(parentDirectoryPath, sevenZipFileName)
    if currentSevenZipPath != sevenZipTarget:
        shutil.move(currentSevenZipPath, sevenZipTarget)

def getFileNameFromUrl(url):
    return os.path.basename(urlparse(url).path)

def stripVars(object, chars):
    for key, value in vars(object).items():
        if isinstance(value, str):
            setattr(object, key, value.strip(chars))

def removeDir(path, raiseNoException = False):
    if os.path.isdir(path):
        print("remove directory: ", path)
        try:
            shutil.rmtree(path)
        except:
            if raiseNoException:
                pass # just do nothing if raiseNoException is True
            else:
                raise

def download(url, savefile):
    # use an inner function to have one function for each download
    def my_reporthook(count, blocksize, totalsize):
        if my_reporthook.infoString is None:
            my_reporthook.infoString = "Downloading a file with size {} bytes to {}".format(
                totalsize, savefile)
            print(my_reporthook.infoString)
        fraction = min(1, float(count * blocksize) / totalsize)
        sys.stdout.write("\r{:.1%}".format(fraction))
        #sys.stdout.flush() # it works without that, maybe because of the not blocked mainthread (?)

    # now a download can be a local path
    if os.path.lexists(url) and os.path.isfile(url):
        shutil.copy2(url, savefile)
        return

    savefile_tmp = os.extsep.join((savefile, 'tmp'))

    try:
        os.makedirs(os.path.dirname(savefile_tmp))
    except: pass
    my_reporthook.infoString = None

    urllib.urlcleanup()
    try:
        urllib.urlretrieve(url, savefile_tmp, reporthook = my_reporthook)
    except IOError:
        type_, value_, traceback_ = sys.exc_info()
        sys.stderr.write((os.linesep + "{}: {}" + os.linesep).format(url, value_))
        sys.exit(1)
    try:
        try:
            os.rename(savefile_tmp, savefile)
        except WindowsError:
            # if it still exists just try that after a microsleep
            if os.path.lexists(savefile_tmp):
                time.sleep(1)
                os.rename(savefile_tmp, savefile)
    except:
        raise
    finally: # this is done before the except code is called
        try:
            os.remove(savefile_tmp)
        except: #swallow, do not shadow actual error
            pass

def setValueOnEnvironmentDict(environment, key, value):
    if key in environment:
        environment[key] = os.pathsep.join((value, environment[key]))
    else:
        environment[key] = value

def getEnvironment(init_environment = {}, callerArguments = None):

    # first take the one from the system and use the plain dictionary data for that
    environment = os.environ.__dict__["data"]

    if hasattr(callerArguments, 'environment_batch') and callerArguments.environment_batch:
        environment = environmentfrombatchfile.get(
            callerArguments.environment_batch, arguments = callerArguments.environment_batch_argument)

    if (hasattr(callerArguments, 'gnuwin32binpath') and callerArguments.gnuwin32binpath and
        os.path.lexists(callerArguments.gnuwin32binpath)):
        setValueOnEnvironmentDict(environment, 'Path', callerArguments.gnuwin32binpath)

    if hasattr(callerArguments, 'pythonpath') and callerArguments.pythonpath:
        setValueOnEnvironmentDict(environment, 'Path', callerArguments.pythonpath)
    if hasattr(callerArguments, 'perlpath') and callerArguments.perlpath:
        setValueOnEnvironmentDict(environment, 'Path', callerArguments.perlpath)
    if hasattr(callerArguments, 'icupath') and callerArguments.icupath:
        setValueOnEnvironmentDict(environment, 'Path', os.path.join(callerArguments.icupath, 'bin'))
        setValueOnEnvironmentDict(environment, 'INCLUDE', os.path.join(callerArguments.icupath, 'include'))
        setValueOnEnvironmentDict(environment, 'LIB', os.path.join(callerArguments.icupath, 'lib'))
    if hasattr(callerArguments, 'opensslpath') and callerArguments.opensslpath:
        setValueOnEnvironmentDict(environment, 'Path', os.path.join(callerArguments.opensslpath, 'bin'))
        setValueOnEnvironmentDict(environment, 'INCLUDE', os.path.join(callerArguments.opensslpath, 'include'))
        setValueOnEnvironmentDict(environment, 'LIB', os.path.join(callerArguments.opensslpath, 'lib'))

    # just merge the added environment with the generated one
    if not environment:
        return init_environment
    elif environment and init_environment:
        for key in environment.viewkeys() & init_environment.viewkeys():
            # merge most of they values, but exclude some of it
            if not any((key == "QMAKESPEC", key == "MAKEFLAGS")):
                environment[key] = os.pathsep.join((init_environment[key], environment[key]))
        for key in init_environment.viewkeys() - environment.viewkeys():
             environment[key] = init_environment[key]
    return environment

def runCommand(command, currentWorkingDirectory, callerArguments = None,
    abort_on_fail = True, init_environment = None):

    environment = getEnvironment(init_environment, callerArguments)

    exitCode = -1
    commandAsList = command[:].split(' ')

    # add some needed pathes and use try to throw away with nothing
    # if that property is not existing
    if hasattr(callerArguments, 'gitpath') and callerArguments.gitpath and commandAsList[0] == 'git':
        commandAsList[0] = os.path.abspath(os.path.join(callerArguments.gitpath, 'git'))
    if hasattr(callerArguments, 'perlpath') and callerArguments.perlpath and commandAsList[0] == 'perl':
        commandAsList[0] = os.path.abspath(os.path.join(callerArguments.perlpath, 'perl'))
    if hasattr(callerArguments, 'sevenzippath') and callerArguments.sevenzippath and commandAsList[0] == '7z':
        commandAsList[0] = os.path.abspath(os.path.join(callerArguments.sevenzippath, '7z'))

    # if we can not find the command, just check the current working dir
    if not os.path.lexists(commandAsList[0]) and currentWorkingDirectory and \
        os.path.lexists(os.path.abspath(os.path.join(currentWorkingDirectory, commandAsList[0]))):
        commandAsList[0] = os.path.abspath(os.path.join(currentWorkingDirectory, commandAsList[0]))

    if 'Path' in environment:
        pathEnvironment = environment['Path']
    elif 'PATH' in environment:
        pathEnvironment = environment['PATH']
    # if we can not find the command, check the environment
    if not os.path.lexists(commandAsList[0]) and find_executable(commandAsList[0], pathEnvironment):
        commandAsList[0] = find_executable(commandAsList[0], pathEnvironment)

    if currentWorkingDirectory and not os.path.lexists(currentWorkingDirectory):
        os.makedirs(currentWorkingDirectory)

    print('========================== do ... ==========================')
    if currentWorkingDirectory:
        print("Working Directory: " + currentWorkingDirectory)
    else:
        print("No currentWorkingDirectory set!")
    print("Last command:      " + ' '.join(commandAsList))

    try:
        if currentWorkingDirectory and not os.path.lexists(currentWorkingDirectory):
            raise Exception("The current working directory is not existing: %s" % currentWorkingDirectory)

        process = subprocess.Popen(commandAsList,
            stdout = subprocess.PIPE, stderr = None,
            cwd = currentWorkingDirectory, bufsize = -1, env = environment)
        while process.poll() is None:
            sys.stdout.write(process.stdout.read(512))

        process.stdout.close()

        exitCode = process.returncode

        if exitCode != 0:
            raise Exception("None zero exit code: %d" % exitCode)
    except:
        if abort_on_fail:
            sys.stderr.write(os.linesep + '======================= error =======================' + os.linesep)
            sys.stderr.write("Working Directory: " + currentWorkingDirectory + os.linesep)
            sys.stderr.write("Last command:      " + ' '.join(commandAsList) + os.linesep)
            traceback.print_exc()
            # lets keep that for debugging
            #if environment:
            #    for key in environment:
            #        sys.stderr.write("set " + key + "=" + environment[key] + os.linesep)
            sys.stderr.write(os.linesep + '======================= error =======================' + os.linesep)
            sys.exit(1)
    return exitCode


def runInstallCommand(arguments = 'install', currentWorkingDirectory = None, callerArguments = None, init_environment = {}):
    installcommand = 'make'
    if hasattr(callerArguments, 'installcommand') and callerArguments.installcommand:
        installcommand = callerArguments.installcommand

    if arguments:
        installcommand = ' '.join((installcommand, arguments))
    runCommand(installcommand, currentWorkingDirectory, callerArguments, init_environment = init_environment)

def runBuildCommand(arguments = None, currentWorkingDirectory = None, callerArguments = None, init_environment = {}):
    buildcommand = 'make'
    if hasattr(callerArguments, 'buildcommand') and callerArguments.buildcommand:
        buildcommand = callerArguments.buildcommand

    if arguments:
        buildcommand = ' '.join((buildcommand, arguments))
    runCommand(buildcommand, currentWorkingDirectory, callerArguments, init_environment = init_environment)

def getReturnValue(command, currentWorkingDirectory = None, init_environment = {}, callerArguments = None):
    commandAsList = command[:].split(' ')
    return subprocess.Popen(commandAsList, stdout=subprocess.PIPE, stderr = subprocess.STDOUT,
        cwd = currentWorkingDirectory, env = getEnvironment(init_environment, callerArguments)).communicate()[0].strip()

def gitSHA(path, callerArguments = None):
    gitBinary = "git"
    if hasattr(callerArguments, 'gitpath') and callerArguments.gitpath:
        gitBinary = os.path.abspath(os.path.join(callerArguments.gitpath, 'git'))
    if isGitDirectory(path):
        return getReturnValue(gitBinary + " rev-list -n1 HEAD", currentWorkingDirectory = path, callerArguments = callerArguments).strip()
    return ''

def isGitDirectory(repository_path):
    if not repository_path:
        return False
    gitConfigDir = os.path.abspath(os.path.join(repository_path, '.git'))
    return os.path.lexists(gitConfigDir)