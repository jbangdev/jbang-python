import logging
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, List, Optional, Union


class CommandResult:
    """Represents the result of a jbang command execution."""
    
    def __init__(self, stdout: str, stderr: str, exitCode: int):
        self.stdout = stdout
        self.stderr = stderr
        self.exitCode = exitCode
    
    def _repr_html_(self) -> str:
        """HTML representation for Jupyter notebooks."""
        # Determine the status and styling based on exit code
        if self.exitCode == 0:
            status = "✅ Success"
            exit_code_style = "color: green; font-weight: bold;"
        else:
            status = f"❌ Failed (exit code: {self.exitCode})"
            exit_code_style = "color: red; font-weight: bold;"
        
        # Count lines for display
        stdout_lines = len(self.stdout.splitlines()) if self.stdout.strip() else 0
        stderr_lines = len(self.stderr.splitlines()) if self.stderr.strip() else 0
        
        html = f"""
        <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; background-color: #f8f9fa;">
            <div style="margin-bottom: 10px;">
                <strong style="{exit_code_style}">{status}</strong>
            </div>
            
            <details style="margin-bottom: 10px;">
                <summary style="cursor: pointer; font-weight: bold; color: #0066cc;">📤 Standard Output ({stdout_lines} lines)</summary>
                <pre style="background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 4px; padding: 10px; margin: 5px 0; overflow-x: auto; font-size: 12px; line-height: 1.4;">{self._escape_html(self.stdout)}</pre>
            </details>
            
            <details style="margin-bottom: 10px;">
                <summary style="cursor: pointer; font-weight: bold; color: #cc6600;">📥 Standard Error ({stderr_lines} lines)</summary>
                <pre style="background-color: #fff5f5; border: 1px solid #ffcccc; border-radius: 4px; padding: 10px; margin: 5px 0; overflow-x: auto; font-size: 12px; line-height: 1.4;">{self._escape_html(self.stderr)}</pre>
            </details>
            
            <div style="font-size: 11px; color: #666; border-top: 1px solid #e0e0e0; padding-top: 8px; margin-top: 10px;">
                Exit Code: <span style="{exit_code_style}">{self.exitCode}</span>
            </div>
        </div>
        """
        return html
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
    
    def __repr__(self) -> str:
        """String representation of the command result."""
        stdout_lines = len(self.stdout.splitlines()) if self.stdout.strip() else 0
        stderr_lines = len(self.stderr.splitlines()) if self.stderr.strip() else 0
        return f"CommandResult(exitCode={self.exitCode}, stdout_lines={stdout_lines}, stderr_lines={stderr_lines})"


# Configure logging based on environment variable
debug_enabled = 'jbang' in os.environ.get('DEBUG', '')
if debug_enabled:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

log = logging.getLogger(__name__)

## used shell quote before but it is
## not working for Windows so ported from jbang 

def escapeCmdArgument(arg: str) -> str:
    cmdSafeChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,_+=:;@()-\\"
    if not all(c in cmdSafeChars for c in arg):
        # Windows quoting is just weird
        arg = ''.join('^' + c if c in '()!^<>&|% ' else c for c in arg)
        arg = arg.replace('"', '\\"')
        arg = '^"' + arg + '^"'
    return arg

def escapeBashArgument(arg: str) -> str:
    shellSafeChars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._+=:@%/-"
    if not all(c in shellSafeChars for c in arg):
        arg = arg.replace("'", "'\\''")
        arg = "'" + arg + "'"
    return arg
    
def quote(xs):
    if platform.system() == 'Windows':
        return ' '.join(escapeCmdArgument(s) for s in xs)
    return ' '.join(escapeBashArgument(s) for s in xs)
    

def _getCommandLine(args: Union[str, List[str]]) -> Optional[str]:
    """Get the jbang command line with arguments, using no-install option if needed."""
    log.debug("Searching for jbang executable...")
    
    # If args is a string, parse it into a list
    if isinstance(args, str):
        log.debug("args is a string, use as is")
        argLine = args;
    else: # else it is already a list and we need to quote each argument before joining them
        log.debug("args is a list, quoting each argument")
        argLine = quote(args)

    log.debug(f"argLine: {argLine}")
    # Try different possible jbang locations
    path = None
    for cmd in ['./jbang.cmd' if platform.system() == 'Windows' else None,
                'jbang',
                os.path.join(os.path.expanduser('~'), '.jbang', 'bin', 'jbang.cmd') if platform.system() == 'Windows' else None,
                os.path.join(os.path.expanduser('~'), '.jbang', 'bin', 'jbang')]:
        if cmd:
            if shutil.which(cmd):
                path = cmd
                break
    
    if path:
        log.debug(f"found existing jbang installation at: {path}")
        return " ".join([path, argLine])
    
    # Try no-install options
    if shutil.which('curl') and shutil.which('bash'):
        log.debug("running jbang using curl and bash")
        return " ".join(["curl -Ls https://sh.jbang.dev | bash -s -", argLine])
    elif shutil.which('powershell'):
        log.debug("running jbang using PowerShell")
        return 'powershell -Command iex "& { $(iwr -useb https://ps.jbang.dev) } $argLine"'
    else:
        log.debug("no jbang installation found")
        return None

def exec(args: Union[str, List[str]]) -> Any:
    log.debug(f"try to execute async command: {args} of type {type(args)}")
    
    cmdLine = _getCommandLine(args)
  
    if cmdLine:
        log.debug("executing command: '%s'", cmdLine);

        result = subprocess.run(
                cmdLine,
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
        result = CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exitCode=result.returncode
            )
        log.debug(f"result: {result.__dict__}")
        return result
    else:
        print("Could not locate a way to run jbang. Try install jbang manually and try again.")
        raise Exception(
            "Could not locate a way to run jbang. Try install jbang manually and try again.",
            2
        )

def spawnSync(args: Union[str, List[str]]) -> Any:
    log.debug(f"try to execute sync command: {args}")
    
    cmdLine = _getCommandLine(args)
  
    if cmdLine:
        log.debug("spawning sync command: '%s'", cmdLine);
        result = subprocess.run(
                cmdLine,
                shell=True,
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
                check=False
            )
        tuple = CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exitCode=result.returncode
            )
        log.debug(f"result: {tuple.__dict__}")
        return tuple
    else:
        print("Could not locate a way to run jbang. Try install jbang manually and try again.")
        raise Exception(
            "Could not locate a way to run jbang. Try install jbang manually and try again.",
            2
        )

def main():
    """Command-line entry point for jbang-python."""
    log.debug("Starting jbang-python CLI")

    try:
        result = spawnSync(sys.argv[1:])
        sys.exit(result.exitCode)
    except KeyboardInterrupt:
        log.debug("Keyboard interrupt")
        sys.exit(130)
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1) 