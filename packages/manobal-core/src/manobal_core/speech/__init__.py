"""Server-side speech-to-text. The device never holds a vendor key."""

from manobal_core.speech.deepgram import transcribe_audio

__all__ = ["transcribe_audio"]
