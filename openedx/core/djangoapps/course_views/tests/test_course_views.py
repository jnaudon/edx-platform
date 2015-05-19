""" Tests of specific tabs. """

from mock import MagicMock
import unittest

import xmodule.tabs as xmodule_tabs
import openedx.core.djangoapps.course_views.course_views as tabs
from student.tests.factories import UserFactory
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase


class TabTestCase(ModuleStoreTestCase):
    """Base class for Tab-related test cases."""
    def setUp(self):
        super(TabTestCase, self).setUp()

        self.course = CourseFactory.create(org='edX', course='toy', run='2012_Fall')
        self.fake_dict_tab = {'fake_key': 'fake_value'}
        self.settings = MagicMock()
        self.settings.FEATURES = {}
        self.reverse = lambda name, args: "name/{0}/args/{1}".format(name, ",".join(str(a) for a in args))
        self.books = None

    def create_mock_user(self, is_authenticated=True, is_staff=True, is_enrolled=True):
        """
        Creates a mock user with the specified properties.
        """
        user = UserFactory()
        user.name = 'mock_user'
        user.is_staff = is_staff
        user.is_enrolled = is_enrolled
        user.is_authenticated = lambda: is_authenticated
        return user

    def is_tab_enabled(self, tab, course, settings, user):
        """
        Returns true if the specified tab is enabled.
        """
        return tab.is_enabled(course, settings, user=user)

    def set_up_books(self, num_books):
        """Initializes the textbooks in the course and adds the given number of books to each textbook"""
        self.books = [MagicMock() for _ in range(num_books)]
        for book_index, book in enumerate(self.books):
            book.title = 'Book{0}'.format(book_index)
        self.course.textbooks = self.books
        self.course.pdf_textbooks = self.books
        self.course.html_textbooks = self.books

    def check_tab(
            self,
            tab_class,
            dict_tab,
            expected_link,
            expected_tab_id,
            expected_name='same',
            invalid_dict_tab=None,
    ):
        """
        Helper method to verify a tab class.

        'tab_class' is the class of the tab that is being tested
        'dict_tab' is the raw dictionary value of the tab
        'expected_link' is the expected value for the hyperlink of the tab
        'expected_tab_id' is the expected value for the unique id of the tab
        'expected_name' is the expected value for the name of the tab
        'invalid_dict_tab' is an invalid dictionary value for the tab.
            Can be 'None' if the given tab class does not have any keys to validate.
        """
        # create tab
        if issubclass(tab_class, tabs.CourseViewType):
            tab = tab_class.create_tab(tab_dict=dict_tab)
        else:
            tab = tab_class(tab_dict=dict_tab)

        # name is as expected
        self.assertEqual(tab.name, expected_name)

        # link is as expected
        self.assertEqual(tab.link_func(self.course, self.reverse), expected_link)

        # verify active page name
        self.assertEqual(tab.tab_id, expected_tab_id)

        # validate tab
        self.assertTrue(tab.validate(dict_tab))
        if invalid_dict_tab:
            with self.assertRaises(xmodule_tabs.InvalidTabsException):
                tab.validate(invalid_dict_tab)

        # check get and set methods
        self.check_get_and_set_methods(tab)

        # check to_json and from_json methods
        self.check_tab_json_methods(tab)

        # check equality methods
        self.check_tab_equality(tab, dict_tab)

        # return tab for any additional tests
        return tab

    def check_tab_equality(self, tab, dict_tab):
        """Tests the equality methods on the given tab"""
        self.assertEquals(tab, dict_tab)  # test __eq__
        ne_dict_tab = dict_tab
        ne_dict_tab['type'] = 'fake_type'
        self.assertNotEquals(tab, ne_dict_tab)  # test __ne__: incorrect type
        self.assertNotEquals(tab, {'fake_key': 'fake_value'})  # test __ne__: missing type

    def check_tab_json_methods(self, tab):
        """Tests the json from and to methods on the given tab"""
        serialized_tab = tab.to_json()
        deserialized_tab = tab.from_json(serialized_tab)
        self.assertEquals(serialized_tab, deserialized_tab)

    def check_can_display_results(
            self,
            tab,
            expected_value=True,
            for_authenticated_users_only=False,
            for_staff_only=False,
            for_enrolled_users_only=False
    ):
        """Checks can display results for various users"""
        if for_staff_only:
            user = self.create_mock_user(is_authenticated=True, is_staff=True, is_enrolled=True)
            self.assertEquals(expected_value, self.is_tab_enabled(tab, self.course, self.settings, user))
        if for_authenticated_users_only:
            user = self.create_mock_user(is_authenticated=True, is_staff=False, is_enrolled=False)
            self.assertEquals(expected_value, self.is_tab_enabled(tab, self.course, self.settings, user))
        if not for_staff_only and not for_authenticated_users_only and not for_enrolled_users_only:
            user = self.create_mock_user(is_authenticated=False, is_staff=False, is_enrolled=False)
            self.assertEquals(expected_value, self.is_tab_enabled(tab, self.course, self.settings, user))
        if for_enrolled_users_only:
            user = self.create_mock_user(is_authenticated=True, is_staff=False, is_enrolled=True)
            self.assertEquals(expected_value, self.is_tab_enabled(tab, self.course, self.settings, user))

    def check_get_and_set_methods(self, tab):
        """Test __getitem__ and __setitem__ calls"""
        self.assertEquals(tab['type'], tab.type)
        self.assertEquals(tab['tab_id'], tab.tab_id)
        with self.assertRaises(KeyError):
            _ = tab['invalid_key']

        self.check_get_and_set_method_for_key(tab, 'name')
        self.check_get_and_set_method_for_key(tab, 'tab_id')
        with self.assertRaises(KeyError):
            tab['invalid_key'] = 'New Value'

    def check_get_and_set_method_for_key(self, tab, key):
        """Test __getitem__ and __setitem__ for the given key"""
        old_value = tab[key]
        new_value = 'New Value'
        tab[key] = new_value
        self.assertEquals(tab[key], new_value)
        tab[key] = old_value
        self.assertEquals(tab[key], old_value)


class TextbooksTestCase(TabTestCase):
    """Test cases for Textbook Tab."""

    def setUp(self):
        super(TextbooksTestCase, self).setUp()

        self.set_up_books(2)

        self.dict_tab = MagicMock()
        self.course.tabs = [
            xmodule_tabs.CourseTab.from_json({'type': 'textbooks'}),
            xmodule_tabs.CourseTab.from_json({'type': 'pdf_textbooks'}),
            xmodule_tabs.CourseTab.from_json({'type': 'html_textbooks'}),
        ]
        self.num_textbook_tabs = sum(1 for tab in self.course.tabs if tab.type in [
            'textbooks', 'pdf_textbooks', 'html_textbooks'
        ])
        self.num_textbooks = self.num_textbook_tabs * len(self.books)

    def test_textbooks_enabled(self):

        type_to_reverse_name = {'textbook': 'book', 'pdftextbook': 'pdf_book', 'htmltextbook': 'html_book'}

        self.settings.FEATURES['ENABLE_TEXTBOOK'] = True
        num_textbooks_found = 0
        user = self.create_mock_user(is_authenticated=True, is_staff=False, is_enrolled=True)
        for tab in xmodule_tabs.CourseTabList.iterate_displayable(self.course, self.settings, user=user):
            # verify all textbook type tabs
            if tab.type == 'single_textbook':
                book_type, book_index = tab.tab_id.split("/", 1)
                expected_link = self.reverse(
                    type_to_reverse_name[book_type],
                    args=[self.course.id.to_deprecated_string(), book_index]
                )
                self.assertEqual(tab.link_func(self.course, self.reverse), expected_link)
                self.assertTrue(tab.name.startswith('Book{0}'.format(book_index)))
                num_textbooks_found = num_textbooks_found + 1
        self.assertEquals(num_textbooks_found, self.num_textbooks)


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
