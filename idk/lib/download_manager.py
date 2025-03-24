import os
import re
import requests
from bs4 import BeautifulSoup
from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn

class DownloadManager:
    def __init__(self, console):
        self.console = console
        self.workflow_files_url = "https://etlegacy.com/workflow-files"
        self.download_base_url = "https://etlegacy.com/download"
        self.temp_dir = "/tmp/etlegacy-installer"
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def get_available_versions(self):
        """Get list of available ET Legacy versions"""
        versions = []
        
        # Get stable version
        try:
            stable_version = self._get_stable_version()
            if stable_version:
                versions.append(stable_version)
        except Exception as e:
            self.console.print(f"[warning]Warning: Could not fetch stable version: {e}[/warning]")
        
        # Get development versions
        try:
            dev_versions = self._get_dev_versions()
            versions.extend(dev_versions)
        except Exception as e:
            self.console.print(f"[warning]Warning: Could not fetch development versions: {e}[/warning]")
        
        return versions
    
    def _get_stable_version(self):
        """Get stable version from download page"""
        try:
            response = requests.get(f"{self.download_base_url}")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for the stable version link (this will need adjustment based on the actual page structure)
            download_links = soup.find_all("a", href=re.compile(r"/download/file/\d+"))
            
            for link in download_links:
                if "linux" in link.text.lower() and "64" in link.text.lower() and ".sh" in link.text.lower():
                    url = f"{self.download_base_url}{link['href']}"
                    version = re.search(r"v(\d+\.\d+\.\d+)", link.text)
                    version_str = version.group(1) if version else "Unknown"
                    return {
                        "name": f"Stable {version_str}",
                        "url": url,
                        "version": version_str,
                        "is_stable": True
                    }
            
            return None
        except Exception as e:
            raise Exception(f"Error fetching stable version: {e}")
    
    def _get_dev_versions(self):
        """Get development versions from workflow files page"""
        try:
            response = requests.get(self.workflow_files_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            versions = []
            # Look for Linux x86_64 .sh files
            # This pattern may need adjustment based on actual page structure
            download_links = soup.find_all("a", href=re.compile(r"/workflow-files/dl/.*?/lnxx8664/.*?\.sh"))
            
            for link in download_links:
                url = f"https://etlegacy.com{link['href']}"
                version_match = re.search(r"etlegacy-v(\d+\.\d+\.\d+(?:-\d+-g[a-f0-9]+)?)", link.text)
                if version_match:
                    version_str = version_match.group(1)
                    versions.append({
                        "name": f"Development {version_str}",
                        "url": url,
                        "version": version_str,
                        "is_stable": False
                    })
            
            return versions
        except Exception as e:
            raise Exception(f"Error fetching development versions: {e}")
    
    def download_version(self, version_info):
        """Download the specified version"""
        filename = os.path.join(self.temp_dir, f"etlegacy-{version_info['version']}.sh")
        
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            DownloadColumn(),
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(f"Downloading {version_info['name']}", total=1000)
            
            with requests.get(version_info['url'], stream=True) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                
                if total_size:
                    progress.update(task, total=total_size)
                
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
        
        # Make the file executable
        os.chmod(filename, 0o755)
        return filename