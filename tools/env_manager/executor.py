import subprocess
import sys
import os
import shutil

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Executor:
    @staticmethod
    def log(message: str, level: str = "INFO"):
        if level == "INFO":
            print(f"{Colors.GREEN}[INFO]{Colors.ENDC} {message}")
        elif level == "WARN":
            print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {message}")
        elif level == "ERROR":
            print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {message}")
        elif level == "EXEC":
            print(f"{Colors.CYAN}[EXEC]{Colors.ENDC} {message}")
        elif level == "HEADER":
            print(f"\n{Colors.HEADER}{Colors.BOLD}=== {message} ==={Colors.ENDC}")

    @staticmethod
    def run_command(command: str, cwd: str = None, env: dict = None, ignore_errors: bool = False) -> bool:
        """
        Runs a shell command with real-time output.
        """
        Executor.log(command, level="EXEC")

        # Merge environment variables
        full_env = os.environ.copy()
        if env:
            full_env.update(env)

        try:
            # Use shell=True for flexibility with string commands
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=full_env,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Merge stderr to stdout for sequential logging
                text=True,
                encoding='utf-8',
                errors='replace' # Handle potential encoding issues
            )

            # Stream output
            for line in process.stdout:
                print(f"  {line}", end='')

            process.wait()

            if process.returncode != 0:
                if not ignore_errors:
                    Executor.log(f"Command failed with exit code {process.returncode}", level="ERROR")
                    return False
                else:
                    Executor.log(f"Command failed (ignored)", level="WARN")
            else:
                Executor.log("Command successful", level="INFO")

            return process.returncode == 0

        except Exception as e:
            Executor.log(f"Failed to execute command: {str(e)}", level="ERROR")
            if not ignore_errors:
                return False
            return True

    @staticmethod
    def check_command_exists(cmd: str) -> bool:
        return shutil.which(cmd) is not None
