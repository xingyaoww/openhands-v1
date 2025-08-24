from pathlib import Path

from openhands_aci.editor.editor import OHEditor
from openhands_aci.editor.results import CLIResult


def test_view_pdf_file():
    editor = OHEditor()

    tests_dir = Path(__file__).parent.parent.parent
    test_file = tests_dir / "data" / "sample.pdf"
    result = editor(command="view", path=str(test_file))

    assert isinstance(result, CLIResult)
    assert f"Here's the content of the file {test_file}" in result.output
    assert "displayed in Markdown format" in result.output

    # Check for specific content present in the PDF
    assert "Printer-Friendly Caltrain Schedule" in result.output
