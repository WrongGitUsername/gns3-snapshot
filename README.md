GNS3 Snapshot & Thumbnail Generator 🚀

A high-performance, parallelized Python tool to generate professional network topology thumbnails and snapshots directly from the GNS3 REST API.

Unlike standard exports, gns3-snapshot uses multi-threading and intelligent caching to process dozens of projects in seconds, rendering them into clean PNG/SVG images with support for custom icons, interface labels, and background colors.
✨ Key Features

    ⚡ High Performance: Built-in ThreadPoolExecutor with auto-detection of optimal worker counts for I/O-bound tasks.

    🎨 Professional Rendering: Generates crisp thumbnails using SVG logic, with support for:

        GNS3 Node Icons: Fetches symbols directly from the GNS3 server or falls back to GitHub repositories.

        Interface Labels: Clear visibility of port connections (e.g., e0/0, Gi1/1).

        Custom Styling: Adjustable node sizes, font sizes, and background colors.

    🧵 Thread-Safe Caching: Implements a shared, thread-locked icon cache to prevent redundant network requests.

    🛠️ Dual-Purpose: Use it as a Command Line Tool (CLI) or import it as a Python Library in your own automation scripts.

🚀 Quick Start
1. Prerequisites

Ensure you have Python 3.12+ installed. You will need a running GNS3 server.
2. Installation
Bash

# Clone the repository
git clone https://github.com/WrongGitUsername/gns3-snapshot.git
cd gns3-snapshot

# Install dependencies
pip install requests pillow cairosvg

3. Basic Usage (CLI)

Generate thumbnails for specific projects by providing their IDs:
Bash

python3 -m gns3_snapshot --project-ids "UUID1,UUID2" --server "http://192.168.1.10:3080"

Bash

python3 gns3_snapshot.py --project-ids 1af4f7ab-0f09-40b7-9fc9-b2208d8caab8,f5011b76-706b-4598-8238-7fdb72d1df3f,3b54fa44-949a-4ee7-b1bb-d6c007de5841,4c160cdc-9a0c-4e99-a4b6-e18c895c974f,361805d5-6616-4efa-9b6d-dbf2999edc14,09ced82b-62c9-46ba-90ce-52577c795abc --node-size 120 --font-size 20 --no-interface-labels --background white --padding 100 --use-node-icons 


Common Flags:

    --use-node-icons: Use actual GNS3 symbols instead of generic shapes.

    --workers auto: Automatically optimize performance based on your CPU.

    --output-dir ./my_shots: Specify where to save the images.

📦 Using as a Library

You can easily integrate the generator into your own Python projects:
Python

from gns3_snapshot import GNS3ThumbnailGenerator

# Initialize the generator
generator = GNS3ThumbnailGenerator(
    server_url="http://localhost:3080",
    output_dir="thumbnails",
    use_node_icons=True
)

# Generate a single thumbnail
success, path = generator.generate_thumbnail("your-project-uuid-here")

if success:
    print(f"Success! Thumbnail saved to {path}")

🛠️ Configuration Options
Argument	Description	Default
--server	GNS3 Server URL	http://localhost:3080
--width	Thumbnail Width (px)	1200
--height	Thumbnail Height (px)	800
--workers	Parallel threads (auto or int)	auto
--background	Background color	white
--no-interface-labels	Hide port labels on links	False
🧪 Testing & Coverage

The project maintains a robust test suite using pytest. We use mocking to simulate GNS3 API responses, ensuring the rendering logic is fully verified.
Bash

# Run tests with coverage report
python3 -m pytest --cov=gns3_snapshot tests/

🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

    Fork the Project

    Create your Feature Branch (git checkout -b feature/AmazingFeature)

    Commit your Changes (git commit -m 'Add some AmazingFeature')

    Push to the Branch (git push origin feature/AmazingFeature)

    Open a Pull Request

📄 License

Distributed under the MIT License. See LICENSE for more information.