import subprocess
import shlex

class BashRunner:
    def __init__(self, console):
        self.console = console
    
    def run_command(self, command, interactive=False, check=False):
        """Run a bash command and return the result"""
        try:
            if interactive:
                # Run command interactively for commands that need user input
                return subprocess.run(command, shell=True)
            else:
                # Run command and capture output
                return subprocess.run(
                    command,
                    shell=True,
                    check=check,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
        except subprocess.CalledProcessError as e:
            self.console.print(f"[danger]Command failed: {e}[/danger]")
            self.console.print(f"[danger]Error output: {e.stderr}[/danger]")
            raise e
        except Exception as e:
            self.console.print(f"[danger]Error running command: {e}[/danger]")
            raise e
    
    def run_script(self, script_path, arguments=None):
        """Run a bash script with arguments"""
        cmd = [script_path]
        if arguments:
            if isinstance(arguments, list):
                cmd.extend(arguments)
            else:
                cmd.append(arguments)
        
        # Make script executable
        self.run_command(f"chmod +x {script_path}")
        
        # Run the script
        cmd_str = " ".join([shlex.quote(arg) for arg in cmd])
        return self.run_command(cmd_str)