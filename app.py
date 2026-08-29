import os
from coffee_spot import CreateApp

if __name__ == "__main__":
    app = CreateApp()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)


