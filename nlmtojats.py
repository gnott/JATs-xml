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

def convert_contrib_label(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find contrib tag and change it regarding labels and numbering
    """
    for contrib_tag in root.findall('./front/article-meta/contrib-group/contrib'):
        # Remove the numeric label 1, 2, etc.
        for xref_tag in contrib_tag.findall('./xref'):
            if xref_tag.get('ref-type') == "aff":
                xref_tag.text = ''
        # Remove the <label> tag
        for aff_tag in contrib_tag.findall('./aff'):      
            for label_tag in aff_tag.findall('./label'):
                if len(label_tag.attrib) <= 0:
                    # Label with no attributes, remove it
                    aff_tag.remove(label_tag)
                    
    return root

def convert_contrib_role(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find contrib role and change it
    """
    
    for contrib_tag in root.findall('./front/article-meta/contrib-group/contrib'):

        # Edit the <role> tag contents
        for role_tag in contrib_tag.findall('./role'):
            # At least two messy articles (02394 and 02619)
            #  require text changes to clean up the role value
            
            if role_tag.text.lstrip()[0:4] == 'is a':
                # Article 02394
                for name_tag in contrib_tag.findall('./name'):
                    x_tag = Element('x')
                    x_tag.text = ' is a '
                    
                    # Hardcoded insert an Element at index 1 for this article
                    contrib_tag.insert(1, x_tag)

                role_tag.text = role_tag.text.lstrip()[4:]
                
                # Also need to change the tail on 02394
                xref_tag = SubElement(contrib_tag, 'xref')
                xref_tag.set('ref-type', "aff")
                xref_tag.set('rid', "aff1")
                
                x_tag = SubElement(contrib_tag, 'x')
                x_tag.text = ', and is at the '
                
                # Hardcoding the remaining values since it is the only article like this
                for contrib_group_tag in root.findall('./front/article-meta/contrib-group'):
                    aff_tag = SubElement(contrib_group_tag, 'aff')
                    aff_tag.set('id', "aff1")
                    institution_tag = SubElement(aff_tag, 'institution')
                    institution_tag.text = 'Max Planck Institute for Chemical Ecology'
                    addr_line_tag = SubElement(aff_tag, 'addr-line')
                    named_content_tag = SubElement(addr_line_tag, 'named-content')
                    named_content_tag.set('content-type', "city")
                    named_content_tag.text = 'Jena'
                    country_tag = SubElement(aff_tag, 'country')
                    country_tag.text = 'Germany'
                    email_tag = SubElement(aff_tag, 'email')
                    for tag in contrib_tag.findall('./email'):
                        email_tag.text = tag.text
                        contrib_tag.remove(tag)
                
                # Remove the old tail content
                for tag in role_tag.iter():
                    tag.tail = ''
            
            elif role_tag.text.lstrip()[0:3] == 'is ':
                # Article 02619
                for name_tag in contrib_tag.findall('./name'):
                    x_tag = Element('x')
                    x_tag.text = ' is '
                    
                    # Hardcoded insert an Element at index 1 for this article
                    contrib_tag.insert(1, x_tag)
                    
                role_tag.text = role_tag.text.lstrip()[3:]

            # Debug print role values for inspection
            """
            for tag in role_tag.iter():
                print tag.text
                if tag.tail:
                    print tag.tail
            """
   
    return root
    
def convert_aff_department(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find aff addr-line named-content content-type="department" and change it
    """
    for addr_line_tag in root.findall('./front/article-meta/contrib-group/aff/addr-line'):
        addr_line_tag = convert_addr_line(addr_line_tag)
    for addr_line_tag in root.findall('./front/article-meta/contrib-group/contrib/aff/addr-line'):
        addr_line_tag = convert_addr_line(addr_line_tag)

    return root

def convert_addr_line(root):
    """
    Given an xml.etree.ElementTree.Element for addr-line
    Change the named-content department tag to the new format
    """
    
    for named_content_tag in root.findall('./named-content'):
        content_type = named_content_tag.get('content-type')

        if content_type == 'department':
            # Rename and change it
            root.tag = 'institution'
            root.set('content-type', "dept")
            root.text = named_content_tag.text
            
            root.remove(named_content_tag)
    
    return root

def convert_contrib_aff(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find contrib aff and change it regarding extra words and punctuation
    """

    # Remove extra label tags
    for aff_tag in root.findall('./front/article-meta/contrib-group/aff'):
        for label_tag in aff_tag.findall('./label'):
            aff_tag.remove(label_tag)   

    # Change contrib aff tag content
    for contrib_tag in root.findall('./front/article-meta/contrib-group/contrib'):
        for aff_tag in contrib_tag.findall('./aff'):

            # Convert the aff tags found inside the corresponding contrib tag
            contrib_tag, aff_tag = convert_aff_bold_tag(contrib_tag, aff_tag)
            
    # Change contrib aff tag that is not found nested inside, need to match by xref id
    # Example is 10.7554/eLife.02854
    for contrib_tag in root.findall('./front/article-meta/contrib-group/contrib'):
        for xref_tag in contrib_tag.findall('./xref'):
            if xref_tag.get('ref-type') == 'aff':
                # Have the matching xref tag now look for the aff tag
                for aff_tag in root.findall('./front/article-meta/contrib-group/aff'):
                    if aff_tag.get('id') == xref_tag.get('rid'):
                        contrib_tag, aff_tag = convert_aff_bold_tag(contrib_tag, aff_tag)

                
    return root

def convert_aff_bold_tag(contrib_tag, aff_tag):
    """
    In order to convert <bold> tag in an aff tag
    Given the corresponding contrib and aff tags
    do the conversion
    """
    
    x_tag = None
    
    # Take the tail of the bold tag and surround it with an x tag
    for bold_tag in aff_tag.findall('./bold'):
        
        print "found a bold tag"
        if bold_tag.tail and bold_tag.tail.strip() != '':
            # Change the bold_tag to an x_tag
            x_tag = Element('x')
            x_tag.text = bold_tag.tail
            
            # Insert the x tag before the aff tag
            try:
                aff_index = get_first_element_index(contrib_tag, 'aff')
                contrib_tag.insert(aff_index - 1, x_tag)
            except TypeError:
                # In the case of where aff tags are not nested inside the contrib tag,
                #  just append it to the end of the contrib tag
                
                #print "special contrib aff"
                contrib_tag.append(x_tag)
            
            aff_tag.remove(bold_tag)
        else:
            # No tail, just remove the tag
            aff_tag.remove(bold_tag)
    
    # Turn the x_tag text into a role for some articles
    if x_tag is not None:
        
        # How do we do this? One way is to first ignore all the values we know
        #  do not contain a role
        non_role_values = ['is an', 'is at', 'is at the', 'is in', 'is in the']
        if x_tag.text.strip() not in non_role_values:
            
            # Convert specific values to roles
            contrib_tag = change_x_tag_to_role(contrib_tag, aff_tag, x_tag)
            #print "x_tag in " + get_doi(root) + ": " + x_tag.text
            
    # Find italic tag if present
    for italic_tag in aff_tag.findall('./italic'):
        # Convert specific values to roles
        contrib_tag = change_italic_tag_to_role(contrib_tag, aff_tag, italic_tag)
        #print "italic_tag in " + get_doi(root) + ": " + italic_tag.text
    
    # Print out some plain text values that start with 'is' for review
    """
    for tag in aff_tag.iter():
        if tag.tail and tag.tail.strip()[0:3] == 'is ':
            print tag.tail
    """
    
    return contrib_tag, aff_tag

def add_tag_before(tag_name, tag_text, parent_tag, before_tag_name):
    """
    Helper function to refactor the adding of new tags
    especially for when converting text to role tags
    """
    new_tag = Element(tag_name)
    new_tag.text = tag_text
    parent_tag.insert( get_first_element_index(parent_tag, before_tag_name) - 1, new_tag)
    return parent_tag
    

def change_x_tag_to_role(contrib_tag, aff_tag, x_tag):
    """
    Special cases of articles that need text to role tag conversions
    """
    if x_tag.text.strip() == 'is the chair of Patients Know Best and was the editor of the BMJ from 1991 to 2004':
        # 10.7554/eLife.00351

        contrib_tag = add_tag_before('x', ' is the ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Chair of Patients Know Best', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' and was the ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Editor of the BMJ from 1991 to 2004', contrib_tag, 'aff')

        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == ', a senior editor on':
        # 10.7554/eLife.00385
        
        contrib_tag = add_tag_before('x', ', a ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Senior editor on ', contrib_tag, 'aff')
        for role_tag in contrib_tag.findall('./role'):
            italic_tag = SubElement(role_tag, 'italic')
            italic_tag.text = 'eLife'
        contrib_tag = add_tag_before('x', ', is in the ', contrib_tag, 'aff')
        
        # Remove aff tag italic and its tail
        for italic_tag in aff_tag.findall('./italic'):
            aff_tag.remove(italic_tag)
        
        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is Deputy Editor of':
        # 10.7554/eLife.00615

        contrib_tag = add_tag_before('x', ' is ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Deputy Editor of ', contrib_tag, 'aff')
        for role_tag in contrib_tag.findall('./role'):
            italic_tag = SubElement(role_tag, 'italic')
            italic_tag.text = 'eLife'
        contrib_tag = add_tag_before('x', ' and ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Director', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' of ', contrib_tag, 'aff')
        
        # Remove aff tag italic and its tail
        for italic_tag in aff_tag.findall('./italic'):
            aff_tag.remove(italic_tag)
        
        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is the director of':
        # 10.7554/eLife.00639
        contrib_tag = add_tag_before('x', ' is the ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Director', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' of ', contrib_tag, 'aff')
        
        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is professor emeritus in the':
        # 10.7554/eLife.00642
        
        contrib_tag = add_tag_before('x', ' is ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Professor emeritus', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' in the ', contrib_tag, 'aff')
        
        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is a PhD student in the':
        # 10.7554/eLife.00646
        # 10.7554/eLife.02658
        
        contrib_tag = add_tag_before('x', ' is a ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'PhD student', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' in the ', contrib_tag, 'aff')

        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is director at the':
        # 10.7554/eLife.00856
        
        contrib_tag = add_tag_before('x', ' is ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Director', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' at the ', contrib_tag, 'aff')

        # Remove x_tag
        contrib_tag.remove(x_tag)
        
        pass
    
    elif x_tag.text.strip() == ', an':
        # 10.7554/eLife.00903

        contrib_tag = add_tag_before('x', ', an ', contrib_tag, 'aff')
        
        contrib_tag = add_tag_before('role', '', contrib_tag, 'aff')
        for role_tag in contrib_tag.findall('./role'):
            italic_tag = SubElement(role_tag, 'italic')
            italic_tag.text = 'eLife'
            italic_tag.tail = ' reviewing editor'
        contrib_tag = add_tag_before('x', ', is at ', contrib_tag, 'aff')
        
        # Remove aff tag italic and its tail
        for italic_tag in aff_tag.findall('./italic'):
            aff_tag.remove(italic_tag)
        
        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is Chief Scientific Adviser at the':
        # 10.7554/eLife.01061
        
        contrib_tag = add_tag_before('x', ' is ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Chief Scientific Adviser', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' at the ', contrib_tag, 'aff')

        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is professor emeritus at the':
        # 10.7554/eLife.01138

        contrib_tag = add_tag_before('x', ' is ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Professor emeritus', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' at the ', contrib_tag, 'aff')
        
        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    elif x_tag.text.strip() == 'is the head of bioinformatics at the':
        # 10.7554/eLife.01294

        contrib_tag = add_tag_before('x', ' is the ', contrib_tag, 'aff')
        contrib_tag = add_tag_before('role', 'Head of bioinformatics', contrib_tag, 'aff')
        contrib_tag = add_tag_before('x', ' at the ', contrib_tag, 'aff')

        # Remove x_tag
        contrib_tag.remove(x_tag)
    
    return contrib_tag
    
def change_italic_tag_to_role(contrib_tag, aff_tag, italic_tag):
    """
    Special cases of articles that need text to role tag conversions
    containing <italic>eLife</italic> in their aff
    """
    if italic_tag.text.strip() not in ['eLife','eLife reviewing editor']:
        # The content format is unexpected just return it
        return contrib_tag
    
    # Continue
    if (italic_tag.tail.strip() == ', and at'
        and italic_tag.text.strip() == 'eLife reviewing editor'):
        # 10.7554/eLife.00302
        
        contrib_tag = convert_italic_tag_to_role(
            contrib_tag = contrib_tag,
            italic_text = 'eLife',
            italic_tail = ' reviewing editor',
            x_tag_text  = ', and at ')

        # Remove italic_tag
        aff_tag.remove(italic_tag)
    
    elif (italic_tag.tail.strip() == 'reviewing editor, and is in the'
          and italic_tag.text.strip() == 'eLife'):
        # 10.7554/eLife.00281
        # 10.7554/eLife.02087
        # 10.7554/eLife.02475

        contrib_tag = convert_italic_tag_to_role(
            contrib_tag = contrib_tag,
            italic_text = 'eLife',
            italic_tail = ' reviewing editor',
            x_tag_text  = ', and is in the ')
        
        # Remove italic_tag
        aff_tag.remove(italic_tag)
    
    elif (italic_tag.tail.strip() == 'reviewing editor, and is at the'
          and italic_tag.text.strip() == 'eLife'):
        # 10.7554/eLife.00533
        # 10.7554/eLife.00648
        # 10.7554/eLife.01115
        # 10.7554/eLife.01968
        # 10.7554/eLife.02088

        contrib_tag = convert_italic_tag_to_role(
            contrib_tag = contrib_tag,
            italic_text = 'eLife',
            italic_tail = ' reviewing editor',
            x_tag_text  = ', and is at the ')

        # Remove italic_tag
        aff_tag.remove(italic_tag)
        
    elif (italic_tag.tail.strip() == 'senior editor and is at the'
          and italic_tag.text.strip() == 'eLife'):
        # 10.7554/eLife.01140
        
        contrib_tag = convert_italic_tag_to_role(
            contrib_tag = contrib_tag,
            italic_text = 'eLife',
            italic_tail = ' senior editor',
            x_tag_text  = ' and is at the ')
        
        # Remove italic_tag
        aff_tag.remove(italic_tag)
        
    elif (italic_tag.tail.strip() == 'senior editor, and is in the'
          and italic_tag.text.strip() == 'eLife'):
        # 10.7554/eLife.00353
        # 10.7554/eLife.01515
        # 10.7554/eLife.02791

        contrib_tag = convert_italic_tag_to_role(
            contrib_tag = contrib_tag,
            italic_text = 'eLife',
            italic_tail = ' senior editor',
            x_tag_text  = ', and is in the ')

        # Remove italic_tag
        aff_tag.remove(italic_tag)
    
    elif (italic_tag.tail.strip() == 'Senior Editor, and is at the'
          and italic_tag.text.strip() == 'eLife'):
        # 10.7554/eLife.00676

        contrib_tag = convert_italic_tag_to_role(
            contrib_tag = contrib_tag,
            italic_text = 'eLife',
            italic_tail = ' Senior Editor',
            x_tag_text  = ', and is at the ')

        # Remove italic_tag
        aff_tag.remove(italic_tag)
    
    elif (italic_tag.tail.strip() ==
           'senior editor and is at the Hospital for Sick Children Research Institute,'
          and italic_tag.text.strip() == 'eLife'):
        # 10.7554/eLife.02517
        
        contrib_tag = convert_italic_tag_to_role(
            contrib_tag = contrib_tag,
            italic_text = 'eLife',
            italic_tail = ' senior editor',
            x_tag_text  = ' and is at the ')
        
        # Need to add a institution department tag
        institution_tag = Element('institution')
        institution_tag.text = 'Hospital for Sick Children Research Institute'
        institution_tag.set('content-type', 'dept')
        institution_tag.tail = ', '
        aff_tag.insert(1, institution_tag)
        
        # Remove italic_tag
        aff_tag.remove(italic_tag)
    
    return contrib_tag

def convert_italic_tag_to_role(contrib_tag, italic_text, italic_tail, x_tag_text):
    """
    Specialized converter used when contrib aff italic eLife
    tags are found and need converting, refactored for cleaner code
    """
    
    try:
        contrib_tag = add_tag_before('role', '', contrib_tag, 'aff')
    except TypeError:
        # In the case of where the aff tag is not nested inside the contrib tag
        #  append it instead
        role_tag = Element('role')
        contrib_tag.append(role_tag)
        
    for role_tag in contrib_tag.findall('./role'):
        role_italic_tag = SubElement(role_tag, 'italic')
        role_italic_tag.text = italic_text
        role_italic_tag.tail = italic_tail
            
    try:
        contrib_tag = add_tag_before('x', x_tag_text, contrib_tag, 'aff')
    except TypeError:
        # In the case of where the aff tag is not nested inside the contrib tag
        #  append it instead
        role_tag = Element('role')
        
        x_tag = Element('x')
        x_tag.text = x_tag_text
        contrib_tag.append(x_tag)
    
    return contrib_tag

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
            fn_tag.set('fn-type', "con")

    for xref_tag in root.findall('./front/article-meta/contrib-group/contrib/xref'):
        ref_type = xref_tag.get('ref-type')
        rid = xref_tag.get('rid')

        if ref_type == "fn" and str(rid)[0:5] == 'equal':
            xref_tag.set('ref-type', "fn")
   
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
        institution_tag.text = funding_source_tag.text.strip()

        # Clean up
        
        funding_source_tag.text = None

    return root

def convert_related_article(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find related-article tag and change it
    """
    
    # Note the double slash to find the tag in all subelements, mostly paragraphs
    for related_article_tag in root.findall('./back/sec/sec//related-article'):
        # Change it
        #print related_article_tag
        if related_article_tag.get('related-article-type') == 'generated-dataset':
            related_article_tag.set('related-article-type', "existing-dataset")
       
    return root

def convert_related_object(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find related-object tag and change it
    """
    
    # Note the double slash to find the tag in all subelements, mostly paragraphs
    for related_object_tag in root.findall('./back/sec/sec//related-object'):
        # Change it
        related_object_tag.tag = 'related-article'
        related_object_tag.set('related-article-type', related_object_tag.get('content-type'))
        
        del related_object_tag.attrib['content-type']
        del related_object_tag.attrib['document-id']
        del related_object_tag.attrib['document-id-type']
        del related_object_tag.attrib['document-type']

    return root

def convert_mixed_citation(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find mixed-citation tag and change it
    """
    
    for mixed_citation_tag in root.findall('./back/ref-list/ref/mixed-citation'):
        # Change it
        mixed_citation_tag.tag = 'element-citation'
        
    # Continue by removing extra punctuation
    for mixed_citation_tag in root.findall('./back/ref-list/ref/element-citation'):
        tag_list = []
        tag_list.append('./person-group')
        tag_list.append('./year')
        tag_list.append('./article-title')
        tag_list.append('./source')
        tag_list.append('./volume')
        tag_list.append('./fpage')
        tag_list.append('./lpage')
        tag_list.append('./ext-link')
        tag_list.append('./pub-id')
        tag_list.append('./publisher-loc')
        tag_list.append('./publisher-name')
        tag_list.append('./comment')
        tag_list.append('./collab')
        tag_list.append('./issue')
        tag_list.append('./edition')
        tag_list.append('./bold')
        tag_list.append('./supplement')
        tag_list.append('./etal')
        
        for tag_name in tag_list:
            for tag in mixed_citation_tag.findall(tag_name):
                if tag.tail:
                    # Debugging - not sure if the editor values of a citation are important
                    #  check them out later - TODO!!!
                    pattern = re.compile("editor", re.UNICODE)
                    if pattern.search(tag.tail):
                        print "found citation editors in article doi " + get_doi(root)
                        
                    # Remove the content
                    tag.tail = ''

    return root

def convert_custom_meta_group(root):
    """
    Given an xml.etree.ElementTree.Element,
    Find custom-meta-group tag and change it
    """
    
    for custom_meta_group_tag in root.findall('./front/article-meta/custom-meta-group'):
        for custom_meta_tag in custom_meta_group_tag.findall('./custom-meta'):
            for meta_name_tag in custom_meta_tag.findall('./meta-name'):
                if meta_name_tag.text == 'elife-xml-version':
                    # Change the version
                    for meta_value_tag in custom_meta_tag.findall('./meta-value'):
                        meta_value_tag.text = "2"
    return root

def get_first_element_index(root, tag_name):
    """
    In order to use Element.insert() in a convenient way,
    this function will find the first child tag with tag_name
    and return its index position
    The index can then be used to insert an element before or after the
    found tag using Element.insert() 
    """
    tag_index = 1
    for tag in root:
        if tag.tag == tag_name:
            # Return the first one found if there is a match
            return tag_index
        tag_index = tag_index + 1
    # Default
    return None

def get_doi(root):
    
    doi = None
    
    for tag in root.findall('./front/article-meta/article-id[@pub-id-type="doi"]'):
        doi = tag.text
        
    return doi

def convert(root):
    """
    Parent method that calls each individual conversion step
    """
    
    convert_root(root)
    convert_issn(root)
    convert_pub_date(root)
    convert_contrib_label(root)
    convert_contrib_orcid(root)
    convert_contrib_role(root)
    convert_contrib_aff(root)
    convert_aff_department(root)
    convert_fn_equal_contrib(root)
    convert_copyright_statement(root)
    convert_license(root)
    convert_funding_source(root)
    # Convert related-article before related-object
    convert_related_article(root)
    convert_mixed_citation(root)
    convert_custom_meta_group(root)

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
                            ,"elife00351.xml"
                            ,"elife00352.xml"
                            ,"elife00365.xml"
                            ,"elife00790.xml"
                            ,"elife02053.xml"
                            ,"elife02394.xml"
                            ,"elife02619.xml"
                            ,"elife02791.xml"
                            ,"elife02951.xml"
                            ,"elife03401.xml"
                            ,"elife00385.xml"
                            ,"elife00615.xml"
                            ,"elife00639.xml"
                            ,"elife00642.xml"
                            ,"elife00646.xml"
                            ,"elife00856.xml"
                            ,"elife00903.xml"
                            ,"elife01061.xml"
                            ,"elife01138.xml"
                            ,"elife01294.xml"
                            ,"elife02658.xml"
                            ,"elife00281.xml"
                            ,"elife00302.xml"
                            ,"elife00353.xml"
                            ,"elife00533.xml"
                            ,"elife00648.xml"
                            ,"elife00676.xml"
                            ,"elife01115.xml"
                            ,"elife01140.xml"
                            ,"elife01515.xml"
                            ,"elife01968.xml"
                            ,"elife02087.xml"
                            ,"elife02088.xml"
                            ,"elife02475.xml"
                            ,"elife02517.xml"
                            ,"elife02854.xml"
                            #,"elife00856.xml"
                            ]
    #"""
    file_type = "/*.xml"
    article_xml_filenames = glob.glob('input' + file_type)

    for f in article_xml_filenames:
        #first_try(article_xml_filename)
        filename = f.split(os.sep)[-1]
        print "converting " + filename
        convert_file(filename)