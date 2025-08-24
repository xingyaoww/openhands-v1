from pathlib import Path

import pytest
from binaryornot.check import is_binary

from openhands_aci.editor.editor import OHEditor
from openhands_aci.editor.exceptions import FileValidationError


def test_validate_large_file(tmp_path):
    """Test that large files are rejected."""
    editor = OHEditor()
    large_file = tmp_path / "large.txt"

    # Create a file just over 10MB
    file_size = 10 * 1024 * 1024 + 1024  # 10MB + 1KB
    with open(large_file, "wb") as f:
        f.write(b"0" * file_size)

    with pytest.raises(FileValidationError) as exc_info:
        editor.validate_file(large_file)
    assert "File is too large" in str(exc_info.value)
    assert "10.0MB" in str(exc_info.value)


def test_validate_binary_file(tmp_path):
    """Test that binary files are rejected."""
    editor = OHEditor()
    binary_file = tmp_path / "binary.bin"

    # Create a binary file with null bytes
    with open(binary_file, "wb") as f:
        f.write(b"Some text\x00with binary\x00content")

    with pytest.raises(FileValidationError) as exc_info:
        editor.validate_file(binary_file)
    assert "file appears to be binary" in str(exc_info.value).lower()


def test_validate_text_file(tmp_path):
    """Test that valid text files are accepted."""
    editor = OHEditor()
    text_file = tmp_path / "valid.txt"

    # Create a valid text file
    with open(text_file, "w") as f:
        f.write("This is a valid text file\nwith multiple lines\n")

    # Should not raise any exception
    editor.validate_file(text_file)


def test_validate_directory():
    """Test that directories are skipped in validation."""
    editor = OHEditor()
    # Should not raise any exception for directories
    editor.validate_file(Path("/tmp"))


def test_validate_nonexistent_file():
    """Test validation of nonexistent file."""
    editor = OHEditor()
    nonexistent = Path("/nonexistent/file.txt")
    # Should not raise FileValidationError since validate_path will handle this case
    editor.validate_file(nonexistent)


def test_validate_pdf_file():
    """Test that PDF files are detected as binary."""
    editor = OHEditor()

    # Get the current directory and construct path to the PDF file
    current_dir = Path(__file__).parent
    pdf_file = current_dir / "data" / "sample.pdf"

    # the is_binary function is not accurate for PDF files
    assert not is_binary(str(pdf_file))

    # PDF is a supported file type, so no exception should be raised
    editor.validate_file(pdf_file)


def test_validate_image_file():
    """Test that image files are detected as binary."""
    editor = OHEditor()

    # Get the current directory and construct path to the image file
    current_dir = Path(__file__).parent.parent
    image_file = current_dir / "data" / "oh-logo.png"

    assert is_binary(str(image_file))

    # Images are not supported and should be detected as binary
    with pytest.raises(FileValidationError) as exc_info:
        editor.validate_file(image_file)

    assert "file appears to be binary" in str(exc_info.value).lower()
