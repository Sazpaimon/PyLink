"""
permissions.py - Permissions Abstraction for PyLink IRC Services.
"""

from collections import defaultdict
import threading

# Global variables: these store mappings of hostmasks/exttargets to lists of permissions each target has.
default_permissions = defaultdict(set)
permissions = defaultdict(set, {'$pylinkacc': {'*'}})

# Only allow one thread to change the permissions index at once.
permissions_lock = threading.Lock()

from pylinkirc import conf, utils
from pylinkirc.log import log

def resetPermissions():
    """
    Loads the permissions specified in the permissions: block of the PyLink configuration,
    if such a block exists. Otherwise, fallback to the default permissions specified by plugins.
    """
    with permissions_lock:
        global permissions
        log.debug('permissions.resetPermissions: old perm list: %s', permissions)

        if not conf.conf.get('permissions_merge_defaults', True):
            log.debug('permissions.resetPermissions: clearing perm list due to permissions_merge_defaults set False.')
            permissions.clear()

        permissions.update(conf.conf.get('permissions', default_permissions))
        log.debug('permissions.resetPermissions: new perm list: %s', permissions)

def addDefaultPermissions(perms):
    """Adds default permissions to the index."""
    with permissions_lock:
        global permissions
        for target, permlist in perms.items():
            permissions[target] |= set(permlist)

def removeDefaultPermissions(perms):
    """Remove default permissions from the index."""
    with permissions_lock:
        global permissions
        for target, permlist in perms.items():
            permissions[target] -= set(permlist)

def checkPermissions(irc, uid, perms, also_show=[]):
    """
    Checks permissions of the caller. If the caller has any of the permissions listed in perms,
    this function returns True. Otherwise, NotAuthorizedError is raised.
    """
    # Iterate over all hostmask->permission list mappings.
    for host, permlist in permissions.copy().items():
        log.debug('permissions: permlist for %s: %s', host, permlist)
        if irc.matchHost(host, uid):
            # Now, iterate over all the perms we are looking for.
            for perm in permlist:
                # Use irc.matchHost to expand globs in an IRC-case insensitive and wildcard
                # friendly way. e.g. 'xyz.*.#Channel\' will match 'xyz.manage.#channel|' on IRCds
                # using the RFC1459 casemapping.
                log.debug('permissions: checking if %s glob matches anything in %s', perm, permlist)
                if any(irc.matchHost(perm, p) for p in perms):
                    return True
    raise utils.NotAuthorizedError("You are missing one of the following permissions: %s" %
                                   (', '.join(perms+also_show)))


# This is called on first import.
resetPermissions()
