import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import next_percent, session_folder, save_log
from live import estimated_savings

class PortableTests(unittest.TestCase):
    def test_overlap(self):
        self.assertEqual(next_percent(0,20,15),21.25)
        self.assertEqual(next_percent(95,20,15),100)
    def test_invalid_scroll_metrics(self):
        for value in (0,100,-1):
            with self.assertRaises(ValueError): next_percent(0,value,15)
    def test_unique_safe_folders(self):
        with tempfile.TemporaryDirectory() as directory:
            a=session_folder(directory,'https://example.com/a?b="c"')
            b=session_folder(directory,'https://example.com/a?b="c"')
            self.assertNotEqual(a,b)
            self.assertEqual(a.parent,Path(directory))
            self.assertFalse(any(c in a.name for c in '<>:"/\\|?*'))
    def test_logs_outside_export(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('app.desktop.log_directory',return_value=Path(directory)/'app-logs'):
                path=save_log({'id':'test','status':'complete'})
            self.assertTrue(path.is_file())
    def test_estimate(self):
        self.assertEqual(estimated_savings(8,2,20),250)
        self.assertEqual(estimated_savings(1,1,100),0)

if __name__=='__main__': unittest.main()
