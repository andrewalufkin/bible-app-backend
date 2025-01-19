# utils/search.py
from collections import Counter
import re
from models.bible import BibleVerse

class BibleSearchEngine:
    def __init__(self):
        self.stop_words = {'the', 'and', 'of', 'to', 'in', 'a', 'that', 'for', 'is', 'was'}
    
    def tokenize(self, text):
        """Convert text to lowercase and split into words"""
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if w not in self.stop_words]
    
    def calculate_similarity(self, query_tokens, verse_tokens, exact_phrase=None):
        """Calculate similarity score between query and verse"""
        if not query_tokens or not verse_tokens:
            return 0
            
        # If there's an exact phrase, check if it exists in the verse
        if exact_phrase:
            verse_text = ' '.join(verse_tokens)
            if exact_phrase.lower() in verse_text:
                return 1.0  # Give highest score for exact matches
            
        query_counter = Counter(query_tokens)
        verse_counter = Counter(verse_tokens)
        
        # Calculate overlap
        common_words = sum((query_counter & verse_counter).values())
        total_words = sum(query_counter.values())
        
        return common_words / total_words if total_words > 0 else 0
    
    def text_search(self, query, limit=10):
        """Perform text search with support for exact phrases"""
        # Clean the query
        query = query.strip()
        exact_phrase = query.lower() if ' ' in query else None
        query_tokens = self.tokenize(query)
        results = []
        
        try:
            # First, try exact phrase matching
            if exact_phrase:
                # Use MongoDB's text search capabilities
                exact_matches = BibleVerse.objects(text__icontains=exact_phrase)
                
                for verse in exact_matches:
                    results.append({
                        'id': str(verse.id),
                        'book_name': verse.book_name,
                        'chapter': verse.chapter,
                        'verse': verse.verse,
                        'text': verse.text,
                        'score': 1.0  # Highest score for exact matches
                    })

            # If we don't have enough results, try word-based matching
            if len(results) < limit:
                # Create OR conditions for each token
                word_conditions = []
                for token in query_tokens:
                    word_conditions.append({'text__icontains': token})
                
                if word_conditions:
                    word_matches = BibleVerse.objects(__raw__={'$or': word_conditions})
                    
                    # Score each verse
                    for verse in word_matches:
                        # Skip if we already have this verse from exact matching
                        if any(r['id'] == str(verse.id) for r in results):
                            continue
                            
                        verse_tokens = self.tokenize(verse.text)
                        score = self.calculate_similarity(query_tokens, verse_tokens, exact_phrase)
                        
                        if score > 0:
                            results.append({
                                'id': str(verse.id),
                                'book_name': verse.book_name,
                                'chapter': verse.chapter,
                                'verse': verse.verse,
                                'text': verse.text,
                                'score': score
                            })
            
            # Sort by score and return top results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []
    
    def search(self, query, limit=10):
        """Main search method"""
        return self.text_search(query, limit)