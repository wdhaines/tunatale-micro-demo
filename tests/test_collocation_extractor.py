"""Tests for the CollocationExtractor class."""
import pytest
from unittest.mock import MagicMock, patch, call, mock_open
import spacy
import json
from pathlib import Path

from collocation_extractor import CollocationExtractor

# Sample test data
SAMPLE_TEXT = """
Carnivorous plants are fascinating organisms that have adapted to grow in nutrient-poor
environments by trapping and digesting insects and other small animals. The Venus flytrap
is one of the most well-known carnivorous plants, with its unique snap-trap mechanism.
Pitcher plants create pitfall traps in their modified leaves, while sundews use sticky
tentacles to capture their prey. These plants often grow in bogs and other areas with
poor soil conditions where they can't get enough nutrients from the ground.
"""

class TestCollocationExtractor:
    """Tests for the CollocationExtractor class."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Set up test environment with proper mocks."""
        # Create a temporary directory for test files
        self.temp_dir = tmp_path
        self.collocations_file = self.temp_dir / "collocations.json"
        
        # Create a real spaCy model for some tests
        self.real_nlp = spacy.load("en_core_web_sm")
        
        # Create a mock spaCy model for other tests
        self.mock_nlp = MagicMock()
        
        # Set up the mock document and sentence
        self.mock_doc = MagicMock()
        self.mock_sent = MagicMock()
        self.mock_doc.sents = [self.mock_sent]
        self.mock_doc.noun_chunks = []
        self.mock_doc.ents = []
        self.mock_nlp.return_value = self.mock_doc
        
        # Set up default mock sentence attributes
        self.mock_sent.__len__.return_value = 10
        self.mock_sent.text = ""
        
        # Set up default token
        self.mock_token = MagicMock()
        self.mock_token.text = "test"
        self.mock_token.lemma_ = "test"
        self.mock_token.pos_ = "NOUN"
        self.mock_token.dep_ = "ROOT"
        self.mock_token.children = []
        self.mock_sent.__iter__.return_value = [self.mock_token]
        
        # Patch the config and spacy.load
        with patch('collocation_extractor.COLLOCATIONS_PATH', self.collocations_file), \
             patch('spacy.load', return_value=self.mock_nlp):
            self.extractor = CollocationExtractor()
        
        # Create a real extractor for tests that need it
        with patch('collocation_extractor.COLLOCATIONS_PATH', self.collocations_file):
            self.real_extractor = CollocationExtractor()
            self.real_extractor.nlp = self.real_nlp
        
    def test_extract_collocations_basic(self):
        """Test basic collocation extraction."""
        # Use real extractor with actual text to avoid mock complexity
        text = "Carnivorous plants catch insects with specialized leaves."
        
        # Test with the real extractor
        result = self.real_extractor.extract_collocations(text)
        
        # Verify we got a result
        assert isinstance(result, dict)
        assert len(result) > 0, f"Expected at least one collocation, got {result}"
        
        # Check for expected patterns (case insensitive)
        result_lower = {k.lower(): v for k, v in result.items()}
        assert any('carnivorous plants' in k.lower() for k in result.keys()), \
            f"'carnivorous plants' not in {result}"
        assert any('catch insects' in k.lower() for k in result.keys()), \
            f"'catch insects' not in {result}"
        assert any('specialized leaves' in k.lower() for k in result.keys()), \
            f"'specialized leaves' not in {result}"
        
    def test_extract_collocations_noun_phrases(self):
        """Test extraction of noun phrases."""
        # Setup mock tokens
        the = MagicMock(text='the', pos_='DET')
        venus = MagicMock(text='Venus', pos_='PROPN')
        flytrap = MagicMock(text='flytrap', pos_='NOUN')
        is_ = MagicMock(text='is', pos_='AUX')
        a = MagicMock(text='a', pos_='DET')
        carnivorous = MagicMock(text='carnivorous', pos_='ADJ')
        plant = MagicMock(text='plant', pos_='NOUN')
        period = MagicMock(text='.', pos_='PUNCT')
        
        # Set up token relationships
        flytrap.children = [the, venus]
        plant.children = [a, carnivorous]
        
        # Configure mock sentence
        self.mock_sent.__iter__.return_value = [the, venus, flytrap, is_, a, carnivorous, plant, period]
        self.mock_sent.__len__.return_value = 8
        self.mock_sent.text = "The Venus flytrap is a carnivorous plant."
        
        # Mock noun chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.text = 'The Venus flytrap'
        mock_chunk2 = MagicMock()
        mock_chunk2.text = 'a carnivorous plant'
        self.mock_doc.noun_chunks = [mock_chunk1, mock_chunk2]
        
        # Test
        result = self.extractor.extract_collocations("The Venus flytrap is a carnivorous plant.")
        
        # Verify
        assert isinstance(result, dict)
        assert len(result) > 0, f"Expected noun phrase collocations, got {result}"
        
        # Check that our mock patterns were found (case insensitive)
        result_lower = {k.lower(): v for k, v in result.items()}
        assert any('venus flytrap' in k.lower() for k in result.keys()), \
            f"'venus flytrap' not in {result}"
        assert any('carnivorous plant' in k.lower() for k in result.keys()), \
            f"'carnivorous plant' not in {result}"
        
    def test_extract_collocations_verb_phrases(self):
        """Test extraction of verb phrases."""
        # Mock tokens for the sentence
        the = MagicMock(text='the', pos_='DET')
        plant = MagicMock(text='plant', pos_='NOUN', dep_='nsubj')
        catches = MagicMock(text='catches', lemma_='catch', pos_='VERB', dep_='ROOT')
        insects = MagicMock(text='insects', pos_='NOUN', dep_='dobj')
        and_ = MagicMock(text='and', pos_='CCONJ')
        digests = MagicMock(text='digests', lemma_='digest', pos_='VERB', dep_='conj')
        them = MagicMock(text='them', pos_='PRON', dep_='dobj')
        slowly = MagicMock(text='slowly', pos_='ADV', dep_='advmod')
        
        # Set up token relationships
        catches.children = [plant, insects, digests]
        digests.children = [them, slowly]
        
        # Configure the mock sentence
        self.mock_sent.__iter__.return_value = [the, plant, catches, insects, and_, digests, them, slowly]
        self.mock_sent.__len__.return_value = 8
        self.mock_sent.text = "The plant catches insects and digests them slowly."
        
        # Test
        result = self.extractor.extract_collocations("The plant catches insects and digests them slowly.")
        
        # Verify we got some results
        assert isinstance(result, dict)
        assert len(result) > 0, f"Expected verb collocations, got {result}"
        
    def test_extract_collocations_adjective_noun(self):
        """Test extraction of adjective-noun patterns."""
        # Setup mock sentence with tokens
        the = MagicMock(text='the', pos_='DET')
        sticky = MagicMock(text='sticky', lemma_='sticky', pos_='ADJ', dep_='amod')
        leaves = MagicMock(text='leaves', lemma_='leaf', pos_='NOUN', dep_='nsubj')
        trap = MagicMock(text='trap', lemma_='trap', pos_='VERB', dep_='ROOT')
        small = MagicMock(text='small', lemma_='small', pos_='ADJ', dep_='amod')
        insects = MagicMock(text='insects', lemma_='insect', pos_='NOUN', dep_='dobj')
        period = MagicMock(text='.', pos_='PUNCT')
        
        # Set up token relationships
        trap.children = [leaves, insects]
        leaves.children = [the, sticky]
        insects.children = [small]
        
        # Configure the mock sentence
        self.mock_sent.__iter__.return_value = [the, sticky, leaves, trap, small, insects, period]
        self.mock_sent.__len__.return_value = 7
        self.mock_sent.text = "The sticky leaves trap small insects."
        
        # Mock noun chunks
        sticky_leaves = MagicMock()
        sticky_leaves.text = 'sticky leaves'
        small_insects = MagicMock()
        small_insects.text = 'small insects'
        self.mock_doc.noun_chunks = [sticky_leaves, small_insects]
        
        # Test
        result = self.extractor.extract_collocations("The sticky leaves trap small insects.")
        
        # Verify we got a result
        assert isinstance(result, dict)
        assert len(result) > 0, f"Expected at least one collocation, got {result}"
        assert any('sticky leaves' in k.lower() for k in result.keys()), \
            f"'sticky leaves' not in {result}"
        assert any('small insects' in k.lower() for k in result.keys()), \
            f"'small insects' not in {result}"
        
        # Check that our mock patterns were found (case insensitive)
        result_lower = {k.lower(): v for k, v in result.items()}
        assert any("sticky leaves" in k.lower() for k in result.keys()), f"'sticky leaves' not in {result}"
        assert any("small insects" in k.lower() for k in result.keys()), f"'small insects' not in {result}"
        
    def test_extract_collocations_filters(self):
        """Test filtering of collocations."""
        # Mock tokens for the sentence
        i = MagicMock(text='i', pos_='PRON')
        like = MagicMock(text='like', pos_='VERB')
        my = MagicMock(text='my', pos_='PRON')
        plants = MagicMock(text='plants', pos_='NOUN')
        period = MagicMock(text='.', pos_='PUNCT')
        
        # Set up token relationships
        like.children = [i, my, plants]
        
        # Configure the mock sentence
        self.mock_sent = MagicMock()
        self.mock_sent.__iter__.return_value = [i, like, my, plants, period]
        self.mock_sent.__len__.return_value = 5
        
        # Mock noun chunks that should be filtered
        mock_chunk = MagicMock()
        mock_chunk.text = 'my plants'
        self.mock_doc.noun_chunks = [mock_chunk]
        
        # Test
        result = self.extractor.extract_collocations("I like my plants.")
        
        # Verify
        assert isinstance(result, dict)
        
        # Check that personal pronouns are filtered out
        assert not any(pronoun in k.lower() for k in result.keys() for pronoun in ['i', 'me', 'my']), \
            f"Personal pronouns should be filtered out, but found in {result}"
            
        # Check that very short phrases are filtered out
        assert not any(len(phrase.split()) < 2 for phrase in result.keys()), \
            f"Very short phrases should be filtered out, but found in {result}"
            
    def test_extract_from_curriculum(self, tmp_path):
        """Test extraction from curriculum file."""
        # Setup
        curriculum_data = {
            "content": "Carnivorous plants are amazing. They catch insects with their leaves.",
            "other_field": "value"
        }
        
        # Mock file operations
        with patch('builtins.open', mock_open(read_data=json.dumps(curriculum_data))), \
             patch('pathlib.Path.exists', return_value=True):
            
            # Mock the extract_collocations method
            with patch.object(self.extractor, 'extract_collocations', 
                           return_value={"carnivorous plants": 1, "catch insects": 1}) as mock_extract:
                
                # Test
                result = self.extractor.extract_from_curriculum()
                
                # Verify
                mock_extract.assert_called_once_with(curriculum_data['content'])
                assert result == {"carnivorous plants": 1, "catch insects": 1}
                
    def test_save_and_get_collocations(self, tmp_path):
        """Test saving and retrieving collocations."""
        # Setup
        collocations = {"carnivorous plants": 3, "venus flytrap": 2, "pitcher plant": 1}
        mock_file = mock_open()
        
        # Mock file operations
        with patch('builtins.open', mock_file), \
             patch('pathlib.Path.exists', return_value=True):
            
            # Test save
            self.extractor._save_collocations(collocations)
            
            # Test get_top_collocations
            with patch('builtins.open', mock_open(read_data=json.dumps(collocations))):
                top = self.extractor.get_top_collocations(2)
                assert top == [("carnivorous plants", 3), ("venus flytrap", 2)]
        
        # Verify file was written correctly
        file_handle = mock_file()
        file_handle.write.assert_called()
        
    def test_handles_loading_error(self):
        """Test handling of spacy model loading error."""
        # Setup - make spacy.load raise an OSError
        with patch('spacy.load', side_effect=OSError("Model not found")):
            with pytest.raises(ImportError) as excinfo:
                CollocationExtractor()
            assert "English language model not found" in str(excinfo.value)
            
    def test_analyze_vocabulary_distribution_saves_collocations(self, tmp_path):
        """Test that analyze_vocabulary_distribution saves collocations to file."""
        # Setup
        test_text = "Carnivorous plants catch insects with specialized leaves."
        expected_collocations = {
            "carnivorous plants": 1,
            "catch insects": 1,
            "specialized leaves": 1
        }
        
        # Create a temporary collocations file path
        collocations_file = tmp_path / "test_collocations.json"
        
        # Mock the extract_collocations method and patch COLLOCATIONS_PATH
        with patch('collocation_extractor.COLLOCATIONS_PATH', collocations_file), \
             patch.object(self.real_extractor, 'extract_collocations', 
                         return_value=expected_collocations) as mock_extract:
            
            # Call the method we're testing
            result = self.real_extractor.analyze_vocabulary_distribution(test_text)
            
            # Verify extract_collocations was called with the right arguments
            mock_extract.assert_called_once_with(test_text, min_words=1, max_words=4, debug=False)
            
            # Verify the result contains our collocations
            assert 'collocations' in result
            assert result['collocations'] == expected_collocations
            
            # Verify the collocations were saved to file
            assert collocations_file.exists(), f"Collocations file was not created at {collocations_file}"
            
            # Read the saved collocations
            with open(collocations_file, 'r') as f:
                saved_collocations = json.load(f)
                
            # Verify the saved collocations match what we expect
            assert saved_collocations == expected_collocations, \
                f"Expected {expected_collocations}, got {saved_collocations}"
                
            # Verify the file was written with proper JSON formatting
            with open(collocations_file, 'r') as f:
                content = f.read()
                json.loads(content)  # This will raise an exception if not valid JSON
