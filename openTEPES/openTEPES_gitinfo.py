import subprocess
import shlex
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def cmd(cmd, cwd=ROOT_DIR) -> str:
    """
    Executes a shell command in a subprocess and returns its output as a string.

    Args:
        cmd (str): The shell command to execute.
        cwd (str): The directory where the command should be executed. Defaults to ROOT_DIR.

    Returns:
        str: The output of the command, decoded to a string and stripped of trailing whitespace.
             If the command fails, an empty string is returned.
    """
    output = ""
    try:
        output = (
            subprocess.check_output(shlex.split(cmd), cwd=cwd, stderr=subprocess.STDOUT)
            .decode()
            .strip()
        )
    except Exception as _:
        ...
    return output


def last_commit_id(cwd=ROOT_DIR) -> str:
    """
    Retrieves the last Git commit ID for the given folder.

    Args:
        cwd (str): The directory where the Git command should be executed. Defaults to ROOT_DIR.

    Returns:
        str: The Git commit ID, or a string indicating if the working tree is dirty.
    """
    return cmd("git describe --always --dirty", cwd=cwd)


def branch(cwd=ROOT_DIR) -> str:
    """
    Retrieves the current Git branch name for the given folder.

    Args:
        cwd (str): The directory where the Git command should be executed. Defaults to ROOT_DIR.

    Returns:
        str: The current Git branch name.
    """
    return cmd("git rev-parse --abbrev-ref HEAD", cwd=cwd)


def get_git_version(cwd=ROOT_DIR) -> str:
    """
    Constructs the Git version string by combining the last commit ID and the current branch name.

    Args:
        cwd (str): The directory where the Git commands should be executed. Defaults to ROOT_DIR.

    Returns:
        str: A string in the format "<commit_id>-<branch_name>".
    """
    return f"{last_commit_id(cwd)}-{branch(cwd)}"
