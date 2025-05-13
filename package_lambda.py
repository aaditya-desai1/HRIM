#!/usr/bin/env python3
"""
Package Lambda functions for deployment to AWS.

This script packages Lambda functions by:
1. Creating a temp directory
2. Copying the Lambda code
3. Creating a zip file
4. Moving the zip file to the Lambda function directory
"""

import os
import sys
import shutil
import tempfile
import zipfile
import subprocess
import argparse

def package_lambda(function_name):
    """
    Package a Lambda function with its dependencies.
    
    Args:
        function_name: Name of the Lambda function (directory name)
    """
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lambda_dir = os.path.join(base_dir, "src", "lambda", function_name)
    target_zip = os.path.join(lambda_dir, "lambda_function.zip")
    utils_file = os.path.join(base_dir, "src", "lambda", "utils.py")
    
    # Check if the Lambda function directory exists
    if not os.path.isdir(lambda_dir):
        print(f"Error: Lambda function directory not found: {lambda_dir}")
        return False
    
    # For generate_pdf function, use Docker to package with compatible dependencies
    if function_name == "generate_pdf":
        return package_with_docker(function_name, lambda_dir, target_zip, utils_file)
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        
        # Copy Lambda function code
        shutil.copy(os.path.join(lambda_dir, "lambda_function.py"), temp_dir)
        print(f"Copied lambda_function.py to temp directory")
        
        # Copy utils module if it exists
        if os.path.exists(utils_file):
            shutil.copy(utils_file, temp_dir)
            print(f"Copied utils.py to temp directory")
        
        # Install function-specific dependencies
        if function_name == "call_gemini":
            print("Installing requests library for call_gemini function...")
            subprocess.run(
                ["pip", "install", "requests", "--target", temp_dir],
                check=True,
                stdout=subprocess.DEVNULL
            )
        
        # Create a zip file
        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add all files in the temp directory to the zip
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    print(f"Adding {arcname} to zip")
                    zipf.write(file_path, arcname)
        
        print(f"Created Lambda package: {target_zip}")
        
    return True

def package_with_docker(function_name, lambda_dir, target_zip, utils_file):
    """
    Package a Lambda function using Docker to ensure compatibility with Lambda runtime.
    
    Args:
        function_name: Name of the Lambda function
        lambda_dir: Path to the Lambda function directory
        target_zip: Path to the target zip file
        utils_file: Path to the utils.py file
        
    Returns:
        bool: True if packaging succeeded, False otherwise
    """
    print(f"Packaging {function_name} with Docker to ensure compatibility...")
    
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Copy Lambda function code to temp directory
        shutil.copy(os.path.join(lambda_dir, "lambda_function.py"), temp_dir)
        
        # Copy utils module if it exists
        if os.path.exists(utils_file):
            shutil.copy(utils_file, temp_dir)
            print(f"Copied utils.py to temp directory")
        
        # Create a requirements.txt file
        requirements_path = os.path.join(temp_dir, "requirements.txt")
        if function_name == "generate_pdf":
            with open(requirements_path, 'w') as f:
                f.write("markdown==3.5\n")
                f.write("xhtml2pdf==0.2.11\n")
                f.write("Pillow==10.0.0\n")  # Specify a stable version of Pillow
        
        # Create a Dockerfile
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write("""FROM public.ecr.aws/lambda/python:3.11

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY utils.py ${LAMBDA_TASK_ROOT}/
COPY requirements.txt .

RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

CMD ["lambda_function.lambda_handler"]
""")
        
        # Check if Docker is installed
        try:
            subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Error: Docker is not installed or not running. Please install Docker to package this function.")
            return False
        
        # Build the Docker image
        print("Building Docker image for Lambda compatibility...")
        subprocess.run(
            ["docker", "build", "-t", f"lambda-{function_name}", temp_dir],
            check=True
        )
        
        # Create a container and copy the package
        container_id = subprocess.run(
            ["docker", "create", f"lambda-{function_name}"],
            check=True, stdout=subprocess.PIPE
        ).stdout.decode('utf-8').strip()
        
        package_dir = os.path.join(temp_dir, "package")
        os.makedirs(package_dir, exist_ok=True)
        
        # Extract the Lambda package from the container
        subprocess.run(
            ["docker", "cp", f"{container_id}:/var/task/.", package_dir],
            check=True
        )
        
        # Remove the container
        subprocess.run(["docker", "rm", container_id], check=True)
        
        # Create the zip file
        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    print(f"Adding {arcname} to zip")
                    zipf.write(file_path, arcname)
        
        print(f"Created Lambda package: {target_zip}")
        return True
        
    except Exception as e:
        print(f"Error packaging with Docker: {str(e)}")
        return False
    finally:
        # Clean up
        shutil.rmtree(temp_dir)

def package_all_lambdas():
    """Package all Lambda functions."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lambda_dir = os.path.join(base_dir, "src", "lambda")
    
    # Get all directories in the Lambda directory
    lambda_functions = [
        d for d in os.listdir(lambda_dir)
        if os.path.isdir(os.path.join(lambda_dir, d)) and d != "__pycache__"
    ]
    
    print(f"Found {len(lambda_functions)} Lambda functions: {', '.join(lambda_functions)}")
    
    # Package each Lambda function
    for function_name in lambda_functions:
        print(f"\nPackaging Lambda function: {function_name}")
        if package_lambda(function_name):
            print(f"Successfully packaged Lambda function: {function_name}")
        else:
            print(f"Failed to package Lambda function: {function_name}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Package Lambda functions for deployment.")
    parser.add_argument("--function", help="Name of the Lambda function to package")
    parser.add_argument("--all", action="store_true", help="Package all Lambda functions")
    
    args = parser.parse_args()
    
    if args.function:
        package_lambda(args.function)
    elif args.all:
        package_all_lambdas()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 