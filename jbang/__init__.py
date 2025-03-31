import logging
import os
import platform
import shutil
import signal
import subprocess
import sys
from typing import Any, Dict, Optional

# Configure logging based on environment variable
debug_enabled = 'jbang' in os.environ.get('DEBUG', '')
if debug_enabled:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )


log = logging.getLogger(__name__)

def quote(xs):
    def quote_string(s):
        if s == '':
            return "''"
        if isinstance(s, dict) and 'op' in s:
            return ''.join(['\\' + char for char in s['op']])
        
        if any(char in s for char in ['"', ' ']) and "'" not in s:
            return "'" + s.replace("'", "\\'").replace("\\", "\\\\") + "'"
        
        if any(char in s for char in ['"', "'", ' ']):
            return '"' + s.replace('"', '\\"').replace('\\', '\\\\').replace('$', '\\$').replace('`', '\\`').replace('!', '\\!') + '"'
        
        return ''.join(['\\' + char if char in '#!"$&\'()*,:;<=>?[\\]^`{|}' else char for char in s])
    
    return ' '.join(map(quote_string, xs))

def _getCommandLine(args: list) -> Optional[str]:
    """Get the jbang command line with arguments, using no-install option if needed."""
    log.debug("Searching for jbang executable...")
    
    argLine = quote(args)
    # Try different possible jbang locations
    path = None
    for cmd in ['jbang', 
                './jbang.cmd' if platform.system() == 'Windows' else None, 
                os.path.expanduser('~/.jbang/bin/jbang')]:
        if cmd:
            if shutil.which(cmd):
                path = cmd
                break
    
    if path:
        log.debug(f"found existing jbang installation at: {path}")
        return ' '.join([path, argLine])
    
    # Try no-install options
    if shutil.which('curl') and shutil.which('bash'):
        log.debug("running jbang using curl and bash")
        return " ".join(["curl", "-Ls", "https://sh.jbang.dev", "|", "bash", "-s", "-", argLine])
    elif shutil.which('powershell'):
        log.debug("running jbang using PowerShell")
        return " ".join(["powershell", "-Command", "iex \"& { $(iwr -useb https://ps.jbang.dev) } $argLine\""])
    else:
        log.debug("no jbang installation found")
        return None

def exec(*args: str) -> Any:
    log.debug(f"try to execute async command: {args}")
    
    cmdLine = _getCommandLine(list(args))
  
    if cmdLine:
        result = subprocess.run(
                cmdLine,
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
        return type('CommandResult', (), {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exitCode': result.returncode
            })
    else:
        print("Could not locate a way to run jbang. Try install jbang manually and try again.")
        raise Exception(
            "Could not locate a way to run jbang. Try install jbang manually and try again.",
            2
        )

def spawnSync(*args: str) -> Any:
    log.debug(f"try to execute sync command: {args}")
    
    cmdLine = _getCommandLine(list(args))
  
    if cmdLine:
        result = subprocess.run(
                cmdLine,
                shell=True,
                stdin=sys.stdin,
                stdout=sys.stdout,
                stderr=sys.stderr,
                check=True
            )
        return type('CommandResult', (), {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exitCode': result.returncode
            })
    else:
        print("Could not locate a way to run jbang. Try install jbang manually and try again.")
        raise Exception(
            "Could not locate a way to run jbang. Try install jbang manually and try again.",
            2
        )

def _handle_signal(signum, frame):
    """Handle signals and propagate them to child processes."""
    if hasattr(frame, 'f_globals') and 'process' in frame.f_globals:
        process = frame.f_globals['process']
        if process and process.poll() is None:  # Process is still running
            if platform.system() == "Windows":
                process.terminate()
            else:
                # Send signal to the entire process group
                os.killpg(os.getpgid(process.pid), signum)
            process.wait()
    sys.exit(0)

def main():
    """Command-line entry point for jbang-python."""
    log.debug("Starting jbang-python CLI")

    try:
        result = spawnSync(*sys.argv[1:])
        sys.exit(result.exitCode)
    except KeyboardInterrupt:
        log.debug("Keyboard interrupt")
        sys.exit(130)
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()