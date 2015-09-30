# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import glob
import os.path
import re

import docutils.core
import testtools


CURRENT_DIR = 'approved'

FIRST_TITLE = 'Problem description'

DRAFT_DIR = 'backlog'
DRAFT_REQUIRED_TITLES = {
        FIRST_TITLE: [],
        'Proposed change': [],
        }

BLUEPRINT_URL = 'https://blueprints.launchpad.net/ironic/+spec/'


class TestTitles(testtools.TestCase):
    def _get_title(self, section_tree):
        section = {
            'subtitles': [],
        }
        for node in section_tree:
            if node.tagname == 'title':
                section['name'] = node.rawsource
            elif node.tagname == 'section':
                subsection = self._get_title(node)
                section['subtitles'].append(subsection['name'])
        return section

    def _get_titles(self, spec):
        titles = {}
        for node in spec:
            if node.tagname == 'section':
                section = self._get_title(node)
                titles[section['name']] = section['subtitles']
        return titles

    def _check_titles(self, filename, expect, allowed, actual):
        missing_sections = [x for x in expect.keys() if x not in actual.keys()]
        extra_sections = [x for x in actual.keys() if x not in
                dict(expect.items() + allowed.items())]

        msgs = []
        if len(missing_sections) > 0:
            msgs.append("Missing sections: %s" % missing_sections)
        if len(extra_sections) > 0:
            msgs.append("Extra sections: %s" % extra_sections)

        for section in expect.keys():
            # Sections missing entirely are already covered above
            if section not in actual:
                continue

            missing_subsections = [x for x in expect[section]
                                   if x not in actual[section]]
            # extra subsections are allowed
            if len(missing_subsections) > 0:
                msgs.append("Section '%s' is missing subsections: %s"
                            % (section, missing_subsections))

        if len(msgs) > 0:
            self.fail("While checking '%s':\n  %s"
                      % (filename, "\n  ".join(msgs)))

    def _check_file_ext(self, filename):
        self.assertTrue(filename.endswith(".rst"),
                        "spec's file must uses 'rst' extension.")

    def _check_filename(self, filename, raw):
        """Check that the filename matches the blueprint name.

        Checks that the URL for the blueprint is mentioned, and that the
        filename matches the name of the blueprint. This assumes that the
        blueprint URL occurs on a line without any other text and the URL
        occurs before the first section (title) of the specification.

        param filename: path/name of the file
        param raw: the data in the file
        """

        (root, _) = os.path.splitext(os.path.basename(filename))
        for i, line in enumerate(raw.split("\n")):
            if BLUEPRINT_URL in line:
               self.assertTrue(line.endswith(root),
                       "Filename '%s' must match blueprint name '%s'" %
                       (filename, line))
               return

            if line.startswith(FIRST_TITLE):
                break
        self.fail("URL of launchpad blueprint is missing")

    def _check_license(self, raw):
        # Check for the presence of this license string somewhere within the
        # header of the spec file, ignoring newlines and blank lines and any
        # other lines before or after it.
        license_check_str = (
            " This work is licensed under a Creative Commons Attribution 3.0"
            " Unported License."
            " http://creativecommons.org/licenses/by/3.0/legalcode")

        header_check = ""
        for i, line in enumerate(raw.split("\n")):
            if line.startswith('='):
                break
            header_check = header_check + line
        self.assertTrue(license_check_str in header_check)

    def _get_spec_titles(self, filename):
        with open(filename) as f:
            data = f.read()

        spec = docutils.core.publish_doctree(data)
        titles = self._get_titles(spec)
        return (data, titles)

    def _get_template_titles(self):
        with open("specs/template.rst") as f:
            template = f.read()
        spec = docutils.core.publish_doctree(template)
        template_titles = self._get_titles(spec)
        return template_titles

    def test_current_cycle_template(self):
        template_titles = self._get_template_titles()
        files = glob.glob('specs/%s/*' % CURRENT_DIR)

        for filename in files:
            self._check_file_ext(filename)

            (data, titles) = self._get_spec_titles(filename)
            self._check_titles(filename, template_titles, {}, titles)
            self._check_license(data)
            self._check_filename(filename, data)

    def test_backlog(self):
        template_titles = self._get_template_titles()
        files = glob.glob('specs/%s/*' % DRAFT_DIR)

        for filename in files:
            self._check_file_ext(filename)
            (data, titles) = self._get_spec_titles(filename)
            self._check_titles(filename, DRAFT_REQUIRED_TITLES,
                                template_titles, titles)
            self._check_filename(filename, data)
