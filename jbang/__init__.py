import shlex
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
    log.debug("Searching for jbang executable...")
    for cmd in ['jbang', './jbang.cmd' if platform.system() == 'Windows' else None, './jbang']:
        if cmd:
            log.debug(f"Checking for command: {cmd}")
            result = subprocess.run(f"which {cmd}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                log.debug(f"Found jbang at: {cmd}")
                return cmd
    log.warning("No jbang executable found in PATH")
    return None

def _get_installer_command() -> Optional[str]:
    """Get the appropriate installer command based on available tools."""
    log.debug("Checking for available installer tools...")
    if subprocess.run("which curl", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0 and \
       subprocess.run("which bash", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        log.debug("Will use curl/bash installer if needed")
        return "curl -Ls https://sh.jbang.dev | bash -s -"
    elif subprocess.run("which powershell", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
        log.debug("Will use PowerShell installer if needed")
        return 'iex "& { $(iwr -useb https://ps.jbang.dev) } $args"'
    log.warning("No suitable installer found")
    return None

def _setup_subprocess_args(capture_output: bool = False) -> Dict[str, Any]:
    """Setup subprocess arguments with proper terminal interaction."""
    log.debug(f"Setting up subprocess arguments (capture_output={capture_output})")
    args = {
        "shell": False,
        "universal_newlines": True,
        "start_new_session": False,
        "preexec_fn": os.setpgrp if platform.system() != "Windows" else None
    }
    
    if capture_output:
        log.debug("Configuring for captured output")
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
    log.debug(f"Received signal {signum}")
    if hasattr(frame, 'f_globals') and 'process' in frame.f_globals:
        process = frame.f_globals['process']
        if process and process.poll() is None:
            log.debug(f"Propagating signal {signum} to process group {os.getpgid(process.pid)}")
            if platform.system() == "Windows":
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signum)
            process.wait()
    sys.exit(0)

def _exec_library(*args: str, capture_output: bool = False) -> Any:
    """Execute jbang command for library usage."""
    arg_line = " ".join(args)
    log.debug(f"Executing library command: {arg_line}")
    
    jbang_path = _get_jbang_path()
    installer_cmd = _get_installer_command()
    
    if not jbang_path and not installer_cmd:
        log.error("No jbang executable or installer found")
        raise JbangExecutionError(
            f"Unable to pre-install jbang: {arg_line}. Please install jbang manually.",
            1
        )

    subprocess_args = {
        "shell": False,
        "universal_newlines": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "stdin": subprocess.PIPE
    }
    
    try:
        if jbang_path:
            log.debug(f"Using jbang executable: {jbang_path}")
            process = subprocess.Popen(
                [jbang_path] + list(args),
                **subprocess_args
            )
        else:
            log.debug(f"Using installer command: {installer_cmd}")
            if "curl" in installer_cmd:
                process = subprocess.Popen(
                    f"{installer_cmd} {arg_line}",
                    shell=True,
                    **{k: v for k, v in subprocess_args.items() if k != "shell"}
                )
            else:
                temp_script = os.path.join(os.environ.get('TEMP', '/tmp'), 'jbang.ps1')
                log.debug(f"Creating temporary PowerShell script: {temp_script}")
                with open(temp_script, 'w') as f:
                    f.write(installer_cmd)
                process = subprocess.Popen(
                    ["powershell", "-Command", f"{temp_script} {arg_line}"],
                    **subprocess_args
                )

        log.debug(f"Process started with PID: {process.pid}")
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            log.error(f"Command failed with code {process.returncode}")
            log.error(f"stderr: {stderr}")
            raise JbangExecutionError(
                f"Command failed with code {process.returncode}: {process.args}",
                process.returncode
            )
            
        result = type('CommandResult', (), {
            'returncode': process.returncode,
            'stdout': stdout,
            'stderr': stderr
        })
        
        if not capture_output:
            if stdout:
                print(stdout, end='', flush=True)
            if stderr:
                print(stderr, end='', flush=True, file=sys.stderr)
                
        return result
        
    except Exception as e:
        log.debug(f"Exception during execution: {str(e)}", exc_info=True)
        if isinstance(e, JbangExecutionError):
            raise
        raise JbangExecutionError(str(e), 1)

def _exec_cli(*args: str, capture_output: bool = False) -> Any:
    """Execute jbang command for CLI usage."""
    arg_line = " ".join(args)
    log.debug(f"Executing CLI command: {arg_line}")
    
    jbang_path = _get_jbang_path()
    installer_cmd = _get_installer_command()
    
    if not jbang_path and not installer_cmd:
        log.warn("No jbang executable or installer found")
        raise JbangExecutionError(
            f"Unable to pre-install jbang: {arg_line}. Please install jbang manually.",
            1
        )

    subprocess_args = _setup_subprocess_args(capture_output)
    
    try:
        if jbang_path:
            log.debug(f"Using jbang executable: {jbang_path}")
            process = subprocess.Popen(
                [jbang_path] + list(args),
                **subprocess_args
            )
        else:
            log.debug(f"Using installer command: {installer_cmd}")
            if "curl" in installer_cmd:
                process = subprocess.Popen(
                    f"{installer_cmd} {arg_line}",
                    shell=True,
                    **{k: v for k, v in subprocess_args.items() if k != "shell"}
                )
            else:
                temp_script = os.path.join(os.environ.get('TEMP', '/tmp'), 'jbang.ps1')
                log.debug(f"Creating temporary PowerShell script: {temp_script}")
                with open(temp_script, 'w') as f:
                    f.write(installer_cmd)
                process = subprocess.Popen(
                    ["powershell", "-Command", f"{temp_script} {arg_line}"],
                    **subprocess_args
                )

        log.debug(f"Process started with PID: {process.pid}")
        globals()['process'] = process

        try:
            process.wait()
            if process.returncode != 0:
                log.warn(f"Command failed with code {process.returncode}")
                raise JbangExecutionError(
                    f"Command failed with code {process.returncode}: {process.args}",
                    process.returncode
                )
            return type('CommandResult', (), {'returncode': process.returncode})
        except KeyboardInterrupt:
            log.debug("Received keyboard interrupt")
            if platform.system() == "Windows":
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGINT)
            process.wait()
            raise
    except Exception as e:
        log.warn(f"Exception during execution: {str(e)}", exc_info=True)
        if isinstance(e, JbangExecutionError):
            raise
        raise JbangExecutionError(str(e), 1)
    finally:
        if 'process' in globals():
            del globals()['process']

def exec(arg: str, capture_output: bool = False) -> Any:
    """Execute jbang command simulating shell."""
    log.debug(f"Executing command: {arg}")
    args = shlex.split(arg)
    return _exec_library(*args, capture_output=capture_output)

def main():
    """Command-line entry point for jbang-python."""
    log.debug("Starting jbang-python CLI")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGHUP, _handle_signal)
    signal.signal(signal.SIGQUIT, _handle_signal)
    log.debug("Signal handlers registered")

    try:
        result = _exec_cli(*sys.argv[1:], capture_output=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        log.debug("Received keyboard interrupt, exiting")
        sys.exit(0)
    except JbangExecutionError as e:
        log.debug(f"Jbang execution error: {str(e)}")
        sys.exit(e.exit_code)
    except Exception as e:
        log.debug(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()