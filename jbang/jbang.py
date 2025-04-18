import logging
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, List, Optional, Union

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
        result = type('CommandResult', (), {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exitCode': result.returncode
            })
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
        tuple = type('CommandResult', (), {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exitCode': result.returncode
            })
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