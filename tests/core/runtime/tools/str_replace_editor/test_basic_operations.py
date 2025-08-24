"""Tests for basic file editor operations."""

import json
import re

from openhands.core.runtime.tools.str_replace_editor import file_editor

from .conftest import parse_result


def test_file_editor_happy_path(temp_file):
    command = "str_replace"
    old_str = "test file"
    new_str = "sample file"

    # Create test file
    with open(temp_file, "w") as f:
        f.write("This is a test file.\nThis file is for testing purposes.")

    # Call the `file_editor` function
    result = file_editor(
        command=command,
        path=temp_file,
        old_str=old_str,
        new_str=new_str,
    )

    # Extract the JSON content using a regular expression
    match = re.search(
        r"<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>",
        result,
        re.DOTALL,
    )
    assert match, (
        "Output does not contain the expected <oh_aci_output_> tags in the correct format."
    )
    result_dict = json.loads(match.group(1))

    # Validate the formatted output in the result dictionary
    formatted_output = result_dict["formatted_output_and_error"]
    assert (
        formatted_output
        == f"""The file {temp_file} has been edited. Here's the result of running `cat -n` on a snippet of {temp_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.
Review the changes and make sure they are as expected. Edit the file again if necessary."""
    )
    assert result_dict["path"] == str(temp_file)
    assert result_dict["prev_exist"] is True
    assert (
        result_dict["old_content"]
        == "This is a test file.\nThis file is for testing purposes."
    )
    assert (
        result_dict["new_content"]
        == "This is a sample file.\nThis file is for testing purposes."
    )

    # Ensure the file content was updated
    with open(temp_file, "r") as f:
        content = f.read()
    assert "This is a sample file." in content


def test_file_editor_with_xml_tag_parsing(temp_file):
    # Create content that includes the XML tag pattern
    xml_content = """This is a file with XML tags parsing logic...
match = re.search(
    r'<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>',
    result,
    re.DOTALL,
)
...More text here.
"""

    with open(temp_file, "w") as f:
        f.write(xml_content)

    result = file_editor(
        command="view",
        path=temp_file,
    )

    # Ensure the content is extracted correctly
    match = re.search(
        r"<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>",
        result,
        re.DOTALL,
    )

    assert match, (
        "Output does not contain the expected <oh_aci_output_> tags in the correct format."
    )
    result_dict = json.loads(match.group(1))

    # Validate the formatted output in the result dictionary
    formatted_output = result_dict["formatted_output_and_error"]
    assert (
        formatted_output
        == f"""Here's the result of running `cat -n` on {temp_file}:
     1\tThis is a file with XML tags parsing logic...
     2\tmatch = re.search(
     3\t    r'<oh_aci_output_[0-9a-f]{{32}}>(.*?)</oh_aci_output_[0-9a-f]{{32}}>',
     4\t    result,
     5\t    re.DOTALL,
     6\t)
     7\t...More text here.
     8\t
"""
    )


def test_successful_operations(temp_file):
    """Test successful file operations and their output formatting."""
    # Create a test file
    content = "line 1\nline 2\nline 3\n"
    with open(temp_file, "w") as f:
        f.write(content)

    # Test view
    result = file_editor(
        command="view",
        path=temp_file,
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert (
        "Here's the result of running `cat -n`"
        in result_json["formatted_output_and_error"]
    )
    assert "line 1" in result_json["formatted_output_and_error"]

    # Test str_replace
    result = file_editor(
        command="str_replace",
        path=temp_file,
        old_str="line 2",
        new_str="replaced line",
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert "has been edited" in result_json["formatted_output_and_error"]
    assert "replaced line" in result_json["formatted_output_and_error"]

    # Test insert
    result = file_editor(
        command="insert",
        path=temp_file,
        insert_line=1,
        new_str="inserted line",
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert "has been edited" in result_json["formatted_output_and_error"]
    assert "inserted line" in result_json["formatted_output_and_error"]

    # Test undo
    result = file_editor(
        command="undo_edit",
        path=temp_file,
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert "undone successfully" in result_json["formatted_output_and_error"]


def test_tab_expansion(temp_file):
    """Test that tabs are properly expanded in file operations."""
    # Create a file with tabs
    content = "no tabs\n\tindented\nline\twith\ttabs\n"
    with open(temp_file, "w") as f:
        f.write(content)

    # Test view command
    result = file_editor(
        command="view",
        path=temp_file,
        enable_linting=False,
    )
    result_json = parse_result(result)
    # Tabs should be expanded to spaces in output
    assert "\tindented" in result_json["formatted_output_and_error"]
    assert "line\twith\ttabs" in result_json["formatted_output_and_error"]

    # Test str_replace with tabs in old_str
    result = file_editor(
        command="str_replace",
        path=temp_file,
        old_str="line\twith\ttabs",
        new_str="replaced line",
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert "replaced line" in result_json["formatted_output_and_error"]

    # Test str_replace with tabs in new_str
    result = file_editor(
        command="str_replace",
        path=temp_file,
        old_str="replaced line",
        new_str="new\tline\twith\ttabs",
        enable_linting=False,
    )
    result_json = parse_result(result)
    # Tabs should be expanded in the output
    assert "new\tline\twith\ttabs" in result_json["formatted_output_and_error"]

    # Test insert with tabs
    result = file_editor(
        command="insert",
        path=temp_file,
        insert_line=1,
        new_str="\tindented\tline",
        enable_linting=False,
    )
    result_json = parse_result(result)
    # Tabs should be expanded in the output
    assert "\tindented\tline" in result_json["formatted_output_and_error"]
