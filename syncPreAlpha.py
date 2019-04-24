import json
import os
import pdb
import time

import requests
from dotenv import load_dotenv

from tumblerLogging import getLogger

# get custom logger
logger = getLogger()


# TODO: don't show all os.system calls, instead only in logger


def _validDir(directory):
    dirname = os.path.dirname(directory)
    if not os.path.exists(dirname):
        logger.error(
            "Not a valid directory name, make sure you're not using ~ or any shorthand"
        )
        return 1
    return 0


def _hubInstalled():

    # check for hub
    logger.info("Checking for hub")
    if os.system("which hub"):
        logger.error("Need to install github/hub to create PRs.")
        return 1
    return 0


def _cloneRock(rockDir):

    # clone Rock if it doesn't exist in the current directory
    if not os.path.exists(rockDir):
        os.system("git clone https://github.com/NewSpring/Rock.git " + rockDir)

    # switch to Rock directory
    os.chdir(rockDir)

    # check that it is a git directory
    if "true" not in os.popen("git rev-parse --is-inside-work-tree").read():
        logger.error(
            "Directory is not valid or is corrupt. May need to delete and retry."
        )
        return 1


def _checkout(branch):

    # checkout and update branch
    logger.info("Updating {} branch".format(branch))
    r = os.popen("git checkout {}".format(branch)).read()
    if "up to date" not in r:
        os.system("git pull")


def _cleanup(deleteRemote=True):

    # delete the local and remote branches
    _checkout("master")
    if deleteRemote:
        os.system("git push --delete origin sync-pre-alpha")
    os.system("git branch -D sync-pre-alpha")


def _createPreAlpha():

    # get Spark remote branches
    if "SparkDevNetwork" not in os.popen("git remote").read():
        # set up Spark as remote
        logger.info("Adding Spark remote")
        os.system(
            "git remote add SparkDevNetwork https://github.com/SparkDevNetwork/Rock.git"
        )
    os.system("git fetch SparkDevNetwork")

    # if sync-pre-alpha doesn't exist, create it
    # if "sync-pre-alpha" not in os.popen("git branch").read():
    logger.info("Creating new sync-pre-alpha from Spark")
    os.system(
        "git checkout -B sync-pre-alpha SparkDevNetwork/pre-alpha-release")

    # push pre alpha branch
    logger.info("Deleting remote sync-pre-alpha")
    os.system("git push --delete origin sync-pre-alpha")
    logger.info("Pushing sync-pre-alpha")
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

    # check for changes
    logger.info("Merging {} -> {}".format(source, destination))
    if ("up to date" in os.popen(
            'git merge {} -m "Merge from NewSpring/{}"'.format(
                source, source)).read()):
        logger.info("No changes to sync")

    # merge source into destination
    else:

        # check for files to safely delete
        conflicts = False
        deletedBySource = (os.popen(
            "git diff --name-only --diff-filter=UD").read().split("\n"))
        logger.debug(deletedBySource)
        if deletedBySource != [""]:
            conflicts = True
            for file in deletedBySource:
                if not os.path.exists(file):
                    continue
                logger.info("{}".format(file))
            choice = input("Safe to delete files? (y/n) ")
            if choice.lower() not in ["y", "yes"]:
                logger.info("Fix conflicts manually")
                return 1
            logger.info("Deleting files...")
            for file in deletedBySource:
                os.system("git rm {}".format(file))

        # run check again
        if os.popen("git diff --diff-filter=U").read() != "":
            logger.warning("Some can't be resolved. Fix conflicts manually.")
            return 1

        # merge commit
        if conflicts:
            logger.info("Committing merge conflict resolution")
            os.system('git commit -am "Merge conflicts resolved"')

    # push destination branch
    logger.info("Pushing {} branch".format(destination))
    os.system("git push --set-upstream origin {}".format(destination))


def _build(branch, authKey):

    # POST request to start appveyor build
    data = {
        "accountName": "NewSpring",
        "projectSlug": "rock",
        "branch": branch
    }
    headers = {"Authorization": "Bearer " + authKey}
    r = requests.post(
        "https://ci.appveyor.com/api/builds", data=data, headers=headers)


def _buildingCheck(branch):

    # wait until the current commit is the one being built
    commit = _getSHA()
    buildCommit = ""
    start = round(time.perf_counter())
    while commit not in buildCommit:
        elapsed = round(time.perf_counter()) - start
        if elapsed > 30:
            logger.warning(
                "\nTimeout. Branch '{}' not building.".format(branch))
            return 1
        print(
            "\rVerifying automatic AppVeyor build ({}s)".format(elapsed),
            end="")
        r = requests.get(
            "https://ci.appveyor.com/api/projects/NewSpring/rock/branch/{}".
            format(branch))
        try:
            buildCommit = json.loads(r.text)["build"]["commitId"]
        except KeyError:
            logger.warning("\nBranch not found.")
            return 1
    print("")
    logger.info("Current commit is building or has already been built")
    return 0


def _buildStatus(branch):

    # wait on Appveyor build to pass or fail
    status = ""
    start = round(time.perf_counter())
    while status not in ["success", "failed"]:
        elapsed = round(time.perf_counter()) - start
        print("\rWaiting on AppVeyor build ({}s)".format(elapsed), end="")
        r = requests.get(
            "https://ci.appveyor.com/api/projects/NewSpring/rock/branch/{}".
            format(branch))
        status = json.loads(r.text)["build"]["status"]
    print("")
    if status == "success":
        logger.info("{} branch build passed".format(branch))
        return 0
    logger.error("Build failed. Debug {} branch and run again.".format(branch))
    return -1


def _getBuildVersion(branch, authKey):

    headers = {"Authorization": "Bearer {}".format(authKey)}
    r = requests.get(
        "https://ci.appveyor.com/api/projects/NewSpring/rock/branch/{}".format(
            branch),
        headers=headers,
    )
    logger.debug(f"Build version response: {r}")
    return json.loads(r.text)["build"]["version"]


def _deploy(branch, version, envID, authKey):

    logger.debug(f"envID: {envID}")
    logger.debug(f"authKey: {authKey}")
    # get Appveyor environment name
    headers = {"Authorization": "Bearer {}".format(authKey)}
    r = requests.get(
        "https://ci.appveyor.com/api/environments/{}/settings".format(envID),
        headers=headers,
    )
    logger.debug(r.text)
    envName = json.loads(r.text)["environment"]["name"]

    # make POST request to trigger deployment
    data = {
        "environmentName": envName,
        "accountName": "NewSpring",
        "projectSlug": "rock",
        "buildVersion": version,
        "environmentVariables": {
            "application_path": "D:\wwwroot"
        },
    }
    r = requests.post(
        "https://ci.appveyor.com/api/deployments", data=data, headers=headers)
    logger.info("Deploying branch {} to {} started.".format(branch, envName))
    logger.debug(r.text)


def _appveyorBuild(branch):

    # run appveyor build on source branch if it's not automatic
    if _buildingCheck(branch):
        _build(branch, os.getenv("APPVEYOR_KEY"))

    # after build passes, we can safely merge
    if _buildStatus(branch):
        return 1


def _safeMerge(destination, source):

    # first merge destination branch into source so we can test the build
    if _merge(source, destination):
        return 1

    # run appveyor build on source branch
    if _appveyorBuild(source):
        return 1

    # merge source into destination
    if _merge(destination, source):
        return 1

    # run appveyor build on destination branch
    if _appveyorBuild(destination):
        return 1


def _pr(base, head):

    _checkout(head)
    if os.system('hub pull-request -b {} -m "Merge from NewSpring/{}"'.format(
            base, head)):
        logger.error("Could not complete pull request")
        return 1
    logger.info(
        "Created {} -> {} PR. Ready to merge and deploy {} manually.".format(
            head, base, base))


def sync(rockDir="/tmp/Rock", safe=True, fast=False):
    """This will sync Rock pre-alpha with our alpha branch."""

    logger.info("*****************")
    logger.info("Syncing pre-alpha")
    logger.info("*****************")

    # load environment variables
    load_dotenv()

    # first make sure a valid directory was passed
    if _validDir(rockDir):
        return 1

    # check that hub is installed
    if _hubInstalled():
        return 1

    # if Rock doesn't exist, clone it
    if _cloneRock(rockDir):
        return 1

    # checkout alpha branch
    _createPreAlpha()

    # stopping at alpha PR
    if safe:
        # if making the PR fails, delete the remote branch too
        if _pr("alpha", "sync-pre-alpha"):
            # _cleanup()
            return 1
    else:
        # merge pre alpha into alpha after it builds successfully
        if _safeMerge("alpha", "sync-pre-alpha"):
            return 1

        if fast:
            if _safeMerge("beta", "alpha"):
                return 1
            _deploy(
                destination,
                _getBuildVersion(destination, os.getenv("APPVEYOR_KEY")),
                os.getenv("APPVEYOR_BETA_ENV"),
                os.getenv("APPVEYOR_KEY"),
            )
        else:
            _pr("beta", "alpha")

    # if alpha was made, don't delete remote pre-alpha branch
    # _cleanup(not prAlpha)
