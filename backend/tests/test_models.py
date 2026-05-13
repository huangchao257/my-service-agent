from app.models import Agent, Conversation, Message, LLMProvider


def test_agent_creation():
    agent = Agent(name="Test", model="gpt-4o", tools=[], temperature=0.7)
    assert agent.name == "Test"
    assert agent.model == "gpt-4o"
    assert agent.tools == []
    assert agent.temperature == 0.7


def test_conversation_fields():
    conv = Conversation(title="Hello")
    assert conv.title == "Hello"


def test_message_roles():
    msg = Message(role="user", content="hi")
    assert msg.role == "user"
    assert msg.content == "hi"


def test_provider_models():
    p = LLMProvider(name="OpenAI", provider="openai", api_base="https://api.openai.com/v1", api_key="sk-test", models=["gpt-4o"], is_active=True)
    assert p.models == ["gpt-4o"]
    assert p.is_active is True