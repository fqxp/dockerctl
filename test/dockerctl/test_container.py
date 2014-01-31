from dockerctl.container import *
import unittest
from mock import MagicMock, patch


class TestContainer(unittest.TestCase):

    def setUp(self):
        self.container = Container('TEST')
        self.container.client = MagicMock()
        self.container.config = MagicMock()

    def test_get_container_by_name_returns_container_by_name(self):
        self.container.client.return_value.containers.return_value = [{'Id': 1, 'Names': ['/A#X']}]

        result = self.container.get_container_by_name('A')

        self.assertEqual(result['Id'], 1)

    def test_get_container_by_name_returns_no_container_that_is_a_child(self):
        self.container.client.return_value.containers.return_value = [{'Id': 1, 'Names': ['/A#X/B']}]

        result = self.container.get_container_by_name('A')

        self.assertIsNone(None)

    def test_get_container_by_name_choses_the_right_container(self):
        self.container.client.return_value.containers.return_value = [
            {'Id': 1, 'Names': ['/A#X']},
            {'Id': 2, 'Names': ['/A#X/B']},
        ]

        result = self.container.get_container_by_name('A')

        self.assertIsNone(None)

        self.container.client.return_value.containers.return_value = [
            {'Id': 1, 'Names': ['/A#X/B']},
            {'Id': 2, 'Names': ['/A#X']},
        ]

        result = self.container.get_container_by_name('A')

        self.assertEqual(result['Id'], 2)

    def test_matching_name_returns_the_matching_name(self):
        self.container.client.return_value.containers.return_value = [
            {'Id': 1, 'Names': ['/A#X']},
            {'Id': 2, 'Names': ['/A#X/B']},
        ]

        result = self.container.matching_name('A')

        self.assertEqual(result, '/A#X')

        self.container.client.return_value.containers.return_value = [
            {'Id': 1, 'Names': ['/A#X']},
            {'Id': 2, 'Names': ['/A#Y']},
        ]

        result = self.container.matching_name('A')

        self.assertEqual(result, '/A#X')
