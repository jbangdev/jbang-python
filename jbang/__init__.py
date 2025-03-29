import subprocess
import os
import platform
import logging
import sys
import signal

log = logging.getLogger(__name__)

class JbangExecutionError(Exception):
    """Custom exception to capture Jbang execution errors with exit code."""
    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code

def exec(*args, capture_output=False):
    arg_line = " ".join(args)
    cmd_result = None
    
    jbang_available = (subprocess.run(["which", "jbang"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0) or \
                    (platform.system() == "Windows" and subprocess.run(["which", "./jbang.cmd"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0) or \
                    subprocess.run(["which", "./jbang"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0

    curl_available = subprocess.run(["which", "curl"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    bash_available = subprocess.run(["which", "bash"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    powershell_available = subprocess.run(["which", "powershell"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    
    # Default subprocess arguments for interactive mode
    subprocess_args = {
        "shell": False,  # Don't use shell=True
        "check": False,
        "stdin": sys.stdin,  # Connect stdin
        "stdout": sys.stdout,  # Connect stdout
        "stderr": sys.stderr,  # Connect stderr
        "universal_newlines": True  # Handle text mode properly
    }
    
    # Only capture output if explicitly requested
    if capture_output:
        subprocess_args["capture_output"] = True
        subprocess_args["text"] = True
        # Remove the stream connections if capturing output
        del subprocess_args["stdin"]
        del subprocess_args["stdout"]
        del subprocess_args["stderr"]
    
    if jbang_available:
        log.debug(f"using jbang: {arg_line}")
        cmd_result = subprocess.run(["jbang"] + list(args), **subprocess_args)
    elif curl_available and bash_available:
        log.debug(f"using curl + bash: {arg_line}")
        cmd_result = subprocess.run(["curl", "-Ls", "https://sh.jbang.dev", "|", "bash", "-s", "-"] + list(args), **subprocess_args)
    elif powershell_available:
        log.debug(f"using powershell: {arg_line}")
        subprocess.run('echo iex "& { $(iwr -useb https://ps.jbang.dev) } $args" > %TEMP%/jbang.ps1', shell=True)
        cmd_result = subprocess.run(["powershell", "-Command", f"%TEMP%/jbang.ps1 {arg_line}"], **subprocess_args)
    else:
        log.debug(f"unable to pre-install jbang: {arg_line}")
        raise JbangExecutionError(f"Unable to pre-install jbang using '{arg_line}'. Please install jbang manually and try again. See https://jbang.dev for more information.", 1)
    
    if cmd_result.returncode != 0:
        if capture_output:
            error_msg = f"The command failed: 'jbang {arg_line}'. Code: {cmd_result.returncode}"
            if hasattr(cmd_result, 'stderr'):
                error_msg += f", Stderr: {cmd_result.stderr}"
            raise JbangExecutionError(error_msg, cmd_result.returncode)
        else:
            raise JbangExecutionError(f"The command failed: 'jbang {arg_line}'. Code: {cmd_result.returncode}", cmd_result.returncode)

    return cmd_result

def handle_signal(signum, frame):
    """Handle common termination signals."""
    exit_codes = {
        signal.SIGINT: 130,
        signal.SIGTERM: 130,
        signal.SIGHUP: 129,
        signal.SIGQUIT: 131,
    }
    sys.exit(exit_codes.get(signum, 1))

def main():
    """Command-line entry point for jbang-python."""
    
    # Configure logging
   # logging.basicConfig(
   #     level=logging.DEBUG,
   #     format='%(levelname)s: %(message)s'
   # )
        
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGHUP, handle_signal)
    signal.signal(signal.SIGQUIT, handle_signal)

    try:
        # Execute with direct stdio connection
        result = exec(*sys.argv[1:], capture_output=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        # Exit silently with the same code as the interrupted process
        sys.exit(0)
    except JbangExecutionError as e:
        #print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(e.exit_code)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()