import base64
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Default neural voice matching Gemini Live warm conversational persona
DEFAULT_VOICE = "en-US-AvaMultilingualNeural"
MALE_VOICE = "en-US-AndrewMultilingualNeural"


async def generate_neural_audio(
    text: str,
    voice: str = DEFAULT_VOICE,
) -> Optional[str]:
    """
    Generates high-fidelity neural speech audio (MP3) matching Gemini Live prosody.
    Returns base64-encoded MP3 data for instant HTML5 Audio playback.
    """
    if not text or not text.strip():
        return None

    try:
        import edge_tts

        # Clean text for spoken human prosody
        clean = re.sub(r"[\*\#\_\[\]\(\)\<\>]", "", text)
        clean = re.sub(r"AED\s*(\d+(?:\.\d+)?)", r"\1 dirhams", clean, flags=re.I)
        clean = re.sub(r"(\d+(?:\.\d+)?)\s*AED", r"\1 dirhams", clean, flags=re.I)
        clean = re.sub(r"(\d+)\s*kg\b", r"\1 kilograms", clean, flags=re.I)
        clean = re.sub(r"(\d+)\s*g\b", r"\1 grams", clean, flags=re.I)
        clean = clean.replace("KON Commerce", "Kon Commerce")
        clean = clean.replace("unit(s)", "")

        communicate = edge_tts.Communicate(
            clean.strip(),
            voice=voice,
            rate="+4%",
            pitch="+2Hz",
        )
        data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data += chunk["data"]

        if data:
            return base64.b64encode(data).decode("utf-8")
    except Exception as e:
        logger.warning(f"Neural TTS generation fallback: {e}")

    return None

