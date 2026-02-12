"""Unit tests for template rendering compatibility."""

from app.core.template_renderer import TemplateRenderer


def test_render_supports_double_single_and_dollar_braces():
    renderer = TemplateRenderer()
    template = "A={{amount}} B={amount} C=${amount}"
    rendered = renderer.render(template, {"amount": 100})
    # ${amount} regex consumes the $ sign — the entire ${amount} is replaced with the value
    assert rendered == "A=100 B=100 C=100"


def test_render_strips_unresolved_placeholders():
    renderer = TemplateRenderer()
    template = "Hello {name}, your balance is {balance}"
    rendered = renderer.render(template, {"name": "Juan"})
    assert rendered == "Hello Juan, your balance is "
    assert "{balance}" not in rendered


def test_render_supports_nested_keys():
    renderer = TemplateRenderer()
    template = "Recipient: {recipient.name}"
    rendered = renderer.render(template, {"recipient": {"name": "Maria"}})
    assert rendered == "Recipient: Maria"
