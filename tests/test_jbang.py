import sys

import pytest

import jbang
from jbang.jbang import CommandResult


def test_version_command():
    """Test version command."""
    print("\nTesting version command...")
    try:
        out = jbang.exec('--version')
        assert out.exitCode == 0
        print("✓ Version command works")
    except Exception as e:
        pytest.fail(f"✗ Version command failed: {e}")

def test_catalog_script():
    """Test catalog script execution."""
    print("\nTesting catalog script...")
    try:
        out = jbang.exec('properties@jbangdev')
        assert out.exitCode == 0
        print("✓ Catalog script works")
    except Exception as e:
        pytest.fail(f"✗ Catalog script failed: {e}")

def test_error_handling():
    """Test error handling."""
    print("\nTesting error handling...")
    out = jbang.exec('nonexistent-script-name')
    assert out.exitCode == 2
    print("✓ Error handling works") 

def test_multiple_argument_as_string():
    """Test multiple arguments as string."""
    print("\nTesting multiple arguments...")
    out = jbang.exec('-Dx="funky string" properties@jbangdev')
    assert out.exitCode == 0
    assert 'funky string' in out.stdout
 
def test_multiple_argument_as_list():
    """Test multiple arguments as list."""
    print("\nTesting multiple arguments...")
    out = jbang.exec(['-Dx=funky list', 'properties@jbangdev'])
    assert out.exitCode == 0
    assert 'funky list' in out.stdout

def test_java_version_specification():
    """Test Java version specification."""
    print("\nTesting Java version specification...")
    out = jbang.exec(['--java', '8+', 'properties@jbangdev', 'java.version'])
    assert out.exitCode == 0
    assert any(char.isdigit() for char in out.stdout), "Expected version number in output"

def test_invalid_java_version():
    """Test invalid Java version handling."""
    print("\nTesting invalid Java version handling...")
    out = jbang.exec('--java invalid properties@jbangdev java.version')
    assert 'Invalid version' in out.stderr

@pytest.mark.skipif(sys.platform == 'win32', reason="Quote tests behave differently on Windows")
class TestQuoting:
    def test_quote_empty_string(self):
        """Test quoting empty string."""
        assert jbang.quote(['']) == ""

    def test_quote_simple_string(self):
        """Test quoting simple string without special chars."""
        assert jbang.quote(['hello']) == 'hello'

    def test_quote_string_with_spaces(self):
        """Test quoting string containing spaces."""
        assert jbang.quote(['hello world']) == "'hello world'"

    def test_quote_string_with_double_quotes(self):
        """Test quoting string containing double quotes."""
        assert jbang.quote(['hello "world"']) == "'hello \"world\"'"

    def test_quote_string_with_single_quotes(self):
        """Test quoting string containing single quotes."""
        assert jbang.quote(["hello'world"]) == "'hello'\\''world'"

    def test_quote_string_with_special_chars(self):
        """Test quoting string containing special characters."""
        assert jbang.quote(['hello$world']) == "'hello$world'"
        assert jbang.quote(['hello!world']) == "'hello!world'"
        assert jbang.quote(['hello#world']) == "'hello#world'"

    def test_quote_multiple_strings(self):
        """Test quoting multiple strings."""
        assert jbang.quote(['hello world']) == "'hello world'"
        assert jbang.quote(["hello 'big world'"]) == "'hello '\\''big world'\\'''"


class TestCommandResult:
    """Test CommandResult class functionality."""
    
    def test_command_result_creation(self):
        """Test CommandResult object creation."""
        result = CommandResult("test output", "test error", 0)
        assert result.stdout == "test output"
        assert result.stderr == "test error"
        assert result.exitCode == 0
    
    def test_command_result_string_representation(self):
        """Test CommandResult string representation."""
        result = CommandResult("line1\nline2", "error1\nerror2", 0)
        repr_str = repr(result)
        assert "exitCode=0" in repr_str
        assert "stdout_lines=2" in repr_str
        assert "stderr_lines=2" in repr_str
    
    def test_command_result_string_representation_empty(self):
        """Test CommandResult string representation with empty outputs."""
        result = CommandResult("", "", 1)
        repr_str = repr(result)
        assert "exitCode=1" in repr_str
        assert "stdout_lines=0" in repr_str
        assert "stderr_lines=0" in repr_str
    
    def test_html_escaping(self):
        """Test HTML escaping functionality."""
        result = CommandResult("<script>alert('xss')</script>", "error & <test>", 0)
        html = result._repr_html_()
        
        # Check that HTML characters are properly escaped
        assert "&lt;script&gt;" in html
        assert "&amp;" in html
        assert "&quot;" in html or "&#x27;" in html
        assert "&gt;" in html
    
    def test_html_representation_success(self):
        """Test HTML representation for successful command."""
        result = CommandResult("Hello World\nLine 2", "", 0)
        html = result._repr_html_()
        
        # Check for success indicators
        assert "✅ Success" in html
        assert "color: green" in html
        assert "Hello World" in html
        assert "Standard Output (2 lines)" in html
        assert "Standard Error (0 lines)" in html
        assert "Exit Code: <span style=\"color: green" in html
    
    def test_html_representation_failure(self):
        """Test HTML representation for failed command."""
        result = CommandResult("Some output", "Error message\nMore error", 1)
        html = result._repr_html_()
        
        # Check for failure indicators
        assert "❌ Failed (exit code: 1)" in html
        assert "color: red" in html
        assert "Some output" in html
        assert "Error message" in html
        assert "Standard Output (1 lines)" in html
        assert "Standard Error (2 lines)" in html
        assert "Exit Code: <span style=\"color: red" in html
    
    def test_html_representation_structure(self):
        """Test HTML representation structure and elements."""
        result = CommandResult("test", "error", 0)
        html = result._repr_html_()
        
        # Check for required HTML elements
        assert "<div style=" in html
        assert "<details" in html
        assert "<summary" in html
        assert "<pre" in html
        assert "📤 Standard Output" in html
        assert "📥 Standard Error" in html
        assert "font-family: 'Monaco'" in html
        assert "border-radius: 8px" in html
    
    def test_html_representation_empty_outputs(self):
        """Test HTML representation with empty stdout and stderr."""
        result = CommandResult("", "", 0)
        html = result._repr_html_()
        
        # Should still show the structure but with 0 lines
        assert "Standard Output (0 lines)" in html
        assert "Standard Error (0 lines)" in html
        assert "✅ Success" in html
    
    def test_html_representation_multiline_output(self):
        """Test HTML representation with multiline output."""
        multiline_stdout = "Line 1\nLine 2\nLine 3\nLine 4"
        multiline_stderr = "Error 1\nError 2"
        result = CommandResult(multiline_stdout, multiline_stderr, 1)
        html = result._repr_html_()
        
        # Check line counts
        assert "Standard Output (4 lines)" in html
        assert "Standard Error (2 lines)" in html
        
        # Check that content is preserved
        assert "Line 1" in html
        assert "Line 4" in html
        assert "Error 1" in html
        assert "Error 2" in html
