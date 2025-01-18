# utils/search.py
from collections import Counter
import re

class BibleSearchEngine:
    def __init__(self):
        self.stop_words = {'the', 'and', 'of', 'to', 'in', 'a', 'that', 'for', 'is', 'was'}
    
    def tokenize(self, text):
        """Convert text to lowercase and split into words"""
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if w not in self.stop_words]
    
    def calculate_similarity(self, query_tokens, verse_tokens):
        """Calculate simple similarity score between query and verse"""
        if not query_tokens or not verse_tokens:
            return 0
            
        query_counter = Counter(query_tokens)
        verse_counter = Counter(verse_tokens)
        
        # Calculate overlap
        common_words = sum((query_counter & verse_counter).values())
        total_words = sum(query_counter.values())
        
        return common_words / total_words if total_words > 0 else 0
    
    def text_search(self, query, limit=10):
        """Perform text search with basic relevance scoring"""
        from database import get_db_connection
        
        query_tokens = self.tokenize(query)
        results = []
        
        conn = get_db_connection()
        try:
            # Get verses that contain any of the query words
            like_conditions = ' OR '.join(['text LIKE ?' for _ in query_tokens])
            params = [f'%{token}%' for token in query_tokens]
            
            verses = conn.execute(f'''
                SELECT v.*, b.name as book_name
                FROM verses v
                JOIN books b ON v.book_id = b.id
                WHERE {like_conditions}
            ''', params).fetchall()
            
            # Score each verse
            for verse in verses:
                verse_tokens = self.tokenize(verse['text'])
                score = self.calculate_similarity(query_tokens, verse_tokens)
                if score > 0:
                    verse_dict = dict(verse)
                    verse_dict['score'] = score
                    results.append(verse_dict)
            
            # Sort by score and return top results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:limit]
            
        finally:
            conn.close()
    
    def search(self, query, limit=10):
        """Main search method"""
        return self.text_search(query, limit)