"""Pure logic for the rotating scan history: which files to prune.

Filenames sort correctly by age with plain string sort because
scanlib.naming.make_filename produces a fixed-width zero-padded
YYYYmmdd_HHMMSS timestamp - no need to parse them here.
"""


def filenames_to_delete(filenames, keep):
    """Given all scan filenames on disk, return the ones beyond the newest `keep`.

    Returns oldest-first. Empty list if nothing needs pruning.
    """
    if keep < 0:
        raise ValueError("keep must be >= 0, got %r" % (keep,))

    ordered = sorted(filenames)  # oldest first
    overflow = len(ordered) - keep
    if overflow <= 0:
        return []
    return ordered[:overflow]
