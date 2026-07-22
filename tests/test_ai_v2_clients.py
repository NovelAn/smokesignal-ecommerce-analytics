from types import SimpleNamespace

from backend.ai.deepseek_client import DeepSeekClient
from backend.ai.minimax_client import MiniMaxClient


class RecordingCompletions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"events": []}'))]
        )


def configured(client_type, model_attribute):
    client = client_type.__new__(client_type)
    completions = RecordingCompletions()
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    setattr(client, model_attribute, "test-model")
    return client, completions


def test_minimax_v2_call_has_no_fixed_max_tokens():
    client, completions = configured(MiniMaxClient, "model")

    assert client.analyze_v2("prompt") == '{"events": []}'
    assert "max_tokens" not in completions.kwargs
    assert completions.kwargs["temperature"] == 0.2


def test_deepseek_v2_call_uses_chat_model():
    client, completions = configured(DeepSeekClient, "model_chat")

    assert client.analyze_v2("prompt") == '{"events": []}'
    assert completions.kwargs["model"] == "test-model"
