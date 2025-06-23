#!/usr/bin/env python3
"""
ROS Local Workspace Auto-Build Script

This script automates the installation and build process for a local ROS workspace.
It sources prepare.sh to get the proper environment setup before running any commands.
Custom packages are now managed via git submodules.

Usage:
    ./auto_build.py                 # Build in current directory
    ./auto_build.py -w /path/to/ws  # Build in specific workspace
"""

import sys
try:
    import yaml
except ImportError:
    print("Error: PyYAML is not installed. Please install it using 'pip install pyyaml'.")
    sys.exit(1)

import subprocess
import argparse
import shutil
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ROSWorkspaceManager:
    def __init__(self, workspace_dir=None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path.cwd()
        self.packages_file = self.workspace_dir / "ros-config.yml"
        self.src_dir = self.workspace_dir / "src"
        self.prepare_script = self.workspace_dir / "prepare.sh"
    
    def check_environment(self):
        """Check if prepare.sh exists and is executable"""
        if not self.prepare_script.exists():
            logger.error("prepare.sh not found! This script is required for environment setup.")
            return False
        
        if not self.prepare_script.stat().st_mode & 0o111:
            logger.info("Making prepare.sh executable...")
            self.prepare_script.chmod(0o755)
        
        # Check for .env file
        env_file = self.workspace_dir / ".env"
        if not env_file.exists():
            logger.warning(".env file not found!")
            logger.info("Please copy .templates/example.env to .env and configure it.")
            logger.info("Using default environment from prepare.sh...")
        else:
            logger.info("Found .env file for environment configuration")
        
        return True
    
    def read_packages_config(self):
        """Read and validate ros-config.yml"""
        if not self.packages_file.exists():
            logger.error(f"Error: {self.packages_file} not found!")
            sys.exit(1)
        try:
            with open(self.packages_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Handle official packages (apt packages)
            official_packages = config.get("official-packages", [])
            
            logger.info(f"Loaded {len(official_packages)} official packages from config")
            return official_packages
        except yaml.YAMLError as e:
            logger.error(f"Error parsing {self.packages_file}: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            sys.exit(1)
    
    def build_ws(self):
        """Build the ROS workspace using colcon"""
        logger.info("Installing workspace dependencies...")
        try:
            # Source environment and update rosdep
            subprocess.run(
                ["bash", "-c", "source prepare.sh && rosdep update"],
                check=True, cwd=self.workspace_dir
            )
            
            # Source environment and install dependencies
            subprocess.run(
                ["bash", "-c", "source prepare.sh && rosdep install --from-paths src --ignore-src -r -y"],
                check=True, cwd=self.workspace_dir
            )
            logger.info("Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to install some dependencies: {e}")
        
        logger.info("Building ROS workspace...")
        try:
            # Source environment and build
            subprocess.run(
                ["bash", "-c", "source prepare.sh && colcon build --symlink-install"],
                check=True, cwd=self.workspace_dir
            )
            logger.info("Workspace built successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build workspace: {e}")
            return False
    
    def install_official_packages(self, official_packages):
        """Install official ROS packages using apt locally"""
        if not official_packages:
            logger.info("No official packages to install")
            return True

        logger.info(f"Installing {len(official_packages)} official packages...")
        try:
            # Update package list first
            subprocess.run(["sudo", "apt", "update"], check=True)
            
            # Install packages
            cmd = ["sudo", "apt", "install", "-y"] + official_packages
            subprocess.run(cmd, check=True)
            logger.info("Official packages installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install official packages: {e}")
            return False
    
    def setup_workspace(self):
        """Setup/update the ROS workspace"""
        logger.info("Setting up ROS workspace...")
        
        # Check environment setup
        if not self.check_environment():
            logger.error("Environment check failed!")
            return False
        
        # Read packages configuration
        official_packages = self.read_packages_config()
        
        # Install official packages via apt
        self.install_official_packages(official_packages)

        # Build workspace (custom packages managed via git submodules)
        self.build_ws()

        logger.info("Workspace setup completed successfully!")
        logger.info("Custom packages are managed via git submodules")
        logger.info("To use the workspace, run: source prepare.sh")

def main():
    parser = argparse.ArgumentParser(description="ROS Workspace Manager")
    parser.add_argument("--workspace", "-w", help="Workspace directory (default: current directory)")
    
    args = parser.parse_args()
    
    try:
        manager = ROSWorkspaceManager(args.workspace)
        manager.setup_workspace()
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()