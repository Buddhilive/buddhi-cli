import os
import sys
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class LiteRTEngine:
    def __init__(self, model_path: str):
        """Initialize the LiteRT-LM model engine."""
        self.model_path = model_path
        self.llm = None
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}. Please download the model first.")
            
        self._initialize_model()

    def _initialize_model(self):
        """Load the LiteRT model with GPU optimization if available."""
        try:
            # Note: The exact import depends on litert-lm-api version
            # Usually it's in ai_edge_litert.genai or litert_lm_api
            import litert_lm_api as litert
        except ImportError:
            logger.error("litert-lm-api is not installed.")
            raise
            
        logger.info(f"Loading LiteRT-LM model from {self.model_path}...")
        
        # Check for GPU
        # This is a conceptual check. LiteRT often handles it via backend flags or automatically.
        use_gpu = False
        try:
            import tensorflow as tf
            if tf.config.list_physical_devices('GPU'):
                use_gpu = True
        except ImportError:
            pass

        logger.info(f"Hardware acceleration: {'GPU' if use_gpu else 'CPU'}")
        
        # Initialize model (Conceptual litert-lm-api)
        # Assuming typical kwargs for hardware backend and options
        # We pass use_gpu flag and enable Multi-Token Prediction if supported by API.
        try:
            self.llm = litert.LLM(
                model_path=self.model_path,
                use_gpu=use_gpu,
                enable_multi_token_prediction=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise
            
        logger.info("LiteRT-LM engine initialized successfully.")

    def generate(self, messages: List[Dict[str, Any]], stream: bool = False, **kwargs) -> Any:
        """
        Generate a response for the given messages.
        Supports multi-modal inputs if included in messages.
        """
        if not self.llm:
            raise RuntimeError("Model engine is not initialized.")
            
        # Map OpenAI style messages to LiteRT format
        # litert_lm_api generally expects a formatted prompt string or specific message list.
        # Here we assume it has a chat interface or we format it.
        
        if stream:
            return self._generate_stream(messages, **kwargs)
        return self._generate_sync(messages, **kwargs)

    def _generate_sync(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """Synchronous generation."""
        # This is a placeholder for actual litert-lm-api call
        # e.g., response = self.llm.chat(messages, **kwargs)
        # return response.text
        try:
            # Assuming self.llm.chat or self.llm.generate exists
            response = self.llm.chat(messages=messages, **kwargs)
            return response.text if hasattr(response, "text") else str(response)
        except AttributeError:
            # Fallback formatting if it only accepts strings
            prompt = self._format_messages_to_prompt(messages)
            return self.llm.generate(prompt, **kwargs)

    def _generate_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Streaming generation."""
        # Yield tokens as they are generated
        try:
            for chunk in self.llm.chat_stream(messages=messages, **kwargs):
                yield chunk.text if hasattr(chunk, "text") else str(chunk)
        except AttributeError:
            prompt = self._format_messages_to_prompt(messages)
            for chunk in self.llm.generate_stream(prompt, **kwargs):
                yield chunk

    def _format_messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Basic formatter for models if direct message list is not supported."""
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Model: {content}\n"
        prompt += "Model: "
        return prompt
