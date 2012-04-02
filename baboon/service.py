import os

from config import Config
from logger import logger


@logger
class Service(object):
    """ The purpose of the service is to manipulate payload of the
    Transport (from, to).
    """

    def __init__(self, diffman):
        self.config = Config()
        self.diffman = diffman

        # Key: author + filepath
        # Value: True if the last message received by the author was a
        # conflict
        self.in_conflict = {}

    def verify_msg(self, payloads):
        for payload in payloads:
            author = payload['author']
            filepath = payload['filepath']
            diff = payload['diff']

            if author != self.config.jid:
                result = self.diffman.patch(diff, "%s" % os.path.join(
                        self.config.path, filepath))
                if not result:
                    self.in_conflict[author + filepath] = True
                    msg = "Conflict detected with %s in %s" % \
                        (author, filepath)
                    self.logger.info(msg)
                    self.logger.debug("With the diff:\n%s" % diff)
                    self.notify(msg)
                else:
                    if self.in_conflict.get(author + filepath):
                        msg = "Conflict resolved with %s in %s" % \
                            (author, filepath)
                        self.in_conflict[author + filepath] = False
                        self.logger.info(msg)
                        self.notify(msg)
                    else:
                        msg = "Everything seems to be perfect with" \
                            " %s in %s" % (author, filepath)
                        self.logger.debug(msg)
