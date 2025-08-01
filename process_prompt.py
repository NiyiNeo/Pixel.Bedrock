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

    S3_BUCKET = S3_BUCKET_BETA if DEPLOY_ENV == 'beta' else S3_BUCKET_PROD

    # AWS clients
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)

    # Paths
    prompts_dir = Path('prompts')
    templates_dir = Path('prompt_templates')
    outputs_dir = Path('outputs')
    outputs_dir.mkdir(exist_ok=True)

    # Load JSON
    json_path = prompts_dir / f'{FILENAME}.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Load template
    template_path = templates_dir / 'welcome_email.txt'
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Render draft prompt
    template = Template(template_content)
    rendered_prompt = template.render(**config['variables'])

    print("✅ Rendered draft prompt:")
    print(rendered_prompt)

    # Call Bedrock
    body = construct_body(rendered_prompt)

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )

    response_body = json.loads(response['body'].read())
    print("✅ Bedrock response:")
    print(json.dumps(response_body, indent=2))

    # Extract response text
    final_output = response_body['content'][0]['text'].strip()

    # Determine output filenames
    output_file_template = config.get("output_file", f"{FILENAME}_{DEPLOY_ENV}.html")
    html_filename = Template(output_file_template).render(**config['variables'])
    md_filename = html_filename.replace('.html', '.md')

    html_path = outputs_dir / html_filename
    md_path = outputs_dir / md_filename

    # Wrap the output in valid HTML
    html_content = f"""
    <html>
    <head><title>Welcome</title></head>
    <body>
    <pre>{final_output}</pre>
    </body>
    </html>
    """

    html_path.write_text(html_content.strip(), encoding='utf-8')
    md_path.write_text(final_output, encoding='utf-8')

    print("✅ Files written locally:", html_path, md_path)

    # Upload to S3
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














