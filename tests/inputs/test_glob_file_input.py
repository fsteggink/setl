import os
import sys

from stetl.etl import ETL
from stetl.packet import Packet
from stetl.inputs.fileinput import GlobFileInput
from tests.stetl_test_case import StetlTestCase

class GlobFileInputTest(StetlTestCase):
    """Unit tests for GlobFileInput"""

    def setUp(self):
        super(GlobFileInputTest, self).setUp()

        # Initialize Stetl
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        cfg_dict = {'config_file': os.path.join(curr_dir, 'configs/globfileinput.cfg')}
        self.etl = ETL(cfg_dict)
    
    def test_class(self):
        chain = StetlTestCase.get_chain(self.etl)
        section = StetlTestCase.get_section(chain)
        class_name = self.etl.configdict.get(section, 'class')
        
        self.assertEqual('stetl.inputs.fileinput.GlobFileInput', class_name)
    
    def test_instance(self):
        chain = StetlTestCase.get_chain(self.etl)
        
        self.assertTrue(isinstance(chain.first_comp, GlobFileInput))
    
    def test_execute(self):
        chain = StetlTestCase.get_chain(self.etl)
        chain.run()
        
        result = sys.stdout.getvalue().strip().split('\n')
        self.assertEqual(len(result), 1)
        
    def test_wildcard(self):
        chain = StetlTestCase.get_chain(self.etl, 1)
        chain.run()
        
        result = sys.stdout.getvalue().strip().split('\n')
        self.assertEqual(len(result), 2)
