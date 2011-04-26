import logging
import urlparse

import reviewboard.diffviewer.parser as diffparser
from reviewboard.scmtools import sshutils
from reviewboard.scmtools.errors import FileNotFoundError


class ChangeSet:
    def __init__(self):
        self.changenum = None
        self.summary = ""
        self.description = ""
        self.testing_done = ""
        self.branch = ""
        self.bugs_closed = []
        self.files = []
        self.username = ""
        self.pending = False


class Revision(object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return self.name == str(other)

    def __ne__(self, other):
        return self.name != str(other)

    def __repr__(self):
        return '<Revision: %s>' % self.name


HEAD = Revision("HEAD")
UNKNOWN = Revision('UNKNOWN')
PRE_CREATION = Revision("PRE-CREATION")


class SCMTool(object):
    #: The human-readable name of the SCMTool. Users will see this
    #: when  they go to select a repository type. Some examples would be
    # "Subversion" or "Perforce".
    name = None

    #: Some systems (such as Subversion) use a single revision to represent
    #: all the changes made to all files in a commit. Others (such as CVS)
    #: have per-file revisions instead, with no atomic indicator representing
    #: that particular commit.
    #:
    #: If ``True``, a single revision is used to represent the commit. Otherwise,
    #: revisions are only per-file.
    #:
    #: By default, this is ``False``.
    uses_atomic_revisions = False

    #: Some systems (such as Mercurial) use atomic changeset IDs in the
    #: revision fields of a diff. Instead of per-file revisions in the diff,
    #: which may all be different, each file would list the same identifier.
    #: This flag indicates whether that is true for this SCMTool.
    #:
    #: If ``True``, the first revision found in a diff will be used for fetching
    #: and identifying all subsequent files. Otherwise, the revisions are
    #: allowed to possibly differ per file.
    #:
    #: By default, this is ``False``.
    diff_uses_changeset_ids = False

    #: Indicates whether the SCMTool should allow for authentication credentials
    #: to be used when talking to the repository. This makes sense for most
    #: types of repositories.
    #:
    #: By default, this is ``False``.
    supports_authentication = False

    #: Some systems (such as Git) have no way of accessing an individual file
    #: in a repository over a network without having a complete checkout on
    #: the Review Board server. For those, Review Board can offer a field for
    #: specifying a URL mask for accessing raw files through a web interface.
    #:
    #: If ``True``, this field will be shown in the repository configuration.
    #: It's up to the SCMTool to handle and parse the value, though.
    #:
    #: By default, this is ``False``.
    supports_raw_file_urls = False

    #: A dictionary containing lists of dependencies needed for this SCMTool.
    #:
    #: This should be overridden by subclasses that require certain
    #: external modules or binaries. It has two keys: ``executables``
    #: and ``modules``. Each map to a list of names.
    #:
    #: The list of Python modules go in ``modules``, and must be valid,
    #: importable modules. If a module is not available, the SCMTool will
    #: be disabled.
    #:
    #: The list of executables shouldn't contain a file extensions (namely,
    #: ``.exe``), as Review Board will automatically attempt to use the
    #: right extension for the platform.
    dependencies = {
        'executables': [],
        'modules': [],
    }

    def __init__(self, repository):
        self.repository = repository

    def get_file(self, path, revision=None):
        """Returns the contents of a file from a repository.

        Provided a full path within the repository and a normalized
        revision, this must attempt to fetch the raw contents of the file
        from the repository.

        :param path: The absolute path to a file in the repository.
        :param revision: The revision of the file to fetch.
        :rtype: The contents of the fetched file.
        :raises FileNotFoundError: The file could not be found.
        :raises InvalidRevisionFormatError: The revision was not in a
                                            valid format.
        """
        raise NotImplementedError

    def file_exists(self, path, revision=HEAD):
        try:
            self.get_file(path, revision)
            return True
        except FileNotFoundError:
            return False

    def parse_diff_revision(self, file_str, revision_str):
        """Parses a filename and revision as represented in an uploaded diff.

        This must return a tuple with the normalized filename and revision.

        A diff may use strings like ``(working copy)`` as a revision. This
        function will be responsible for converting this to something
        Review Board can understand.

        :param file_str: The filename as represented in the diff.
        :param revision_str: The revision as represented in the diff.
        :rtype: A tuple in the form of (filename, revision).
        """
        raise NotImplementedError

    def get_diffs_use_absolute_paths(self):
        return False

    def get_changeset(self, changesetid):
        raise NotImplementedError

    def get_pending_changesets(self, userid):
        raise NotImplementedError

    def get_filenames_in_revision(self, revision):
        raise NotImplementedError

    def get_repository_info(self):
        raise NotImplementedError

    def get_fields(self):
        """Returns a list of fields that should be shown in the Upload Diff and
        New Review Request forms.

        This supports only a few very specific field names.

        * ``basedir`` - The :guilabel:`Base Directory` field.
        * ``changenum`` - The :guilabel:`Change Number` field.
        * ``diff_path`` - The :guilabel:`Diff Path` field for choosing a
          diff to upload.
        * ``parent_diff_path`` - The :guilabel:`Parent Diff Path` field for
          choosing a parent diff to upload.

        :rtype: A list of fields to explicitly show in the Upload Diff and
                    New Review Request forms.

        .. note:: It is expected that this function will be replaced in
                  time with capability flags, much like the other
                  attributes listed above.
        """
        # This is kind of a crappy mess in terms of OO design.  Oh well.
        # Return a list of fields which are valid for this tool in the "new
        # review request" page.
        raise NotImplementedError

    def get_parser(self, data):
        return diffparser.DiffParser(data)

    def normalize_path_for_display(self, filename):
        return filename

    @classmethod
    def check_repository(cls, path, username=None, password=None):
        """
        Performs checks on a repository to test its validity.

        This should check if a repository exists and can be connected to.
        This will also check if the repository requires an HTTPS certificate.

        The result is returned as an exception. The exception may contain
        extra information, such as a human-readable description of the problem.
        If the repository is valid and can be connected to, no exception
        will be thrown.
        """
        if sshutils.is_ssh_uri(path):
            username, hostname = SCMTool.get_auth_from_uri(path, username)
            logging.debug(
                "%s: Attempting ssh connection with host: %s, username: %s" % \
                (cls.__name__, hostname, username))
            sshutils.check_host(hostname, username, password)

    @classmethod
    def get_auth_from_uri(cls, path, username):
        """
        Returns a 2-tuple of the username and hostname, given the path.

        If a username is implicitly passed via the path (``user@host``), it
        takes precedence over a passed username.
        """
        url = urlparse.urlparse(path)

        if '@' in url[1]:
            netloc_username, hostname = url[1].split('@', 1)
        else:
            hostname = url[1]
            netloc_username = None

        if netloc_username:
            return netloc_username, hostname
        else:
            return username, hostname

    @classmethod
    def accept_certificate(cls, path):
        """Accepts the HTTPS certificate for the given repository path.

        This is needed for repositories that support HTTPS-backed
        repositories. It should mark an HTTPS certificate as accepted
        so that the user won't see validation errors in the future.

        The administration UI will call this after a user has seen and verified
        the HTTPS certificate.
        """
        raise NotImplemented
