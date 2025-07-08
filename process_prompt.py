import boto3
import os
import json
from datetime import datetime
from pathlib import Path
from jinja2 import Template


def main():
    # Load environment variables
    S3_BUCKET_BETA = os.getenv('S3_BUCKET_BETA')
    S3_BUCKET_PROD = os.getenv('S3_BUCKET_PROD')
    DEPLOY_ENV = os.getenv('DEPLOY_ENV', 'beta')
    FILENAME = os.getenv('FILENAME')
    TEMPLATE_NAME = os.getenv('TEMPLATE_NAME', 'welcome_email.txt')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

    if not FILENAME:
        raise ValueError("❌ FILENAME environment variable is required.")
    if not S3_BUCKET_BETA or not S3_BUCKET_PROD:
        raise ValueError("❌ Both S3_BUCKET_BETA and S3_BUCKET_PROD must be set.")
    
    # Select the correct bucket
    S3_BUCKET = S3_BUCKET_BETA if DEPLOY_ENV == 'beta' else S3_BUCKET_PROD

    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)

    # Define paths
    prompts_dir = Path('prompts')
    templates_dir = Path('prompt_templates')
    outputs_dir = Path('outputs')
    outputs_dir.mkdir(exist_ok=True)

    json_path = prompts_dir / f"{FILENAME}.json"
    template_path = templates_dir / TEMPLATE_NAME

    # Read the JSON config
    with json_path.open('r', encoding='utf-8') as f:
        config = json.load(f)

    # Verify JSON structure
    if 'variables' not in config or 'template_file' not in config:
        raise ValueError("❌ JSON file is missing required keys: 'template_file' or 'variables'.")

    variables = config['variables']

    # Read the Jinja2 template
    with template_path.open('r', encoding='utf-8') as f:
        template = Template(f.read())

    # Render the prompt
    rendered_prompt = template.render(**variables)

    if not rendered_prompt.strip():
        raise ValueError("❌ Rendered prompt is empty — check your template and variables.")

    # Construct the Bedrock body
    def construct_body(prompt: str, max_tokens: int = 2000) -> dict:
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": f"Human: {prompt}"
                }
            ]
        }

    request_body = construct_body(rendered_prompt)

    # Call Bedrock Claude
    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body)
    )

    response_body = json.loads(response['body'].read())

    print("✅ Bedrock response:")
    print(json.dumps(response_body, indent=2))

    # Extract the response text
    output_text = response_body.get('content', [{}])[0].get('text', 'No response.')

    # Prepare output filenames
    html_filename = f"{FILENAME}_{DEPLOY_ENV}_{timestamp}.html"
    md_filename = f"{FILENAME}_{DEPLOY_ENV}_{timestamp}.md"

    html_path = outputs_dir / html_filename
    md_path = outputs_dir / md_filename

    # Save outputs locally
    html_path.write_text(
        f"<html><body><pre>{output_text}</pre></body></html>", encoding='utf-8'
    )
    md_path.write_text(output_text, encoding='utf-8')

    # Upload to S3 with structured prefix
    s3_html_key = f"{DEPLOY_ENV}/outputs/{html_filename}"
    s3_md_key = f"{DEPLOY_ENV}/outputs/{md_filename}"

    s3_client.upload_file(str(html_path), S3_BUCKET, s3_html_key)
    s3_client.upload_file(str(md_path), S3_BUCKET, s3_md_key)

    print(f"✅ Uploaded to S3 bucket '{S3_BUCKET}' in folder '{DEPLOY_ENV}/outputs/'")
    print(f"📄 HTML: {s3_html_key}")
    print(f"📄 Markdown: {s3_md_key}")


if __name__ == "__main__":
    main()
