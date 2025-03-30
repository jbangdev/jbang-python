import subprocess
import os
import platform
import logging
import sys
import signal
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)

class JbangExecutionError(Exception):
    """Custom exception to capture Jbang execution errors with exit code."""
    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code

def _get_jbang_path() -> Optional[str]:
    """Get the path to jbang executable."""
    for cmd in ['jbang', './jbang.cmd' if platform.system() == 'Windows' else None, './jbang']:
        if cmd:
            result = subprocess.run(f"which {cmd}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                return cmd
    return None

def _get_installer_command() -> Optional[str]:
    """Get the appropriate installer command based on available tools."""
    if subprocess.run("which curl", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0 and \
       subprocess.run("which bash", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        return "curl -Ls https://sh.jbang.dev | bash -s -"
    elif subprocess.run("which powershell", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        return 'iex "& { $(iwr -useb https://ps.jbang.dev) } $args"'
    return None

def _setup_subprocess_args(capture_output: bool = False) -> Dict[str, Any]:
    """Setup subprocess arguments with proper terminal interaction."""
    args = {
        "shell": False,
        "universal_newlines": True,
        "start_new_session": False,  # Changed to False to ensure proper signal propagation
        "preexec_fn": os.setpgrp if platform.system() != "Windows" else None  # Create new process group
    }
    
    if capture_output:
        args.update({
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "stdin": subprocess.PIPE
        })
    else:
        # Try to connect to actual terminal if available
        try:
            if hasattr(sys.stdin, 'fileno'):
                args["stdin"] = sys.stdin
        except (IOError, OSError):
            args["stdin"] = subprocess.PIPE

        try:
            if hasattr(sys.stdout, 'fileno'):
                args["stdout"] = sys.stdout
        except (IOError, OSError):
            args["stdout"] = subprocess.PIPE

        try:
            if hasattr(sys.stderr, 'fileno'):
                args["stderr"] = sys.stderr
        except (IOError, OSError):
            args["stderr"] = subprocess.PIPE

    return args

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

def exec(*args: str, capture_output: bool = False) -> Any:
    """Execute jbang command."""
    arg_line = " ".join(args)
    jbang_path = _get_jbang_path()
    installer_cmd = _get_installer_command()
    
    if not jbang_path and not installer_cmd:
        raise JbangExecutionError(
            f"Unable to pre-install jbang: {arg_line}. Please install jbang manually.",
            1
        )

    subprocess_args = _setup_subprocess_args(capture_output)
    
    try:
        if jbang_path:
            process = subprocess.Popen(
                [jbang_path] + list(args),
                **subprocess_args
            )
        else:
            if "curl" in installer_cmd:
                process = subprocess.Popen(
                    f"{installer_cmd} {arg_line}",
                    shell=True,
                    **{k: v for k, v in subprocess_args.items() if k != "shell"}
                )
            else:
                # PowerShell case
                temp_script = os.path.join(os.environ.get('TEMP', '/tmp'), 'jbang.ps1')
                with open(temp_script, 'w') as f:
                    f.write(installer_cmd)
                process = subprocess.Popen(
                    ["powershell", "-Command", f"{temp_script} {arg_line}"],
                    **subprocess_args
                )

        # Store process in globals for signal handler
        globals()['process'] = process

        try:
            process.wait()
            if process.returncode != 0:
                raise JbangExecutionError(
                    f"Command failed with code {process.returncode}: {arg_line}",
                    process.returncode
                )
            return type('CommandResult', (), {'returncode': process.returncode})
        except KeyboardInterrupt:
            if platform.system() == "Windows":
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGINT)
            process.wait()
            raise
    except Exception as e:
        if isinstance(e, JbangExecutionError):
            raise
        raise JbangExecutionError(str(e), 1)
    finally:
        # Clean up globals
        if 'process' in globals():
            del globals()['process']

def main():
    """Command-line entry point for jbang-python."""
    
    # Register signal handlers
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGHUP, _handle_signal)
    signal.signal(signal.SIGQUIT, _handle_signal)

    try:
        result = exec(*sys.argv[1:], capture_output=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(0)
    except JbangExecutionError as e:
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()