import xml
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom
#import cgi
import re
import glob
import os

def register_xmlns():
    """
    Register namespaces globally
    """
    ElementTree.register_namespace("mml","http://www.w3.org/1998/Math/MathML")
    ElementTree.register_namespace("xlink","http://www.w3.org/1999/xlink")

def parse(filename):
    parser = ElementTree.XMLParser(html=0, target=None, encoding='utf-8')
    #parser.entity['&#x2020;'] = unichr(0x2020)
    
    tree = ElementTree.parse(filename, parser)
    #tree = ElementTree.parse(filename)
    root = tree.getroot()
    
    return root

def parse_string(s):
    tree = ElementTree.fromstring(s)
    return tree
    
def convert_root(root):

    # Change root article element
    root.set('dtd-version', '1.1d1')
    
    # Add back namespaces if they do not exist, we expect them to be present
    """
    if not root.get('xmlns:xlink'):
        root.set('xmlns:xlink', 'http://www.w3.org/1999/xlink')
    if not root.get('xmlns:mml'):
        root.set('xmlns:mml', 'http://www.w3.org/1998/Math/MathML')
    """
    
    return root

def convert_issn(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find issn tag and change it
    """
    for tag in root.findall('./front/journal-meta/issn'):
        pub_type = tag.get('pub-type')
        if pub_type == 'epub':
            # Change it
            tag.set('publication-format', 'electronic')
            del tag.attrib['pub-type']

    return root

def convert_pub_date(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find pub-date tag and change it
    """
    for tag in root.findall('./front/article-meta/pub-date'):
        pub_type = tag.get('pub-type')
        if pub_type == 'epub':
            # Change it
            tag.set('publication-format', 'electronic')
            tag.set('date-type', 'pub')
            del tag.attrib['pub-type']

    return root

def convert_contrib_orcid(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find contrib uri content-type="orcid" tag and change it
    """
    for contrib_tag in root.findall('./front/article-meta/contrib-group/contrib'):
        for uri_tag in contrib_tag.findall('./uri'):
            content_type = uri_tag.get('content-type')
            if content_type == 'orcid':
                # Rename and change it
                uri_tag.tag = 'contrib-id'
                uri_tag.set('contrib-id-type', "orcid")
                del uri_tag.attrib['content-type']
                
    return root

def convert_aff_department(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find aff addr-line named-content content-type="department" and change it
    """
    for addr_line_tag in root.findall('./front/article-meta/contrib-group/aff/addr-line'):

        for named_content_tag in addr_line_tag.findall('./named-content'):
            content_type = named_content_tag.get('content-type')

            if content_type == 'department':
                # Rename and change it
                addr_line_tag.tag = 'institution'
                addr_line_tag.set('content-type', "dept")
                addr_line_tag.text = named_content_tag.text
                
                addr_line_tag.remove(named_content_tag)

    return root

def convert_fn_equal_contrib(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find fn fn-type="other" id="equal-contrib" and change it
    """
    for fn_tag in root.findall('./front/article-meta/author-notes/fn'):
        fn_type = fn_tag.get('fn-type')
        id = fn_tag.get('id')
        
        # Convert id to a string in case it is None
        if fn_type == "other" and str(id)[0:5] == 'equal':
            fn_tag.set('fn-type', "equal-contrib")

    for xref_tag in root.findall('./front/article-meta/contrib-group/contrib/xref'):
        ref_type = xref_tag.get('ref-type')
        rid = xref_tag.get('rid')

        if ref_type == "fn" and str(rid)[0:5] == 'equal':
            xref_tag.set('ref-type', "equal-contrib")
   
    return root

def convert_copyright_statement(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find copyright-statement tag and change it
    """
    for copyright_tag in root.findall('./front/article-meta/permissions/copyright-statement'):
        # Remove the leading Copyright word
        pattern = re.compile("^Copyright ", re.UNICODE)
        copyright_tag.text = pattern.sub('', copyright_tag.text)

    return root

def convert_license(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find license tag and change it
    """
    for license_tag in root.findall('./front/article-meta/permissions/license'):
        del license_tag.attrib['license-type']
        for license_p_tag in license_tag.findall('./license-p'):
            if len(license_p_tag.attrib) > 0:
                len(license_p_tag.attrib)

    return root

def convert_funding_source(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find funding-source tag and change it
    """
    for funding_source_tag in root.findall('./front/article-meta/funding-group/award-group/funding-source'):
        institution_wrap_tag = SubElement(funding_source_tag, 'institution-wrap')
        
        for ext_link_tag in funding_source_tag.findall('./ext-link'):
            # Assume it is a fundref tag, we do not need it anymore
            funding_source_tag.remove(ext_link_tag)
            
        for named_content_tag in funding_source_tag.findall('./named-content'):
            institution_id_tag = SubElement(institution_wrap_tag, 'institution-id')
            institution_id_tag.set('institution-id-type', "FundRef")
            institution_id_tag.text = named_content_tag.text
            funding_source_tag.remove(named_content_tag)
            
        institution_tag = SubElement(institution_wrap_tag, 'institution')
        institution_tag.set('content-type', "university")
        institution_tag.text = funding_source_tag.text.strip()

        # Clean up
        
        funding_source_tag.text = None

    return root

def convert_related_object(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find related-object tag and change it
    """
    
    # Note the double slash to find the tag in all subelements, mostly paragraphs
    for related_object_tag in root.findall('./back/sec/sec//related-object'):
        # Rename and change it
        related_object_tag.tag = 'related-article'
        related_object_tag.set('related-article-type', related_object_tag.get('content-type'))
        
        del related_object_tag.attrib['content-type']
        del related_object_tag.attrib['document-id']
        del related_object_tag.attrib['document-id-type']
        del related_object_tag.attrib['document-type']

    return root

def convert(root):
    """
    Parent method that calls each individual conversion step
    """
    
    convert_root(root)
    convert_issn(root)
    convert_pub_date(root)
    convert_contrib_orcid(root)
    convert_aff_department(root)
    convert_fn_equal_contrib(root)
    convert_copyright_statement(root)
    convert_license(root)
    convert_funding_source(root)
    convert_related_object(root)

    return root


def output(root, type = 'JATS'):

    if type == 'NLM':
        publicId = "-//NLM//DTD Journal Archiving and Interchange DTD v3.0 20080202//EN"
        systemId = 'archivearticle3.dtd'
    elif type == 'JATS':
        publicId = "-//NLM//DTD JATS (Z39.96) Journal Archiving and Interchange DTD v1.1d1 20130915//EN"
        systemId = 'JATS-archivearticle1.dtd'
    encoding = 'UTF-8'

    namespaceURI = None
    qualifiedName = "article"


    doctype = ElifeDocumentType(qualifiedName)
    doctype._identified_mixin_init(publicId, systemId)

    rough_string = ElementTree.tostring(root, encoding)

    reparsed = minidom.parseString(rough_string)
    if doctype:
        reparsed.insertBefore(doctype, reparsed.documentElement)

    # Remove  article xmlns:ns0=
    #reparsed.documentElement.removeAttribute('xmlns:ns0')
    
    reparsed_string =  reparsed.toprettyxml(indent="\t", encoding = encoding)
    #reparsed_string = reparsed.toxml(encoding = encoding)

    #reparsed_string = cgi.escape(reparsed_string).encode('utf-8', 'xmlcharrefreplace')
    return reparsed_string

def escape(string):
    for c in string:
        if ord(c) > 255:
            print c

class ElifeDocumentType(minidom.DocumentType):
    """
    Override minidom.DocumentType in order to get
    double quotes in the DOCTYPE rather than single quotes
    """
    def writexml(self, writer, indent="", addindent="", newl=""):
        writer.write("<!DOCTYPE ")
        writer.write(self.name)
        if self.publicId:
            writer.write('%s PUBLIC "%s"%s  "%s"'
                         % (newl, self.publicId, newl, self.systemId))
        elif self.systemId:
            writer.write('%s SYSTEM "%s"' % (newl, self.systemId))
        if self.internalSubset is not None:
            writer.write(" [")
            writer.write(self.internalSubset)
            writer.write("]")
        writer.write(">"+newl)

def convert_file(article_xml_filename, output_type = "JATS"):

    # Register namespaces
    register_xmlns()

    f = open("input/" + article_xml_filename, 'rb')
    original_string = f.read()
    f.close()
    
    root = parse("input/" + article_xml_filename)
    
    if output_type == "JATS":
        # Do the conversion
        root = convert(root)
    
    reparsed_string = output(root, output_type)
    
    
    f = open("output/" + article_xml_filename, 'wb')
    f.write(reparsed_string)
    f.close()
    
    escape(reparsed_string)

if __name__ == '__main__':
    
    #"""
    article_xml_filenames = ["elife00003.xml"
                            #,"elife00005.xml"
                            ,"elife00007.xml"
                            #,"elife00011.xml"
                            ,"elife00012.xml"
                            ,"elife00365.xml"
                            ,"elife02053.xml"
                            ,"elife02619.xml"
                            ,"elife02951.xml"
                            #,"elife00856.xml"
                            ]
    #"""
    #file_type = "/*.xml"
    #article_xml_filenames = glob.glob('input' + file_type)

    for f in article_xml_filenames:
        #first_try(article_xml_filename)
        filename = f.split(os.sep)[-1]
        print "converting " + filename
        convert_file(filename)