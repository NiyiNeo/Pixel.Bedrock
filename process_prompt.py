import boto3
import os
import json
from pathlib import Path
from jinja2 import Template

def construct_body(prompt: str, max_tokens: int = 300) -> dict:
    """
    Build the request body for Amazon Bedrock Claude with required Human: prefix.
    """
    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": (
                    f"""Human: You are a professional instructor at Pixel Learning Company.
Your task is to rewrite the following draft email to the student naturally, warmly, and professionally — as if written by a human instructor. 
Do NOT mention anything about being an AI, model, or assistant. 
Focus only on encouraging the student and clearly communicating the draft content below.

Draft:
{prompt}
"""
                )
            }
        ]
    }

def main():
    # Load environment variables
    S3_BUCKET_BETA = os.getenv('S3_BUCKET_BETA')
    S3_BUCKET_PROD = os.getenv('S3_BUCKET_PROD')
    DEPLOY_ENV = os.getenv('DEPLOY_ENV', 'beta')
    FILENAME = os.getenv('FILENAME')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

    if not FILENAME:
        raise ValueError("FILENAME must be set as an environment variable.")

    # Select target bucket
    S3_BUCKET = S3_BUCKET_BETA if DEPLOY_ENV == 'beta' else S3_BUCKET_PROD

    # AWS clients
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)

    # Directories
    prompts_dir = Path('prompts')
    templates_dir = Path('prompt_templates')
    outputs_dir = Path('outputs')
    outputs_dir.mkdir(exist_ok=True)

    # Load JSON prompt data
    json_path = prompts_dir / f'{FILENAME}.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        prompt_data = json.load(f)

    # Load template
    template_path = templates_dir / prompt_data['template_file']
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Render Jinja2 template
    template = Template(template_content)
    rendered_prompt = template.render(**prompt_data['variables'])

    print("✅ Rendered Prompt:")
    print(rendered_prompt)

    # Call Bedrock
    request_body = construct_body(rendered_prompt)
    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body)
    )

    response_body = json.loads(response['body'].read())
    print("✅ Bedrock response:")
    print(json.dumps(response_body, indent=2))

    # Extract output text
    completion_text = response_body['content'][0]['text']

    # Save outputs
    html_filename = f"{FILENAME}_{DEPLOY_ENV}.html"
    md_filename = f"{FILENAME}_{DEPLOY_ENV}.md"

    html_path = outputs_dir / html_filename
    md_path = outputs_dir / md_filename

    html_content = f"""
    <html>
    <head><title>Welcome</title></head>
    <body>
    <pre>{completion_text}</pre>
    </body>
    </html>
    """.strip()

    html_path.write_text(html_content, encoding='utf-8')
    md_path.write_text(completion_text, encoding='utf-8')

    print("✅ Files written locally:", html_path, md_path)

    # Upload to S3 with proper Content-Type
    s3_client.upload_file(
        str(html_path),
        S3_BUCKET,
        f"{DEPLOY_ENV}/outputs/{html_filename}",
        ExtraArgs={'ContentType': 'text/html'}
    )

    s3_client.upload_file(
        str(md_path),
        S3_BUCKET,
        f"{DEPLOY_ENV}/outputs/{md_filename}",
        ExtraArgs={'ContentType': 'text/markdown'}
    )

    print(f"✅ Uploaded to S3 bucket `{S3_BUCKET}` in `{DEPLOY_ENV}/outputs/`")
    print(f"📄 HTML: {html_filename}")
    print(f"📄 Markdown: {md_filename}")

if __name__ == "__main__":
    main()










