#!/usr/bin/env bash
# Build and push the Lambda image with AWS CodeBuild instead of GitHub
# Actions (fallback for GitHub outages). Builds the committed HEAD of the
# current branch and tags the image with its commit hash, like CI does.
#
#   infrastructure/codebuild/build.sh            # build HEAD
#   infrastructure/codebuild/build.sh --setup    # one-time: create role + project
set -euo pipefail

REGION=${AWS_REGION:-us-east-1}
PROJECT=bet-hope-image-build
ROLE=bet-hope-codebuild
REPO=bet-hope-web
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET=$(aws s3api list-buckets --query "Buckets[?starts_with(Name,'aws-sam-cli-managed-default-samclisourcebucket')].Name | [0]" --output text)
KEY=codebuild/bet-hope-backend.zip
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
export AWS_PAGER=""

if [ "${1:-}" = "--setup" ]; then
  aws iam create-role --role-name $ROLE --assume-role-policy-document '{
    "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"codebuild.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam put-role-policy --role-name $ROLE --policy-name bet-hope-codebuild --policy-document "{
    \"Version\":\"2012-10-17\",\"Statement\":[
      {\"Effect\":\"Allow\",\"Action\":[\"logs:CreateLogGroup\",\"logs:CreateLogStream\",\"logs:PutLogEvents\"],
       \"Resource\":\"arn:aws:logs:$REGION:$ACCOUNT:log-group:/aws/codebuild/$PROJECT*\"},
      {\"Effect\":\"Allow\",\"Action\":\"ecr:GetAuthorizationToken\",\"Resource\":\"*\"},
      {\"Effect\":\"Allow\",\"Action\":[\"ecr:BatchCheckLayerAvailability\",\"ecr:InitiateLayerUpload\",\"ecr:UploadLayerPart\",
        \"ecr:CompleteLayerUpload\",\"ecr:PutImage\",\"ecr:BatchGetImage\",\"ecr:GetDownloadUrlForLayer\"],
       \"Resource\":\"arn:aws:ecr:$REGION:$ACCOUNT:repository/$REPO\"},
      {\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:GetObjectVersion\"],\"Resource\":\"arn:aws:s3:::$BUCKET/$KEY\"}]}"
  echo "Waiting for the new role to propagate..."; sleep 15
  aws codebuild create-project --name $PROJECT --region $REGION \
    --source "type=S3,location=$BUCKET/$KEY,buildspec=buildspec.yml" \
    --artifacts type=NO_ARTIFACTS \
    --environment "type=LINUX_CONTAINER,image=aws/codebuild/standard:7.0,computeType=BUILD_GENERAL1_MEDIUM,privilegedMode=true" \
    --service-role "arn:aws:iam::$ACCOUNT:role/$ROLE" --timeout-in-minutes 30 \
    --logs-config "cloudWatchLogs={status=ENABLED}" --query 'project.name' --output text
  aws logs put-retention-policy --log-group-name /aws/codebuild/$PROJECT --retention-in-days 14 2>/dev/null \
    || aws logs create-log-group --log-group-name /aws/codebuild/$PROJECT && \
       aws logs put-retention-policy --log-group-name /aws/codebuild/$PROJECT --retention-in-days 14
  echo "Setup done."
  exit 0
fi

TAG=$(git -C "$ROOT" rev-parse HEAD)
git -C "$ROOT" diff --quiet HEAD -- backend || echo "WARNING: backend/ has uncommitted changes; building the COMMITTED version ($TAG)"
TMP=$(mktemp -d)
# Exactly the committed backend tree + the buildspec (respects .dockerignore at build time)
git -C "$ROOT" archive --format=zip -o "$TMP/src.zip" HEAD:backend
(cd "$HERE" && zip -q "$TMP/src.zip" buildspec.yml)
aws s3 cp "$TMP/src.zip" "s3://$BUCKET/$KEY" --only-show-errors
rm -rf "$TMP"

BUILD=$(aws codebuild start-build --project-name $PROJECT --region $REGION \
  --environment-variables-override "name=IMAGE_TAG,value=$TAG" --query 'build.id' --output text)
echo "Started $BUILD (image tag $TAG)"
until STATUS=$(aws codebuild batch-get-builds --ids "$BUILD" --query 'builds[0].buildStatus' --output text) && [ "$STATUS" != IN_PROGRESS ]; do sleep 15; done
echo "Build $STATUS"
[ "$STATUS" = SUCCEEDED ] && echo "IMAGE_URI=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/$REPO:$TAG"
[ "$STATUS" = SUCCEEDED ]
