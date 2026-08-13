"""Pure filename generation for saved scans."""


def make_filename(extension, now):
    """Build the on-disk filename for a scan.

    `now` is injected (a datetime.datetime) rather than read from the clock
    here, so this stays a pure function callers can unit test deterministically.
    """
    return "scan_%s.%s" % (now.strftime("%Y%m%d_%H%M%S"), extension)
