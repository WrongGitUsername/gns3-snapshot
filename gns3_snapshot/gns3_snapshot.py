#!/usr/bin/env python3
"""
GNS3 Topology Thumbnail Generator (High Performance Version)
Fast and reliable thumbnail generation using GNS3 REST API with built-in parallel processing.
"""

import math
import base64
import json
import time
import os
import threading
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET

try:
    import requests
    from PIL import Image
    from cairosvg import svg2png
except ImportError as e:
    raise ImportError(
        f"Required library not found: {e}\n"
        "Please install: pip install requests pillow cairosvg"
    )


def _auto_detect_workers(io_bound: bool = True) -> int:
    """
    Auto-detect optimal number of workers based on system capabilities.
    
    Args:
        io_bound: If True, optimize for I/O bound tasks (default).
                  If False, optimize for CPU bound tasks.
    
    Returns:
        Recommended number of workers
    """
    cpu_count = os.cpu_count() or 4
    
    if io_bound:
        # For I/O bound tasks (network requests, file I/O), use more workers
        # Rule of thumb: 2-5x CPU count for I/O bound operations
        return min(cpu_count * 4, 50)  # Cap at 50 to avoid overwhelming the server
    else:
        # For CPU bound tasks, use CPU count
        return cpu_count


class GNS3ThumbnailGenerator:
    """
    Generate clean thumbnail images from GNS3 topology data via API.
    Optimized for high throughput by reading project files directly and sharing caches.
    """
    
    # ---------------------------------------------------------
    # SHARED PERFORMANCE CACHE (Across all threads)
    # ---------------------------------------------------------
    _shared_icon_cache: Dict[str, str] = {}
    _cache_lock = threading.Lock()

    def __init__(
        self,
        server_url: str = "http://localhost:3080",
        username: Optional[str] = None,
        password: Optional[str] = None,
        output_dir: str = "thumbnails",
        thumbnail_width: int = 1200,
        thumbnail_height: int = 800,
        padding: int = 40,
        background_color: str = "white",
        node_size: int = 60,
        font_size: int = 12,
        show_interface_labels: bool = True,
        use_node_icons: bool = False,
        verbose: bool = False
    ):
        self.server_url = server_url.rstrip('/')
        self.auth = (username, password) if username and password else None
        self.output_dir = Path(output_dir)
        self.thumbnail_width = thumbnail_width
        self.thumbnail_height = thumbnail_height
        self.padding = padding
        self.background_color = background_color
        self.node_size = node_size
        self.font_size = font_size
        self.show_interface_labels = show_interface_labels
        self.use_node_icons = use_node_icons
        self.verbose = verbose
        
        # Link instance cache to the shared class-level cache
        self._icon_cache = GNS3ThumbnailGenerator._shared_icon_cache
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Session for requests
        self.session = requests.Session()
        if self.auth:
            self.session.auth = self.auth

        self.GITHUB_FALLBACK_URLS = {
            'router': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/router.svg',
            'vpcs': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/vpcs_guest.svg',
            'vpcs_guest': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/vpcs_guest.svg',
            'cloud': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/cloud.svg',
            'nat': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/nat.svg',
            'atm_switch': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/atm_switch.svg',
            'hub': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/hub.svg',
            'ethernet_switch': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/ethernet_switch.svg',
            'asa': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/asa.svg',
            'computer': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/computer.svg',
            'docker_guest': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/docker_guest.svg',
            'firewall': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/firewall.svg',
            'frame_relay_switch': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/frame_relay_switch.svg',
            'multilayer_switch': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/multilayer_switch.svg',
            'qemu_guest': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/qemu_guest.svg',
            'vbox_guest': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/vbox_guest.svg',
            'vmware_guest': 'https://raw.githubusercontent.com/GNS3/gns3-gui/master/resources/symbols/vmware_guest.svg',
        }

    def _get_nodes(self, project_id: str) -> List[Dict]:
        """Get all nodes in the project."""
        nodes = self._api_get(f"/v2/projects/{project_id}/nodes")
        return nodes if nodes else []

    def _get_links(self, project_id: str) -> List[Dict]:
        """Get all links in the project."""
        links = self._api_get(f"/v2/projects/{project_id}/links")
        return links if links else []

    def _get_drawings(self, project_id: str) -> List[Dict]:
        """Get all drawings (notes, shapes) in the project."""
        drawings = self._api_get(f"/v2/projects/{project_id}/drawings")
        return drawings if drawings else []
    
    # ---------------------------------------------------------
    # OPTIMIZED DATA FETCHING (FAST PATH)
    # ---------------------------------------------------------
    
    def _get_topology_from_file(self, project_id: str, project_data: Dict) -> Optional[Tuple[list, list, list]]:
        """
        FAST PATH: Download and parse the .gns3 file content directly.
        Avoids opening the project simulation engine.
        """
        filename = project_data.get('filename', 'project.gns3')
        
        try:
            # GNS3 API allows reading file content
            # Endpoint: /v2/projects/{project_id}/files/{filename}
            url = f"{self.server_url}/v2/projects/{project_id}/files/{filename}"
            response = self.session.get(url, timeout=5)
            
            if response.status_code != 200:
                self._log(f"  ⚠ Could not read project file directly (Status {response.status_code})")
                return None
                
            data = response.json()
            
            # Structure varies by GNS3 version
            # V2.2+: Root keys 'topology' or directly 'nodes'
            if 'topology' in data:
                topo = data['topology']
                return (
                    topo.get('nodes', []),
                    topo.get('links', []),
                    topo.get('drawings', [])
                )
            elif 'nodes' in data:
                return (
                    data.get('nodes', []),
                    data.get('links', []),
                    data.get('drawings', [])
                )
            else:
                return None
                
        except Exception as e:
            self._log(f"  ⚠ Direct file read failed: {e}")
            return None

    # ---------------------------------------------------------
    # ICON & SVG HANDLING
    # ---------------------------------------------------------

    def _make_data_uri(self, content: bytes, filename: str) -> str:
        mime_type = "image/svg+xml" if filename.lower().endswith('.svg') else "image/png"
        b64 = base64.b64encode(content).decode('ascii')
        return f"data:{mime_type};base64,{b64}"

    def _svg_icon_to_png(self, svg_bytes: bytes, size: int) -> bytes:
        return svg2png(bytestring=svg_bytes, output_width=size, output_height=size)

    def _svg_to_icon_data_uri(self, svg_bytes: bytes, name: str) -> str:
        png_bytes = self._svg_icon_to_png(svg_bytes, int(self.node_size * 1.2))
        return self._make_data_uri(png_bytes, f"{name}.png")

    def _get_github_fallback_url(self, filename_base: str) -> Optional[str]:
        return self.GITHUB_FALLBACK_URLS.get(filename_base)

    def _get_node_icon(self, symbol: str) -> Optional[str]:
        MIN_VALID_SVG_SIZE = 100
        
        if not symbol or not symbol.strip():
            return None
        
        # 1. Thread-Safe Cache Check
        with self._cache_lock:
            if symbol in self._icon_cache and self._icon_cache[symbol]:
                return self._icon_cache[symbol]
        
        # Extract filename without extension
        filename_base = Path(symbol.split('/')[-1]).stem.lower()
        self._log(f"Fetching icon: {symbol} (base: {filename_base})")
        
        # Setup local directory
        script_dir = Path(__file__).parent
        local_symbols_dir = script_dir / "gns3_node_symbols"
        local_symbols_dir.mkdir(parents=True, exist_ok=True)
        
        local_svg_path = local_symbols_dir / f"{filename_base}.svg"
        
        # Helper to cache and return
        def cache_and_return(data_uri_val):
            with self._cache_lock:
                self._icon_cache[symbol] = data_uri_val
            return data_uri_val

        # 2. Check local disk
        if local_svg_path.exists():
            try:
                svg_content = local_svg_path.read_bytes()
                if len(svg_content) > MIN_VALID_SVG_SIZE:
                    data_uri = self._svg_to_icon_data_uri(svg_content, filename_base)
                    return cache_and_return(data_uri)
            except Exception as e:
                self._log(f" Warning: Failed to read local {filename_base}.svg: {e}")

        # 3. GNS3 API
        try:
            url = f"{self.server_url}/v2/symbols/{symbol}/raw"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200 and len(response.content) > MIN_VALID_SVG_SIZE:
                try:
                    local_svg_path.write_bytes(response.content)
                except: pass
                
                data_uri = self._svg_to_icon_data_uri(response.content, filename_base)
                return cache_and_return(data_uri)
        except Exception:
            pass
        
        # 4. GitHub Fallback
        github_url = self._get_github_fallback_url(filename_base)
        if github_url:
            try:
                response = self.session.get(github_url, timeout=15)
                if response.status_code == 200 and len(response.content) > MIN_VALID_SVG_SIZE:
                    try:
                        local_svg_path.write_bytes(response.content)
                    except: pass
                    
                    data_uri = self._svg_to_icon_data_uri(response.content, filename_base)
                    return cache_and_return(data_uri)
            except Exception:
                pass
        
        # Cache failure to avoid retries
        with self._cache_lock:
            self._icon_cache[symbol] = None
        return None

    # ---------------------------------------------------------
    # API & HELPERS
    # ---------------------------------------------------------

    def _log(self, message: str, end: str = '\n') -> None:
        if self.verbose:
            print(message, end=end)
    
    def _api_get(self, endpoint: str) -> Optional[Dict]:
        try:
            url = f"{self.server_url}{endpoint}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self._log(f"  ✗ API GET failed {endpoint}: {e}")
            return None
    
    def _api_post(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        try:
            url = f"{self.server_url}{endpoint}"
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            if response.status_code == 204: return {}
            return response.json()
        except Exception as e:
            self._log(f"  ✗ API POST failed {endpoint}: {e}")
            return None

    def _ensure_project_open(self, project_id: str) -> Tuple[bool, bool]:
        """Slow path: ensure project is running to query API."""
        try:
            project_data = self._api_get(f"/v2/projects/{project_id}")
            if not project_data: return False, False
            
            if project_data.get('status') == 'opened':
                return True, False
            
            self._log(f"  → Opening project (Slow Path)...")
            result = self._api_post(f"/v2/projects/{project_id}/open")
            return (result is not None), True
        except Exception:
            return False, False
    
    # ---------------------------------------------------------
    # RENDERING
    # ---------------------------------------------------------

    def _calculate_bounds(self, nodes: List[Dict], drawings: List[Dict]) -> Dict:
        if not nodes and not drawings:
            return {'min_x': 0, 'min_y': 0, 'max_x': 800, 'max_y': 600, 'width': 800, 'height': 600}
        
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for node in nodes:
            x, y = node.get('x', 0), node.get('y', 0)
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x + self.node_size), max(max_y, y + self.node_size)
        
        for drawing in drawings:
            x, y = drawing.get('x', 0), drawing.get('y', 0)
            svg_data = drawing.get('svg', '')
            
            # Try to extract width/height from SVG
            width = height = 100  # default
            if svg_data:
                try:
                    root = ET.fromstring(svg_data)
                    width = int(root.get('width', 100))
                    height = int(root.get('height', 100))
                except:
                    pass
            
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x + width), max(max_y, y + height)
        
        return {
            'min_x': min_x - self.padding, 'min_y': min_y - self.padding,
            'max_x': max_x + self.padding, 'max_y': max_y + self.padding,
            'width': (max_x - min_x) + 2 * self.padding, 'height': (max_y - min_y) + 2 * self.padding
        }
    
    def _get_node_color(self, node: Dict) -> str:
        node_type = node.get('node_type', '').lower()
        symbol = node.get('symbol', '').lower()
        colors = {
            'router': '#4A90E2', 'switch': '#7ED321', 'vpcs': '#F5A623', 
            'cloud': '#50E3C2', 'nat': '#BD10E0', 'ethernet_switch': '#7ED321',
            'ethernet_hub': '#B8E986', 'frame_relay_switch': '#4A90E2', 
            'atm_switch': '#4A90E2'
        }

        for key, color in colors.items():
            if key in node_type or key in symbol: return color
        return '#9B9B9B'

    def _create_empty_svg(self) -> str:
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="100%" height="100%" fill="{self.background_color}"/><text x="400" y="300" font-family="Arial" font-size="24" fill="#CCCCCC" text-anchor="middle">Empty Project</text></svg>'

    def _create_svg(self, nodes: List[Dict], links: List[Dict], drawings: List[Dict]) -> str:
        if not nodes and not links and not drawings:
            return self._create_empty_svg()

        bounds = self._calculate_bounds(nodes, drawings)
        width, height = bounds['width'], bounds['height']
        offset_x, offset_y = -bounds['min_x'], -bounds['min_y']
        
        svg_parts = [
            f'<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f'<rect width="100%" height="100%" fill="{self.background_color}"/>'
        ]
        
        # Links
        for link in links:
            nodes_data = link.get('nodes', [])
            if len(nodes_data) >= 2:
                # Naive link drawing
                n1 = next((n for n in nodes if n['node_id'] == nodes_data[0]['node_id']), None)
                n2 = next((n for n in nodes if n['node_id'] == nodes_data[1]['node_id']), None)
                if n1 and n2:
                    x1 = n1.get('x', 0) + offset_x + self.node_size/2
                    y1 = n1.get('y', 0) + offset_y + self.node_size/2
                    x2 = n2.get('x', 0) + offset_x + self.node_size/2
                    y2 = n2.get('y', 0) + offset_y + self.node_size/2
                    svg_parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#333" stroke-width="2" opacity="0.6"/>')
                    
                    # Labels (Simplified for conciseness)
                    if self.show_interface_labels:
                        dx, dy = x2 - x1, y2 - y1
                        length = math.sqrt(dx*dx + dy*dy)
                        if length > 0:
                            ux, uy = dx/length, dy/length
                            label_off = self.node_size/2 + 20
                            for i, nd in enumerate(nodes_data):
                                txt = nd.get('label', {}).get('text', '')
                                if txt:
                                    lx = (x1 if i==0 else x2) + (ux if i==0 else -ux) * label_off
                                    ly = (y1 if i==0 else y2) + (uy if i==0 else -uy) * label_off
                                    anchor = ("start" if ux >= 0 else "end") if i==0 else ("end" if ux >= 0 else "start")
                                    svg_parts.append(f'<text x="{lx}" y="{ly}" font-family="Arial" font-size="{self.font_size-2}" fill="#666" text-anchor="{anchor}" stroke="white" stroke-width="3" paint-order="stroke">{txt}</text>')
                                    svg_parts.append(f'<text x="{lx}" y="{ly}" font-family="Arial" font-size="{self.font_size-2}" fill="#666" text-anchor="{anchor}">{txt}</text>')

        # Drawings
        for d in drawings:
            x = d.get('x', 0) + offset_x
            y = d.get('y', 0) + offset_y
            svg = d.get('svg', '')
            if svg:
                svg_parts.append(f'<g transform="translate({x},{y})">{svg}</g>')

        # Nodes
        for node in nodes:
            x = node.get('x', 0) + offset_x
            y = node.get('y', 0) + offset_y
            name = node.get('name', 'Node')
            symbol = node.get('symbol', '')
            
            icon_data = None
            if self.use_node_icons and symbol:
                icon_data = self._get_node_icon(symbol)
            
            if icon_data:
                sz = self.node_size
                # Center the icon
                svg_parts.append(f'<g transform="translate({x+sz/2}, {y+sz/2})">')
                svg_parts.append(f'<image x="-{sz*0.4}" y="-{sz*0.4}" width="{sz*0.8}" height="{sz*0.8}" href="{icon_data}"/>')
                svg_parts.append(f'</g>')
            else:
                color = self._get_node_color(node)
                svg_parts.append(f'<rect x="{x}" y="{y}" width="{self.node_size}" height="{self.node_size}" fill="{color}" stroke="#333" stroke-width="2" rx="5"/>')
            
            # Label
            svg_parts.append(f'<text x="{x+self.node_size/2}" y="{y+self.node_size+15}" font-family="Arial" font-size="{self.font_size}" fill="#333" text-anchor="middle" font-weight="bold">{name}</text>')

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)
    
    def _svg_to_png(self, svg_content: str, output_path: str) -> bool:
        try:
            from io import BytesIO
            png_data = svg2png(bytestring=svg_content.encode('utf-8'))
            img = Image.open(BytesIO(png_data))
            img.thumbnail((self.thumbnail_width, self.thumbnail_height), Image.LANCZOS)
            
            final_img = Image.new('RGB', (self.thumbnail_width, self.thumbnail_height), self.background_color)
            x = (self.thumbnail_width - img.width) // 2
            y = (self.thumbnail_height - img.height) // 2
            final_img.paste(img, (x, y))
            final_img.save(output_path, 'PNG', optimize=True)
            return True
        except Exception as e:
            self._log(f"  ✗ PNG conversion failed: {e}")
            return False

    def generate_thumbnail(self, project_id: str, save_svg: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Generate a thumbnail for a single project (Optimized).
        """
        self._log(f"Processing: {project_id}")
        was_opened = False
        
        try:
            # 1. Get Project Info
            project_data = self._api_get(f"/v2/projects/{project_id}")
            if not project_data: return False, None

            # 2. FAST PATH: Read File directly. Faster than opening the project
            topo_data = self._get_topology_from_file(project_id, project_data)
            
            if topo_data:
                nodes, links, drawings = topo_data
                self._log("  ✓ Loaded via Fast Path (File Read)")
            else:
                # 3. SLOW PATH: Open Project
                self._log("  ⚠ Fast Path failed, trying Slow Path (Open Project)...")
                is_open, was_opened = self._ensure_project_open(project_id)
                if not is_open: return False, None
                
                nodes = self._get_nodes(project_id)
                links = self._get_links(project_id)
                drawings = self._get_drawings(project_id)

            # 4. Generate Image
            svg_content = self._create_svg(nodes, links, drawings)
            
            if save_svg:
                (self.output_dir / f"{project_id}.svg").write_text(svg_content)
                
            out_path = self.output_dir / f"{project_id}.png"
            if self._svg_to_png(svg_content, str(out_path)):
                return True, str(out_path)
            
            return False, None

        except Exception as e:
            self._log(f"Error: {e}")
            if self.verbose:
                import traceback; traceback.print_exc()
            return False, None
            
        finally:
            # Only close if we opened it (Slow Path)
            if was_opened:
                try:
                    self._api_post(f"/v2/projects/{project_id}/close")
                except: pass

    def generate_thumbnails(self, project_ids: List[str], max_workers: Union[int, str] = "auto", show_progress: bool = True) -> Dict:
        """
        Generate thumbnails for multiple projects in parallel.
        
        Args:
            project_ids: List of GNS3 project UUIDs
            max_workers: Number of parallel workers. Use "auto" for auto-detection,
                        or specify an integer (default: "auto")
            show_progress: Show progress information (default: True)
            
        Returns:
            Dictionary with 'success', 'failed' lists and 'paths' dictionary
        """
        # Handle auto worker detection
        if isinstance(max_workers, str) and max_workers.lower() == "auto":
            max_workers = _auto_detect_workers(io_bound=True)
            if show_progress:
                print(f"🔧 Auto-detected {max_workers} workers (based on {os.cpu_count()} CPUs)")
        elif not isinstance(max_workers, int):
            raise ValueError(f"max_workers must be 'auto' or an integer, got: {max_workers}")
        
        if show_progress:
            print(f"Starting thumbnail generation")
            print(f"Projects: {len(project_ids)}")
            print(f"Workers: {max_workers}")
        
        start_time = time.time()
        results = {'success': [], 'failed': [], 'paths': {}}
        
        # Create a config dict for thread workers
        config = {
            'server_url': self.server_url,
            'username': self.auth[0] if self.auth else None,
            'password': self.auth[1] if self.auth else None,
            'output_dir': str(self.output_dir),
            'thumbnail_width': self.thumbnail_width,
            'thumbnail_height': self.thumbnail_height,
            'padding': self.padding,
            'background_color': self.background_color,
            'node_size': self.node_size,
            'font_size': self.font_size,
            'show_interface_labels': self.show_interface_labels,
            'use_node_icons': self.use_node_icons,
            'verbose': False  # Disable verbose in parallel mode
        }
        
        def process_single(pid: str) -> dict:
            """Process a single project in a thread."""
            gen = GNS3ThumbnailGenerator(**config)
            success, path = gen.generate_thumbnail(pid)
            return {'project_id': pid, 'success': success, 'path': path}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single, pid): pid for pid in project_ids}
            
            for i, future in enumerate(as_completed(futures), 1):
                pid = futures[future]
                try:
                    res = future.result()
                    if res['success']:
                        results['success'].append(pid)
                        results['paths'][pid] = res['path']
                    else:
                        results['failed'].append(pid)
                    
                    if show_progress and i % 5 == 0:
                        print(f"  ✓ {i}/{len(project_ids)} completed...", end='\r')
                        
                except Exception as e:
                    results['failed'].append(pid)
                    if self.verbose:
                        print(f"\nError processing {pid}: {e}")
        
        elapsed = time.time() - start_time
        
        if show_progress:
            print(f"\n{'='*60}")
            print(f"Total Time: {elapsed:.2f}s")
            print(f"Throughput: {len(project_ids)/elapsed:.2f} projects/sec")
            print(f"Success: {len(results['success'])}")
            print(f"Failed: {len(results['failed'])}")
            print(f"{'='*60}")
        
        return results


# Convenience function for direct usage
def generate_thumbnails(
    project_ids: List[str],
    server_url: str = "http://localhost:3080",
    username: Optional[str] = None,
    password: Optional[str] = None,
    output_dir: str = "thumbnails",
    thumbnail_width: int = 1200,
    thumbnail_height: int = 800,
    max_workers: Union[int, str] = "auto",
    show_progress: bool = True,
    **kwargs
) -> Dict:
    """
    Convenience function to generate thumbnails with simple parameters.
    Uses parallel processing by default for optimal performance.
    
    Args:
        project_ids: List of GNS3 project UUIDs
        server_url: GNS3 server URL (default: http://localhost:3080)
        username: Optional username for authentication
        password: Optional password for authentication
        output_dir: Directory to save thumbnails (default: thumbnails)
        thumbnail_width: Maximum width in pixels (default: 1200)
        thumbnail_height: Maximum height in pixels (default: 800)
        max_workers: Number of parallel workers. Use "auto" for auto-detection
                     or specify an integer (default: "auto")
        show_progress: Show progress information (default: True)
        **kwargs: Additional arguments passed to GNS3ThumbnailGenerator
        
    Returns:
        Dictionary with 'success', 'failed' lists and 'paths' dictionary
        
    Example:
        from gns3_topology_snapshot import generate_thumbnails
        
        # Auto-detect workers
        results = generate_thumbnails(
            project_ids=['abc-123', 'def-456'],
            server_url='http://localhost:3080',
            output_dir='./my_thumbnails'
        )
        
        # Specify worker count
        results = generate_thumbnails(
            project_ids=['abc-123', 'def-456'],
            max_workers=10
        )
        
        print(f"Generated {len(results['success'])} thumbnails")
        for project_id, path in results['paths'].items():
            print(f"  {project_id}: {path}")
    """
    generator = GNS3ThumbnailGenerator(
        server_url=server_url,
        username=username,
        password=password,
        output_dir=output_dir,
        thumbnail_width=thumbnail_width,
        thumbnail_height=thumbnail_height,
        **kwargs
    )
    
    return generator.generate_thumbnails(project_ids, max_workers=max_workers, show_progress=show_progress)


# CLI interface (when run as script)
def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Generate clean thumbnail images from GNS3 topologies using the API (with parallel processing)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single project
  %(prog)s --project-ids abc-123-def
  
  # Multiple projects with authentication
  %(prog)s --server http://192.168.1.100:3080 \\
           --username admin --password secret \\
           --project-ids abc-123,def-456,ghi-789
  
  # Custom output, size, and parallel workers
  %(prog)s --project-ids abc-123 \\
           --output-dir ./topology-images \\
           --width 1920 --height 1080 \\
           --workers 30
        """
    )
    
    parser.add_argument('--server', default='http://localhost:3080',
                        help='GNS3 server URL (default: http://localhost:3080)')

    parser.add_argument('--username', help='GNS3 username (optional)')
    parser.add_argument('--password', help='GNS3 password (optional)')

    parser.add_argument('--project-ids', required=True,
                        help='Comma-separated list of GNS3 project UUIDs')

    parser.add_argument('--output-dir', default='thumbnails',
                        help='Output directory for thumbnails (default: thumbnails)')

    parser.add_argument('--width', type=int, default=1200,
                        help='Maximum thumbnail width in pixels (default: 1200)')

    parser.add_argument('--height', type=int, default=800,
                        help='Maximum thumbnail height in pixels (default: 800)')

    parser.add_argument('--padding', type=int, default=40,
                        help='Padding around topology in pixels (default: 40)')

    parser.add_argument('--node-size', type=int, default=60,
                        help='Size of node icons in pixels (default: 60)')

    parser.add_argument('--font-size', type=int, default=12,
                        help='Font size for labels (default: 12)')

    parser.add_argument('--no-interface-labels', action='store_true',
                        help='Hide interface labels on links')

    parser.add_argument('--background', default='white',
                        help='Background color (default: white)')

    parser.add_argument('--workers', type=str, default='auto',
                        help='Number of parallel workers, or "auto" for auto-detection (default: auto)')

    parser.add_argument('--quiet', action='store_true',
                        help='Suppress progress messages')

    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    
    parser.add_argument('--use-node-icons', action='store_true',
                        help='Use GNS3 node icons instead of colored shapes')

    args = parser.parse_args()
    
    # Parse project IDs
    project_ids = [pid.strip() for pid in args.project_ids.split(',') if pid.strip()]
    
    if not project_ids:
        print("Error: No valid project IDs provided")
        return 1
    
    # Parse workers argument
    try:
        if args.workers.lower() == 'auto':
            workers = 'auto'
        else:
            workers = int(args.workers)
    except (ValueError, AttributeError):
        print(f"Error: --workers must be 'auto' or an integer, got: {args.workers}")
        return 1
    
    # Generate thumbnails using convenience function
    results = generate_thumbnails(
        project_ids=project_ids,
        server_url=args.server,
        username=args.username,
        password=args.password,
        output_dir=args.output_dir,
        thumbnail_width=args.width,
        thumbnail_height=args.height,
        padding=args.padding,
        node_size=args.node_size,
        font_size=args.font_size,
        show_interface_labels=not args.no_interface_labels,
        use_node_icons=args.use_node_icons,
        background_color=args.background,
        max_workers=workers,
        show_progress=not args.quiet,
        verbose=args.verbose
    )
    
    # Exit with error code if any failed
    return 0 if not results['failed'] else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())