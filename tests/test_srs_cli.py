"""
Test suite for SRS CLI commands.
"""
import pytest
import tempfile
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import sys

# Import CLI modules
from cli.srs_commands import (
    handle_populate_command, handle_stats_command, handle_clean_command,
    _populate_from_story_file, _filter_noisy_collocations, _get_database_stats
)
from cli.vocab_commands import (
    handle_vocab_command, _parse_day_specification, _extract_from_file,
    vocab_filter_noise
)
from cli.enforcement_commands import (
    handle_test_enforcement, handle_show_enforcement,
    _test_constraint_enforcement, _test_llm_enforcement
)
from srs_database import SRSDatabase
from collocation_extractor import CollocationExtractor


class TestSRSCLICommands:
    """Test SRS database management CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Create test database
        self.db = SRSDatabase(self.db_path)
        
        # Create test story content
        self.test_story_content = """
        [NARRATOR]: Day 1: Test Story
        
        Key Phrases:
        
        [TAGALOG-FEMALE-1]: salamat po
        [NARRATOR]: thank you
        [TAGALOG-FEMALE-1]: magandang hapon
        [NARRATOR]: good afternoon
        
        [NARRATOR]: Natural Speed
        
        [TAGALOG-FEMALE-1]: Salamat po sa tulong.
        [TAGALOG-MALE-1]: Walang anuman!
        """
        
        # Create test story file
        self.story_file = tempfile.NamedTemporaryFile(mode='w', suffix='_day1.txt', delete=False)
        self.story_file.write(self.test_story_content)
        self.story_file.close()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary files
        Path(self.db_path).unlink(missing_ok=True)
        Path(self.story_file.name).unlink(missing_ok=True)
    
    def test_populate_single_day_success(self):
        """Test successful population from single day."""
        # Create mock arguments
        args = Mock()
        args.day = 1
        args.all_stories = False
        args.clean_first = False
        args.dry_run = False
        args.overwrite = False
        args.filter_noise = True
        
        # Mock story files
        with patch('cli.srs_commands.get_story_files') as mock_get_files:
            mock_get_files.return_value = [Path(self.story_file.name)]
            
            with patch('cli.srs_commands.CollocationExtractor') as mock_extractor:
                mock_extractor_instance = mock_extractor.return_value
                mock_extractor_instance.extract_collocations.return_value = [
                    'salamat po', 'magandang hapon', 'walang anuman'
                ]
                
                with patch('cli.srs_commands.SRSDatabase') as mock_db_class:
                    mock_db_class.return_value = self.db
                    
                    # Capture output
                    captured_output = StringIO()
                    with patch('sys.stdout', captured_output):
                        handle_populate_command(args)
                    
                    output = captured_output.getvalue()
                    assert "Added" in output
                    assert "collocations from day 1" in output
    
    def test_populate_dry_run(self):
        """Test dry run mode for populate command."""
        args = Mock()
        args.day = 1
        args.all_stories = False
        args.clean_first = False
        args.dry_run = True
        args.overwrite = False
        args.filter_noise = True
        
        with patch('cli.srs_commands.get_story_files') as mock_get_files:
            mock_get_files.return_value = [Path(self.story_file.name)]
            
            with patch('cli.srs_commands.CollocationExtractor') as mock_extractor:
                mock_extractor_instance = mock_extractor.return_value
                mock_extractor_instance.extract_collocations.return_value = [
                    'salamat po', 'magandang hapon'
                ]
                
                with patch('cli.srs_commands.SRSDatabase') as mock_db_class:
                    mock_db_class.return_value = self.db
                    
                    captured_output = StringIO()
                    with patch('sys.stdout', captured_output):
                        handle_populate_command(args)
                    
                    output = captured_output.getvalue()
                    assert "DRY RUN" in output
                    assert "Would add" in output
    
    def test_populate_all_stories(self):
        """Test populating from all stories."""
        args = Mock()
        args.day = None
        args.all_stories = True
        args.clean_first = False
        args.dry_run = False
        args.overwrite = False
        args.filter_noise = True
        
        with patch('cli.srs_commands.get_story_files') as mock_get_files:
            mock_get_files.return_value = [
                Path(self.story_file.name),
                Path(self.story_file.name.replace('day1', 'day2'))
            ]
            
            with patch('cli.srs_commands.CollocationExtractor') as mock_extractor:
                mock_extractor_instance = mock_extractor.return_value
                mock_extractor_instance.extract_collocations.return_value = [
                    'salamat po', 'magandang hapon'
                ]
                
                with patch('cli.srs_commands.SRSDatabase') as mock_db_class:
                    mock_db_class.return_value = self.db
                    
                    captured_output = StringIO()
                    with patch('sys.stdout', captured_output):
                        handle_populate_command(args)
                    
                    output = captured_output.getvalue()
                    assert "Processed" in output
                    assert "files" in output
    
    def test_stats_command_basic(self):
        """Test basic stats command."""
        # Add test data to database
        self.db.add_collocation('salamat po', 1, 1, [1])
        self.db.add_collocation('magandang hapon', 1, 1, [1])
        
        args = Mock()
        args.detailed = False
        args.export_csv = None
        
        with patch('cli.srs_commands.SRSDatabase') as mock_db_class:
            mock_db_class.return_value = self.db
            
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                handle_stats_command(args)
            
            output = captured_output.getvalue()
            assert "SRS DATABASE STATISTICS" in output
            assert "Total Collocations" in output
            assert "2" in output  # Should show 2 collocations
    
    def test_stats_command_detailed(self):
        """Test detailed stats command."""
        # Add test data with review information
        self.db.add_collocation('salamat po', 1, 1, [1], review_count=2)
        self.db.add_collocation('magandang hapon', 2, 2, [2], review_count=0)
        
        args = Mock()
        args.detailed = True
        args.export_csv = None
        
        with patch('cli.srs_commands.SRSDatabase') as mock_db_class:
            mock_db_class.return_value = self.db
            
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                handle_stats_command(args)
            
            output = captured_output.getvalue()
            assert "Avg Review Count" in output
            assert "Unreviewed Count" in output
    
    def test_clean_command_dry_run(self):
        """Test clean command in dry run mode."""
        # Add corrupted test data
        self.db.add_collocation('tagalog-female-1', 1, 1, [1])  # Corrupted
        self.db.add_collocation('salamat po', 1, 1, [1])  # Clean
        
        args = Mock()
        args.dry_run = True
        args.backup = False
        
        with patch('cli.srs_commands.SRSDatabase') as mock_db_class:
            mock_db_class.return_value = self.db
            
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                handle_clean_command(args)
            
            output = captured_output.getvalue()
            assert "Found" in output
            assert "corrupted entries" in output
            assert "DRY RUN" in output
    
    def test_filter_noisy_collocations(self):
        """Test noise filtering function."""
        noisy_collocations = [
            'salamat po',  # Clean
            'tagalog-female-1',  # Voice tag - should be filtered
            '[narrator',  # Markup - should be filtered  
            'po',  # Too short - should be filtered
            'the',  # Common English - should be filtered
            'magandang hapon',  # Clean
            'a',  # Single letter - should be filtered
        ]
        
        clean = _filter_noisy_collocations(noisy_collocations)
        
        assert 'salamat po' in clean
        assert 'magandang hapon' in clean
        assert 'tagalog-female-1' not in clean
        assert '[narrator' not in clean
        assert 'po' not in clean
        assert 'the' not in clean
        assert 'a' not in clean
    
    def test_get_database_stats(self):
        """Test database statistics calculation."""
        # Add test data
        self.db.add_collocation('salamat po', 1, 1, [1], review_count=2)
        self.db.add_collocation('magandang hapon', 2, 3, [2, 3], review_count=1)
        
        stats = _get_database_stats(self.db, detailed=True)
        
        assert stats['total_collocations'] == 2
        assert stats['database_exists'] is True
        assert 'avg_review_count' in stats
        assert 'min_day' in stats
        assert 'max_day' in stats


class TestVocabCLICommands:
    """Test vocabulary extraction CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_story_content = """
        [NARRATOR]: Day 5: Beach Day
        
        Key Phrases:
        
        [TAGALOG-FEMALE-1]: salamat po
        [NARRATOR]: thank you
        
        [NARRATOR]: Natural Speed
        
        [TAGALOG-FEMALE-1]: Magandang umaga po!
        [TAGALOG-MALE-1]: Salamat sa pagdating.
        """
        
        self.story_file = tempfile.NamedTemporaryFile(mode='w', suffix='_day5.txt', delete=False)
        self.story_file.write(self.test_story_content)
        self.story_file.close()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.story_file.name).unlink(missing_ok=True)
    
    def test_parse_day_specification_single(self):
        """Test parsing single day specification."""
        args = Mock()
        args.day = 5
        args.days = None
        
        days = _parse_day_specification(args)
        assert days == [5]
    
    def test_parse_day_specification_range(self):
        """Test parsing day range specification."""
        args = Mock()
        args.day = None
        args.days = "3-7"
        
        days = _parse_day_specification(args)
        assert days == [3, 4, 5, 6, 7]
    
    def test_parse_day_specification_list(self):
        """Test parsing day list specification."""
        args = Mock()
        args.day = None
        args.days = "1,3,5,7"
        
        days = _parse_day_specification(args)
        assert days == [1, 3, 5, 7]
    
    def test_parse_day_specification_mixed(self):
        """Test parsing mixed day specification."""
        args = Mock()
        args.day = None
        args.days = "1-3,5,7-8"
        
        days = _parse_day_specification(args)
        assert days == [1, 2, 3, 5, 7, 8]
    
    def test_extract_from_file_success(self):
        """Test successful vocabulary extraction from file."""
        # Create a mock extractor that returns known good Filipino phrases
        mock_extractor = Mock()
        mock_extractor.extract_collocations.return_value = {
            'magandang umaga po': 1,  # Good Filipino phrase 
            'salamat sa pagdating': 1  # Good Filipino phrase
        }
        
        result = _extract_from_file(mock_extractor, Path(self.story_file.name), filter_noise=True)
        
        assert len(result) == 2
        assert 'magandang umaga po' in result
        assert 'salamat sa pagdating' in result
    
    def test_vocab_filter_noise(self):
        """Test vocabulary-specific noise filtering."""
        noisy_vocab = [
            'magandang umaga',  # Clean
            'tagalog-female-1',  # Voice tag
            '[narrator]: hello',  # Markup
            'the',  # Common English
            'po',  # Too short
            'salamat po',  # Clean
            '123',  # Numbers
            'a',  # Single letter
        ]
        
        clean = vocab_filter_noise(noisy_vocab)
        
        assert 'magandang umaga' in clean
        assert 'salamat po' in clean
        assert 'tagalog-female-1' not in clean
        assert '[narrator]: hello' not in clean
        assert 'the' not in clean
        assert 'po' not in clean
        assert '123' not in clean
        assert 'a' not in clean

    def test_extract_from_file_natural_speed_filtering(self):
        """Test that _extract_from_file processes only Natural Speed section."""
        # Create story file with all sections to test filtering
        story_content = '''[NARRATOR]: Day 15: Test Story

Key Phrases:

[TAGALOG-FEMALE-1]: salamat po
po
mat
salamat

[NARRATOR]: Natural Speed

[TAGALOG-MALE-1]: Kumusta po!
[TAGALOG-FEMALE-1]: Salamat sa pagdating.
[NARRATOR]: They continue talking.

[NARRATOR]: Slow Speed

[TAGALOG-MALE-1]: Kumusta... po!
[TAGALOG-FEMALE-1]: Salamat... sa... pagdating.

[NARRATOR]: Translated

[TAGALOG-MALE-1]: Kumusta po!
[NARRATOR]: How are you!
'''
        
        # Create temporary file with complete story content
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(story_content)
            temp_path = f.name
        
        try:
            # Mock extractor to capture what content gets processed
            mock_extractor = Mock()
            mock_extractor.extract_collocations.return_value = {
                'kumusta po': 1,
                'salamat sa pagdating': 1
            }
            
            result = _extract_from_file(mock_extractor, Path(temp_path), filter_noise=False)
            
            # Verify extractor was called with Natural Speed content only
            mock_extractor.extract_collocations.assert_called_once()
            processed_content = mock_extractor.extract_collocations.call_args[0][0]
            
            # Should contain Natural Speed dialogue
            assert 'Kumusta po!' in processed_content
            assert 'Salamat sa pagdating.' in processed_content
            
            # Should NOT contain content from other sections
            assert 'po\nmat\nsalamat' not in processed_content  # Key Phrases artifacts
            assert 'Kumusta... po!' not in processed_content  # Slow Speed ellipses
            assert 'How are you!' not in processed_content  # Translated English
            assert 'They continue talking.' not in processed_content  # Narrator descriptions
            
            # Should return processed collocations
            assert result == ['kumusta po', 'salamat sa pagdating']
            
        finally:
            # Cleanup
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_extract_from_file_no_natural_speed_section(self):
        """Test handling when story file lacks Natural Speed section."""
        story_without_natural = '''[NARRATOR]: Day 1: Test

Key Phrases:
[TAGALOG-FEMALE-1]: test

[NARRATOR]: Slow Speed
[TAGALOG-FEMALE-1]: test...
'''
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(story_without_natural)
            temp_path = f.name
        
        try:
            mock_extractor = Mock()
            result = _extract_from_file(mock_extractor, Path(temp_path), filter_noise=False)
            
            # Should return empty list when no Natural Speed content
            assert result == []
            # Extractor should not be called
            mock_extractor.extract_collocations.assert_not_called()
            
        finally:
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_vocab_command_preview(self):
        """Test vocabulary extraction in preview mode."""
        args = Mock()
        args.day = 5
        args.days = None
        args.preview = True
        args.save = False
        args.filter_noise = True
        args.limit = 10
        
        # Mock the extraction function directly to return known results
        with patch('cli.vocab_commands.get_story_files') as mock_get_files:
            mock_get_files.return_value = [Path(self.story_file.name)]
            
            with patch('cli.vocab_commands.extract_day_number') as mock_extract_day:
                mock_extract_day.return_value = 5
                
                with patch('cli.vocab_commands._extract_from_file') as mock_extract_file:
                    mock_extract_file.return_value = [
                        'magandang umaga po', 'salamat sa pagdating'
                    ]
                    
                    captured_output = StringIO()
                    with patch('sys.stdout', captured_output):
                        handle_vocab_command(args)
                    
                    output = captured_output.getvalue()
                    assert "Extracted 2 collocations" in output
                    assert "magandang umaga po" in output


class TestEnforcementCLICommands:
    """Test constraint enforcement testing CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = SRSDatabase(self.db_path)
        
        # Add test vocabulary
        self.db.add_collocation('tubig', 1, 1, [1])
        self.db.add_collocation('salamat po', 1, 1, [1])
        
    def teardown_method(self):
        """Clean up test fixtures."""
        Path(self.db_path).unlink(missing_ok=True)
    
    def test_constraint_enforcement_success(self):
        """Test successful constraint enforcement."""
        test_text = "I need water and thank you"
        
        with patch('cli.enforcement_commands.SRSDatabase') as mock_db_class:
            mock_db_class.return_value = self.db
            
            with patch('cli.enforcement_commands.SRSEnforcer') as mock_enforcer_class:
                mock_enforcer = mock_enforcer_class.return_value
                mock_enforcer.enforce_constraints.return_value = (
                    "I need tubig and salamat po",
                    [
                        {'english': 'water', 'filipino': 'tubig', 'count': 1},
                        {'english': 'thank you', 'filipino': 'salamat po', 'count': 1}
                    ]
                )
                
                args = Mock()
                args.context = 'test'
                
                result = _test_constraint_enforcement(self.db, test_text, args)
                
                assert result['success'] is True
                assert result['replacement_count'] == 2
                assert 'tubig' in result['enforced_text']
                assert 'salamat po' in result['enforced_text']
    
    def test_constraint_enforcement_failure(self):
        """Test constraint enforcement failure handling."""
        test_text = "test text"
        
        with patch('cli.enforcement_commands.SRSEnforcer') as mock_enforcer_class:
            mock_enforcer = mock_enforcer_class.return_value
            mock_enforcer.enforce_constraints.side_effect = Exception("Test error")
            
            args = Mock()
            args.context = 'test'
            
            result = _test_constraint_enforcement(self.db, test_text, args)
            
            assert result['success'] is False
            assert 'Test error' in result['error']
    
    def test_llm_enforcement_success(self):
        """Test successful LLM enforcement."""
        test_text = "I need water and thank you"
        
        with patch('cli.enforcement_commands.create_llm_enforcer') as mock_create_enforcer:
            mock_enforcer = Mock()
            mock_enforcer.enforce_with_llm.return_value = (
                "I need tubig and salamat po",
                [
                    {'original': 'water', 'replacement': 'tubig', 'count': 1},
                    {'original': 'thank you', 'replacement': 'salamat po', 'count': 1}
                ]
            )
            mock_create_enforcer.return_value = mock_enforcer
            
            with patch('cli.enforcement_commands.MockLLM'):
                args = Mock()
                args.day = 1
                args.context = 'test'
                
                result = _test_llm_enforcement(self.db, test_text, args)
                
                assert result['success'] is True
                assert result['replacement_count'] == 2
                assert 'tubig' in result['enforced_text']
    
    def test_show_enforcement_command(self):
        """Test show enforcement rules command."""
        args = Mock()
        args.format = 'table'
        args.filter = None
        args.stats = False
        
        with patch('cli.enforcement_commands.SRSDatabase') as mock_db_class:
            mock_db_class.return_value = self.db
            
            with patch('cli.enforcement_commands.SRSEnforcer') as mock_enforcer_class:
                mock_enforcer = mock_enforcer_class.return_value
                mock_enforcer.replacement_dict = {
                    'water': 'tubig',
                    'thank you': 'salamat po',
                    'good morning': 'magandang umaga'
                }
                
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    handle_show_enforcement(args)
                
                output = captured_output.getvalue()
                assert "CONSTRAINT ENFORCEMENT RULES" in output
                assert "water" in output
                assert "tubig" in output


class TestSRSIntegration:
    """Test end-to-end SRS workflow integration."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = SRSDatabase(self.db_path)
        
        # Create test story
        self.test_story = """
        [NARRATOR]: Day 1: Welcome
        
        [TAGALOG-FEMALE-1]: salamat po
        [NARRATOR]: thank you
        [TAGALOG-FEMALE-1]: magandang hapon
        [NARRATOR]: good afternoon
        
        [NARRATOR]: Natural Speed
        
        [TAGALOG-FEMALE-1]: Salamat po sa tulong mo.
        [TAGALOG-MALE-1]: Magandang hapon din!
        """
        
        self.story_file = tempfile.NamedTemporaryFile(mode='w', suffix='_day1.txt', delete=False)
        self.story_file.write(self.test_story)
        self.story_file.close()
    
    def teardown_method(self):
        """Clean up integration test fixtures."""
        Path(self.db_path).unlink(missing_ok=True)
        Path(self.story_file.name).unlink(missing_ok=True)
    
    def test_full_pipeline_workflow(self):
        """Test complete pipeline: extract → populate → enforce."""
        # Step 1: Extract vocabulary - create mock extractor with Filipino phrases
        mock_extractor = Mock()
        extracted_vocab = ['salamat po', 'magandang hapon', 'sa tulong mo']
        mock_extractor.extract_collocations.return_value = {
            'salamat po': 1,
            'magandang hapon': 1,
            'sa tulong mo': 1
        }
        
        result = _extract_from_file(mock_extractor, Path(self.story_file.name), filter_noise=True)
        
        assert len(result) == 3
        assert 'salamat po' in result
        
        # Step 2: Populate database
        for colloc in extracted_vocab:
            self.db.add_collocation(colloc, 1, 1, [1])
        
        # Verify population
        all_collocations = self.db.get_all_collocations()
        assert len(all_collocations) == 3
        
        # Step 3: Test enforcement
        with patch('cli.enforcement_commands.SRSEnforcer') as mock_enforcer_class:
            mock_enforcer = mock_enforcer_class.return_value
            mock_enforcer.enforce_constraints.return_value = (
                "Salamat po and magandang hapon",
                [
                    {'english': 'thank you', 'filipino': 'salamat po', 'count': 1},
                    {'english': 'good afternoon', 'filipino': 'magandang hapon', 'count': 1}
                ]
            )
            
            args = Mock()
            args.context = 'integration_test'
            
            result = _test_constraint_enforcement(self.db, "thank you and good afternoon", args)
            
            assert result['success'] is True
            assert result['replacement_count'] == 2
    
    def test_vocabulary_alignment(self):
        """Test alignment between database and enforcement."""
        # Add vocabulary to database
        vocabulary = ['tubig', 'salamat po', 'magandang umaga', 'paumanhin po']
        for vocab in vocabulary:
            self.db.add_collocation(vocab, 1, 1, [1])
        
        # Mock enforcement rules
        enforcement_rules = {
            'water': 'tubig',
            'thank you': 'salamat po', 
            'good morning': 'magandang umaga',
            'excuse me': 'paumanhin po',
            'hello': 'kumusta'  # This one not in database
        }
        
        with patch('cli.enforcement_commands.SRSEnforcer') as mock_enforcer_class:
            mock_enforcer = mock_enforcer_class.return_value
            mock_enforcer.replacement_dict = enforcement_rules
            
            # Check alignment
            db_vocabulary = {c['text'] for c in self.db.get_all_collocations()}
            enforcement_filipino = set(enforcement_rules.values())
            
            # Calculate coverage
            covered = enforcement_filipino.intersection(db_vocabulary)
            coverage_rate = len(covered) / len(enforcement_filipino)
            
            # Should have good coverage (4/5 = 80%)
            assert coverage_rate >= 0.8
            assert 'tubig' in covered
            assert 'salamat po' in covered
            assert 'kumusta' not in covered  # Missing from database
    
    def test_error_recovery_workflow(self):
        """Test error recovery in CLI workflows."""
        # Test with corrupted database
        corrupted_collocation = 'tagalog-female-1'  # Voice tag corruption
        clean_collocation = 'salamat po'
        
        self.db.add_collocation(corrupted_collocation, 1, 1, [1])
        self.db.add_collocation(clean_collocation, 1, 1, [1])
        
        # Test clean operation identifies corruption
        all_collocations = self.db.get_all_collocations()
        corrupted_count = 0
        
        for colloc in all_collocations:
            text = colloc['text']
            if ('tagalog-' in text.lower() or 
                len(text) <= 2 or 
                text.startswith('[') or
                '\n' in text):
                corrupted_count += 1
        
        assert corrupted_count == 1  # Should identify the corrupted entry
        
        # Test that clean vocabulary remains accessible
        clean_entries = [c for c in all_collocations 
                        if c['text'] == clean_collocation]
        assert len(clean_entries) == 1


@pytest.fixture
def temp_story_dir():
    """Create temporary directory with test story files."""
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    
    # Create test story files
    stories = {
        'story_day1.txt': 'Test content for day 1',
        'story_day2.txt': 'Test content for day 2',
        'demo-0.0.3-day-3.txt': 'Test content for day 3'
    }
    
    for filename, content in stories.items():
        file_path = Path(temp_dir) / filename
        with open(file_path, 'w') as f:
            f.write(content)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


def test_cli_help_output():
    """Test that CLI help output is properly formatted."""
    # This test ensures help text is available and properly formatted
    # Would need to be integrated with actual CLI parser
    pass


def test_cli_error_handling():
    """Test CLI error handling and user-friendly messages."""
    # Test various error conditions produce helpful messages
    pass


class TestCLIUtilities:
    """Test CLI utility functions."""
    
    def test_extract_day_number_patterns(self):
        """Test day number extraction from various filename patterns."""
        from cli.utils import extract_day_number
        
        test_cases = [
            (Path('story_day1.txt'), 1),
            (Path('story_day16.txt'), 16),
            (Path('demo-0.0.3-day-5.txt'), 5),
            (Path('day-10-content.txt'), 10),
            (Path('no_day_info.txt'), 1),  # Fallback
        ]
        
        for path, expected_day in test_cases:
            result = extract_day_number(path)
            assert result == expected_day, f"Failed for {path}: expected {expected_day}, got {result}"
    
    def test_format_stats_table(self):
        """Test statistics table formatting."""
        from cli.utils import format_stats_table
        
        test_stats = {
            'total_collocations': 1234,
            'database_exists': True,
            'avg_review_count': 2.5,
            'min_day': 1,
            'max_day': 17
        }
        
        formatted = format_stats_table(test_stats)
        
        assert "SRS DATABASE STATISTICS" in formatted
        assert "1234" in formatted
        assert "True" in formatted
        assert "2.5" in formatted
        assert len(formatted.split('\n')) > 5  # Multiple lines