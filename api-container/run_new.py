from app import create_app
import os
import sys

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = create_app('development')

if __name__ == "__main__":
    print("Starting Together API server...")
    print("Environment: Development")
    print("MongoDB URI:", os.environ.get("MONGO_URI", "mongodb://localhost:27017/together"))

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )