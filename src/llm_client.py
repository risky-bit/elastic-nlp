"""
vLLM API client for MOI Elasticsearch NLP Query System

Handles all vLLM API operations: model verification, DSL generation.
Follows constitution principles: modular architecture, timeout handling, error categorization.
"""

import requests
from typing import Optional, Dict, Any
from requests.exceptions import ConnectionError, Timeout, RequestException


class VLLMClient:
    """
    vLLM API client wrapper (OpenAI-compatible).

    Provides clean interface for:
    - Model availability verification
    - Query DSL generation via chat completions endpoint
    - Timeout and error handling

    Following constitution: Module exposes public methods only, handles connection failures gracefully
    """

    def __init__(self, config):
        """
        Initialize vLLM API client.

        Args:
            config: Config instance with vLLM connection details

        Following constitution: API endpoint versioned (v1)
        """
        self.config = config
        self.base_url = config.VLLM_URL
        self.model = config.VLLM_MODEL
        self.default_temperature = config.LLM_TEMPERATURE
        self.default_max_tokens = config.LLM_MAX_TOKENS

    def verify_model(self) -> bool:
        """
        Verify that the vLLM server is responding and model is loaded.

        Returns:
            bool: True if server is available, False otherwise

        Following constitution: Verify model availability (FR-002)
        """
        try:
            # Check if API is responsive by calling models endpoint
            response = requests.get(
                f'{self.base_url}/models',
                timeout=5
            )

            if response.status_code == 200:
                return True
            else:
                return False

        except (ConnectionError, Timeout):
            return False
        except Exception:
            return False

    def generate_dsl(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 30
    ) -> str:
        """
        Generate Query DSL using vLLM chat completions endpoint.

        Args:
            prompt: Full prompt with index mapping and NL query
            temperature: Sampling temperature (default: from config, 0.1 for deterministic)
            max_tokens: Maximum response tokens (default: from config, 500)
            timeout: Request timeout in seconds (default: 30s per constitution)

        Returns:
            str: Generated Query DSL as text

        Raises:
            ConnectionError: If vLLM server is unreachable
            Timeout: If request times out
            RequestException: For other API errors

        Following constitution: LLM API call (FR-006), 30-second timeout, temperature/max_tokens logging
        """
        # Use provided values or defaults from config
        temp = temperature if temperature is not None else self.default_temperature
        tokens = max_tokens if max_tokens is not None else self.default_max_tokens

        # Construct request payload (OpenAI-compatible chat format)
        # vLLM uses chat completions, so wrap prompt in messages array
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': temp,
            'max_tokens': tokens,
        }

        try:
            # POST to /v1/chat/completions endpoint
            response = requests.post(
                f'{self.base_url}/chat/completions',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=timeout
            )

            # Check response status
            response.raise_for_status()

            # Parse response
            result = response.json()

            # Extract generated text from choices[0].message.content
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0].get('message', {})
                generated_text = message.get('content', '')
                # Strip chat end tokens that some models append (e.g. <|im_end|>)
                for token in ['<|im_end|>', '<|endoftext|>', '</s>', '<|end|>']:
                    generated_text = generated_text.replace(token, '')
                return generated_text.strip()
            else:
                raise RequestException("Invalid response format from vLLM API")

        except Timeout as e:
            raise Timeout(
                f"vLLM API request timed out after {timeout}s. "
                f"Model inference may be slow. Check vLLM server status."
            ) from e

        except ConnectionError as e:
            raise ConnectionError(
                f"Failed to connect to vLLM server at {self.base_url}. "
                f"Ensure vLLM is running with {self.model} model loaded.\n"
                f"Start vLLM with: vllm serve \"{self.model}\""
            ) from e

        except RequestException as e:
            # Catch other request errors (4xx, 5xx, etc.)
            raise RequestException(
                f"vLLM API error: {str(e)}"
            ) from e

    def test_connection(self) -> bool:
        """
        Test connection to vLLM API.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = requests.get(
                f'{self.base_url}/models',
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


# Backward compatibility alias (for any code referencing LMStudioClient)
LMStudioClient = VLLMClient
