"""
Partial Tests for GNS3ThumbnailGenerator.

"""

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import from the package as per your __init__.py fix
from gns3_snapshot import GNS3ThumbnailGenerator, generate_thumbnails, main


@pytest.fixture
def generator(tmp_path):
    """Create a generator instance with temp output dir."""
    return GNS3ThumbnailGenerator(
        server_url="http://test:3080",
        output_dir=str(tmp_path),
        verbose=False
    )


@pytest.fixture
def sample_topology():
    """Sample topology data."""
    return {
        'nodes': [
            {'node_id': 'n1', 'name': 'R1', 'x': 100, 'y': 100, 'node_type': 'router', 'symbol': 'router.svg'},
            {'node_id': 'n2', 'name': 'S1', 'x': 300, 'y': 100, 'node_type': 'switch', 'symbol': 'switch.svg'}
        ],
        'links': [
            {'nodes': [{'node_id': 'n1', 'label': {'text': 'e0'}}, {'node_id': 'n2', 'label': {'text': 'e1'}}]}
        ],
        'drawings': []
    }


class TestGNS3ThumbnailGenerator:
    """Test GNS3ThumbnailGenerator class logic."""
    
    def test_initialization(self, tmp_path):
        gen = GNS3ThumbnailGenerator(output_dir=str(tmp_path))
        assert gen.output_dir.exists()

    def test_calculate_bounds(self, generator, sample_topology):
        bounds = generator._calculate_bounds(sample_topology['nodes'], [])
        assert bounds['width'] > 0
        assert bounds['min_x'] < 100

    @patch('gns3_snapshot.gns3_snapshot.svg2png')
    @patch('gns3_snapshot.gns3_snapshot.Image')
    def test_svg_to_png(self, mock_image, mock_svg2png, generator, tmp_path):
        mock_svg2png.return_value = b'fake_png'
        mock_img = MagicMock()
        mock_image.open.return_value = mock_img
        mock_image.new.return_value = MagicMock()
        
        result = generator._svg_to_png('<svg></svg>', str(tmp_path / 'out.png'))
        assert result is True

    def test_get_node_icon_cached(self, generator):
        symbol = "test.svg"
        generator._icon_cache[symbol] = "data:image/png;base64,data"
        assert generator._get_node_icon(symbol) == "data:image/png;base64,data"

    @patch('gns3_snapshot.gns3_snapshot.Path.exists')
    @patch('gns3_snapshot.gns3_snapshot.Path.read_bytes')
    @patch('gns3_snapshot.gns3_snapshot.svg2png')
    def test_get_node_icon_from_disk(self, mock_svg, mock_read, mock_exists, generator):
        """Covers the file-reading logic for icons."""
        mock_exists.return_value = True
        mock_read.return_value = b'<svg xmlns="http://www.w3.org/2000/svg">Icon</svg>'
        mock_svg.return_value = b'png_bytes'
        
        # Ensure cache is clear
        GNS3ThumbnailGenerator._shared_icon_cache.clear()
        
        icon_data = generator._get_node_icon("router.svg")
        assert "data:image/png" in icon_data

    @patch('sys.argv', ['gns3_snapshot', '--project-ids', '123,456', '--workers', '1'])
    @patch('gns3_snapshot.gns3_snapshot.generate_thumbnails')
    def test_cli_main_success(self, mock_gen):
        """Tests the CLI success path and arg parsing."""
        mock_gen.return_value = {'success': ['123'], 'failed': [], 'paths': {}}
        assert main() == 0

    @patch('sys.argv', ['gns3_snapshot', '--project-ids', ' '])
    def test_cli_main_no_ids(self, capsys):
        """Tests CLI error handling for empty input."""
        assert main() == 1
        assert "Error: No valid project IDs" in capsys.readouterr().out

    def test_auto_detect_workers(self):
        from gns3_snapshot.gns3_snapshot import _auto_detect_workers
        assert _auto_detect_workers(io_bound=True) >= _auto_detect_workers(io_bound=False)

    @patch.object(GNS3ThumbnailGenerator, '_api_get')
    @patch.object(GNS3ThumbnailGenerator, '_get_topology_from_file')
    @patch.object(GNS3ThumbnailGenerator, '_svg_to_png')
    def test_generate_thumbnail_flow(self, mock_svg, mock_file, mock_api, generator, sample_topology):
        """Tests the main generation coordination logic."""
        mock_api.return_value = {'filename': 'p.gns3', 'status': 'closed'}
        mock_file.return_value = (sample_topology['nodes'], [], [])
        mock_svg.return_value = True
        
        success, path = generator.generate_thumbnail('id')
        assert success is True
        assert 'id.png' in path

class TestParallelAndConvenience:
    """Tests for multi-project logic."""

    @patch.object(GNS3ThumbnailGenerator, 'generate_thumbnail')
    def test_generate_thumbnails_parallel(self, mock_gen, generator):
        mock_gen.return_value = (True, 'path.png')
        results = generator.generate_thumbnails(['p1', 'p2'], max_workers=2, show_progress=False)
        assert len(results['success']) == 2

    @patch("gns3_snapshot.gns3_snapshot.GNS3ThumbnailGenerator")
    def test_convenience_function(self, mock_gen_class):
        mock_instance = mock_gen_class.return_value
        mock_instance.generate_thumbnails.return_value = {'success': ['p1'], 'failed': [], 'paths': {}}
        
        results = generate_thumbnails(['p1'], server_url='http://test:3080')
        assert 'p1' in results['success']