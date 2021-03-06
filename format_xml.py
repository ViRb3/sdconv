from pathlib import Path
from typing import List
import xml.etree.ElementTree as ET
import argparse


def get_node_key(node, attr=None):
    """Return the sorting key of an xml node
    using tag and attributes
    """
    if attr is None:
        return "%s" % node.tag + ":".join([node.get(attr) for attr in sorted(node.attrib)])
    if attr in node.attrib:
        return "%s:%s" % (node.tag, node.get(attr))
    return "%s" % node.tag


def sort_children(node, attr=None):
    """Sort children along tag and given attribute.
    if attr is None, sort along all attributes"""
    if not isinstance(node.tag, str):
        # not a TAG, it is comment or DATA
        # no need to sort
        return
    # sort attributes by key, works only on Python 3.7+
    node.attrib = dict(sorted(node.attrib.items()))
    # sort child along attr
    node[:] = sorted(node, key=lambda child: get_node_key(child, attr))
    # and recurse
    for child in node:
        sort_children(child, attr)


def sort(unsorted_file, sorted_file, attr=None):
    """Sort unsorted xml file and save to sorted_file"""
    try:
        tree = ET.parse(unsorted_file)
    except Exception as e:
        print("Error parsing: " + str(e))
        return
    root = tree.getroot()
    sort_children(root, attr)

    ET.indent(tree, space=2 * " ", level=0)
    sorted_unicode = ET.tostring(root, encoding="unicode")
    with open(sorted_file, "w", encoding="utf-8") as output_fp:
        output_fp.write(sorted_unicode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sort XML elements alphabetically for better diffing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "inputs",
        metavar="INPUT",
        nargs="+",
        type=str,
        help="XML files to process.",
    )

    args = parser.parse_args()
    inputs: List[Path] = [Path(a).resolve() for a in args.inputs]

    for input in inputs:
        print(f"Processing {input}")
        sort(input, input)

    print(f"Done")
