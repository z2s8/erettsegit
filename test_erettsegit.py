import os
import unittest
from erettsegit import argparse, yearify, monthify, levelify
from erettsegit import MessageType, message_for


class TestErettsegit(unittest.TestCase):
    def test_yearify_raises_out_of_bounds_years(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            yearify(2003)
            yearify(1999)
            yearify(2)
            yearify(2999)

    def test_yearify_pads_short_year(self):
        self.assertEqual(yearify(12), 2012)

    def test_monthify_handles_textual_dates(self):
        self.assertEqual(monthify('Feb'), 2)
        self.assertEqual(monthify('majus'), 5)
        self.assertEqual(monthify('ősz'), 10)

    def test_levelify_handles_multi_lang(self):
        self.assertEqual(levelify('mid-level'), 'k')
        self.assertEqual(levelify('advanced'), 'e')

    def test_messages_get_interpolated_with_extra(self):
        os.environ['ERETTSEGIT_LANG'] = 'EN'
        self.assertEqual(message_for(MessageType.e_input, MessageType.c_year),
                         'incorrect year')

    def test_messages_ignore_unnecessary_extra(self):
        self.assertNotIn('None', message_for(MessageType.i_quit, extra=None))
