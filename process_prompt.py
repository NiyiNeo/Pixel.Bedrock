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
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

    if not FILENAME:
        raise ValueError("❌ FILENAME environment variable is required.")
    if not S3_BUCKET_BETA or not S3_BUCKET_PROD:
        raise ValueError("❌ Both pixel.br.beta and pixel.br.prod must be set.")

    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    bedrock_client = boto3.client('bedrock-runtime', region_name=AWS_REGION)

    S3_BUCKET = S3_BUCKET_BETA if DEPLOY_ENV == 'beta' else S3_BUCKET_PROD

    # Define paths
    prompts_dir = Path('prompts')
    templates_dir = Path('prompt_templates')
    outputs_dir = Path('outputs')
    outputs_dir.mkdir(exist_ok=True)

    json_path = prompts_dir / f"{FILENAME}.json"
   
    # Load JSON config
    with json_path.open('r', encoding='utf-8') as f:
        prompt_data = json.load(f)
    
    template_file = prompt_data.get('template_file')
    if not template_file:
        raise ValueError("❌ template_file is missing in JSON config.")

    template_path = templates_dir / template_file

    # Load template and render
    with template_path.open('r', encoding='utf-8') as f:
        template = Template(f.read())

    rendered_prompt = template.render(**prompt_data['variables'])

    # Construct the Bedrock request body
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

    #Call Bedrock
    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(construct_body(rendered_prompt))
    )

    response_body = json.loads(response['body'].read()) 
    print ("Bedrock response:", json.dumps(response_body, indent=2))

    #Extract output text
    output_text = response_body.get('content', [{}])[0].get('text', 'No response.')

    #Timestamp & output filenames 
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    html_filename = f"{FILENAME}_{DEPLOY_ENV}_{timestamp}.html"
    md_filename = f"{FILENAME}_{DEPLOY_ENV}_{timestamp}.md"

    html_path = outputs_dir / html_filename
    md_path = outputs_dir / md_filename

    # Save outputs
    html_path.write_text(f"<html><body><pre>{output_text}</pre></body></html>", encoding='utf-8')
    md_path.write_text(output_text, encoding='utf-8')

    # Upload to S3
    s3_client.upload_file(str(html_path), S3_BUCKET, f"{DEPLOY_ENV}/outputs/{html_filename}")
    s3_client.upload_file(str(md_path), S3_BUCKET, f"{DEPLOY_ENV}/outputs/{md_filename}")

    print(f"✅ Uploaded to S3 bucket '{S3_BUCKET}' in folder '{DEPLOY_ENV}/outputs/'")
    print(f"📄 HTML: {html_filename}")
    print(f"📄 Markdown: {md_filename}")

if __name__ == "__main__":
    main()
