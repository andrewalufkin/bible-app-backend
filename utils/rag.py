# backend/utils/rag.py
import requests
import torch
import os
import json
import time
import random
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Optional

# Load environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Load the sentence transformer model (this will be cached after first load)
def get_embedding_model():
    try:
        return SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        print(f"Error loading embedding model: {e}")
        return None

def call_anthropic_api(messages, max_tokens=1024, temperature=0.7, max_retries=3):
    """Call the Anthropic Claude API with retry mechanism for overloaded errors"""
    retry_count = 0
    base_delay = 2  # Base delay in seconds
    
    while retry_count <= max_retries:
        try:
            headers = {
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            # Extract system message and user messages
            system_content = None
            user_messages = []
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                else:
                    user_messages.append(msg)
            
            # Construct data with top-level system parameter
            data = {
                "model": "claude-3-7-sonnet-20250219",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": user_messages
            }
            
            # Only add system parameter if a system message was provided
            if system_content:
                data["system"] = system_content
            
            response = requests.post(
                ANTHROPIC_API_URL,
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                error_message = "Unknown API error"
                should_retry = False
                
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_type = error_json.get("error", {}).get("type", "unknown_error")
                        if error_type == "overloaded_error":
                            error_message = "Claude's servers are currently overloaded. Please try again in a few minutes."
                            should_retry = True
                        else:
                            error_message = error_json.get("error", {}).get("message", "API error")
                except:
                    pass
                
                print(f"API error: {response.status_code}, {response.text}")
                
                if should_retry and retry_count < max_retries:
                    retry_count += 1
                    # Calculate exponential backoff with jitter
                    delay = base_delay * (2 ** retry_count) + random.uniform(0, 1)
                    print(f"Retrying in {delay:.2f} seconds (attempt {retry_count}/{max_retries})...")
                    time.sleep(delay)
                    continue
                    
                return {"error": error_message}
            
            return response.json()
            
        except Exception as e:
            print(f"Error calling Anthropic API: {e}")
            retry_count += 1
            
            if retry_count <= max_retries:
                delay = base_delay * (2 ** retry_count) + random.uniform(0, 1)
                print(f"Retrying in {delay:.2f} seconds (attempt {retry_count}/{max_retries})...")
                time.sleep(delay)
            else:
                return {"error": f"Failed to connect to Claude API after {max_retries} attempts: {str(e)}"}
    
    # If we get here, all retries failed
    return {"error": "Failed to connect to Claude API after multiple attempts"}

def get_embeddings(texts: List[str]) -> Optional[List[np.ndarray]]:
    """Generate embeddings for a list of texts"""
    model = get_embedding_model()
    if not model:
        return None
    
    try:
        with torch.no_grad():
            embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None

def calculate_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    return float(np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2)))

def fetch_bible_references(verses: List[Dict[str, str]]) -> List[str]:
    """Fetch relevant Bible references for a set of verses
    
    Args:
        verses: List of verse objects with book, chapter, verse, and text fields
        
    Returns:
        List of relevant Bible passages and commentaries
    """
    # This would typically connect to a Bible API or database
    # For now, we'll return a simplified response
    references = []
    
    # Mock implementation - in a real app, fetch from a Bible API
    for verse in verses:
        verse_ref = f"{verse['book']} {verse['chapter']}:{verse['verse']}"
        references.append(f"Reference for {verse_ref}: Sample commentary text.")
    
    return references

def generate_verse_insights(
    verses: List[Dict[str, str]],
    verse_notes: List[Dict[str, str]],
    chapter_note: Dict[str, str],
    ai_preferences: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate insights on Bible verses using user notes and RAG
    
    Args:
        verses: List of verse objects with book, chapter, verse, and text
        verse_notes: List of user notes for individual verses
        chapter_note: User's note for the entire chapter
        ai_preferences: User's AI preferences:
            - model_temperature: Controls randomness (0-1)
            - response_length: Desired length of response
            - writing_style: 'academic', 'casual', or 'devotional' style
            - preferred_topics: List of topics to focus on
            - challenge_level: How much to challenge user assumptions (0-1)
            - depth_level: 'beginner', 'intermediate', or 'scholarly' content depth
            - time_orientation: Historical vs modern focus (0-1)
            - user_context: User-specific information for personalization
        
    Returns:
        Dictionary with generated insights
    """
    try:
        if not ANTHROPIC_API_KEY:
            return {"error": "ANTHROPIC_API_KEY not set in environment variables"}
        
        # Extract preferences
        writing_style = ai_preferences.get('writing_style', 'devotional')
        response_length = ai_preferences.get('response_length', 4000)
        # Always set a minimum response_length to avoid truncation
        if response_length < 8000:
            response_length = 8000
        preferred_topics = ai_preferences.get('preferred_topics', [])
        challenge_level = ai_preferences.get('challenge_level', 0.5)
        depth_level = ai_preferences.get('depth_level', 'intermediate')
        time_orientation = ai_preferences.get('time_orientation', 0.5)
        user_context = ai_preferences.get('user_context', {})
        model_temperature = ai_preferences.get('model_temperature', 0.7)
        
        # Get chapter reference
        chapter_ref = f"{verses[0]['book']} {verses[0]['chapter']}"
        
        # Prepare the verses text
        verses_text = ""
        for verse in verses:
            verses_text += f"{verse['verse']}: {verse['text']}\n"
        
        # Prepare user notes
        notes_text = ""
        if verse_notes:
            notes_text = "User's verse notes:\n"
            for note in verse_notes:
                notes_text += f"{note['book']} {note['chapter']}:{note['verse']} - {note['content']}\n"
        
        # Add chapter note if available
        chapter_note_text = ""
        if chapter_note and 'content' in chapter_note and chapter_note['content']:
            chapter_note_text = f"User's chapter note: {chapter_note['content']}\n"
        
        # Construct prompt components based on preferences
        historical_focus = "Focus more on historical context and original meaning." if time_orientation < 0.3 else ""
        modern_focus = "Focus more on modern application and relevance today." if time_orientation > 0.7 else ""
        
        # Depth level instructions
        depth_instructions = ""
        if depth_level == "beginner":
            depth_instructions = "Keep explanations simple and accessible for someone new to Bible study."
        elif depth_level == "intermediate":
            depth_instructions = "Provide moderate depth suitable for someone familiar with Bible study."
        else:  # scholarly
            depth_instructions = "Include scholarly insights and detailed analysis for advanced Bible students."
        
        # Challenge level instructions
        challenge_instructions = ""
        if challenge_level > 0.7:
            challenge_instructions = "Challenge common assumptions and present alternative viewpoints."
        
        # Topics focus
        topics_instruction = ""
        if preferred_topics:
            topics_instruction = f"Focus on these topics: {', '.join(preferred_topics)}."
        
        # Writing style
        style_instruction = f"Write in a {writing_style} style."
        
        # User context for personalization
        personalization = ""
        if user_context:
            user_context_str = ", ".join([f"{k}: {v}" for k, v in user_context.items()])
            personalization = f"Personalize the response for someone who: {user_context_str}."
        
        # Construct the system prompt
        system_message = f"""You are a thoughtful Bible study assistant that provides insights on scripture passages. 
Analyze the Bible chapter and generate insightful commentary.
{style_instruction} {depth_instructions} {historical_focus} {modern_focus} {challenge_instructions} {topics_instruction} {personalization}
IMPORTANT: Always provide complete, well-structured responses. Never leave thoughts or paragraphs unfinished."""

        # Construct the user prompt
        user_message = f"""Please provide insights on {chapter_ref}.

Bible text:
{verses_text}

{notes_text}
{chapter_note_text}

Generate a cohesive analysis that draws connections between verses and highlights key themes and applications.
Aim for around {response_length} characters, but you MUST complete your thoughts properly.
It is CRUCIAL that you do not cut your response off mid-thought or mid-sentence. Always finish your complete analysis.
Make sure all your sections and paragraphs are properly completed.
Your response must be complete and well-structured with a proper conclusion."""

        # Call Claude API
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Calculate appropriate max tokens based on response_length
        # Use a high fixed value to ensure we get complete responses
        max_tokens = 20000
        
        claude_response = call_anthropic_api(
            messages=messages,
            max_tokens=max_tokens,
            temperature=model_temperature
        )
        
        # Check if there was an error from the API call
        if claude_response and "error" in claude_response:
            return {"error": claude_response["error"]}
        
        if not claude_response or "content" not in claude_response:
            return {"error": "Failed to generate insights from Claude API"}
        
        # Extract insights from Claude's response
        insights = claude_response["content"][0]["text"]
        
        result = {
            "chapter_reference": chapter_ref,
            "insights": insights,
            "verse_count": len(verses),
            "note_count": len(verse_notes) + (1 if chapter_note and 'content' in chapter_note else 0),
            "preferences_used": {
                "writing_style": writing_style,
                "depth_level": depth_level,
                "challenge_level": challenge_level,
                "time_orientation": time_orientation,
                "response_length": response_length,
                "personalized": bool(user_context)
            }
        }
        
        return result
        
    except Exception as e:
        print(f"Error generating insights: {e}")
        return {"error": f"Failed to generate insights: {str(e)}"} 