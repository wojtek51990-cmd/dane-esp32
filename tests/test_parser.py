import unittest

from app.data_parser import DataParser


class DataParserTests(unittest.TestCase):
    def test_numeric_csv(self):
        parser = DataParser()
        self.assertEqual(parser.parse("23.5,4.2,12.8"), {
            "CH1": 23.5, "CH2": 4.2, "CH3": 12.8
        })

    def test_csv_header(self):
        parser = DataParser()
        self.assertIsNone(parser.parse("temperatura,cisnienie"))
        self.assertEqual(parser.parse("23.5,4.2"), {
            "temperatura": 23.5, "cisnienie": 4.2
        })

    def test_named_fields(self):
        parser = DataParser()
        self.assertEqual(parser.parse("TEMP:23.5; PRESS:4.2"), {
            "TEMP": 23.5, "PRESS": 4.2
        })

    def test_json_object(self):
        parser = DataParser()
        self.assertEqual(
            parser.parse('{"temp":23.5,"pressure":4.2,"state":"ok"}'),
            {"temp": 23.5, "pressure": 4.2}
        )

    def test_json_array(self):
        parser = DataParser()
        self.assertEqual(parser.parse("[1,2.5,3]"), {
            "CH1": 1.0, "CH2": 2.5, "CH3": 3.0
        })

    def test_ignores_text(self):
        parser = DataParser()
        self.assertIsNone(parser.parse("starting sensor..."))
        self.assertIsNone(parser.parse(""))


if __name__ == "__main__":
    unittest.main()
