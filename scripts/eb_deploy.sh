#!/usr/bin/env bash

AWS_REGION=${AWS_REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
EB_APP_NAME=${EB_APP_NAME}
EB_ENV_NAME=${EB_ENV_NAME}
BUNDLEUP_API_DOCKER_TAG=${BUNDLEUP_API_DOCKER_TAG:-latest}
BUNDLEUP_API_DOCKER_IMAGE="${BUNDLEUP_API_DOCKER_IMAGE}"
EASYPOST_API_KEY_PROD=${EASYPOST_API_KEY_PROD}

EB_BUCKET="elasticbeanstalk-${AWS_REGION}-${AWS_ACCOUNT_ID}"

APP_RELEASE_VERSION=$(date '+%s')
ZIP=app-$APP_RELEASE_VERSION.zip

CUR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "${CUR_DIR}/elastic_beanstalk"

rm -rf deploy_dir
mkdir -p deploy_dir
cd deploy_dir

if [ -d "../.ebextensions" ]; then
    cp -rp ../.ebextensions .
fi

cat ../Dockerrun.aws.json \
    |jq ".containerDefinitions=([.containerDefinitions[] | if .image == \"app_image_placeholder\" then .image = \"${BUNDLEUP_API_DOCKER_IMAGE}:${BUNDLEUP_API_DOCKER_TAG}\" else . end])" \
    | tee Dockerrun.aws.json


zip -r ${ZIP} Dockerrun.aws.json .ebextensions

S3_REGION=$(aws s3api get-bucket-location --bucket ${EB_BUCKET} | jq -r '.LocationConstraint')
if [ "${S3_REGION}" == "null" ]; then
    S3_REGION=us-east-1
fi

echo "copy ${ZIP} to s3://${EB_BUCKET}/${EB_APP_NAME}/${EB_ENV_NAME}/${ZIP}"
aws s3 cp ${ZIP} s3://${EB_BUCKET}/${EB_APP_NAME}/${EB_ENV_NAME}/${ZIP} \
    --region ${S3_REGION}

echo "Create a new application version with the zipped up Dockerrun file"
aws elasticbeanstalk create-application-version \
    --no-auto-create-application \
    --application-name ${EB_APP_NAME} \
    --version-label $APP_RELEASE_VERSION \
    --source-bundle S3Bucket=$EB_BUCKET,S3Key=${EB_APP_NAME}/${EB_ENV_NAME}/${ZIP} \
    --region ${AWS_REGION}

echo "Update the environment to use the new application version"
aws elasticbeanstalk update-environment \
    --application-name ${EB_APP_NAME} \
    --environment-name ${EB_ENV_NAME} \
    --version-label $APP_RELEASE_VERSION \
    --region ${AWS_REGION}
