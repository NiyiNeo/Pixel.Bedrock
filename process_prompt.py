import boto3
import os
import json
from pathlib import Path
from jinja2 import Template

# Constants
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

def construct_body(prompt: str, max_tokens: int = 300) -> dict:
    """Build the Bedrock request body with minimal Human: prefix."""
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

def main():
    # Environment Variables
    S3_BUCKET_BETA = os.getenv("S3_BUCKET_BETA")
    S3_BUCKET_PROD = os.getenv("S3_BUCKET_PROD")
    DEPLOY_ENV = os.getenv("DEPLOY_ENV", "beta")
    FILENAME = os.getenv("FILENAME")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

    if not FILENAME:
        raise ValueError("❌ FILENAME must be set as an environment variable.")
    
    S3_BUCKET = S3_BUCKET_BETA if DEPLOY_ENV == "beta" else S3_BUCKET_PROD
    if not S3_BUCKET:
        raise ValueError(f"❌ S3 bucket for environment {DEPLOY_ENV} not defined.")

    # Clients
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    # Directories
    prompts_dir = Path("prompts")
    templates_dir = Path("prompt_templates")
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)

    # Load JSON config
    json_path = prompts_dir / f"{FILENAME}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        prompt_data = json.load(f)

    # Resolve template dynamically based on json
    template_name = prompt_data.get("template_file", "welcome_email.txt")
    template_path = templates_dir / template_name
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    # Render draft email
    template = Template(template_content)
    rendered_prompt = template.render(**prompt_data["variables"])
    print("✅ Rendered draft:")
    print(rendered_prompt)

    # Call Claude
    body = construct_body(rendered_prompt)
    response = bedrock_client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body)
    )

    response_body = json.loads(response["body"].read())
    final_output = response_body["content"][0]["text"].strip()
    print("✅ Claude response:")
    print(final_output)

    # Output filenames
    html_filename = f"{FILENAME}_{DEPLOY_ENV}.html"
    md_filename = f"{FILENAME}_{DEPLOY_ENV}.md"

    html_path = outputs_dir / html_filename
    md_path = outputs_dir / md_filename

    # Save files
    html_content = f"""
    <html>
    <head><title>Welcome</title></head>
    <body>
    <pre>{final_output}</pre>
    </body>
    </html>
    """

    html_path.write_text(html_content.strip(), encoding="utf-8")
    md_path.write_text(final_output, encoding="utf-8")

    print("✅ Files written:", html_path, md_path)

    # Upload to S3
    s3_client.upload_file(
        str(html_path),
        S3_BUCKET,
        f"{DEPLOY_ENV}/outputs/{html_filename}",
        ExtraArgs={"ContentType": "text/html"}
    )

    s3_client.upload_file(
        str(md_path),
        S3_BUCKET,
        f"{DEPLOY_ENV}/outputs/{md_filename}",
        ExtraArgs={"ContentType": "text/markdown"}
    )

    print(f"✅ Uploaded to S3: `{S3_BUCKET}/{DEPLOY_ENV}/outputs/`")
    print(f"📄 HTML: {html_filename}")
    print(f"📄 Markdown: {md_filename}")

if __name__ == "__main__":
    main()












