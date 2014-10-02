# -*- coding: utf-8 -*-
#
# Utility functions and classes.
#
# Author:Just van den Broecke

import logging, os, glob, sys, types
from time import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)s %(levelname)s %(message)s')

# Static utility methods
class Util:
    # http://wiki.tei-c.org/index.php/Remove-Namespaces.xsl
    xslt_strip_ns = '''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" indent="no"/>

    <xsl:template match="/|comment()|processing-instruction()">
        <xsl:copy>
          <xsl:apply-templates/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="*">
        <xsl:element name="{local-name()}">
          <xsl:apply-templates select="@*|node()"/>
        </xsl:element>
    </xsl:template>

    <xsl:template match="@*">
        <xsl:attribute name="{local-name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    </xsl:stylesheet>
    '''

    xslt_strip_ns_doc = False

    @staticmethod
    def get_log(name):
        log = logging.getLogger(name)
        log.setLevel(logging.DEBUG)
        return log

    @staticmethod
    def make_file_list(candidate_file, file_list=None, filename_pattern='*.[gxGX][mM][lL]', depth_search=False):

        if file_list is None:
            file_list = []

        candidate_file = candidate_file.strip()
        input_list = candidate_file.split(',')
        if len(input_list) > 1:
            for file in input_list:
                Util.make_file_list(file, file_list, filename_pattern, depth_search)
            return file_list

        if os.path.isdir(candidate_file):
            # Is a dir: get list
            matching_file_list = glob.glob(os.path.join(candidate_file, filename_pattern))
            for file in matching_file_list:
                # Matching file: append to file
                file_list.append(file)

            for dir in os.listdir(candidate_file):
                dir = os.path.join(candidate_file, dir)
                if os.path.isdir(dir):
                    Util.make_file_list(dir, file_list, filename_pattern, depth_search)
        elif candidate_file.startswith('http'):
            file_list.append(candidate_file)
        else:
            # A single file or list of files
            matching_file_list = glob.glob(candidate_file)
            for file in matching_file_list:
                # Matching file: append to file
                file_list.append(file)

        return file_list

    # Start (global) + print timer: useful to time for processing and optimization
    @staticmethod
    def start_timer(message=""):
        log.info("Timer start: " + message)
        return time()

    # End (global) timer + print seconds passed: useful to time for processing and optimization
    @staticmethod
    def end_timer(start_time, message=""):
        log.info("Timer end: " + message + " time=" + str(round((time() - start_time), 0)) + " sec")

    # Convert a string to a dict
    @staticmethod
    def string_to_dict(s, separator='=', space='~'):
        # Convert string to dict: http://stackoverflow.com/a/1248990
        dict_arr = [x.split(separator) for x in s.split()]
        for x in dict_arr:
            x[1] = x[1].replace(space, ' ')

        return dict(dict_arr)

    @staticmethod
    def elem_to_dict(elem, strip_space=True, strip_ns=True, sub=False, attr_prefix='', gml2ogr=True, ogr2json=True):
        """Convert an Element into an internal dictionary (not JSON!)."""

        def splitNameSpace(tag):
            if tag[0] == "{":
                return tag[1:].split("}")
            else:
                return None, tag

        def parseAttributes(attribs):
            ns = set()
            for attrib in attribs.keys():
                if ':' in attrib:
                    ns.add(attrib.split(':')[0])
            if len(ns) == 0:
                return attribs
            else:
                result = {}
                for x in ns:
                    result[x] = {}
                for attrib, value in attribs.items():
                    if ':' in attrib:
                        this_ns, tag = attrib.split(':')
                        result[this_ns][attr_prefix + tag] = value
                    else:
                        result[attrib] = value
                return result

        def parseChildren(tags):
            final = {}

            for x in tags:
                prepend = {}
                result = ""
                uri, tag = splitNameSpace(x.tag)

                # if uri is not None:
                #     prepend['$$'] = uri

                if len(x.attrib) > 0:
                    prepend = dict(prepend.items() + parseAttributes(x.attrib).items())

                if len(x) == 0:
                    if x.text is not None:
                        if len(prepend) == 0:
                            result = x.text
                        else:
                            result = dict(prepend.items() + {"$": x.text}.items())
                    else:
                        if len(prepend) > 0:
                            result = prepend

                else:
                    if len(prepend) == 0:
                        result = {"$": parseChildren(x.getchildren())}
                    else:
                        result = dict(prepend.items() + {"$": parseChildren(x.getchildren())}.items())

                if tag in final:
                    if type(final[tag]) is not types.ListType:
                        final[tag] = [final[tag]]

                    final[tag].append(result)
                else:
                    final[tag] = result

            return final

        # Build-up structure

        # First the attributes in dict, optionally split-off NS
        d = {}
        for key, value in elem.attrib.items():
            if strip_ns is True:
                uri, key = splitNameSpace(key)

            d[attr_prefix + key] = value

        # Loop over sub-elements to merge them
        is_geom = False
        value = None
        for subelem in elem:
            tag = subelem.tag
            uri, bare_tag = splitNameSpace(tag)
            is_geom = False

            # What to do if GML Geometry found...
            if gml2ogr and bare_tag in ['Point', 'Polygon', 'MultiPolygon', 'LineString', 'MultiLineString']:
                is_geom = True

                # Create OGR Geometry object from GML string
                value = etree.tostring(subelem)
                from osgeo import ogr
                geom = ogr.CreateGeometryFromGML(value)

                value = geom
                if ogr2json:
                    # Make OGR Geometry object a GeoJSON internal structure like
                    #  { "type": "Point",
                    #    "coordinates": [4.894836363636363, 52.373045454545455] }
                    import ast
                    # http://stackoverflow.com/questions/988228/converting-a-string-to-dictionary
                    # ast.literal_eval("{'muffin' : 'lolz', 'foo' : 'kitty'}")
                    value = ast.literal_eval(geom.ExportToJson())

            else:
                v = Util.elem_to_dict(subelem, strip_space=strip_space, strip_ns=strip_ns, sub=True,
                                      attr_prefix=attr_prefix, ogr2json=ogr2json, gml2ogr=gml2ogr)
                value = v[subelem.tag]

            if strip_ns is True:
                tag = bare_tag

            try:
                # add to existing list for this tag
                d[tag].append(value)
            except AttributeError:
                # turn existing entry into a list
                d[tag] = [d[tag], value]
            except KeyError:
                # add a new non-list entry
                d[tag] = value

        text = elem.text
        tail = elem.tail
        if strip_space is True:
            # ignore leading and trailing whitespace
            if text:
                text = text.strip()
            if tail:
                tail = tail.strip()

        if tail:
            d['#tail'] = tail

        if d:
            # use #text element if other attributes exist
            if text:
                d["#text"] = text

            # We replace the tag like 'Polygon' when we have a geometry
            if is_geom:
                d = value
        else:
            # text is the value if no attributes
            d = text or None

        elem_tag = elem.tag
        if strip_ns is True and sub is False:
            uri, elem_tag = splitNameSpace(elem_tag)

        return {elem_tag: d}

    # Remove all Namespaces from an etree Node
    # Handy for e.g. XPath expressions
    @staticmethod
    def stripNamespaces(node):
        if not Util.xslt_strip_ns_doc:
            Util.xslt_strip_ns_doc = etree.fromstring(Util.xslt_strip_ns)

        transform = etree.XSLT(Util.xslt_strip_ns_doc)
        return transform(node)


log = Util.get_log("util")

# GDAL/OGR Python Bindings not needed for now...
#import sys
#try:
#    from osgeo import ogr #apt-get install python-gdal
#except ImportError:
#    print("FATAAL: GDAL Python bindings not available, install e.g. with  'apt-get install python-gdal'")
#    sys.exit(-1)

try:
    from lxml import etree

    log.info("running with lxml.etree, good!")
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree

        log.warning("running with cElementTree on Python 2.5+ (suboptimal)")
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree

            log.warning("running with ElementTree on Python 2.5+")
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree

                log.warning("running with cElementTree")
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree

                    log.warning("running with ElementTree")
                except ImportError:
                    log.warning("Failed to import ElementTree from any known place")

try:
    from cStringIO import StringIO

    log.info("running with cStringIO, fabulous!")
except:
    from StringIO import StringIO

    log.warning("running with StringIO (this is suboptimal, try cStringIO")


class ConfigSection():
    def __init__(self, config_section):
        self.config_dict = dict(config_section)

    def has(self, name):
        return name in self.config_dict

    def get(self, name, default=None):
        if not self.config_dict.has_key(name):
            return default
        return self.config_dict[name]

    def get_int(self, name, default=-1):
        result = self.get(name)
        if result is None:
            result = default
        else:
            result = int(result)
        return result

    # Get value as bool
    def get_bool(self, name, default=False):
        s = self.get(name)
        if s is None:
            result = default
        else:
            if s == 'false' or s == 'False':
                result = False
            else:
                if s == 'true' or s == 'True':
                    result = True
                else:
                    result = bool(s)

        return result

    # Get value as list
    def get_list(self, name, split_char=',', default=None):
        result = self.get(name)
        if result is None:
            result = default
        else:
            result = result.split(split_char)
        return result

    # Get value as tuple
    def get_tuple(self, name, split_char=',', default=None):
        result = self.get_list(name, split_char)
        if result is None:
            result = default
        else:
            result = tuple(result)
        return result

    def get_dict(self, name=None, default=None):
        """
        Get value as dict or entire config dict if no name given
        """
        if name is None:
            return self.config_dict

        result = self.get(name)
        if result is None:
            result = default
        else:
            import ast
            # http://stackoverflow.com/questions/988228/converting-a-string-to-dictionary
            # ast.literal_eval("{'muffin' : 'lolz', 'foo' : 'kitty'}")
            result = ast.literal_eval(result)
        return result

    def to_string(self):
        return repr(self.config_dict)

