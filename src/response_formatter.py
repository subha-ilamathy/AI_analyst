#!/usr/bin/env python3
"""Response formatter using OpenAI LLM for natural language output."""

import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class FormattedResponse:
    """Structured response from the formatter."""
    formatted_text: str
    error: Optional[str] = None


def is_configured() -> bool:
    """Check if OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))


def format_response_natural(
    query: str,
    raw_result: str,
    context: Optional[Dict[str, Any]] = None
) -> FormattedResponse:
    """
    Format a raw result into natural language using OpenAI LLM.
    
    Args:
        query: The original user query
        raw_result: The raw result from the system
        context: Optional context information (time window, etc.)
    
    Returns:
        FormattedResponse with natural language text or error
    """
    if not is_configured():
        return FormattedResponse(
            formatted_text=raw_result,
            error="OpenAI API key not configured. Using raw result."
        )
    
    try:
        import openai
        
        # Build context string
        context_str = ""
        if context:
            if context.get("time_window"):
                context_str += f"Time window: {context['time_window']}\n"
            if context.get("metric"):
                context_str += f"Metric: {context['metric']}\n"
        
        # Create the prompt
        prompt = f"""You are an AI analyst helping users understand email campaign data. 
Convert the raw result into a natural, conversational response that directly answers the user's question.

User Question: "{query}"

Context:
{context_str}

Raw Result: {raw_result}

Please provide a natural, conversational response that:
1. Directly answers the user's question
2. Uses natural language (not technical jargon)
3. Includes relevant numbers and insights
4. Is concise but informative
5. Sounds like a helpful analyst explaining the data

Response:"""

        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful email campaign analyst who explains data in natural, conversational language."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        formatted_text = response.choices[0].message.content.strip()
        
        return FormattedResponse(formatted_text=formatted_text)
        
    except Exception as e:
        return FormattedResponse(
            formatted_text=raw_result,
            error=f"Error formatting response: {str(e)}"
        )


def format_error_natural(error_message: str, query: str) -> str:
    """
    Format error messages into natural language.
    
    Args:
        error_message: The technical error message
        query: The original user query
    
    Returns:
        Natural language error message
    """
    if not is_configured():
        return f"I encountered an issue: {error_message}"
    
    try:
        import openai
        
        prompt = f"""You are a helpful AI analyst. The user asked: "{query}"
But there was an error: {error_message}

Please provide a friendly, natural explanation of what went wrong and suggest what the user can try instead.

Response:"""

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful email campaign analyst who explains errors in friendly, natural language."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"I encountered an issue: {error_message}"
