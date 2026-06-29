import importlib.util
import os
import sys
import subprocess

REQUIRED_PACKAGES = {
    "langgraph": "langgraph>=0.6",
    "langchain": "langchain>=0.3",
    "langchain_core": "langchain-core>=0.3",
    "langchain_groq": "langchain-groq>=0.3",
    "flask_login": "Flask-Login>=0.6",
    "flask_sqlalchemy": "Flask-SQLAlchemy>=3.0",
    "trafilatura": "trafilatura"
}

def check_dependencies():
    missing_packages = []
    
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        if importlib.util.find_spec(module_name) is None:
            missing_packages.append(pip_name)
            
    if not missing_packages:
        print("✅ All required neural dependencies are present.")
        return True
        
    print("\n==============================")
    print(" MISSING NEURAL DEPENDENCIES")
    print("==============================")
    for pkg in missing_packages:
        print(f" - {pkg}")
        
    if os.environ.get("AUTO_INSTALL_DEPS", "").lower() == "true":
        print("\nAUTO_INSTALL_DEPS=true detected. Installing missing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
        print("✅ Dependencies installed successfully.")
        return True
    else:
        print("\nTo install them automatically, run with AUTO_INSTALL_DEPS=true")
        print("Example: set AUTO_INSTALL_DEPS=true && python check_dependencies.py")
        
        response = input("Do you want to install them now? [y/N]: ")
        if response.lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("✅ Dependencies installed successfully.")
            return True
        else:
            print("❌ Setup aborted. Some features will remain offline.")
            return False

if __name__ == "__main__":
    check_dependencies()
