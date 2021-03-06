import unittest

from artifact_py import code
from artifact_py import lint


class TestCode(unittest.TestCase):
    def setUp(self):
        self.invalid = []
        self.impls = {}

    def test_re_single(self):
        text = "#SPC-single"
        result = [m.group(0) for m in code.NAME_TAG_RE.finditer(text)]
        assert ["#SPC-single"] == result

    def test_re_outside(self):
        text = "stuff #SPC-single. other"
        result = [m.group(0) for m in code.NAME_TAG_RE.finditer(text)]
        assert ["#SPC-single"] == result

    def test_re_ref(self):
        text = "stuff [SPC-single]. other"
        result = [m.group(0) for m in lint.NAME_REF_RE.finditer(text)]
        assert ["[SPC-single]"] == result
