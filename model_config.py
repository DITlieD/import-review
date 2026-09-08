"""Shared model configuration for single imports and inbox processing."""
import os


def add_model_arguments(parser):
    parser.add_argument("--model", required=True)
    parser.add_argument("--region", default="ap-southeast-2")
    parser.add_argument("--base-url", help="OpenAI-compatible gateway; requires OPENAI_API_KEY")


def create_model(args):
    if args.base_url:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY is required for --base-url")
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": key, "base_url": args.base_url,
                         "timeout": 90, "max_retries": 0},
            model_id=args.model, stream=False, params={"max_tokens": 1500})
    from strands.models import BedrockModel
    return BedrockModel(model_id=args.model, region_name=args.region,
                        max_tokens=1500, temperature=0)
