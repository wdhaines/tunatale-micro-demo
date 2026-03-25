#!/usr/bin/env python3
"""
Frequency updater for SRS integration with story generation.

This module provides functionality to update collocation frequencies
after new stories are generated and mark newly frequent items for translation.
"""

from typing import List, Dict, Set, Tuple
from collections import Counter
from pathlib import Path

from srs_database import SRSDatabase
from story_collocation_extractor import StoryCollocationExtractor


def extract_filipino_dialogue(content: str) -> str:
    """Extract only Filipino dialogue from story content, excluding voice tags."""
    lines = content.split('\n')
    
    # Find Natural Speed section
    natural_start = -1
    slow_start = -1
    
    for i, line in enumerate(lines):
        if "[NARRATOR]: Natural Speed" in line:
            natural_start = i
        elif "[NARRATOR]: Slow Speed" in line:
            slow_start = i
            break
    
    if natural_start == -1:
        return ""
    
    # Extract content between Natural Speed and Slow Speed
    end_line = slow_start if slow_start != -1 else len(lines)
    natural_lines = lines[natural_start + 1:end_line]
    
    # Extract only Filipino dialogue (lines starting with [TAGALOG-*]:)
    filipino_sentences = []
    for line in natural_lines:
        line = line.strip()
        if line.startswith('[TAGALOG-') and ']:' in line:
            # Extract the Filipino text after the voice tag
            filipino_text = line.split(']: ', 1)[1].strip()
            if filipino_text:
                filipino_sentences.append(filipino_text)
    
    return ' '.join(filipino_sentences)


class FrequencyUpdater:
    """Updates SRS collocation frequencies after story generation."""
    
    def __init__(self):
        """Initialize the frequency updater."""
        self.srs_db = SRSDatabase()
        self.extractor = StoryCollocationExtractor()
    
    def update_frequencies_after_story_generation(self, new_story_path: str, verbose: bool = True) -> Dict[str, int]:
        """Update frequencies after a new story is generated.
        
        Args:
            new_story_path: Path to the newly generated story file
            verbose: Whether to print progress information
            
        Returns:
            Dictionary with update statistics
        """
        if verbose:
            print("🔄 Updating collocation frequencies after story generation...")
        
        # Recalculate frequencies across entire corpus including new story
        corpus_frequencies = self._calculate_corpus_frequencies(verbose)
        
        # Update all SRS collocations with new frequencies
        stats = self._update_srs_frequencies(corpus_frequencies, verbose)
        
        return stats
    
    def get_newly_frequent_collocations(self, previous_ready_count: int) -> List[str]:
        """Get collocations that became ready for translation after frequency update.
        
        Args:
            previous_ready_count: Number of ready collocations before update
            
        Returns:
            List of newly frequent collocation texts
        """
        # Get current ready collocations
        ready_collocations = self.srs_db.get_collocations_ready_for_translation()
        current_ready_count = len(ready_collocations)
        
        if current_ready_count > previous_ready_count:
            # Sort by frequency (descending) and return the newly added ones
            ready_collocations.sort(key=lambda x: x['corpus_frequency'], reverse=True)
            newly_frequent = ready_collocations[previous_ready_count:]
            return [colloc['text'] for colloc in newly_frequent]
        
        return []
    
    def _calculate_corpus_frequencies(self, verbose: bool = True) -> Counter:
        """Calculate frequencies across entire story corpus."""
        if verbose:
            print("  📊 Recalculating frequencies across entire corpus...")
        
        # Get all story files
        stories_dir = Path("instance/data/stories")
        if not stories_dir.exists():
            return Counter()
        
        story_files = list(stories_dir.glob("*.txt"))
        all_collocations_counter = Counter()
        
        for story_file in story_files:
            try:
                with open(story_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                filipino_dialogue = extract_filipino_dialogue(content)
                if filipino_dialogue:
                    collocations_dict = self.extractor.extract_collocations(filipino_dialogue)
                    all_collocations_counter.update(collocations_dict)
            
            except Exception as e:
                if verbose:
                    print(f"    ⚠️ Error processing {story_file.name}: {e}")
                continue
        
        return all_collocations_counter
    
    def _update_srs_frequencies(self, corpus_frequencies: Counter, verbose: bool = True) -> Dict[str, int]:
        """Update SRS database with new frequency counts."""
        if verbose:
            print("  🗃️ Updating SRS database frequencies...")
        
        # Get current SRS collocations
        srs_collocations = self.srs_db.get_all_collocations()
        
        # Track statistics
        stats = {
            'total_collocations': len(srs_collocations),
            'updated_count': 0,
            'newly_frequent_count': 0,
            'previous_ready_count': 0,
            'current_ready_count': 0
        }
        
        # Count collocations that were ready before update
        stats['previous_ready_count'] = len(self.srs_db.get_collocations_ready_for_translation())
        
        # Update frequency for each SRS collocation
        for collocation in srs_collocations:
            text = collocation['text']
            old_frequency = collocation.get('corpus_frequency', 0)
            new_frequency = corpus_frequencies.get(text, 0)
            
            if self.srs_db.update_corpus_frequency(text, new_frequency):
                stats['updated_count'] += 1
                
                # Check if this became newly frequent
                if old_frequency < 3 and new_frequency >= 3:
                    stats['newly_frequent_count'] += 1
        
        # Count collocations ready after update
        stats['current_ready_count'] = len(self.srs_db.get_collocations_ready_for_translation())
        
        if verbose:
            print(f"    ✅ Updated {stats['updated_count']:,} collocations")
            print(f"    🎯 {stats['newly_frequent_count']:,} collocations became ready for translation")
            print(f"    📈 Ready for translation: {stats['previous_ready_count']:,} → {stats['current_ready_count']:,}")
        
        return stats