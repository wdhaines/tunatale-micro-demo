"""
Tests for data validation and cleanup issues identified in CLAUDE.md.

This test suite focuses on the critical data quality problems that need to be 
addressed before implementing the "Go Wider vs Go Deeper" framework:

1. Collocation data quality issues (embedded syllables)
2. SRS tracking logic problems (returns voice tags)
3. Format inconsistencies between dict/list structures
4. Data validation for the refactor
"""

import json
import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from srs_tracker import SRSTracker, CollocationStatus
from collocation_extractor import CollocationExtractor
from curriculum_models import Curriculum, CurriculumDay


class TestCollocationDataQuality:
    """Test suite for identifying and validating collocation data quality issues."""
    
    def test_detect_embedded_syllables_in_collocations(self):
        """Test detection of embedded syllable data in collocations (CLAUDE.md Issue 1.1)."""
        # Example of corrupted collocation data mentioned in CLAUDE.md
        corrupted_collocation = "ito po\\npo\\nito\\nto\\ni\\nito\\nito po\\nito po"
        
        # This function should detect embedded syllable patterns
        def has_embedded_syllables(text: str) -> bool:
            """Detect if collocation text contains embedded syllable breakdowns."""
            # Look for patterns indicating syllable breakdowns
            lines = text.split('\\n')
            if len(lines) > 1:
                # Check if we have repeated partial words
                first_line = lines[0].strip()
                for line in lines[1:]:
                    line = line.strip()
                    if line and line in first_line and line != first_line:
                        return True
            return False
        
        assert has_embedded_syllables(corrupted_collocation), "Should detect embedded syllables"
        
        # Valid collocations should not trigger false positives
        valid_collocations = [
            "kumusta po",
            "salamat po",
            "paano po kayo",
            "magandang umaga"
        ]
        
        for collocation in valid_collocations:
            assert not has_embedded_syllables(collocation), f"'{collocation}' should be valid"
    
    def test_clean_collocation_data(self):
        """Test cleaning of corrupted collocation data."""
        corrupted_data = {
            "ito po\\npo\\nito\\nto\\ni\\nito\\nito po\\nito po": 3,
            "kumusta po\\npo\\nkumusta\\nkum\\nkumusta po": 2,
            "salamat po": 5,  # Clean data should remain unchanged
            "magandang umaga": 4
        }
        
        def clean_collocation_data(data: Dict[str, int]) -> Dict[str, int]:
            """Clean collocation data by removing embedded syllables."""
            cleaned = {}
            for colloc, count in data.items():
                if '\\n' in colloc:
                    # Extract the main phrase (first line)
                    main_phrase = colloc.split('\\n')[0].strip()
                    if main_phrase:
                        cleaned[main_phrase] = count
                else:
                    cleaned[colloc] = count
            return cleaned
        
        cleaned_data = clean_collocation_data(corrupted_data)
        
        # Should extract main phrases from corrupted entries
        assert "ito po" in cleaned_data
        assert "kumusta po" in cleaned_data
        
        # Clean data should remain unchanged
        assert "salamat po" in cleaned_data
        assert "magandang umaga" in cleaned_data
        
        # Corrupted entries should be removed
        assert "ito po\\npo\\nito\\nto\\ni\\nito\\nito po\\nito po" not in cleaned_data
        assert "kumusta po\\npo\\nkumusta\\nkum\\nkumusta po" not in cleaned_data
        
        # Values should be preserved
        assert cleaned_data["ito po"] == 3
        assert cleaned_data["salamat po"] == 5
    
    def test_collocation_validation_rules(self):
        """Test validation rules for collocation data quality."""
        def validate_collocation(text: str) -> List[str]:
            """Validate a collocation and return list of issues found."""
            issues = []
            
            if not text or not text.strip():
                issues.append("Empty collocation")
                return issues
            
            # Check for embedded syllables
            if '\\n' in text:
                issues.append("Contains embedded syllables")
            
            # Check for excessive repetition
            words = text.split()
            if len(words) != len(set(words)) and len(words) > 2:
                issues.append("Contains repeated words")
            
            # Check for non-linguistic content
            if any(char.isdigit() for char in text):
                issues.append("Contains digits")
            
            # Check for voice tags (mentioned in CLAUDE.md Issue 1.2)
            voice_tags = ["tagalog-female-1", "tagalog-male-1", "english-1"]
            if any(tag in text.lower() for tag in voice_tags):
                issues.append("Contains voice tags")
            
            return issues
        
        # Test cases based on CLAUDE.md issues
        test_cases = [
            ("ito po\\npo\\nito\\nto\\ni\\nito\\nito po\\nito po", ["Contains embedded syllables"]),
            ("mango shake, they, the waiter, asks, tagalog-female-1", ["Contains voice tags"]),
            ("kumusta po", []),  # Valid
            ("salamat salamat salamat po", ["Contains repeated words"]),
            ("", ["Empty collocation"]),
            ("Day 1 lesson", ["Contains digits"])
        ]
        
        for collocation, expected_issues in test_cases:
            issues = validate_collocation(collocation)
            for expected_issue in expected_issues:
                assert expected_issue in issues, f"'{collocation}' should have issue: {expected_issue}"


class TestSRSTrackingLogic:
    """Test suite for SRS tracking logic problems (CLAUDE.md Issue 1.2)."""
    
    @pytest.fixture
    def srs_tracker(self, tmp_path):
        """Create SRS tracker with test data."""
        srs_dir = tmp_path / 'srs_test'
        srs_dir.mkdir(exist_ok=True)
        tracker = SRSTracker(data_dir=str(srs_dir), filename='test_srs.json')
        
        # Add valid collocations
        valid_collocations = ["kumusta po", "salamat po", "paano po"]
        tracker.add_collocations(valid_collocations, day=1)
        
        return tracker
    
    def test_srs_returns_valid_phrases_only(self, srs_tracker):
        """Test that SRS returns only valid collocation phrases, not voice tags."""
        due_collocations = srs_tracker.get_due_collocations(day=1)
        
        # Verify all returned items are valid phrases
        voice_tags = ["tagalog-female-1", "tagalog-male-1", "english-1"]
        for colloc in due_collocations:
            assert isinstance(colloc, str), "Collocation should be string"
            assert colloc.strip(), "Collocation should not be empty"
            assert not any(tag in colloc.lower() for tag in voice_tags), \
                f"Collocation '{colloc}' contains voice tag"
    
    def test_srs_collocation_extraction_integrity(self, srs_tracker):
        """Test that SRS properly extracts and stores only linguistic content."""
        # Simulate story content with mixed data
        story_content = """
        Maria went to the palengke to buy vegetables.
        "Kumusta po kayo?" she greeted the vendor.
        The vendor smiled and said "Salamat po!"
        [Voice: tagalog-female-1] plays audio
        """
        
        # Mock collocation extractor that might return mixed data
        mixed_collocations = [
            "kumusta po kayo",
            "salamat po", 
            "tagalog-female-1",  # This should be filtered out
            "palengke"
        ]
        
        def filter_valid_collocations(collocations: List[str]) -> List[str]:
            """Filter out non-linguistic content from collocations."""
            valid = []
            voice_tags = ["tagalog-female-1", "tagalog-male-1", "english-1"]
            
            for colloc in collocations:
                if not any(tag in colloc.lower() for tag in voice_tags):
                    if colloc.strip() and not colloc.isdigit():
                        valid.append(colloc.strip())
            
            return valid
        
        filtered_collocations = filter_valid_collocations(mixed_collocations)
        
        # Voice tags should be filtered out
        assert "tagalog-female-1" not in filtered_collocations
        
        # Valid linguistic content should remain
        assert "kumusta po kayo" in filtered_collocations
        assert "salamat po" in filtered_collocations
        assert "palengke" in filtered_collocations
        
        # Add filtered collocations to SRS
        srs_tracker.add_collocations(filtered_collocations, day=2)
        
        # Verify SRS contains only valid content
        all_collocations = srs_tracker.get_all_collocations()
        voice_tags = ["tagalog-female-1", "tagalog-male-1", "english-1"]
        for colloc in all_collocations:
            assert not any(tag in colloc.lower() for tag in voice_tags), \
                f"SRS contains invalid voice tag: {colloc}"
    
    def test_srs_review_logic_validation(self, srs_tracker):
        """Test that SRS review logic produces sensible results."""
        # Add collocations with different review states
        day1_collocations = ["kumusta po", "salamat po"]
        day3_collocations = ["paano po", "saan po"]
        
        srs_tracker.add_collocations(day1_collocations, day=1)
        srs_tracker.add_collocations(day3_collocations, day=3)
        
        # Review some collocations to update their status
        srs_tracker.add_collocations(["kumusta po"], day=2)  # Review on day 2
        
        # Get due collocations for day 3
        due_on_day3 = srs_tracker.get_due_collocations(day=3)
        
        # Verify results make linguistic sense
        for colloc in due_on_day3:
            assert colloc in srs_tracker.get_all_collocations(), \
                f"'{colloc}' should exist in SRS"
            
            colloc_status = srs_tracker.collocations[colloc]
            assert colloc_status.next_review_day <= 3, \
                f"'{colloc}' should be due by day 3"
            
            # Verify no nonsensical content like the CLAUDE.md example
            invalid_patterns = ["**mango shake, they, the waiter, asks, tagalog-female-1"]
            assert not any(pattern in colloc for pattern in invalid_patterns), \
                f"'{colloc}' contains nonsensical content"


class TestCurriculumFormatConsistency:
    """Test suite for curriculum format consistency issues (CLAUDE.md Issue 1.3)."""
    
    def test_curriculum_format_standardization(self):
        """Test standardization between dict and list-based curriculum formats."""
        # Example of dict-based format (inconsistent)
        dict_based_curriculum = {
            "learning_objective": "Learn Filipino basics",
            "target_language": "Filipino",
            "learner_level": "A2",
            "presentation_length": 30,
            "days": {
                "day_1": {
                    "day": 1,
                    "title": "Greetings",
                    "focus": "Basic greetings",
                    "collocations": ["kumusta po"],
                    "presentation_phrases": ["hello"],
                    "learning_objective": "Greet people"
                }
            }
        }
        
        # Example of list-based format (consistent with CurriculumDay dataclass)
        list_based_curriculum = {
            "learning_objective": "Learn Filipino basics",
            "target_language": "Filipino",
            "learner_level": "A2",
            "presentation_length": 30,
            "days": [
                {
                    "day": 1,
                    "title": "Greetings",
                    "focus": "Basic greetings",
                    "collocations": ["kumusta po"],
                    "presentation_phrases": ["hello"],
                    "learning_objective": "Greet people",
                    "story_guidance": ""
                }
            ]
        }
        
        def normalize_curriculum_format(curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
            """Convert curriculum to standardized list-based format."""
            normalized = curriculum_data.copy()
            
            if isinstance(curriculum_data.get("days"), dict):
                # Convert dict-based days to list-based
                days_list = []
                for day_key, day_data in curriculum_data["days"].items():
                    # Ensure story_guidance field exists
                    if "story_guidance" not in day_data:
                        day_data["story_guidance"] = ""
                    days_list.append(day_data)
                
                # Sort by day number to maintain order
                days_list.sort(key=lambda x: x.get("day", 0))
                normalized["days"] = days_list
            
            return normalized
        
        # Test normalization
        normalized_dict = normalize_curriculum_format(dict_based_curriculum)
        
        # Should have list-based days format
        assert isinstance(normalized_dict["days"], list)
        assert len(normalized_dict["days"]) == 1
        assert normalized_dict["days"][0]["day"] == 1
        assert "story_guidance" in normalized_dict["days"][0]
        
        # Should be able to create Curriculum object from normalized data
        curriculum = Curriculum.from_dict(normalized_dict)
        assert len(curriculum.days) == 1
        assert curriculum.days[0].day == 1
        assert curriculum.days[0].title == "Greetings"
    
    def test_curriculum_validation_consistency(self):
        """Test that curriculum validation catches format inconsistencies."""
        def validate_curriculum_format(data: Dict[str, Any]) -> List[str]:
            """Validate curriculum format and return list of issues."""
            issues = []
            
            # Check required top-level fields
            required_fields = ["learning_objective", "target_language", "learner_level", 
                             "presentation_length", "days"]
            for field in required_fields:
                if field not in data:
                    issues.append(f"Missing required field: {field}")
            
            # Check days format consistency
            if "days" in data:
                days = data["days"]
                if isinstance(days, dict):
                    issues.append("Days should be list format, not dict")
                elif isinstance(days, list):
                    # Validate each day has required fields
                    required_day_fields = ["day", "title", "focus", "collocations", 
                                         "presentation_phrases", "learning_objective"]
                    for i, day in enumerate(days):
                        if not isinstance(day, dict):
                            issues.append(f"Day {i+1} is not a dictionary")
                            continue
                        
                        for field in required_day_fields:
                            if field not in day:
                                issues.append(f"Day {i+1} missing field: {field}")
                        
                        # story_guidance should have default value
                        if "story_guidance" not in day:
                            issues.append(f"Day {i+1} missing story_guidance field")
            
            return issues
        
        # Test valid format
        valid_curriculum = {
            "learning_objective": "Test",
            "target_language": "Filipino",
            "learner_level": "A2",
            "presentation_length": 30,
            "days": [{
                "day": 1,
                "title": "Test Day",
                "focus": "Testing",
                "collocations": [],
                "presentation_phrases": [],
                "learning_objective": "Test",
                "story_guidance": ""
            }]
        }
        
        issues = validate_curriculum_format(valid_curriculum)
        assert len(issues) == 0, f"Valid curriculum should have no issues: {issues}"
        
        # Test invalid format (dict-based days)
        invalid_curriculum = {
            "learning_objective": "Test",
            "target_language": "Filipino",
            "learner_level": "A2",
            "presentation_length": 30,
            "days": {
                "day_1": {
                    "day": 1,
                    "title": "Test Day"
                    # Missing required fields
                }
            }
        }
        
        issues = validate_curriculum_format(invalid_curriculum)
        assert "Days should be list format, not dict" in issues


class TestDataValidationIntegration:
    """Integration tests for data validation across the system."""
    
    def test_end_to_end_data_quality_validation(self, tmp_path):
        """Test comprehensive data quality validation across curriculum, SRS, and collocations."""
        # Create test curriculum with mixed data quality
        curriculum_data = {
            "learning_objective": "Test comprehensive validation",
            "target_language": "Filipino",
            "learner_level": "A2",
            "presentation_length": 30,
            "days": [
                {
                    "day": 1,
                    "title": "Mixed Quality Data Test",
                    "focus": "Data validation",
                    "collocations": [
                        "kumusta po",  # Valid
                        "ito po\\npo\\nito\\nto\\ni\\nito\\nito po\\nito po",  # Corrupted
                        "salamat po"   # Valid
                    ],
                    "presentation_phrases": [
                        "good morning",  # Valid
                        "tagalog-female-1"  # Invalid voice tag
                    ],
                    "learning_objective": "Test data validation",
                    "story_guidance": ""
                }
            ]
        }
        
        def comprehensive_data_validation(curriculum_data: Dict[str, Any]) -> Dict[str, List[str]]:
            """Perform comprehensive data validation and return categorized issues."""
            issues = {
                "format_issues": [],
                "collocation_issues": [],
                "content_issues": []
            }
            
            # Format validation
            if isinstance(curriculum_data.get("days"), dict):
                issues["format_issues"].append("Days format should be list, not dict")
            
            # Content validation
            if "days" in curriculum_data and isinstance(curriculum_data["days"], list):
                for day_idx, day in enumerate(curriculum_data["days"]):
                    day_num = day_idx + 1
                    
                    # Validate collocations
                    if "collocations" in day:
                        for colloc in day["collocations"]:
                            if '\\n' in colloc:
                                issues["collocation_issues"].append(
                                    f"Day {day_num}: Collocation '{colloc[:20]}...' contains embedded syllables"
                                )
                    
                    # Validate presentation phrases
                    if "presentation_phrases" in day:
                        voice_tags = ["tagalog-female-1", "tagalog-male-1", "english-1"]
                        for phrase in day["presentation_phrases"]:
                            if any(tag in phrase.lower() for tag in voice_tags):
                                issues["content_issues"].append(
                                    f"Day {day_num}: Presentation phrase contains voice tag: '{phrase}'"
                                )
            
            return issues
        
        # Run comprehensive validation
        validation_results = comprehensive_data_validation(curriculum_data)
        
        # Should detect collocation issues
        assert len(validation_results["collocation_issues"]) > 0
        assert any("embedded syllables" in issue for issue in validation_results["collocation_issues"])
        
        # Should detect content issues
        assert len(validation_results["content_issues"]) > 0
        assert any("voice tag" in issue for issue in validation_results["content_issues"])
        
        # Test cleanup functionality
        def cleanup_curriculum_data(curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
            """Clean up curriculum data based on validation results."""
            cleaned = curriculum_data.copy()
            
            if "days" in cleaned and isinstance(cleaned["days"], list):
                for day in cleaned["days"]:
                    # Clean collocations
                    if "collocations" in day:
                        clean_collocations = []
                        for colloc in day["collocations"]:
                            if '\\n' in colloc:
                                # Extract main phrase
                                main_phrase = colloc.split('\\n')[0].strip()
                                if main_phrase:
                                    clean_collocations.append(main_phrase)
                            else:
                                clean_collocations.append(colloc)
                        day["collocations"] = clean_collocations
                    
                    # Clean presentation phrases
                    if "presentation_phrases" in day:
                        voice_tags = ["tagalog-female-1", "tagalog-male-1", "english-1"]
                        clean_phrases = [
                            phrase for phrase in day["presentation_phrases"]
                            if not any(tag in phrase.lower() for tag in voice_tags)
                        ]
                        day["presentation_phrases"] = clean_phrases
            
            return cleaned
        
        # Clean the data
        cleaned_curriculum = cleanup_curriculum_data(curriculum_data)
        
        # Re-validate after cleanup
        post_cleanup_results = comprehensive_data_validation(cleaned_curriculum)
        
        # Should have fewer issues after cleanup
        assert len(post_cleanup_results["collocation_issues"]) == 0
        assert len(post_cleanup_results["content_issues"]) == 0
        
        # Verify clean data integrity
        day_1 = cleaned_curriculum["days"][0]
        assert "ito po" in day_1["collocations"]  # Cleaned from embedded syllables
        assert "kumusta po" in day_1["collocations"]  # Valid data preserved
        assert "tagalog-female-1" not in day_1["presentation_phrases"]  # Voice tag removed
        assert "good morning" in day_1["presentation_phrases"]  # Valid content preserved
    
    def test_migration_script_validation(self, tmp_path):
        """Test validation for migration scripts mentioned in CLAUDE.md."""
        # Create sample files that would need migration
        old_format_file = tmp_path / "old_curriculum.json"
        
        # Old dict-based format
        old_format_data = {
            "learning_objective": "Test migration",
            "target_language": "Filipino", 
            "learner_level": "A2",
            "presentation_length": 30,
            "days": {
                "day_1": {
                    "day": 1,
                    "title": "Test",
                    "focus": "Testing",
                    "collocations": ["test\\ntest\\ntest"],  # Needs cleanup
                    "presentation_phrases": ["hello", "tagalog-male-1"],  # Needs cleanup
                    "learning_objective": "Test"
                    # Missing story_guidance
                }
            }
        }
        
        with open(old_format_file, 'w') as f:
            json.dump(old_format_data, f)
        
        def migrate_curriculum_file(file_path: Path) -> Dict[str, Any]:
            """Migrate curriculum file to new standardized format."""
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Normalize format
            if isinstance(data.get("days"), dict):
                days_list = []
                for day_key, day_data in data["days"].items():
                    # Add missing fields
                    if "story_guidance" not in day_data:
                        day_data["story_guidance"] = ""
                    
                    # Clean collocations
                    if "collocations" in day_data:
                        clean_collocations = []
                        for colloc in day_data["collocations"]:
                            if '\\n' in colloc:
                                main_phrase = colloc.split('\\n')[0].strip()
                                if main_phrase:
                                    clean_collocations.append(main_phrase)
                            else:
                                clean_collocations.append(colloc)
                        day_data["collocations"] = clean_collocations
                    
                    # Clean presentation phrases
                    if "presentation_phrases" in day_data:
                        voice_tags = ["tagalog-female-1", "tagalog-male-1", "english-1"]
                        clean_phrases = [
                            phrase for phrase in day_data["presentation_phrases"]
                            if not any(tag in phrase.lower() for tag in voice_tags)
                        ]
                        day_data["presentation_phrases"] = clean_phrases
                    
                    days_list.append(day_data)
                
                days_list.sort(key=lambda x: x.get("day", 0))
                data["days"] = days_list
            
            return data
        
        # Test migration
        migrated_data = migrate_curriculum_file(old_format_file)
        
        # Verify migration results
        assert isinstance(migrated_data["days"], list), "Should convert to list format"
        assert len(migrated_data["days"]) == 1
        
        day_1 = migrated_data["days"][0]
        assert "story_guidance" in day_1, "Should add missing story_guidance field"
        assert day_1["story_guidance"] == "", "Should have empty default value"
        
        # Should clean collocations
        assert "test" in day_1["collocations"], "Should extract main phrase from embedded syllables"
        assert "test\\ntest\\ntest" not in day_1["collocations"], "Should remove corrupted data"
        
        # Should clean presentation phrases
        assert "hello" in day_1["presentation_phrases"], "Should preserve valid content"
        assert "tagalog-male-1" not in day_1["presentation_phrases"], "Should remove voice tags"
        
        # Should be able to create valid Curriculum object
        curriculum = Curriculum.from_dict(migrated_data)
        assert curriculum is not None
        assert len(curriculum.days) == 1