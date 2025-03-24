import os
import re

class ConfigManager:
    def __init__(self, config_file=None):
        self.config_file = config_file
        self.config = {}
        
        if config_file and os.path.exists(config_file):
            self.load_env_file(config_file)
    
    def load_env_file(self, env_file):
        """Load configuration from environment file"""
        if not os.path.exists(env_file):
            return {}
        
        config = {}
        
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    config[key] = value
        
        self.config = config
        return config
    
    def save_env_file(self, filename, config=None):
        """Save configuration to environment file"""
        if config is None:
            config = self.config
        
        with open(filename, 'w') as f:
            f.write("# ET Legacy Server Configuration\n\n")
            
            # Server Information
            f.write("# Server Information\n")
            f.write(f'servername="{config.get("servername", "")}"\n')
            f.write(f'port={config.get("port", "27960")}\n')
            f.write(f'sv_maxclients={config.get("sv_maxclients", "16")}\n')
            f.write(f'g_password="{config.get("g_password", "")}"\n')
            f.write(f'sv_privateclients={config.get("sv_privateclients", "0")}\n')
            f.write(f'sv_privatepassword="{config.get("sv_privatepassword", "")}"\n')
            f.write(f'rconpassword="{config.get("rconpassword", "")}"\n')
            f.write(f'refereepassword="{config.get("refereepassword", "")}"\n')
            f.write(f'ShoutcastPassword="{config.get("ShoutcastPassword", "")}"\n')
            f.write(f'sv_wwwBaseURL="{config.get("sv_wwwBaseURL", "")}"\n')
            
            # Installation Information
            f.write("\n# Installation Information\n")
            f.write(f'installDir="{config.get("installDir", "/home/etlegacy")}"\n')
            f.write(f'ftpuser="{config.get("ftpuser", "")}"\n')
            
            # Version Information
            if isinstance(config.get("version"), dict):
                f.write(f'version="{config["version"].get("version", "")}"\n')
                f.write(f'version_url="{config["version"].get("url", "")}"\n')
            
            # Additional Options
            f.write("\n# Additional Options\n")
            f.write(f'install_maps={"true" if config.get("install_maps", True) else "false"}\n')
            f.write(f'configure_firewall={"true" if config.get("configure_firewall", True) else "false"}\n')
        
        return True
    
    def export_server_config(self, server_info, filename=None):
        """Export server configuration to file"""
        if filename is None:
            filename = f"etl_server_{server_info['port']}.env"
        
        config = {
            "servername": server_info.get("name", ""),
            "port": server_info.get("port", "27960"),
            "installDir": server_info.get("installDir", ""),
            "version": server_info.get("version", "")
        }
        
        # Try to read additional config from server config file
        cfg_file = f"{server_info['dir']}/etmain/etl_server.cfg"
        if os.path.exists(cfg_file):
            with open(cfg_file, 'r') as f:
                cfg_content = f.read()
            
            # Extract values
            patterns = {
                "sv_maxclients": r'set sv_maxclients\s+"(.+?)"',
                "g_password": r'set g_password\s+"(.+?)"',
                "sv_privateclients": r'set sv_privateclients\s+"(.+?)"',
                "sv_privatepassword": r'set sv_privatepassword\s+"(.+?)"',
                "rconpassword": r'set rconpassword\s+"(.+?)"',
                "refereepassword": r'set refereePassword\s+"(.+?)"',
                "ShoutcastPassword": r'set ShoutcastPassword\s+"(.+?)"',
                "sv_wwwBaseURL": r'set sv_wwwBaseURL\s+"(.+?)"'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, cfg_content)
                if match:
                    config[key] = match.group(1)
        
        return self.save_env_file(filename, config)