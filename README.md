# gns3-snapshot

High-performance, parallelized Python tool to generate professional network topology thumbnails and snapshots directly from a GNS3 server. Designed for automation at scale — it renders crisp PNG images using SVG logic, supports fetching official GNS3 node icons (with fallbacks), and exposes both a CLI and a simple Python API.

- Status: Production-ready
- Language: Python 3.12+
- License: MIT

---

## Key features

- Fast, parallel processing with ThreadPoolExecutor and auto-tuned worker counts for I/O-bound workloads.
- Professional rendering using SVG logic → clean, high-DPI PNG thumbnails.
- Node icons: fetches symbols from the GNS3 server or falls back to configured GitHub/icon sources.
- Interface/port labels (e.g., `e0/0`, `Gi1/1`) for improved readability.
- Thread-safe icon cache to avoid redundant network requests.
- Usable as a CLI tool or importable library for automation pipelines.

---

## Requirements

- Python 3.12 or newer
- A running GNS3 server reachable from the machine running this tool
- Python packages:
  - requests
  - pillow
  - cairosvg

---

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/WrongGitUsername/gns3-snapshot.git
cd gns3-snapshot
pip install -r requirements.txt
# or
pip install requests pillow cairosvg
```

(If you prefer, install into a virtual environment.)

---

## Quick start (CLI)

Generate thumbnails for one or more projects by project ID(s):

Single project:
```bash
python3 -m gns3_snapshot --project-ids "1af4f7ab-0f09-40b7-9fc9-b2208d8caab8" --server "http://192.168.1.10:3080"
```

Multiple projects:
```bash
python3 -m gns3_snapshot --project-ids "UUID1,UUID2,UUID3" --server "http://localhost:3080" --output-dir ./my_shots
```

Common flags:
- `--server` : GNS3 Server URL (default: `http://localhost:3080`)
- `--project-ids` : Comma-separated list of project UUIDs (required)
- `--output-dir` : Directory to save images (default: `./thumbnails`)
- `--width` : Thumbnail width in pixels (default: `1200`)
- `--height` : Thumbnail height in pixels (default: `800`)
- `--workers` : Number of parallel worker threads, or `auto` to detect (default: `auto`)
- `--use-node-icons` : Use actual GNS3 symbols instead of generic shapes (flag)
- `--background` : Background color (CSS color string, default: `white`)
- `--no-interface-labels` : Hide port/interface labels on links (flag)
- `--verbose` : Enable verbose logging

Example with auto workers and node icons:
```bash
python3 -m gns3_snapshot \
  --project-ids "proj-uuid-1,proj-uuid-2" \
  --server "http://192.168.1.10:3080" \
  --workers auto \
  --use-node-icons \
  --output-dir ./shots
```

---

## Usage as a library

Import and use the generator in your own scripts or automation pipelines.

Example:
```python
from gns3_snapshot import GNS3ThumbnailGenerator

generator = GNS3ThumbnailGenerator(
    server_url="http://localhost:3080",
    output_dir="thumbnails",
    use_node_icons=True,
    width=1200,
    height=800,
)

success, path = generator.generate_thumbnail("your-project-uuid-here")
if success:
    print(f"Success! Thumbnail saved to {path}")
else:
    print("Failed to generate thumbnail for project.")
```

API highlights:
- `GNS3ThumbnailGenerator(server_url, output_dir, use_node_icons=True, width=1200, height=800, workers='auto', background='white', no_interface_labels=False)` — constructor with sensible defaults.
- `generate_thumbnail(project_id)` — generates a single thumbnail, returns `(success: bool, path: str|None)`.
- There are batch helpers to generate thumbnails for a list of projects with parallelization and progress reporting.

---

## Configuration options (defaults)

| Option | Description | Default |
|---|---:|---|
| server | GNS3 Server URL | `http://localhost:3080` |
| username | GNS3 Username | `(optional)` |
| password | GNS3 Password | `(optional)` |
| project-ids | Comma-separated list of GNS3 project UUIDs | `(mandatory)` |
| output_dir | Directory to save thumbnails | `thumbnails` |
| width | Thumbnail width (px) | `1200` |
| height | Thumbnail height (px) | `800` |
| padding | Padding around topology in pixels | `40` |
| node-size | Size of node icons (px) | `60` |
| font-size | Font size for labels | `12` |
| no_interface_labels | Hide port labels | `False` |
| background | Background color | `white` |
| workers | Number of parallel workers, or "auto" for auto-detection | `auto` |
| quiet | Suppress progress messages | `False` |
| verbose | Enable verbose output | `True` |
| use_node_icons | Use GNS3 node icons instead of colored shapes | `True` |

---

## Implementation notes

- Icon caching is thread-safe: the cache is shared and protected by locks to avoid redundant network requests when multiple threads request the same asset.
- When node icons aren't available from the GNS3 server, the tool falls back to pre-configured sources (e.g., a GitHub repository mirror or bundled icons).
- Rendering uses SVG-to-PNG conversion (via cairosvg) to ensure vector-based crisp output regardless of target size.

---

## Testing & CI

The project includes a test suite using pytest and uses mocking to simulate GNS3 API responses so rendering logic can be validated offline.

Run tests with coverage:
```bash
python3 -m pytest --cov=gns3_snapshot tests/
```

CI recommendations:
- Run tests in a matrix for supported Python versions.
- Cache pip dependencies and test artifacts where appropriate.
- Optionally run a small integration job against a disposable GNS3 server for end-to-end verification.

---

## Troubleshooting

- Timeout / connection errors: confirm the `--server` URL and that the GNS3 server is reachable from the runner/machine.
- Missing icons: enable `--use-node-icons` only if the server exposes symbols; otherwise the fallback will be used.
- Slow runs: set `--workers` to a reasonable number for your environment (start at #cores * 2 for I/O-heavy tasks, or use `auto`).

---

## Contributing

Contributions are welcome — please follow these steps:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/YourFeature`
3. Make changes and add tests where applicable.
4. Commit: `git commit -m "Add some feature"`
5. Push: `git push origin feature/YourFeature`
6. Open a Pull Request describing the change and motivation.

Please keep changes small and focused. Include unit tests for new behavior and update documentation where needed.

---

## Roadmap / Ideas

- Optional higher-DPI output and retina-ready export flags.
- Plugin system for custom rendering or icon sources.
- Native thumbnail caching and incremental updates for frequently changing projects.

If you'd like to see a specific feature prioritized, open an issue or a discussion in the repo.

---

## License

Distributed under the MIT License. See LICENSE for details.

---

## Contact

If you find bugs or have questions, please open an issue on the repository: https://github.com/WrongGitUsername/gns3-snapshot