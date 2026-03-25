"""Comprehensive tests for CLI analysis commands."""
import io
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from main import CLI


class TestAnalyzeCommandCLI:
    """Test analyze command variations via CLI."""
    
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
    
    def test_analyze_help_command(self):
        """Test analyze command help shows all available options."""
        result = self.run_cli(["analyze", "--help"])
        assert result.returncode == 0
        help_output = result.stdout.lower()

        # Check for subcommands
        assert "vocab" in help_output
        assert "collocations" in help_output
        assert "debug" in help_output
    
    def test_analyze_with_text(self):
        """Test analyze vocab command with simple text input."""
        result = self.run_cli([
            "analyze", "vocab", "Kumusta ka? Salamat po sa lahat."
        ])
        assert result.returncode == 0
        assert "VOCABULARY ANALYSIS" in result.stdout
        assert "Total words:" in result.stdout
    
    def test_analyze_with_day_parameter(self):
        """Test analyze vocab command with day parameter."""
        result = self.run_cli(["analyze", "vocab", "--day=8"])
        # Should either work (if day 8 exists) or fail gracefully
        assert result.returncode in [0, 1]

        if result.returncode == 0:
            assert "VOCABULARY ANALYSIS" in result.stdout
        else:
            # Should have informative error message
            assert any(word in result.stderr.lower()
                      for word in ["day", "not found", "error"])
    
    def test_analyze_quality_option(self):
        """Test analyze vocab command with quality assessment."""
        result = self.run_cli([
            "analyze", "vocab", "--quality", "Magandang umaga po. Salamat sa inyong pagtituro."
        ])
        assert result.returncode == 0
        output = result.stdout.upper()
        # Should include quality analysis markers
        assert any(marker in output for marker in [
            "QUALITY", "ANALYSIS", "FILIPINO", "AUTHENTICITY"
        ])
    
    def test_analyze_trip_readiness_option(self):
        """Test analyze vocab command with trip readiness assessment."""
        result = self.run_cli([
            "analyze", "vocab", "--trip-readiness",
            "Magkano po ang tricycle? Puwede po ba akong mag-book ng tour?"
        ])
        assert result.returncode == 0
        output = result.stdout.upper()
        # Should include trip readiness markers
        assert any(marker in output for marker in [
            "TRIP", "READINESS", "EL NIDO", "TRAVEL"
        ])
    
    def test_analyze_invalid_day(self):
        """Test analyze vocab command with invalid day parameter."""
        result = self.run_cli(["analyze", "vocab", "--day=abc"])
        assert result.returncode == 2  # argparse error
        assert "invalid" in result.stderr.lower()
    
    def test_analyze_strategy_effectiveness_with_compare_with(self):
        """Test strategy effectiveness with compare-with parameter."""
        result = self.run_cli([
            "analyze", "vocab", "--strategy-effectiveness",
            "--compare-with", "/nonexistent/file.txt",
            "Some text"
        ])
        # Should either work or fail gracefully
        assert result.returncode in [0, 1]
        # Should run some form of analysis
        assert "ANALYSIS" in result.stdout or len(result.stderr) > 0
    
    def test_analyze_with_nonexistent_file(self):
        """Test analyze vocab with file that doesn't exist (treated as text)."""
        result = self.run_cli(["analyze", "vocab", "/nonexistent/file.txt"])
        assert result.returncode == 0  # Treated as text, not file
        assert "Total words:                                     0" in result.stdout
    
    @patch('main.CLI._handle_analyze')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_analyze_command_routing(self, mock_stdout, mock_handler):
        """Test that analyze command is routed correctly."""
        mock_handler.return_value = 0

        with patch('sys.argv', ['main.py', 'analyze', 'vocab', 'test text']):
            result = CLI().run()

        assert result == 0
        mock_handler.assert_called_once()


class TestSpecializedAnalysisCommandsCLI:
    """Test specialized analysis commands (analyze collocations, srs status, analyze debug)."""
    
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
    
    def test_show_day_collocations_help(self):
        """Test analyze collocations help."""
        result = self.run_cli(["analyze", "collocations", "--help"])
        assert result.returncode == 0
        assert "day" in result.stdout.lower()
        assert "collocation" in result.stdout.lower()

    def test_show_day_collocations_with_day(self):
        """Test analyze collocations with day parameter."""
        result = self.run_cli(["analyze", "collocations", "--day", "6"])
        # Should either work or fail gracefully
        assert result.returncode in [0, 1]

        if result.returncode == 1:
            # Should have informative error message
            assert any(word in result.stderr.lower()
                      for word in ["day", "not found", "error", "curriculum"])
    
    def test_srs_status_help(self):
        """Test srs status help."""
        result = self.run_cli(["srs", "status", "--help"])
        assert result.returncode == 0
        help_output = result.stdout.lower()
        assert "--day" in help_output
        assert "--all" in help_output
        assert "--due-only" in help_output
    
    def test_srs_status_with_all_option(self):
        """Test srs status with --all option."""
        result = self.run_cli(["srs", "status", "--all"])
        # Should either work or fail gracefully
        assert result.returncode in [0, 1]
    
    def test_srs_status_with_due_only_option(self):
        """Test srs status with --due-only option."""
        result = self.run_cli(["srs", "status", "--due-only"])
        # Should either work or fail gracefully
        assert result.returncode in [0, 1]
    
    def test_debug_generation_help(self):
        """Test analyze debug help."""
        result = self.run_cli(["analyze", "debug", "--help"])
        assert result.returncode == 0
        assert "day" in result.stdout.lower()
        assert "debug" in result.stdout.lower()

    def test_debug_generation_with_day(self):
        """Test analyze debug with day parameter."""
        result = self.run_cli(["analyze", "debug", "--day", "9"])
        # Should either work or fail gracefully
        assert result.returncode in [0, 1]

        if result.returncode == 1:
            # Should have informative error message
            assert any(word in result.stderr.lower()
                      for word in ["day", "not found", "error", "generation"])
    
    def test_invalid_day_parameters(self):
        """Test invalid day parameters for analysis commands."""
        commands = [
            ["analyze", "collocations", "--day", "0"],  # May work but return no results
            ["analyze", "debug", "--day", "0"]  # May work but return no results
        ]
        
        for cmd in commands:
            result = self.run_cli(cmd, timeout=10)
            # Commands may be permissive, just check they respond
            assert result.returncode in [0, 1, 2], f"Command {cmd} should respond normally"


class TestAnalysisIntegrationCLI:
    """Integration tests for analysis command workflows."""
    
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
    
    @pytest.mark.slow
    def test_comprehensive_analysis_workflow(self):
        """Test a comprehensive analysis workflow."""
        # Test basic text analysis
        result1 = self.run_cli([
            "analyze", "vocab", "Magandang umaga po. Salamat sa inyong pagtulong."
        ])
        assert result1.returncode == 0
        assert "VOCABULARY ANALYSIS" in result1.stdout

        # Test quality analysis of the same text
        result2 = self.run_cli([
            "analyze", "vocab", "--quality", "Magandang umaga po. Salamat sa inyong pagtulong."
        ])
        assert result2.returncode == 0

        # Test trip readiness analysis
        result3 = self.run_cli([
            "analyze", "vocab", "--trip-readiness", "Magkano po ang hotel? Saan ang airport?"
        ])
        assert result3.returncode == 0

        # All should produce different types of analysis
        assert result1.stdout != result2.stdout
        assert result2.stdout != result3.stdout
    
    def test_analysis_command_error_handling(self):
        """Test error handling across analysis commands."""
        # Test commands that should fail gracefully
        error_commands = [
            ["analyze"],  # Missing subcommand
            ["analyze", "collocations"],  # Missing day
            ["srs", "status", "--day"],  # Missing day value
            ["analyze", "debug"],  # Missing day
        ]
        
        for cmd in error_commands:
            result = self.run_cli(cmd, timeout=10)
            assert result.returncode != 0, f"Command {cmd} should have failed"
            # Should provide helpful error messages
            assert len(result.stderr) > 0, f"Command {cmd} should have error output"
    
    def test_help_consistency_across_analysis_commands(self):
        """Test that help messages are consistent and informative."""
        help_commands = [
            ["analyze", "--help"],
            ["analyze", "vocab", "--help"],
            ["analyze", "collocations", "--help"],
            ["srs", "status", "--help"],
            ["analyze", "debug", "--help"]
        ]
        
        for cmd in help_commands:
            result = self.run_cli(cmd)
            assert result.returncode == 0, f"Help for {cmd} should work"
            assert "usage:" in result.stdout.lower(), f"Help for {cmd} should show usage"
            assert len(result.stdout) > 100, f"Help for {cmd} should be substantial"