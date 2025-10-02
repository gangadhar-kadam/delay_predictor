from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="delay_predictor",
    version="1.0.0",
    author="Gangadhar Kadam",
    author_email="email.kadam@gmail.com",
    description="AI-powered production delay prediction system for ERPNext",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gangadharkadam/delay_predictor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "production": [
            "gunicorn>=20.1.0",
            "psutil>=5.9.0",
            "supervisor>=4.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "delay-predictor=delay_predictor.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "delay_predictor": [
            "custom/*.json",
            "public/js/*.js",
            "public/css/*.css",
            "templates/*.html",
        ],
    },
    zip_safe=False,
)
