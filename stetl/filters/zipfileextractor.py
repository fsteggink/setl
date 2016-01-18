# -*- coding: utf-8 -*-
#
# Extracts a file from a ZIP file, and saves it as the given file name.
#
# Author: Frank Steggink
#
from stetl.component import Config
from stetl.filter import Filter
from stetl.util import Util
from stetl.packet import FORMAT

log = Util.get_log('zipfileextractor')


class ZipFileExtractor(Filter):
    """
    Extracts a file from a ZIP file, and saves it as the given file name.

    consumes=FORMAT.record, produces=FORMAT.string
    """

    # Start attribute config meta
    @Config(ptype=str, default=None, required=True)
    def file_path(self):
        """
        File name to write the extracted file to.

        Required: True

        Default: None
        """
        pass

    # End attribute config meta

    # Constructor
    def __init__(self, configdict, section):
        Filter.__init__(self, configdict, section, consumes=FORMAT.record, produces=FORMAT.string)
        self.cur_file_path = self.cfg.get('file_path')

    def invoke(self, packet):
        event = None
            
        if packet.data is None:
            log.info("No file name given")
            return packet
        
        import os
        import zipfile

        with zipfile.ZipFile(packet.data['file_path']) as z:
            with open(self.cur_file_path, 'wb') as f:
                f.write(z.read(packet.data['name']))

        packet.data = self.cur_file_path
        return packet
        
    def after_chain_invoke(self, packet):
        import os.path
        if os.path.isfile(self.cur_file_path):
            os.remove(self.cur_file_path)
            
        return True