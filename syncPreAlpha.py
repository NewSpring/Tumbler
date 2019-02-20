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
    os.system("git clone https://github.com/NewSpring/Rock.git " + rockDir)
    return True


def _cleanup(deleteRepo=False):

    # delete the Rock repo
    if deleteRepo:
        os.system("rm -rf Rock")
    os.system("git push --delete origin sync-pre-alpha")
    os.system("git checkout alpha")
    os.system("git branch -D sync-pre-alpha")


def _createPreAlpha(rockDir):

    # switch to Rock directory
    os.chdir(rockDir)
    # checkout alpha branch
    os.system("git checkout alpha")
    os.system("git pull")
    # set up Spark as remote
    os.system(
        "git remote add SparkDevNetwork https://github.com/SparkDevNetwork/Rock.git"
    )
    # get Spark remote branches
    os.system("git fetch SparkDevNetwork")
    # create pre-alpha branch from spark off of NewSpring alpha
    os.system(
        "git checkout -b sync-pre-alpha SparkDevNetwork/pre-alpha-release")


def _merge(destination, source):

    # checkout destination branch
    os.system("git checkout {}".format(destination))
    os.system("git pull")
    # merge alpha into pre-alpha branch
    os.system("git merge --no-ff {} -m \"Merge from NewSpring/{}\"".format(
        source, source))
    # push pre alpha branch
    os.system("git push --set-upstream origin {}".format(destination))


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


def _buildSuccess(branch):

    status = ""
    start = round(time.perf_counter())
    while status not in ["success", "fail"]:
        elapsed = round(time.perf_counter()) - start
        print("\rWaiting on AppVeyor build ({}s)...".format(elapsed), end="")
        r = requests.get(
            "https://ci.appveyor.com/api/projects/NewSpring/rock/branch/{}".
            format(branch))
        status = json.loads(r.text)["build"]["status"]
    print("\n")
    if status == "success": return True
    print("Build failed. Debug {} branch and run again.".format(branch))
    return False


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


def _mergeAndDeploy(destination, source, triggerBuild, triggerDeploy):

    # first merge destination branch into source so we can test the build
    _merge(source, destination)

    # run appveyor build on source branch
    if triggerBuild: _build(source, os.getenv("APPVEYOR_KEY"))

    # check for status of build and wait until it completes
    # NOTE: may need to wait a little to insure automatic build was triggered
    if _buildSuccess(source):

        # merge source into destination
        _merge(destination, source)

        # deploy
        if triggerDeploy:
            _deploy(destination, os.getenv("APPVEYOR_ENV"),
                    os.getenv("APPVEYOR_KEY"))


def _pr(base, head):

    os.system(
        "hub pull-request -b {} -h {} -m \"Merge from NewSpring/{}\"".format(
            base, head, head))
    print("Created {} -> {} PR. You will have to merge and deploy manually.".
          format(head, base))


def sync(rockDir="Rock", safe=False):
    """This will sync Rock pre-alpha with our alpha branch."""

    # load environment variables
    load_dotenv()

    # first make sure a valid directory was passed
    if not _isValidDir(rockDir): return 1

    # check that hub is installed
    if not _isHubInstalled(): return 1

    # if Rock doesn't exist, clone it and delete it later
    deleteRepo = _cloneRock(rockDir)

    # checkout alpha branch
    _createPreAlpha(rockDir)

    # merge pre alpha into alpha after it builds successfully
    _mergeAndDeploy("alpha", "sync-pre-alpha", True, False)

    if safe:
        # create a PR instead of automatic deploy
        _pr("beta", "alpha")
    else:
        # merge alpha into beta
        _mergeAndDeploy("beta", "alpha", False, True)

    # cleanup repo and stale branches
    _cleanup(deleteRepo)


sync("/Users/michael.neeley/Documents/Projects/Rock")
