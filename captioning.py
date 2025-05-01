import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Tone descriptions for the prompt
TONE_DESCRIPTIONS = {
    "friendly": "warm, approachable, and conversational",
    "professional": "formal, precise, and informative",
    "casual": "relaxed, simple, and everyday language",
    "enthusiastic": "excited, energetic, and positive",
    "thoughtful": "reflective, nuanced, and detailed",
    "humorous": "funny, light-hearted, and playful"
}

# Prompt template
TEMPLATE = """
You are a helpful assistant.
Caption the image at "{image_path}"
in a {tone} tone, focusing on objects and background.
Keep the description concise but informative (1-2 sentences).
Make it ready for Instagram Post, try adding some hashtags.
"""

# LLM and chain are initialized on first use
_llm = None
_chain = None


def _initialize_llm():
    """Initialize the LLM and chain on first use"""
    global _llm, _chain

    try:
        from langchain_ollama import OllamaLLM
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        # Initialize LLM with llava2 model
        logger.info("Initializing Ollama LLM with llava model")
        _llm = OllamaLLM(model="llava:latest", verbose=False)

        # Create prompt template
        prompt = PromptTemplate(input_variables=["image_path", "tone"], template=TEMPLATE)

        # Create chain
        _chain = prompt | _llm | StrOutputParser()
        logger.info("LLM and chain initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing LLM: {str(e)}")
        raise


def generate_caption(image_path: str, tone: str = "friendly") -> str:
    """
    Generate a caption for the image using the specified tone.

    Args:
        image_path: Path to the image file
        tone: Tone for the caption (friendly, professional, casual, etc.)

    Returns:
        Generated caption string
    """
    global _llm, _chain

    # Initialize LLM if not already initialized
    if _llm is None or _chain is None:
        _initialize_llm()

    # Get the detailed tone description or use the tone itself if not found
    tone_description = TONE_DESCRIPTIONS.get(tone, tone)

    try:
        logger.info(f"Generating caption for {image_path} with tone {tone}")

        # Run the chain
        result = _chain.invoke({"image_path": image_path, "tone": tone_description})

        # Clean up the result
        caption = result.strip()
        logger.info(f"Caption generated successfully: {caption[:50]}...")

        return caption

    except ConnectionError as e:
        logger.error(f"Connection error with Ollama: {str(e)}")
        return "Unable to connect to Ollama for caption generation. Please ensure Ollama is running with the llava:latest model installed."
    except Exception as e:
        logger.error(f"Error generating caption: {str(e)}")
        # Return a fallback message
        return "Unable to generate caption. The image enhancement was successful, but caption generation failed. Check if Ollama is installed and running with llava:latest model."