import xml
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from xml.dom import minidom
#import cgi
import re
import glob
import os
import requests


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
    
def get_date_string(root, date_type):

    date_string = ''
    date_tag = None
    for tag in root.findall('.//history/date[@date-type="' + date_type + '"]'):
        date_tag = tag
    if date_tag is None:
        for tag in root.findall('.//pub-date[@date-type="' + date_type + '"]'):
            date_tag = tag
    if date_tag is None:
        return date_string
            
    for tag in date_tag.findall('.//year'):
        date_string += tag.text
    for tag in date_tag.findall('.//month'):
        date_string += tag.text
    for tag in date_tag.findall('.//day'):
        date_string += tag.text

    return date_string
    
def date_accepted(root):
    
    return get_date_string(root, 'accepted')

def date_published(root):
    
    return get_date_string(root, 'pub')


def display_channel(root):
    
    display_channel = ''
    for tag in root.findall('.//article-meta/article-categories/subj-group[@subj-group-type="display-channel"]/subject'):
        display_channel = tag.text
        
    return display_channel

def affs(root, aff_tags = None):
    """
    
    """
    value_list = []

    if aff_tags is None:
        aff_tags = []
        for aff_tag in (root.findall('.//contrib-group/contrib[@contrib-type="author"]/aff') + root.findall('.//contrib-group/aff')):
            aff_tags.append(aff_tag)
    
    for aff_tag in aff_tags:
        aff_string = ''
        aff_id = aff_tag.get('id')
        if aff_id is not None:
            aff_number = aff_id.replace('aff','')
        else:
            aff_number = 0
        
        department = None
        for dept_tag in aff_tag.findall('.//institution[@content-type="dept"]'):
            department = dept_tag.text
        
        institution = None
        for i_tag in aff_tag.findall('.//institution'):
            if len(i_tag.attrib) <=0:
                institution = i_tag.text
                
        # Concatenate string
        if department is None:
            department = ''
        if institution is None:
            institution = ''

        aff_string = str(aff_number)
        #if department:
        aff_string = "\t".join((aff_string, department))
        #if institution:
        aff_string = "\t".join((aff_string, institution))
            
        if aff_string != '':
            value_list.append(aff_string)

    return value_list
    
    
def funding_institutions(root, award_tags = None):
    """
    
    """
    value_list = []
    if award_tags is None:
        award_tags = []
        for award_tag in root.findall('.//funding-group/award-group/funding-source'):
            award_tags.append(award_tag)
    
    for award_tag in award_tags:
        found_i_tag = None
        for i_tag in award_tag.findall('.//institution'):
            if len(i_tag.attrib) <= 0:
                found_i_tag = True
                value_list.append(i_tag.text)
        if found_i_tag is not True:
            # look for university type
            for i_tag in award_tag.findall('.//institution'):
                if i_tag.get('content-type') == 'university':
                    found_i_tag = True
                    value_list.append(i_tag.text)
            
    return value_list

def get_doi(root):
    
    doi = None
    
    for tag in root.findall('./front/article-meta/article-id[@pub-id-type="doi"]'):
        doi = tag.text
        
    return doi

def get_doi_id(root):
    
    doi = get_doi(root)
    doi_id = doi.split('.')[-1]
    return doi_id


def log_funding(root):
    """
    """

    f1 = open("funding.txt", 'ab')

    institution_string = '\t'.join(funding_institutions(root)).encode('utf8')
    date = date_accepted(root)
    if date == '':
        date = date_published(root)
    doi_id = get_doi_id(root)
    article_type = display_channel(root)

    f1.write("\n" + '\t'.join((date,doi_id,article_type,institution_string)))

    f1.close()

def log_affiliations(root):
    """
    """
    f1 = open("affiliations.txt", 'ab')

    affiliations_string = '\t'.join(affs(root)).encode('utf8')
    date = date_accepted(root)
    if date == '':
        date = date_published(root)
    doi_id = get_doi_id(root)
    article_type = display_channel(root)

    f1.write("\n" + '\t'.join((date,doi_id,article_type,affiliations_string)))

    f1.close()

def first_author_xref(root):
    """
    Get the xref values for the first author
    """
    xref_tags = []
    for contrib_tag in (root.findall('.//contrib-group/contrib[@contrib-type="author"]')):
        for xref_tag in contrib_tag.findall('.//xref'):
            xref_tags.append(xref_tag)
        break
    return xref_tags

def corresp_author_xref(root):
    """
    Get the xref values for the corresponding authors
    """
    xref_tags = []
    for contrib_tag in (root.findall('.//contrib-group/contrib[@contrib-type="author"]')):
        xref_tags_pending = []
        add_tags = False
        if contrib_tag.get('corresp') == "yes":
            add_tags = True
        
        for xref_tag in contrib_tag.findall('.//xref'):
            xref_tags_pending.append(xref_tag)
            if xref_tag.get('ref-type') == 'corresp':
                add_tags = True
        if add_tags is True:
            xref_tags = xref_tags + xref_tags_pending
    
    return xref_tags

def award_groups_by_xref(root, xref_tags):
    award_groups = []
    for xref in xref_tags:
        attrib_match = '[@id="' + xref.get('rid') + '"]'
        for tag in root.findall('.//*' + attrib_match):
            if tag.tag == 'award-group':
                award_groups.append(tag)
    return award_groups

def write_award_group_to_file(f, root, award_groups):

    institution_string = '\t'.join(funding_institutions(root, award_groups)).encode('utf8')
    date = date_accepted(root)
    if date == '':
        date = date_published(root)
    doi_id = get_doi_id(root)
    article_type = display_channel(root)

    f.write("\n" + '\t'.join((date,doi_id,article_type,institution_string)))

def affs_by_xref(root, xref_tags):
    aff_tags = []
    for xref in xref_tags:
        attrib_match = '[@id="' + xref.get('rid') + '"]'
        for tag in root.findall('.//*' + attrib_match):
            if tag.tag == 'aff':
                aff_tags.append(tag)
    return aff_tags

def write_aff_to_file(f, root, aff_tags):

    affiliations_string = '\t'.join(affs(root, aff_tags)).encode('utf8')
    date = date_accepted(root)
    if date == '':
        date = date_published(root)
    doi_id = get_doi_id(root)
    article_type = display_channel(root)

    f.write("\n" + '\t'.join((date,doi_id,article_type,affiliations_string)))

def log_first_author_funding(root, xref_tags):
    """
    First each xref_tag of funding type, get the data and log it
    """
    award_groups = award_groups_by_xref(root, xref_tags)

    f1 = open("first_author_funding.txt", 'ab')
    write_award_group_to_file(f1, root, award_groups)
    f1.close()

def log_first_author_affiliations(root, xref_tags):
    """
    First each xref_tag of aff type, get the data and log it
    """
    aff_tags = affs_by_xref(root, xref_tags)

    # Bit of a repeat of logging code, could be refactored if important
    f1 = open("first_author_affiliations.txt", 'ab')
    write_aff_to_file(f1, root, aff_tags)
    f1.close()

def log_corresp_author_funding(root, xref_tags):
    """

    """
    award_groups = award_groups_by_xref(root, xref_tags)

    f1 = open("corresp_author_funding.txt", 'ab')
    write_award_group_to_file(f1, root, award_groups)
    f1.close()

def log_corresp_author_affiliations(root, xref_tags):
    """

    """
    aff_tags = affs_by_xref(root, xref_tags)

    # Bit of a repeat of logging code, could be refactored if important
    f1 = open("corresp_author_affiliations.txt", 'ab')
    write_aff_to_file(f1, root, aff_tags)
    f1.close()


def process_xml_file(article_xml_filename):
    
    # Register namespaces
    register_xmlns()

    f = open("input/" + article_xml_filename, 'rb')
    original_string = f.read()
    f.close()
    
    root = parse("input/" + article_xml_filename)
    
    log_funding(root)
    log_affiliations(root)
    
    first_author_xref_tags = first_author_xref(root)
    log_first_author_funding(root, first_author_xref_tags)
    log_first_author_affiliations(root, first_author_xref_tags)

    corresp_author_xref_tags = corresp_author_xref(root)
    print str(len(corresp_author_xref_tags))
    log_corresp_author_funding(root, corresp_author_xref_tags)
    log_corresp_author_affiliations(root, corresp_author_xref_tags)

if __name__ == '__main__':
    
    #"""
    file_type = "/*.xml"
    article_xml_filenames = glob.glob('input' + file_type)
    
    #article_xml_filenames = ['elife02245.xml','elife01779.xml']
    #article_xml_filenames = ['elife04250.xml']
    #article_xml_filenames = ['elife04953.xml']
    #article_xml_filenames = ['elife00243.xml']

    # Reset log file
    f = open("funding.txt", 'wb')
    f.close()
    f = open("affiliations.txt", 'wb')
    f.close()
    f = open("first_author_funding.txt", 'wb')
    f.close()
    f = open("first_author_affiliations.txt", 'wb')
    f.close()
    f = open("corresp_author_funding.txt", 'wb')
    f.close()
    f = open("corresp_author_affiliations.txt", 'wb')
    f.close()

    for f in article_xml_filenames:
        #first_try(article_xml_filename)
        filename = f.split(os.sep)[-1]
        print "working on  " + filename
        process_xml_file(filename)


