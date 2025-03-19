"""
Environment variable loader for YourCinemaFilms project.
This module loads environment variables from a secure location outside the project directory.
"""

import os
import sys
import platform
from pathlib import Path

def convert_value(name, value):
    """
    Convert environment variable values to the appropriate type based on the variable name.
    """
    # Integer variables
    if name in {'UPCOMING_FILMS_MONTHS', 'MAX_CINEMA_FILMS', 'CACHE_UPDATE_INTERVAL_MINUTES', 'FILMS_PER_PAGE', 'EMAIL_PORT'}:
        return str(int(value))
    
    # Boolean variables
    if name in {'DJANGO_DEBUG', 'PRODUCTION', 'EMAIL_USE_TLS'}:
        # Convert Python boolean to string 'True' or 'False'
        return str(value).lower() == 'true'
    
    # All other variables should be strings
    return str(value)

def load_environment_variables():
    """
    Load environment variables from a secure location outside the project directory.
    Works on both Windows development and Linux Docker production environments.
    """
    # Determine the environment (Windows or Linux)
    is_windows = platform.system().lower() == 'windows'
    
    # Define paths for both environments
    if is_windows:
        # Windows development environment
        env_path = Path('C:/EnvironmentVariables/YourCinemaFilms/env.py')
    else:
        # Linux Docker production environment
        env_path = Path('/etc/yourcinemafilms/env.py')
    
    # Check if the environment file exists
    if not env_path.exists():
        print(f"Warning: Environment file not found at {env_path}")
        return False
    
    # Add the directory containing the environment file to the Python path
    sys.path.insert(0, str(env_path.parent))
    
    try:
        # Import the environment module
        env_module_name = env_path.stem
        env_module = __import__(env_module_name)
        
        # Set environment variables from the module
        for var_name in dir(env_module):
            # Skip private variables and modules
            if var_name.startswith('__') or callable(getattr(env_module, var_name)):
                continue
            
            # Get the value and convert it to the appropriate type
            value = getattr(env_module, var_name)
            os.environ[var_name] = str(convert_value(var_name, value))
        
        return True
    except ImportError as e:
        print(f"Error importing environment module: {e}")
        return False
    except Exception as e:
        print(f"Error loading environment variables: {e}")
        return False 