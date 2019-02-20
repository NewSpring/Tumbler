import json
import os
import time

import requests
from dotenv import load_dotenv


def _isValidDir(directory):
    dirname = os.path.dirname(directory)
    if os.path.exists(dirname): return True
    print(
        "Not a valid directory name, make sure you're not using ~ or any shorthand"
    )
    return False


def _isHubInstalled():

    # check for hub
    print("Checking for hub...")
    if os.system("which hub"):
        print("Need to install hub to create PRs. Run `brew install hub`.")
        return False
    return True


def _cloneRock(rockDir):

    # clone Rock if it doesn't exist in the current directory
    if os.path.exists(rockDir):
        return False
    print("Cloning into " + rockDir + " directory...")
    os.system("hub clone NewSpring/Rock " + rockDir)
    return True


def _cleanup(deleteRepo=False):

    # delete the Rock repo
    if deleteRepo:
        os.system("rm -rf Rock")
    os.system("git push --delete origin sync-pre-alpha")
    os.system("git checkout alpha")
    os.system("git branch -D sync-pre-alpha")


def _pushPreAlpha(rockDir):

    # switch to Rock directory
    os.chdir(rockDir)
    # fetch branches from remote and pulls latest
    os.system("hub sync")
    # checkout alpha branch
    os.system("git checkout alpha")
    # set up Spark as remote
    os.system(
        "git remote add SparkDevNetwork https://github.com/SparkDevNetwork/Rock.git"
    )
    # get Spark remote branches
    os.system("git fetch SparkDevNetwork")
    # create pre-alpha branch from spark off of NewSpring alpha
    os.system(
        "git checkout -b sync-pre-alpha SparkDevNetwork/pre-alpha-release")
    # merge alpha into pre-alpha branch
    os.system("git merge alpha")
    # push pre alpha branch
    os.system("git push --set-upstream origin sync-pre-alpha")


def _runBuild(authKey):

    # POST request to start appveyor build
    data = {
        "accountName": "NewSpring",
        "projectSlug": "rock",
        "branch": "sync-pre-alpha",
    }
    headers = {"Authorization": "Bearer" + authKey}
    r = requests.post(
        "https://ci.appveyor.com/api/builds", data=data, headers=headers)
    print(r.text)


def _checkBuild():

    status = ""
    start = time.clock()
    print("\n")
    while status not in ["success", "fail"]:
        elapsed = time.clock() - start
        print("\rwaiting on AppVeyor build({}s)...".format(elapsed))
        r = requests.get(
            "https://ci.appveyor.com/api/projects/NewSpring/rock/branch/sync-pre-alpha"
        )
        status = r.json()["build"]["status"]
        if elapsed > 30:
            print(status)
            return False


def sync(rockDir="Rock"):
    """This will sync Rock pre-alpha with our alpha branch."""

    # load environment variables
    load_dotenv()

    # first make sure a valid directory was passed
    if not _isValidDir(rockDir): return 1

    # check that hub is installed
    if not _isHubInstalled(): return 1

    # if Rock doesn't exist, clone it and delete it later
    deleteRepo = False
    if _cloneRock(rockDir): deleteRepo = True

    # checkout alpha branch
    _pushPreAlpha(rockDir)

    # get AppVeyor API Key
    authKey = os.getenv("APPVEYOR_KEY")

    # run appveyor build on pre-alpha
    _runBuild(authKey)

    # check for status of build and wait until it completes
    # _checkBuild()

    # cleanup repo and stale branches
    _cleanup(deleteRepo)


sync("/Users/michael.neeley/Documents/Projects/Rock")
