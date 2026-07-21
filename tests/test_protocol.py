import time

import pytest
from cryptography.fernet import Fernet

from redteam_core import Commit, constants


@pytest.fixture
def short_cooldown():
    """Temporarily shrink the commit-reveal cooldown so reveal timing is testable quickly."""
    original = constants.COMMIT_COOLDOWN
    constants.COMMIT_COOLDOWN = 0.1
    yield constants.COMMIT_COOLDOWN
    constants.COMMIT_COOLDOWN = original


def _decrypt(commit: Commit, task_name: str) -> str:
    key = commit.public_keys[task_name]
    return Fernet(key).decrypt(commit.encrypted_commit_dockers[task_name]).decode()


def test_add_encrypted_commit_stores_ciphertext_and_key():
    commit = Commit()

    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:abcd")

    assert commit.commit_dockers["mychallenge"] == "myuser/myrepo@sha256:abcd"
    assert "mychallenge" in commit.encrypted_commit_dockers
    assert "mychallenge" in commit.secret_keys
    assert commit.public_keys == {}


def test_add_encrypted_commit_duplicate_is_noop():
    commit = Commit()
    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:abcd")
    first_ciphertext = commit.encrypted_commit_dockers["mychallenge"]
    first_timestamp, first_key = commit.secret_keys["mychallenge"]

    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:abcd")

    assert commit.encrypted_commit_dockers["mychallenge"] == first_ciphertext
    assert commit.secret_keys["mychallenge"] == (first_timestamp, first_key)


def test_add_encrypted_commit_new_docker_id_overwrites():
    commit = Commit()
    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:abcd")
    first_ciphertext = commit.encrypted_commit_dockers["mychallenge"]

    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:efgh")

    assert commit.commit_dockers["mychallenge"] == "myuser/myrepo@sha256:efgh"
    assert commit.encrypted_commit_dockers["mychallenge"] != first_ciphertext


def test_reveal_before_cooldown_stays_hidden(short_cooldown):
    commit = Commit()
    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:abcd")

    commit.reveal_if_ready()

    assert commit.public_keys == {}


def test_reveal_after_cooldown_exposes_key(short_cooldown):
    commit = Commit()
    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:abcd")

    time.sleep(short_cooldown * 2)
    commit.reveal_if_ready()

    assert "mychallenge" in commit.public_keys


def test_revealed_key_decrypts_original_commit(short_cooldown):
    commit = Commit()
    original = "mychallenge---myuser/myrepo@sha256:abcd"
    commit.add_encrypted_commit(original)

    time.sleep(short_cooldown * 2)
    commit.reveal_if_ready()

    assert _decrypt(commit, "mychallenge") == original


def test_hide_secret_info_strips_private_fields_without_mutating_original():
    commit = Commit()
    commit.add_encrypted_commit("mychallenge---myuser/myrepo@sha256:abcd")

    response = commit._hide_secret_info()

    assert response.secret_keys == {}
    assert response.commit_dockers == {}
    assert commit.secret_keys != {}
    assert commit.commit_dockers != {}
    assert response.encrypted_commit_dockers == commit.encrypted_commit_dockers
