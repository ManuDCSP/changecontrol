from django.contrib.postgres.fields import ArrayField
from django.db import models
import os
import sys
import xml.etree.ElementTree as ET
from django.shortcuts import render
from lxml import etree
from pathlib import Path

# constants

ERROR_FOLDER_NOT_FOUND = 0xA0
STATUS_CHOICES = (
    ("PREP" , "Preparation"),
    ("ONGOING", "Ongoing"),
    ("DEPLOYED" , "Deployed")
)

# models

class ChangeSet(models.Model):
    reference = models.CharField(max_length=255)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="PREP")


class XmlFile(models.Model):

    filename = models.CharField(max_length=255)
    object_type =  models.CharField(max_length=255,
        db_comment="Miles Object Type")
    object_ids = ArrayField(models.SmallIntegerField(),
        db_comment="Miles Object Ids")
    timestamp = models.DateTimeField(
        db_comment="Date and time when the file was generated",
    )

def upload(request):
    return render(request,'upload.html')


class Document(models.Model):
    description = models.CharField(max_length=255, blank=True)
    document = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

# internal classes used by models

class NodeToSort:
    def __init__(self, x_element):
        # initialize properties
        self.Name = None
        self.SortByAttr = None
        self.GroupWithNextSibling = False
        self.SortedChilds = []
        self.SortedNodeNames = []
        self.GroupedNodeNames = []

        name_x_element = x_element.find("Name")
        if name_x_element is not None:
            self.Name = name_x_element.text
            # if self.Name != '':
            #     self.SortedNodeNames.append(self.Name)

        sort_by_attr_x_element = x_element.find("SortByAttr")
        if sort_by_attr_x_element is not None:
            self.SortByAttr = sort_by_attr_x_element.text

        group_with_next_sibling_x_element = x_element.find("GroupWithNextSibling")
        if group_with_next_sibling_x_element is not None:
            self.GroupWithNextSibling = group_with_next_sibling_x_element.text == 'true'
            if self.GroupWithNextSibling:
                self.GroupedNodeNames.append(self.Name)

        sorted_childs_x_element = x_element.find("NodesToSort")
        if sorted_childs_x_element is not None:
            for child in sorted_childs_x_element.findall("NodeToSort"):
                child_node_to_sort = NodeToSort(child)
                self.SortedChilds.append(child_node_to_sort)
                # populate names from child into parent, avoiding duplicates
                self.SortedNodeNames.extend(
                    name for name in child_node_to_sort.SortedNodeNames if name not in self.SortedNodeNames
                )
                self.GroupedNodeNames.extend(
                    name for name in child_node_to_sort.GroupedNodeNames if name not in self.GroupedNodeNames
                )

    def FindRecursivelyByName(self, name):
        if self.Name == name:
            return self
        else:
            # search in childs
            result = next((x for x in self.SortedChilds if x.Name == name), None)
            if result is not None:
                return result
            else:
                # search recursively in each child
                for child in self.SortedChilds:
                    result = child.FindRecursivelyByName(name)
                    if result is not None:
                        return result

        return None  # no item found


class SortOptions:
    def __init__(self, e):
        self.SortedChilds = []
        self.SortedNodeNames = []
        # self.GroupedNodeNames = []

        for child in e:
            # recursive search of child items, loading the values in SortOptions
            sort_option_entry = NodeToSort(child)
            self.SortedChilds.append(sort_option_entry)

            # populate list of sorted node names
            if sort_option_entry.SortByAttr:
                self.SortedNodeNames.append(sort_option_entry.Name)

            self.SortedNodeNames.extend(
                [name for name in sort_option_entry.SortedNodeNames if name not in self.SortedNodeNames]
            )
            # if sort_option_entry.GroupWithNextSibling:
            #     self.GroupedNodeNames.append(sort_option_entry.Name)
            # self.GroupedNodeNames.extend(
            #     [name for name in sort_option_entry.GroupedNodeNames if name not in self.GroupedNodeNames]
            # )

    def FindRecursivelyByName(self, name):
        # search in childs
        result = next((x for x in self.SortedChilds if x.Name == name), None)
        if result and result.SortedChilds:
            return result
        else:
            # search recursively in each child
            for child in self.SortedChilds:
                result = child.FindRecursivelyByName(name)
                if result and result.SortedChilds:
                    return result
        return None  # no item found


class XMLTools(object):
    def __init__(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.sort_options = None
        # read XML file defining sorting criteria
        self.load_sorting_criteria_from_xml()


    def run_test2(self):
        self.input_dir = r"C:\Users\Manuel\source\repos\tests\\"
        # self.input_dir = os.getcwd()  # Uncomment for production use

        self.output_dir = os.path.join(os.getcwd(), "Output")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.input_dir = os.path.join(os.getcwd(), "Input")
        if not os.path.exists(self.input_dir):
            print(f"Input directory not found: {self.input_dir}")
            input()
            sys.exit(ERROR_FOLDER_NOT_FOUND)

        print(f"Processing xml files found in folder {self.input_dir}")
        for file in os.listdir(self.input_dir):
            if file.endswith(".xml"):
                resulting_file_name = f"{os.path.splitext(file)[0]}_sorted{os.path.splitext(file)[1]}"
                sorted_file_a = self.process_document(os.path.join(self.input_dir, file), resulting_file_name)

        print("Finished processing files")
        sys.exit(0)

    def process_document(self, original_file_path, resulting_file_name):
        print(f"Processing document {original_file_path}")
        with open(original_file_path, 'r', encoding='utf-8') as f:
            xml_file_text = f.read()

        xml_file_a = ET.parse(original_file_path)
        # recursive processing
        sorted_file = ET.ElementTree(self.process_xelement(xml_file_a.getroot()))

        ET.indent(sorted_file, space="  ", level=0)
        header_comments = self.get_header_comment(xml_file_text)
        with open(resulting_file_name, 'wb') as writer:
            writer.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            if header_comments:
                writer.write(f'<!--{header_comments}-->\n'.encode('utf-8'))
            sorted_file.write(writer, encoding="utf-8")

        reulting_file_path = os.path.join(self.output_dir, resulting_file_name)
        if os.path.exists(reulting_file_path):
            os.remove(reulting_file_path)
        os.rename(resulting_file_name, reulting_file_path)
        print(f"Sorted XML document created {resulting_file_name}")
        return sorted_file

    def process_xelement(self, e):
        processed_childs = []
        sort_opt = self.sort_options.FindRecursivelyByName(e.tag)

        if sort_opt is not None:
            # sort element
            sorted_xelement_childs = []
            next_batch_of_childs = []
            grouped_elements_in_next_batch = []

            # TODO: validate child elements found match with sorting configuration

            for child_sort_opt in sort_opt.SortedChilds:

                childs_found = e.findall(child_sort_opt.Name)
                if childs_found:

                    next_batch_of_childs.extend(childs_found)

                    if not child_sort_opt.GroupWithNextSibling:
                        # sort batch
                        order_by_str = ""
                        if child_sort_opt.SortByAttr:
                            order_by_str = child_sort_opt.SortByAttr

                        for group_element in grouped_elements_in_next_batch:
                            if not order_by_str:
                                order_by_str = group_element
                            else:
                                order_by_str += ", " + group_element

                        if not order_by_str:
                            # copy batch into final list
                            sorted_xelement_childs.extend(next_batch_of_childs)
                        else:
                            order_by_field_list = order_by_str.split(",")
                            order_by_field_list.reverse()

                            for sortby_field in order_by_str.split(","):
                                if any(attrName == sortby_field for attrName in next_batch_of_childs[0].attrib.keys()):
                                    next_batch_of_childs.sort(key=lambda e: e.get(sortby_field))
                                elif any(child.tag == sortby_field for child in next_batch_of_childs[0]):
                                    next_batch_of_childs.sort(key=lambda e: e.find(sortby_field).text)

                            sorted_xelement_childs.extend(next_batch_of_childs)

                        # clear batch list and list of grouped element names
                        next_batch_of_childs = []
                        grouped_elements_in_next_batch = []

            for child in sorted_xelement_childs:
                processed_childs.append(self.process_xelement(child))
        else:
            for child in e:
                processed_childs.append(self.process_xelement(child))

        root = etree.Element(e.tag)
        # add attributes
        for att in e.attrib:
            root.set(att, e.attrib[att])

        # first_text_node = next((node for node in e if isinstance(node, etree._ElementText)), None)
        # first_text_node = next((node for node in e if node.text is not None), None)
        # if first_text_node is not None:
        #    root.text = first_text_node.text

        # text_value = e.get_text()
        # if text_value is not None:
        root.text = e.text

        for processed_child in processed_childs:
            root.append(processed_child)

        return root

    def get_header_comment(self, xml):
        XML_COMMENT_START_DECLARATION = "<!--"
        XML_COMMENT_END_DECLARATION = "-->"

        if XML_COMMENT_START_DECLARATION in xml and XML_COMMENT_END_DECLARATION in xml:
            start_pos = xml.rindex(XML_COMMENT_START_DECLARATION) + len(XML_COMMENT_START_DECLARATION)
            length = xml.index(XML_COMMENT_END_DECLARATION) - start_pos

            sub = xml[start_pos:start_pos + length]

            return sub
            # xml = xml.replace(XML_COMMENT_START_DECLARATION, "").replace(XML_COMMENT_END_DECLARATION, "").replace(sub, "")
        else:
            return None

    def load_sorting_criteria_from_xml(self):
        import sys
        from xml.etree import ElementTree

        # Get the current module
        # this_module = sys.modules[__name__]
        # Get the module name
        # assembly_name = this_module.__package__ or this_module.__name__.split('.')[0]
        # Construct resource path
        # resource_path = f"{assembly_name}.Config.XmlSortingOptions.xml"
        # Open and read the resource
        try:

            # with pkg_resources.resource_stream(assembly_name, "Config/XmlSortingOptions.xml") as stream:
            path = Path('static/changeset/XmlSortingOptions.xml')
            print(path.exists())

            sorting_options_element = ElementTree.parse(path.absolute()).getroot()
            self.sort_options = SortOptions(sorting_options_element)
        except Exception as e:
            raise Exception(f"Failed to load sorting criteria: {str(e)}")