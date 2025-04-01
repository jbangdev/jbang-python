import pytest
import jbang

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
    out = jbang.exec('-Dx="funky bear" properties@jbangdev')
    assert out.exitCode == 0
    assert 'funky bear' in out.stdout
 
def test_multiple_argument_as_list():
    """Test multiple arguments as list."""
    print("\nTesting multiple arguments...")
    out = jbang.exec(['-Dx=funky bear', 'properties@jbangdev'])
    assert out.exitCode == 0
    assert 'funky bear' in out.stdout
 
def test_quote_empty_string():
    """Test quoting empty string."""
    assert jbang.quote(['']) == "''"

def test_quote_simple_string():
    """Test quoting simple string without special chars."""
    assert jbang.quote(['hello']) == 'hello'

def test_quote_string_with_spaces():
    """Test quoting string containing spaces."""
    assert jbang.quote(['hello world']) == "'hello world'"

def test_quote_string_with_double_quotes():
    """Test quoting string containing double quotes."""
    assert jbang.quote(['hello "world"']) == "'hello \"world\"'"

def test_quote_string_with_single_quotes():
    """Test quoting string containing single quotes."""
    assert jbang.quote(['hello\'world']) == '"hello\'world"'

def test_quote_string_with_special_chars():
    """Test quoting string containing special characters."""
    assert jbang.quote(['hello$world']) == 'hello\\$world'
    assert jbang.quote(['hello!world']) == 'hello\\!world'
    assert jbang.quote(['hello#world']) == 'hello\\#world'

def test_quote_multiple_strings():
    """Test quoting multiple strings."""
    assert jbang.quote(['hello world']) == "'hello world'"
    assert jbang.quote(["hello 'big world'"]) == '"hello \'big world\'"'
