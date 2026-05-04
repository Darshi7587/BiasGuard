import sys
sys.path.insert(0, r'C:\Users\darsh\Downloads\BiasGuard\BiasGuard-Platform\backend')
from app.main import app

print("Registered routes:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        print(f"  {list(route.methods)} {route.path}")
    elif hasattr(route, 'path'):
        print(f"  {route.path}")
