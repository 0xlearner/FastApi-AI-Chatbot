from typing import List, Union
import re
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import logging

# Download required NLTK data
try:
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)
    nltk.download("wordnet", quiet=True)
except Exception as e:
    logging.warning(f"Failed to download NLTK data: {str(e)}")

logger = logging.getLogger(__name__)


class TextProcessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words("english"))
        logger.info("TextProcessor initialized with NLTK resources")

    def preprocess_text(self, text: Union[str, List]) -> str:
        """Preprocess text for better matching"""
        logger.debug(f"Processing text input type: {type(text)}")

        # Handle list input (embedding vectors)
        if isinstance(text, list):
            logger.warning(
                "Received list instead of string, skipping text preprocessing"
            )
            return ""

        try:
            # Convert to lowercase
            processed = text.lower()
            logger.debug("Text converted to lowercase")

            # Remove special characters and digits
            processed = re.sub(r"[^a-zA-Z\s]", " ", processed)
            logger.debug("Removed special characters and digits")

            # Tokenize
            words = word_tokenize(processed)
            logger.debug(f"Tokenized into {len(words)} words")

            # Remove stop words and lemmatize
            processed_words = [
                self.lemmatizer.lemmatize(word)
                for word in words
                if word not in self.stop_words
            ]
            logger.debug(
                f"Processed to {len(processed_words)} words after stop word removal and lemmatization"
            )

            result = " ".join(processed_words)
            logger.debug(f"Final processed text length: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"Error in text preprocessing: {str(e)}")
            return ""

    def extract_keywords(self, text: Union[str, List]) -> List[str]:
        """Extract important keywords from text"""
        if isinstance(text, list):
            logger.warning("Received list instead of string for keyword extraction")
            return []

        try:
            processed_text = self.preprocess_text(text)
            keywords = processed_text.split()
            logger.debug(f"Extracted {len(keywords)} keywords")
            return keywords
        except Exception as e:
            logger.error(f"Error in keyword extraction: {str(e)}")
            return []
