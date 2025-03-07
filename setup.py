from setuptools import setup, find_packages

setup(
    name="discourse-bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "httpx",
        "python-dotenv",
        "pydantic",
        "google-generativeai",
        "google-cloud-aiplatform",
    ],
)
