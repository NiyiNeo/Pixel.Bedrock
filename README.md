**##📄 Pixel Learning AI Email Pipeline**
This project automates the generation  human-like emails to students using Amazon Bedrock (Claude), GitHub Actions, and S3 Static Website Hosting.
Emails are rendered from templates & JSON configs, rewritten by Claude via Bedrock, and deployed to S3 buckets (Beta & Prod) as static websites — triggered by GitHub PRs and merges.

**##🚀 Features**
Render email drafts with Jinja2 templates & JSON configs.
Rewrite drafts using Claude in Amazon Bedrock.
Deploy Beta environment on pull request (on_pull_request.yml).
Deploy Production environment on merge (on_merge.yml).
View hosted outputs in S3 static website URLs.

**🔧 AWS Setup**
1️⃣ S3 Buckets
Create two S3 buckets:
pixel.br.beta → for Beta environment
pixel.br.prod → for Production
Enable Static Website Hosting for both buckets.
Allow public read access:
Uncheck Block all public access.

Add this bucket policy (replace your-bucket-name):


**2️⃣ IAM**
Create an IAM user or role with permissions:
AmazonS3FullAccess
AmazonBedrockFullAccess
Generate AWS access keys for this user.

**3️⃣ Amazon Bedrock**
Ensure your AWS account has access to Claude 3 (Sonnet) in Bedrock.
Check in AWS Console → Bedrock → Models that anthropic.claude-3-sonnet is available in your region (e.g., us-east-1).

**🔑 GitHub Secrets**
Set the following secrets in your repository settings:
Secret	Description
AWS_ACCESS_KEY_ID	IAM user access key
AWS_SECRET_ACCESS_KEY	IAM user secret
AWS_REGION	AWS region (e.g., us-east-1)
S3_BUCKET_BETA	Beta bucket name
S3_BUCKET_PROD	Production bucket name
FILENAME	JSON config filename (without .json)

**📝 Templates & Configs:**
Template (prompt_templates/welcome_email.txt)
Hello {{ student_name }},

Congratulations on completing {{ course_module }}!

Here’s a summary of your achievements:
- {{ goal1 }}
- {{ goal2 }}
- {{ goal3 }}

Keep up the excellent work!


Config (prompts/welcome_prompt.json)
{
  "output_file": "welcome_{{student_name|lower}}.html",
  "variables": {
    "student_name": "Jordan",
    "course_module": "AWS Cloud Fundamentals",
    "goal1": "Launched and configured an EC2 instance",
    "goal2": "Hosted a static website on S3",
    "goal3": "Set up IAM roles and policies"
  }
}

**🔄 Workflows**
Beta Deployment
Trigger: Pull Request
Workflow: .github/workflows/on_pull_request.yml
Deploys to pixel.br.beta
Production Deployment
Trigger: Merge to main
Workflow: .github/workflows/on_merge.yml
Deploys to pixel.br.prod

Each workflow:
✅ Checks out code
✅ Configures AWS credentials
✅ Installs dependencies (boto3, jinja2)
✅ Runs process_prompt.py

**🌐 View the Emails**
Once deployed:
Beta:
http://pixel.br.beta.s3-website-us-east-1.amazonaws.com
Production:
http://pixel.br.prod.s3-website-us-east-1.amazonaws.com

**📄 Notes**
Ensure FILENAME secret matches your JSON file name (welcome_prompt.json → FILENAME=welcome_prompt).
Outputs (.html and .md) are saved to outputs/ locally and uploaded to S3.
Claude rewrites the drafts to sound human, warm, and encouraging.

🧪 Contributing
To update the README:
✅ Make your changes in a branch.
✅ Open a Pull Request.
✅ Once reviewed & approved, merge into main.
