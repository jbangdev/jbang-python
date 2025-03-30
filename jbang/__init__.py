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
    
    jbang_available = (subprocess.run("which jbang", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0) or \
                    (platform.system() == "Windows" and subprocess.run("which ./jbang.cmd", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0) or \
                    subprocess.run("which ./jbang", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0

    curl_available = subprocess.run("which curl", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    bash_available = subprocess.run("which bash", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    powershell_available = subprocess.run("which powershell", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    
    # Default subprocess arguments for interactive mode
    subprocess_args = {
        "shell": False,  # Don't use shell=True
        "universal_newlines": True,  # Handle text mode properly
        "stdout": subprocess.PIPE,  # Always capture output
        "stderr": subprocess.PIPE,  # Always capture stderr
        "stdin": subprocess.PIPE,   # Always capture stdin
        "start_new_session": True   # Start in new process group
    }
    
    # Only connect stdin/stdout/stderr if they are available and not being captured
    try:
        if hasattr(sys.stdin, 'fileno'):
            try:
                sys.stdin.fileno()
                subprocess_args["stdin"] = sys.stdin
            except (IOError, OSError):
                pass
    except Exception:
        pass

    try:
        if hasattr(sys.stdout, 'fileno'):
            try:
                sys.stdout.fileno()
                subprocess_args["stdout"] = sys.stdout
            except (IOError, OSError):
                pass
    except Exception:
        pass

    try:
        if hasattr(sys.stderr, 'fileno'):
            try:
                sys.stderr.fileno()
                subprocess_args["stderr"] = sys.stderr
            except (IOError, OSError):
                pass
    except Exception:
        pass
    
    # Only capture output if explicitly requested
    if capture_output:
        subprocess_args["capture_output"] = True
        subprocess_args["text"] = True
        # Remove the stream connections if capturing output
        if "stdin" in subprocess_args:
            del subprocess_args["stdin"]
        if "stdout" in subprocess_args:
            del subprocess_args["stdout"]
        if "stderr" in subprocess_args:
            del subprocess_args["stderr"]
    
    if jbang_available:
        log.debug(f"using jbang: {arg_line}")
        process = subprocess.Popen(["jbang"] + list(args), **subprocess_args)
        try:
            cmd_result = process.wait()
            # Print output in real-time for Jupyter
            if hasattr(process, 'stdout') and process.stdout:
                print(process.stdout.read(), end='', flush=True)
            if hasattr(process, 'stderr') and process.stderr:
                print(process.stderr.read(), end='', flush=True, file=sys.stderr)
        except KeyboardInterrupt:
            if platform.system() == "Windows":
                process.terminate()
            else:
                process.send_signal(signal.SIGINT)
            process.wait()
            raise
    elif curl_available and bash_available:
        log.debug(f"using curl + bash: {arg_line}")
        # Create a copy of subprocess_args without shell parameter for shell commands
        shell_args = {k: v for k, v in subprocess_args.items() if k != "shell"}
        process = subprocess.Popen(f"curl -Ls https://sh.jbang.dev | bash -s - {arg_line}", shell=True, **shell_args)
        try:
            cmd_result = process.wait()
            # Print output in real-time for Jupyter
            if hasattr(process, 'stdout') and process.stdout:
                print(process.stdout.read(), end='', flush=True)
            if hasattr(process, 'stderr') and process.stderr:
                print(process.stderr.read(), end='', flush=True, file=sys.stderr)
        except KeyboardInterrupt:
            if platform.system() == "Windows":
                process.terminate()
            else:
                process.send_signal(signal.SIGINT)
            process.wait()
            raise
    elif powershell_available:
        log.debug(f"using powershell: {arg_line}")
        # Create a copy of subprocess_args without shell parameter for shell commands
        shell_args = {k: v for k, v in subprocess_args.items() if k != "shell"}
        subprocess.run('echo iex "& { $(iwr -useb https://ps.jbang.dev) } $args" > %TEMP%/jbang.ps1', shell=True, **shell_args)
        process = subprocess.Popen(["powershell", "-Command", f"%TEMP%/jbang.ps1 {arg_line}"], **subprocess_args)
        try:
            cmd_result = process.wait()
            # Print output in real-time for Jupyter
            if hasattr(process, 'stdout') and process.stdout:
                print(process.stdout.read(), end='', flush=True)
            if hasattr(process, 'stderr') and process.stderr:
                print(process.stderr.read(), end='', flush=True, file=sys.stderr)
        except KeyboardInterrupt:
            if platform.system() == "Windows":
                process.terminate()
            else:
                process.send_signal(signal.SIGINT)
            process.wait()
            raise
    else:
        log.debug(f"unable to pre-install jbang: {arg_line}")
        raise JbangExecutionError(f"Unable to pre-install jbang using '{arg_line}'. Please install jbang manually and try again. See https://jbang.dev for more information.", 1)
    
    if cmd_result != 0:
        if capture_output:
            error_msg = f"The command failed: 'jbang {arg_line}'. Code: {cmd_result}"
            if hasattr(process, 'stderr') and process.stderr:
                error_msg += f", Stderr: {process.stderr.read()}"
            raise JbangExecutionError(error_msg, cmd_result)
        else:
            raise JbangExecutionError(f"The command failed: 'jbang {arg_line}'. Code: {cmd_result}", cmd_result)

    return type('CommandResult', (), {'returncode': cmd_result})

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