# TODO: write reporter script
"""this script should take in status information from multiple pi's via socket connections to their watcher processes,
parse those status reports, and compile them into a human-readable format/file (possibly a file that is read-only
to the user, but writeable by this program?).

Should also notice when a particular host suddenly stops pinging, and potentially notify someone? probably easiest to
have the status reports include the email associated with each project, and set up a simple sendgrid notifier.

"""
