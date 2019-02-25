import json
import os
import time

import requests
from dotenv import load_dotenv

from tumblerLogging import getLogger

# get custom logger
logger = getLogger()


def _validDir(directory):
    dirname = os.path.dirname(directory)
    if not os.path.exists(dirname):
        print(
            "Not a valid directory name, make sure you're not using ~ or any shorthand"
        )
        return 1
    return 0


def _hubInstalled():

    # check for hub
    logger.info("Checking for hub...")
    if os.system("which hub"):
        logger.error("Need to install github/hub to create PRs.")
        return 1
    return 0


def _cloneRock(rockDir):

    # clone Rock if it doesn't exist in the current directory
    if os.path.exists(rockDir):
        return 0
    os.system("git clone https://github.com/NewSpring/Rock.git " + rockDir)
    return 1


def _checkout(branch):

    # checkout and update branch
    r = os.popen("git checkout {}".format(branch)).read()
    if "up to date" not in r: os.system("git pull")


def _cleanup(deleteRemote=True):

    # delete the local and remote branches
    _checkout("master")
    if deleteRemote: os.system("git push --delete origin sync-pre-alpha")
    os.system("git branch -D sync-pre-alpha")


def _createPreAlpha(rockDir):

    # switch to Rock directory
    os.chdir(rockDir)

    # get Spark remote branches
    if "SparkDevNetwork" not in os.popen("git remote").read():
        # set up Spark as remote
        os.system(
            "git remote add SparkDevNetwork https://github.com/SparkDevNetwork/Rock.git"
        )
    os.system("git fetch SparkDevNetwork")

    # create pre-alpha branch from spark off of NewSpring alpha
    if "sync-pre-alpha" not in os.popen("git branch").read():
        os.system(
            "git checkout -b sync-pre-alpha SparkDevNetwork/pre-alpha-release")

    # push pre alpha branch
    os.system("git push --set-upstream origin sync-pre-alpha")


def _getSHA():

    # this will return the last commit SHA-1 hash
    return os.popen("git rev-parse --short HEAD").read().strip("\n")


def _getBranch():

    # this will get the current branch name
    return os.popen("git rev-parse --abbrev-ref HEAD").read().strip("\n")


def _merge(destination, source):

    _checkout(source)
    _checkout(destination)

    # merge source into destination branch
    if "up to date" in os.popen(
            "git merge {} -m \"Merge from NewSpring/{}\"".format(
                source, source)).read():
        logger.info("No changes to sync")
        return 1

    # loop over files that the source deleted
    # TODO: don't need to ask about every file, just show them all
    # and ask yes or no
    deletedBySource = os.popen(
        "git diff --name-only --diff-filter=UD").read().split("\n")
    for file in deletedBySource:
        if not os.path.exists(file): continue
        choice = input("Safe to delete '{}'? (y/n) ".format(file))
        if choice.lower() not in ["y", "yes"]:
            print("Fix conflicts manually and run again.")
            return 1
        os.system("git rm {}".format(file))

    if os.popen("git diff --diff-filter=U").read() != "":
        print("Some can't be resolved. Fix conflicts manually and run again.")
        return 1

    # merge commit
    os.system("git commit -am \"Merge conflicts resolved\"")

    # push destination branch
    os.system("git push --set-upstream origin {}".format(destination))
    return 0


def _build(branch, authKey):

    # POST request to start appveyor build
    data = {
        "accountName": "NewSpring",
        "projectSlug": "rock",
        "branch": branch,
    }
    headers = {"Authorization": "Bearer " + authKey}
    r = requests.post(
        "https://ci.appveyor.com/api/builds", data=data, headers=headers)


def _buildCheck(branch):

    # wait until the current commit is the one being built
    commit = _getSHA()
    buildCommit = ""
    start = round(time.perf_counter())
    while commit not in buildCommit:
        elapsed = round(time.perf_counter()) - start
        if elapsed > 30:
            print("\nTimeout. Branch '{}' not building.".format(branch))
            return 1
        print(
            "\rVerifying automatic AppVeyor build ({}s)...".format(elapsed),
            end="")
        r = requests.get(
            "https://ci.appveyor.com/api/projects/NewSpring/rock/branch/{}".
            format(branch))
        buildCommit = json.loads(r.text)["build"]["commitId"]
    print("\n")
    return 0


def _buildStatus(branch):

    # wait on Appveyor build to pass or fail
    status = ""
    start = round(time.perf_counter())
    while status not in ["success", "failed"]:
        elapsed = round(time.perf_counter()) - start
        print("\rWaiting on AppVeyor build ({}s)...".format(elapsed), end="")
        r = requests.get(
            "https://ci.appveyor.com/api/projects/NewSpring/rock/branch/{}".
            format(branch))
        status = json.loads(r.text)["build"]["status"]
    print("\n")
    if status == "success": return 0
    print("Build failed. Debug {} branch and run again.".format(branch))
    return 1


def _deploy(branch, envID, authKey):

    # get Appveyor environment name
    headers = {"Authorization": "Bearer {}".format(authKey)}
    r = requests.get(
        "https://ci.appveyor.com/api/environments/{}/deployments".format(
            envID),
        headers=headers)
    envName = json.loads(r.text)["environment"]["name"]

    # make POST request to trigger deployment
    data = {
        "environmentName": envName,
        "accountName": "NewSpring",
        "projectSlug": "rock"
    }
    r = requests.post(
        "https://ci.appveyor.com/api/deployments", data=data, headers=headers)
    print("Deployment to {} started.".format(envName))


def _safeMerge(destination, source):

    # first merge destination branch into source so we can test the build
    if _merge(source, destination): return 1

    # run appveyor build on source branch if it's not automatic
    if _buildCheck(source): _build(source, os.getenv("APPVEYOR_KEY"))

    # after build passes, we can safely merge
    if _buildStatus(source): return 1

    # merge source into destination
    if _merge(destination, source): return 1


def _pr(base):

    head = _getBranch()
    if os.system(
            "hub pull-request -b {} -m \"Merge from NewSpring/{}\"".format(
                base, head)):
        return 1
    print("Created {} -> {} PR. Ready to merge and deploy {} manually.".format(
        head, base, base))
    return 0


def sync(rockDir="/tmp/Rock",
         alpha="alpha",
         beta="beta",
         prAlpha=False,
         prBeta=True):
    """This will sync Rock pre-alpha with our alpha branch."""

    logger.info("Syncing pre-alpha...")

    # load environment variables
    load_dotenv()

    # first make sure a valid directory was passed
    if _validDir(rockDir): return 1

    # check that hub is installed
    if _hubInstalled(): return 1

    # if Rock doesn't exist, clone it and delete it later
    _cloneRock(rockDir)

    # checkout alpha branch
    _createPreAlpha(rockDir)

    # stopping at alpha PR
    if prAlpha:
        # if making the PR fails, delete the remote branch too
        if _pr(alpha):
            _cleanup()
            return 1
        # if alpha PR was successful, don't delete the remote branch
    else:
        # merge pre alpha into alpha after it builds successfully
        if _safeMerge(alpha, "sync-pre-alpha"): return 1

        if prBeta:
            _pr(beta)
        else:
            if _safeMerge(beta, alpha): return 1
            _deploy(destination, os.getenv("APPVEYOR_ENV"),
                    os.getenv("APPVEYOR_KEY"))

    # if alpha was made, don't delete remote pre-alpha branch
    _cleanup(not prAlpha)


# sync("/Users/michael.neeley/Documents/Projects/Rock", "alpha", "beta", True, True)
