import os
from unittest.mock import patch, MagicMock
from stupify_phi.ai_redactor import AIRedactor

@patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
@patch("stupify_phi.ai_redactor.OpenAI")
def test_redact_text_success(mock_openai_class):
    mock_client = MagicMock()
    mock_response = MagicMock()

    mock_choice = MagicMock()
    mock_choice.message.content = "Redacted text"
    mock_response.choices = [mock_choice]

    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_class.return_value = mock_client

    redactor = AIRedactor()
    result = redactor.redact_text("Patient John Doe visited the ER.")
    assert result == "Redacted text"
