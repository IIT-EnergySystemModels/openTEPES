from unittest import mock
from openTEPES.openTEPES_gitinfo import get_git_version


@mock.patch("subprocess.check_output")
def test_get_git_version(mock_check_output):
    mock_check_output.side_effect = [
        b"5655c9c\n",
        b"master\n",
    ]
    git_version = get_git_version()
    assert (
        git_version == "5655c9c-master"
    ), "Git version string should be formatted correctly"
