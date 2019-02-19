import os


def _hub():

    # check for hub
    print("Checking for hub...")
    if os.system("which hub") != 0:
        print("Need to install hub to create PRs. Run `brew install hub`.")
        return 1
    return 0


def pullAlpha():
    """This will clone the NewSpring repo and checkout the alpha branch."""
    # clone Rock if it doesn't exist in the current directory
    if not os.path.exists("Rock"):
        os.system("hub clone NewSpring/Rock")


def sync():
    """This will sync Rock pre-alpha with our alpha branch."""
    _hub()
