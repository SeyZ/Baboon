import os

from abc import ABCMeta, abstractmethod, abstractproperty
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from errors.baboon_exception import BaboonException
from logger import logger
from config import Config
from transport import Item


@logger
class EventHandler(FileSystemEventHandler):
    """ An abstract class that extends watchdog FileSystemEventHandler in
    order to describe the behavior when a file is
    added/modified/deleted. The behavior is dependend of the SCM to
    detect exclude patterns (e.g. .git for git, .hg for hg, etc.)
    """

    __metaclass__ = ABCMeta

    def __init__(self, transport, diffman):
        """ Take the diffman to generate a patch when a change is
        detected and a transport to send it to other people.
        """

        super(EventHandler, self).__init__()
        self.config = Config()
        self.transport = transport
        self.diffman = diffman

    @abstractproperty
    def scm_name(self):
        """ The name of the scm. This name will be used in the baboonrc
        configuration file in order to retrieve and instanciate the correct
        class.
        """

        return

    @abstractmethod
    def exclude(self, path):
        '''Returns True when file matches an exclude pattern specified in the
        scm specific monitor plugin.
        '''
        return

    def on_modified(self, event):
        """ Triggered when a file is modified in the watched project.
        @param event: the watchdog event
        @raise BaboonException: if cannot retrieve the relative project path
        """

        fullpath = event.src_path
        self.logger.debug('Detected a modification on [{0}]'.format(fullpath))
        rel_path = os.path.relpath(fullpath, self.config.path)
        if self.exclude(rel_path):
            self.logger.debug("Ignore the modification on %s" % rel_path)
        else:
            # Computes the changes on the rel_path
            thediff = self.diffman.diff(rel_path)
            payload = {
                'filepath': rel_path,
                'diff': thediff,
                'author': self.config.jid,
                }
            self.transport.broadcast(Item(payload))
            return

    def on_deleted(self, event):
        """ Trigered when a file is deleted in the watched project.
        """

        self.on_modified(event)


@logger
class Monitor(object):
    def __init__(self, transport, diffman):
        """ Watches file change events (creation, modification) in the
        watched project.
        """

        self.config = Config()
        self.transport = transport
        self.diffman = diffman

        # Initialize the event handler class to use depending on the SCM to use
        handler = None
        scm_classes = EventHandler.__subclasses__()

        for cls in scm_classes:
            tmp_inst = cls(self.transport, self.diffman)
            if tmp_inst.scm_name == self.config.scm:
                self.logger.debug("Uses the %s class for the monitoring of FS "
                                  "changes" % tmp_inst.scm_name)
                handler = tmp_inst
                break
        else:
            # Raises this BaboonException if no plugin has found
            # according to the scm entry in the config file
            raise BaboonException("Cannot get a valid FS event handler"
                                  " class for your SCM written in your"
                                  " baboonrc file")

        self.monitor = Observer()
        try:
            self.monitor.schedule(handler, self.config.path, recursive=True)
        except OSError, err:
            self.logger.error(err)
            raise BaboonException(err)

    def watch(self):
        """ Starts to watch the watched project
        """

        self.monitor.start()
        self.logger.debug("Started to monitor the %s directory"
                         % self.config.path)

    def close(self):
        """ Stops the monitoring on the watched project
        """

        self.monitor.stop()
        self.monitor.join()
