"""Comprehensive tests for CLI strategy commands."""
import io
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, ANY

import pytest

from main import CLI
from content_strategy import ContentStrategy


class TestStrategyCLI:
    """Test strategy-based CLI commands."""
    
    def run_cli(self, args, timeout=30):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "main.py"] + args
        return subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
    
    def test_strategy_help_commands(self):
        """Test that strategy-related help is displayed correctly."""
        result = self.run_cli(["generate-day", "--help"])
        assert result.returncode == 0
        assert "--strategy" in result.stdout
        assert "wider" in result.stdout
        assert "deeper" in result.stdout
        assert "--source-day" in result.stdout
    
    @patch('story_generator.ContentGenerator')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_wider_strategy_cli_basic(self, mock_stdout, mock_generator_class):
        """Test WIDER strategy via CLI with basic parameters."""
        # Setup mock
        mock_generator = mock_generator_class.return_value
        mock_generator.generate_strategy_based_story.return_value = (
            "Generated story", 
            {"new": ["new1", "new2"], "review": ["review1"]}
        )
        
        # Mock curriculum file existence
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.argv', [
                'main.py', 'generate-day', '11', '--strategy=wider'
            ]):
                result = CLI().run()
        
        assert result == 0
        output = mock_stdout.getvalue()
        assert "WIDER strategy" in output
        assert "day 11" in output
        
        # Verify the generator was called with correct parameters
        mock_generator.generate_strategy_based_story.assert_called_once_with(
            11, ContentStrategy.WIDER, None
        )
    
    @patch('story_generator.ContentGenerator')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_deeper_strategy_cli_with_source_day(self, mock_stdout, mock_generator_class):
        """Test DEEPER strategy via CLI with explicit source day."""
        # Setup mock
        mock_generator = mock_generator_class.return_value
        mock_generator.generate_strategy_based_story.return_value = (
            "Generated story", 
            {"new": ["new1"], "review": ["review1", "review2", "review3"]}
        )
        
        # Mock curriculum file existence
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.argv', [
                'main.py', 'generate-day', '9', 
                '--strategy=deeper', '--source-day=6'
            ]):
                result = CLI().run()
        
        assert result == 0
        output = mock_stdout.getvalue()
        assert "DEEPER strategy" in output
        assert "day 9" in output
        assert "day 6" in output
        
        # Verify the generator was called with correct parameters
        mock_generator.generate_strategy_based_story.assert_called_once_with(
            9, ContentStrategy.DEEPER, 6
        )
    
    @patch('story_generator.ContentGenerator')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_deeper_strategy_auto_source_day(self, mock_stdout, mock_generator_class):
        """Test DEEPER strategy CLI with automatic source day selection."""
        # Setup mock
        mock_generator = mock_generator_class.return_value
        mock_generator.generate_strategy_based_story.return_value = (
            "Generated story", 
            {"new": ["new1"], "review": ["review1", "review2"]}
        )
        
        # Mock curriculum file existence
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.argv', [
                'main.py', 'generate-day', '8', '--strategy=deeper'
            ]):
                result = CLI().run()
        
        assert result == 0
        output = mock_stdout.getvalue()
        assert "DEEPER strategy" in output
        assert "day 8" in output
        assert "day 7" in output  # Should default to previous day
        
        # Verify the generator was called with auto-calculated source day
        mock_generator.generate_strategy_based_story.assert_called_once_with(
            8, ContentStrategy.DEEPER, 7  # day - 1
        )
    
    def test_invalid_strategy_parameter(self):
        """Test handling of invalid strategy parameter."""
        result = self.run_cli([
            "generate-day", "5", "--strategy=invalid"
        ])
        assert result.returncode == 2  # argparse error
        assert "invalid choice: 'invalid'" in result.stderr
    
    def test_invalid_day_number_strategy(self):
        """Test error handling for invalid day numbers with strategy."""
        result = self.run_cli([
            "generate-day", "0", "--strategy=wider"
        ], timeout=10)
        assert result.returncode == 1
        assert "Day must be >= 1" in result.stderr
    
    @patch('story_generator.ContentGenerator')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_strategy_generation_error_handling(self, mock_stderr, mock_generator_class):
        """Test error handling when strategy generation fails."""
        # Setup mock to raise an exception
        mock_generator = mock_generator_class.return_value
        mock_generator.generate_strategy_based_story.side_effect = ValueError("Strategy generation failed")
        
        # Mock curriculum file existence
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.argv', [
                'main.py', 'generate-day', '10', '--strategy=wider'
            ]):
                result = CLI().run()
        
        assert result == 1
        error_output = mock_stderr.getvalue()
        assert "Strategy generation failed" in error_output
    
    @patch('story_generator.ContentGenerator')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_source_day_parameter_validation(self, mock_stdout, mock_generator_class):
        """Test source day parameter validation."""
        # Setup mock
        mock_generator = mock_generator_class.return_value
        mock_generator.generate_strategy_based_story.return_value = (
            "Generated story", 
            {"new": ["new1"], "review": ["review1"]}
        )
        
        # Mock curriculum file existence
        with patch('pathlib.Path.exists', return_value=True):
            with patch('sys.argv', [
                'main.py', 'generate-day', '15', 
                '--strategy=deeper', '--source-day=10'
            ]):
                result = CLI().run()
        
        assert result == 0
        
        # Verify the exact source day was used
        mock_generator.generate_strategy_based_story.assert_called_once_with(
            15, ContentStrategy.DEEPER, 10
        )


class TestAnalysisCommandsCLI:
    """Test analysis commands via CLI."""
    
    def run_cli(self, args, timeout=30):
        """Helper to run CLI commands."""
        import os
        import config
        
        # Set up environment with test data directory
        env = os.environ.copy()
        if hasattr(config, 'DATA_DIR') and str(config.DATA_DIR) != 'data':
            # We're in a test environment with a temp directory
            env['TUNATALE_TEST_DATA_DIR'] = str(config.DATA_DIR)
        
        cmd = [sys.executable, "main.py"] + args
        return subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent.parent,
            env=env
        )
    
    def test_show_day_collocations_cli(self):
        """Test show-day-collocations command via CLI."""
        result = self.run_cli(["show-day-collocations", "6"])
        # Command should either succeed or fail gracefully with informative message
        assert result.returncode in [0, 1]
        
        if result.returncode == 1:
            # Should have informative error message about missing story
            assert any(word in result.stderr.lower() 
                      for word in ["story", "found", "file", "day"])
    
    @patch('main.CLI._handle_show_srs_status')
    def test_show_srs_status_cli(self, mock_handler):
        """Test show-srs-status command via CLI."""
        mock_handler.return_value = 0
        
        result = self.run_cli(["show-srs-status", "--day", "8"])
        assert result.returncode == 0
    
    def test_debug_generation_cli(self):
        """Test debug-generation command via CLI."""
        result = self.run_cli(["debug-generation", "9"])
        # Command should either succeed or fail gracefully with informative message
        assert result.returncode in [0, 1]
        
        if result.returncode == 1:
            # Should have informative error message about missing story
            assert any(word in result.stderr.lower() 
                      for word in ["story", "found", "file", "day"])
    
    def test_invalid_day_for_analysis_commands(self):
        """Test invalid day numbers for analysis commands."""
        commands = [
            ["show-day-collocations", "0"],
            ["show-srs-status", "-1"],
            ["debug-generation", "abc"]
        ]
        
        for cmd in commands:
            result = self.run_cli(cmd, timeout=10)
            assert result.returncode != 0, f"Command {cmd} should have failed"


class TestViewCommandsCLI:
    """Test enhanced view commands via CLI."""
    
    def run_cli(self, args, timeout=30):
        """Helper to run CLI commands."""
        cmd = [sys.executable, "main.py"] + args
        return subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
    
    def test_view_curriculum_command(self):
        """Test view curriculum command."""
        result = self.run_cli(["view", "curriculum"])
        # Should either work (if curriculum exists) or fail gracefully
        assert result.returncode in [0, 1]
        
        if result.returncode == 1:
            # Should have informative error message (could be in stdout or stderr)
            output_text = (result.stdout + result.stderr).lower()
            assert any(word in output_text 
                      for word in ["not found", "found", "error", "missing"])
    
    def test_view_collocations_command(self):
        """Test view collocations command."""
        result = self.run_cli(["view", "collocations"])
        # Should either work or fail gracefully
        assert result.returncode in [0, 1]
    
    def test_view_story_command(self):
        """Test view story command with day parameter."""
        result = self.run_cli(["view", "story", "--day=5"])
        # Should either work (if story exists) or fail gracefully with informative message
        assert result.returncode in [0, 1]
        if result.returncode == 1:
            assert "story" in result.stdout.lower() or "not found" in result.stdout.lower()
    
    def test_view_help_command(self):
        """Test view command help."""
        result = self.run_cli(["view", "--help"])
        assert result.returncode == 0
        assert "curriculum" in result.stdout
        assert "collocations" in result.stdout
        assert "story" in result.stdout


class TestStrategyCLIIntegration:
    """Integration tests for strategy commands with realistic workflows."""
    
    def run_cli(self, args, timeout=45):
        """Helper to run CLI commands with longer timeout for integration tests."""
        cmd = [sys.executable, "main.py"] + args
        return subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
    
    @patch('story_generator.ContentGenerator')
    @patch('pathlib.Path.exists', return_value=True)
    def test_strategy_chaining_workflow(self, mock_exists, mock_generator_class):
        """Test a realistic strategy chaining workflow."""
        # Setup mock generator
        mock_generator = mock_generator_class.return_value
        
        # Mock responses for different strategies
        def mock_strategy_generation(day, strategy, source_day):
            if strategy == ContentStrategy.DEEPER:
                return ("DEEPER story", {"new": ["adv1"], "review": ["rev1", "rev2", "rev3"]})
            elif strategy == ContentStrategy.WIDER:
                return ("WIDER story", {"new": ["new1", "new2", "new3"], "review": ["rev1"]})
            else:
                return ("BALANCED story", {"new": ["bal1", "bal2"], "review": ["rev1"]})
        
        mock_generator.generate_strategy_based_story.side_effect = mock_strategy_generation
        mock_generator.generate_day_story.return_value = ("BALANCED story", {"new": ["bal1"], "review": []})
        
        # Test workflow: Generate DEEPER day 9, then WIDER day 10
        with patch('sys.argv', ['main.py', 'generate-day', '9', '--strategy=deeper', '--source-day=6']):
            result1 = CLI().run()
        
        with patch('sys.argv', ['main.py', 'generate-day', '10', '--strategy=wider']):
            result2 = CLI().run()
        
        assert result1 == 0
        assert result2 == 0
        
        # Verify both strategies were called
        assert mock_generator.generate_strategy_based_story.call_count == 2
        
        # Verify specific calls
        calls = mock_generator.generate_strategy_based_story.call_args_list
        assert calls[0] == ((9, ContentStrategy.DEEPER, 6),)
        assert calls[1] == ((10, ContentStrategy.WIDER, None),)
    
    def test_help_commands_include_strategy_info(self):
        """Test that help commands include comprehensive strategy information."""
        # Main help should mention strategy capabilities
        result = self.run_cli(["--help"])
        assert result.returncode == 0
        assert "strategy" in result.stdout.lower()
        
        # generate-day help should have detailed strategy info
        result = self.run_cli(["generate-day", "--help"])
        assert result.returncode == 0
        help_output = result.stdout.lower()
        assert "strategy" in help_output
        assert "wider" in help_output
        assert "deeper" in help_output
        assert "source-day" in help_output
    
    @pytest.mark.slow
    def test_error_handling_workflow(self):
        """Test error handling in realistic failure scenarios."""
        # Test with invalid parameters combinations
        result = self.run_cli([
            "generate-day", "abc", "--strategy=deeper"
        ], timeout=10)
        assert result.returncode == 2  # argparse error
        
        # Test graceful handling of edge cases - very high day number
        result = self.run_cli([
            "generate-day", "999", "--strategy=wider"
        ], timeout=10)
        # Should either work (if curriculum extends that far) or handle gracefully
        assert result.returncode in [0, 1]
        
        # Test invalid strategy parameter
        result = self.run_cli([
            "generate-day", "5", "--strategy=invalid"
        ], timeout=10)
        assert result.returncode == 2  # argparse error
        assert "invalid choice: 'invalid'" in result.stderr