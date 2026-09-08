import argparse
import os
import unittest
from unittest.mock import patch
from model_config import add_model_arguments, create_model


class ModelConfigTests(unittest.TestCase):
    def arguments(self, *extra):
        parser = argparse.ArgumentParser()
        add_model_arguments(parser)
        return parser.parse_args(["--model", "example-model", *extra])

    def test_default_preserves_bedrock(self):
        with patch("strands.models.BedrockModel") as provider:
            create_model(self.arguments())
        self.assertEqual(provider.call_args.kwargs, {
            "model_id": "example-model", "region_name": "ap-southeast-2",
            "max_tokens": 1500, "temperature": 0})

    def test_gateway_uses_environment_key_and_bounded_requests(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}), \
                patch("strands.models.openai.OpenAIModel") as provider:
            create_model(self.arguments("--base-url", "http://localhost:9020/v1"))
        options = provider.call_args.kwargs
        self.assertEqual(options["client_args"], {
            "api_key": "test-only", "base_url": "http://localhost:9020/v1",
            "timeout": 90, "max_retries": 0})
        self.assertFalse(options["stream"])
        self.assertEqual(options["params"], {"max_tokens": 1500})

    def test_missing_key_fails_before_provider_construction(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch("strands.models.openai.OpenAIModel") as provider:
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                create_model(self.arguments("--base-url", "http://localhost:9020/v1"))
            provider.assert_not_called()
