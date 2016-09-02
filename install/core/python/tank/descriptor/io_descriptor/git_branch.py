# Copyright (c) 2016 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.
import os
import copy

from .git import IODescriptorGit
from ..errors import TankDescriptorError
from ... import LogManager

log = LogManager.get_logger(__name__)


class IODescriptorGitBranch(IODescriptorGit):
    """
    Represents a commit in git, belonging to a particular branch.

    Branch format:
    location: {"type": "git_branch",
               "path": "/path/to/repo.git",
               "branch": "master",
               "version": "17fedd8a4e3c7c004316af5001331ad2c9e14bd5"}

    Short hashes can be used:
    location: {"type": "git_branch",
               "path": "/path/to/repo.git",
               "branch": "master",
               "version": "17fedd8"}

    path can be on the form:

        git@github.com:manneohrstrom/tk-hiero-publish.git
        https://github.com/manneohrstrom/tk-hiero-publish.git
        git://github.com/manneohrstrom/tk-hiero-publish.git
        /full/path/to/local/repo.git

    The hash can be short, as long as it is unique, e.g. it follows the same logic
    that git is using for shortening its hashes. A recommendation is to use the first
    seven digits to describe a hash that is unique within a repository.

    The payload cached in the bundle cache represents the entire git repo,
    adjusted to point at the given branch and commit.
    """

    def __init__(self, descriptor_dict):
        """
        Constructor

        :param descriptor_dict: descriptor dictionary describing the bundle
        :return: Descriptor instance
        """
        # make sure all required fields are there
        self._validate_descriptor(
            descriptor_dict,
            required=["type", "path", "version", "branch"],
            optional=[]
        )

        # call base class
        super(IODescriptorGitBranch, self).__init__(descriptor_dict)

        # path is handled by base class - all git descriptors
        # have a path to a repo
        self._version = descriptor_dict.get("version")
        self._branch = descriptor_dict.get("branch")

    def __str__(self):
        """
        Human readable representation
        """
        # git@github.com:manneohrstrom/tk-hiero-publish.git, branch master, commit 12313123
        return "%s, Branch %s, Commit %s" % (self._path, self._branch, self._version)

    def _get_bundle_cache_path(self, bundle_cache_root):
        """
        Given a cache root, compute a cache path suitable
        for this descriptor, using the 0.18+ path format.

        :param bundle_cache_root: Bundle cache root path
        :return: Path to bundle cache location
        """
        # to be MAXPATH-friendly, we only use the first seven chars
        short_hash = self._version[:7]

        # git@github.com:manneohrstrom/tk-hiero-publish.git -> tk-hiero-publish.git
        # /full/path/to/local/repo.git -> repo.git
        name = os.path.basename(self._path)

        return os.path.join(
            bundle_cache_root,
            "git",
            name,
            short_hash
        )

    def get_version(self):
        """
        Returns the version number string for this item, .e.g 'v1.2.3'
        or the branch name 'master'
        """
        return self._version

    def download_local(self):
        """
        Retrieves this version to local repo.
        Will exit early if app already exists local.

        This will connect to remote git repositories.
        Depending on how git is configured, https repositories
        requiring credentials may result in a shell opening up
        requesting username and password.

        The git repo will be cloned into the local cache and
        will then be adjusted to point at the relevant commit.
        """
        if self.exists_local():
            # nothing to do!
            return

        # cache into the primary location
        target = self._get_primary_cache_path()

        try:
            # clone the repo, switch to the given branch
            # then reset to the given commit
            commands = [
                "checkout -q \"%s\"" % self._branch,
                "reset --hard -q \"%s\"" % self._version
            ]
            self._clone_then_execute_git_commands(target, commands)

        except Exception, e:
            raise TankDescriptorError(
                "Could not download %s, branch %s, "
                "commit %s: %s" % (self._path, self._branch, self._version, e)
            )


    def get_latest_version(self, constraint_pattern=None):
        """
        Returns a descriptor object that represents the latest version.

        This will connect to remote git repositories.
        Depending on how git is configured, https repositories
        requiring credentials may result in a shell opening up
        requesting username and password.

        This will clone the git repository into a temporary location in order to
        introspect its properties.

        .. note:: The concept of constraint patterns doesn't apply to
                  git commit hashes and any data passed via the
                  constraint_pattern argument will be ignored by this
                  method implementation.

        :param constraint_pattern: If this is specified, the query will be constrained
               by the given pattern. Version patterns are on the following forms:

                - v0.1.2, v0.12.3.2, v0.1.3beta - a specific version
                - v0.12.x - get the highest v0.12 version
                - v1.x.x - get the highest v1 version

        :returns: IODescriptorGitBranch object
        """
        if constraint_pattern:
            log.warning(
                "%s does not handle constraint patterns. "
                "Latest version will be used." % self
            )

        try:
            # clone the repo, get the latest commit hash
            # for the given branch
            commands = [
                "checkout -q \"%s\"" % self._branch,
                "log -n 1 \"%s\" --pretty=format:'%%H'" % self._branch
            ]
            git_hash = self._tmp_clone_then_execute_git_commands(commands)

        except Exception, e:
            raise TankDescriptorError(
                "Could not get latest commit for %s, "
                "branch %s: %s" % (self._path, self._branch, e)
            )

        # make a new descriptor
        new_loc_dict = copy.deepcopy(self._descriptor_dict)
        new_loc_dict["version"] = git_hash
        desc = IODescriptorGitBranch(new_loc_dict)
        desc.set_cache_roots(self._bundle_cache_root, self._fallback_roots)
        return desc

