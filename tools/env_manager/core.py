import os
import yaml
from typing import List, Dict
from .schema import SetupConfig
from .executor import Executor
from .utils import is_docker, is_root, is_linux

class EnvManager:
    def __init__(self, root_dir: str, scope: str = "dev"):
        self.root_dir = root_dir
        self.scope = scope
        self.configs: List[SetupConfig] = []
        self.system_deps: List[str] = []

    def scan(self):
        Executor.log(f"Scanning for setup.yaml in {self.root_dir}...", "HEADER")
        for root, dirs, files in os.walk(self.root_dir):
            if "setup.yaml" in files:
                file_path = os.path.join(root, "setup.yaml")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if not data:
                            continue
                        config = SetupConfig.from_dict(data)

                        # Store the directory context with the config
                        config._context_dir = root
                        self.configs.append(config)

                        Executor.log(f"Found config: {config.name} in {root}")

                        # Optimization: if scan_subdirs is False, remove subdirs from walk
                        if not config.scan_subdirs:
                            dirs[:] = []

                except Exception as e:
                    Executor.log(f"Error reading {file_path}: {e}", "ERROR")

    def install(self):
        Executor.log(f"Starting installation (Scope: {self.scope})", "HEADER")

        # 1. Collect System Deps first
        self._collect_system_deps()
        self._install_system_deps()

        # 2. Process each module
        for config in self.configs:
            self._process_module(config)

    def _collect_system_deps(self):
        for config in self.configs:
            for dep in config.system:
                dep_scope = dep.get("scope", "all")
                if dep_scope == "all" or dep_scope == self.scope:
                    self.system_deps.append(dep["name"])
        # Deduplicate
        self.system_deps = list(set(self.system_deps))

    def _install_system_deps(self):
        if not self.system_deps:
            return

        Executor.log(f"Installing system dependencies: {', '.join(self.system_deps)}", "INFO")

        if not is_linux():
            Executor.log("Skipping system dep installation (Not Linux)", "WARN")
            return

        cmd = f"apt-get update && apt-get install -y {' '.join(self.system_deps)}"

        if not is_root():
             Executor.log("Not root, trying with sudo...", "WARN")
             cmd = "sudo " + cmd

        Executor.run_command(cmd)

    def _process_module(self, config: SetupConfig):
        Executor.log(f"Processing module: {config.name}", "HEADER")
        cwd = getattr(config, '_context_dir', self.root_dir)

        # 1. Strategy Execution
        if "python" in config.strategies:
            strategy = config.strategies["python"]
            if strategy == "poetry":
                self._run_poetry(cwd)

        if "node" in config.strategies:
            strategy = config.strategies["node"]
            if strategy == "npm":
                self._run_npm(cwd)

        # 2. Script Execution
        # Execute 'install' scripts by default, or specific lifecycle hooks if we add them later
        scripts = config.scripts.get("install", [])
        if scripts:
            self._run_scripts(scripts, cwd)

    def _run_poetry(self, cwd):
        if not Executor.check_command_exists("poetry"):
            Executor.log("Poetry not found. Please install poetry first.", "ERROR")
            return

        cmd = "poetry install"
        if self.scope == "prod":
            cmd += " --no-dev"

        Executor.log(f"Running Poetry in {cwd}")
        Executor.run_command(cmd, cwd=cwd)

    def _run_npm(self, cwd):
        if not Executor.check_command_exists("npm"):
            Executor.log("npm not found.", "ERROR")
            return

        cmd = "npm install"
        if self.scope == "prod":
            cmd = "npm ci --production"

        Executor.log(f"Running npm in {cwd}")
        Executor.run_command(cmd, cwd=cwd)

    def _run_scripts(self, scripts: List[str], cwd: str):
        for script in scripts:
            # Check for risk
            if "pip install" in script and not is_docker() and is_root():
                 Executor.log(f"Risk Warning: Running '{script}' as root on host.", "WARN")

            Executor.run_command(script, cwd=cwd)
