mkdir build

cp lambda_function.py build
cp ksp_utils.py build
cp aws_helpers.py build

(
  cd build || exit
  pip install --target . -r ../requirements.txt
  zip -r -u ../terraform/lambda.zip ./*
)
rm -rf build

(
  cd terraform || exit
  terraform apply -auto-approve
  rm -rf lambda.zip
)

aws --profile dantelore s3 cp data/example_input.sfs s3://dantelore.ksp/input/example_input.sfs

aws --profile dantelore s3 cp index.html s3://dantelore.com/ksp/index.html
aws --profile dantelore s3 cp --recursive content s3://dantelore.com/ksp/content
