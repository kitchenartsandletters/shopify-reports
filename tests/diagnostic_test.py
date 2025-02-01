import sys
import os

print("Python Executable:", sys.executable)
print("Python Version:", sys.version)
print("\nPython Path:")
for path in sys.path:
    print(path)

print("\nInstalled Packages:")
try:
    import pkg_resources
    installed_packages = pkg_resources.working_set
    for package in installed_packages:
        print(f"{package.key} == {package.version}")
except ImportError:
    print("Could not list installed packages")

print("\nTrying to import Shopify:")
try:
    import shopify
    print("Shopify imported successfully")
    print("Shopify library location:", shopify.__file__)
    
    # Try to access some basic Shopify attributes
    print("\nShopify module attributes:")
    print(dir(shopify))
except Exception as e:
    print(f"Import failed with error: {e}")
    print("Full traceback:")
    import traceback
    traceback.print_exc()