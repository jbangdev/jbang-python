import subprocess
import os
import platform
import logging

log = logging.getLogger(__name__)

def exec(*args):
    arg_line = " ".join(args)
    cmd_result = None
    
    jbang_available = (subprocess.run(["which", "jbang"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0) or \
                    (platform.system() == "Windows" and subprocess.run(["which", "./jbang.cmd"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0) or \
                    subprocess.run(["which", "./jbang"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0

    curl_available = subprocess.run(["which", "curl"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    bash_available = subprocess.run(["which", "bash"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    powershell_available = subprocess.run(["which", "powershell"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0
    
    if jbang_available:
        log.debug(f"using jbang: {arg_line}")
        cmd_result = subprocess.run(f"jbang {arg_line}", shell=True, capture_output=True, text=True)
    elif curl_available and bash_available:
        log.debug(f"using curl + bash: {arg_line}")
        cmd_result = subprocess.run(f"curl -Ls https://sh.jbang.dev | bash -s - {arg_line}", shell=True, capture_output=True, text=True)
    elif powershell_available:
        log.debug(f"using powershell: {arg_line}")
        subprocess.run('echo iex "& { $(iwr -useb https://ps.jbang.dev) } $args" > %TEMP%/jbang.ps1', shell=True)
        cmd_result = subprocess.run(f'powershell -Command "%TEMP%/jbang.ps1 {arg_line}"', shell=True, capture_output=True, text=True)
    else:
        log.debug(f"unable to pre-install jbang: {arg_line}")
        raise Exception(f"Unable to pre-install jbang using '{arg_line}'. Please install jbang manually and try again. See https://jbang.dev for more information.")
    
    if cmd_result.returncode != 0:
        raise Exception(f"The command failed: 'jbang {arg_line}'. Code: {cmd_result.returncode}, Stderr: {cmd_result.stderr}")

    return cmd_result