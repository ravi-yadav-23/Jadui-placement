import os
import google.generativeai as genai
from app.core.config import settings
from typing import Optional

# Initialize the Gemini client configuration once.
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

def get_gemini_model(
    model_name: Optional[str] = None, 
    temperature: Optional[float] = None, 
    max_output_tokens: Optional[int] = None
) -> genai.GenerativeModel:
    """
    Returns a configured Gemini GenerativeModel instance.
    """
    name = model_name or settings.GEMINI_MODEL
    
    # Setup generation config if specified
    gen_cfg = {}
    if temperature is not None:
        gen_cfg["temperature"] = temperature
    if max_output_tokens is not None:
        gen_cfg["max_output_tokens"] = max_output_tokens
        
    return genai.GenerativeModel(
        name,
        generation_config=gen_cfg if gen_cfg else None
    )

def generate_text(
    prompt: str,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None
) -> str:
    """
    Convenience method to generate text directly from a prompt.
    """
    model = get_gemini_model(model_name, temperature, max_output_tokens)
    response = model.generate_content(prompt)
    return response.text

async def generate_text_async(
    prompt: str,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_output_tokens: Optional[int] = None
) -> str:
    """
    Convenience method to generate text asynchronously from a prompt.
    """
    model = get_gemini_model(model_name, temperature, max_output_tokens)
    response = await model.generate_content_async(prompt)
    return response.text
