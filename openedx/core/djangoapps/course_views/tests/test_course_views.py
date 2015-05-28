""" Tests of specific tabs. """

from mock import MagicMock
import unittest

import xmodule.tabs as xmodule_tabs
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase


class KeyCheckerTestCase(unittest.TestCase):
    """Test cases for KeyChecker class"""

    def setUp(self):
        super(KeyCheckerTestCase, self).setUp()

        self.valid_keys = ['a', 'b']
        self.invalid_keys = ['a', 'v', 'g']
        self.dict_value = {'a': 1, 'b': 2, 'c': 3}

    def test_key_checker(self):

        self.assertTrue(xmodule_tabs.key_checker(self.valid_keys)(self.dict_value, raise_error=False))
        self.assertFalse(xmodule_tabs.key_checker(self.invalid_keys)(self.dict_value, raise_error=False))
        with self.assertRaises(xmodule_tabs.InvalidTabsException):
            xmodule_tabs.key_checker(self.invalid_keys)(self.dict_value)


class NeedNameTestCase(unittest.TestCase):
    """Test cases for NeedName validator"""

    def setUp(self):
        super(NeedNameTestCase, self).setUp()

        self.valid_dict1 = {'a': 1, 'name': 2}
        self.valid_dict2 = {'name': 1}
        self.valid_dict3 = {'a': 1, 'name': 2, 'b': 3}
        self.invalid_dict = {'a': 1, 'b': 2}

    def test_need_name(self):
        self.assertTrue(xmodule_tabs.need_name(self.valid_dict1))
        self.assertTrue(xmodule_tabs.need_name(self.valid_dict2))
        self.assertTrue(xmodule_tabs.need_name(self.valid_dict3))
        with self.assertRaises(xmodule_tabs.InvalidTabsException):
            xmodule_tabs.need_name(self.invalid_dict)
